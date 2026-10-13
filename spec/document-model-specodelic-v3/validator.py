#!/usr/bin/env python3
"""DSC 0.2 descriptor reference validator (not a PDF/EPUB extractor)."""
import json, re, sys, unicodedata
from pathlib import Path
class Duplicate(Exception): pass
def load(path):
    def pairs(xs):
        out={}
        for k,v in xs:
            if k in out: raise Duplicate('duplicate_key')
            out[k]=v
        return out
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite')))
def canonical(x):
    return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
def validate(d):
    errors=set()
    def err(x): errors.add(x)
    def shape(obj,required,optional=()):
        if not isinstance(obj,dict):err('invalid_shape');return False
        if not set(required)<=set(obj) or set(obj)-set(required)-set(optional):err('invalid_shape');return False
        return True
    if not shape(d,['version','id','source','regions','contents','relations','annotations','evidence','vocabularies']):return ['invalid_shape']
    if d['version']!='0.2' or not isinstance(d['id'],str) or not d['id']:err('invalid_shape')
    if not shape(d['source'],['format','sha256','locator']):err('invalid_shape')
    else:
        if not isinstance(d['source']['format'],str) or not d['source']['format']:err('invalid_shape')
        if not isinstance(d['source']['sha256'],str) or not re.fullmatch('[0-9a-f]{64}',d['source']['sha256']):err('invalid_digest')
        if not isinstance(d['source']['locator'],str) or not d['source']['locator']:err('invalid_shape')
    for key in ['regions','contents','relations','annotations','evidence','vocabularies']:
        if not isinstance(d[key],list):return ['invalid_shape']
    ids={}; typed={};
    for key,required,opt in [('regions',['id','view','kind'],['geometry']),('contents',['id','kind','value'],[]),('relations',['id','kind','from','to'],[]),('annotations',['id','target','term','value','origin','status','evidence'],[]),('evidence',['id','origin','source_ref'],['transform'])]:
        for item in d[key]:
            if not shape(item,required,opt):continue
            i=item['id']
            if not isinstance(i,str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]*',i):err('invalid_id');continue
            if i in ids:err('duplicate_id')
            ids[i]=item;typed[i]=key
    for i in d['regions']:
        if not isinstance(i,dict) or 'id' not in i:continue
        if i.get('view') not in ['physical','logical']:err('invalid_view')
        if not isinstance(i.get('kind'),str) or not i['kind']:err('invalid_shape')
        if 'geometry' in i:
            g=i['geometry'];
            if not shape(g,['space','x','y','width','height']):continue
            if i.get('view')!='physical':err('logical_geometry')
            if not isinstance(g['space'],str) or not g['space']:err('invalid_geometry')
            for k in ['x','y','width','height']:
                if type(g[k]) is not int or g[k]<0:err('invalid_geometry')
    for i in d['contents']:
        if not isinstance(i,dict):continue
        if i.get('kind') not in ['text','image','number','structured','binary-reference'] or not isinstance(i.get('value'),str):err('invalid_content')
    graph={k:[] for k in ['contains','precedes','derived-from']};parents={}
    edges=set()
    rules={'contains':('regions','regions'),'precedes':('regions','regions'),'realizes':('regions','regions'),'has-content':('regions','contents'),'derived-from':('evidence','evidence')}
    for r in d['relations']:
        if not isinstance(r,dict):continue
        kind=r.get('kind');a=r.get('from');b=r.get('to')
        if kind not in rules:err('unknown_relation');continue
        if a not in typed or b not in typed:err('dangling_reference');continue
        if (typed[a],typed[b])!=rules[kind]:err('relation_type');continue
        if kind=='realizes' and not (ids[a].get('view')=='physical' and ids[b].get('view')=='logical'):err('relation_type')
        if (kind,a,b) in edges:err('duplicate_edge')
        edges.add((kind,a,b))
        if kind in graph:graph[kind].append((a,b))
        if kind=='contains':parents[b]=parents.get(b,0)+1
    def cycle(edges):
        adj={}
        for a,b in edges:adj.setdefault(a,[]).append(b)
        temp=set();done=set()
        def visit(x):
            if x in temp:return True
            if x in done:return False
            temp.add(x)
            if any(visit(y) for y in adj.get(x,[])):return True
            temp.remove(x);done.add(x);return False
        return any(visit(x) for x in adj)
    for kind,code in [('contains','containment_cycle'),('precedes','order_cycle'),('derived-from','lineage_cycle')]:
        if cycle(graph[kind]):err(code)
    roots=[r['id'] for r in d['regions'] if isinstance(r,dict) and 'id' in r and parents.get(r['id'],0)==0]
    if len(roots)!=1 or any(x>1 for x in parents.values()):err('containment_roots')
    vocabs=set()
    for v in d['vocabularies']:
        if shape(v,['namespace','version']):
            if not isinstance(v['namespace'],str) or not v['namespace'] or not isinstance(v['version'],str) or not v['version']:err('invalid_vocabulary')
            elif v['namespace'] in vocabs:err('duplicate_vocabulary')
            else:vocabs.add(v['namespace'])
    origins={'source','extracted','inferred','manual','external'}
    for e in d['evidence']:
        if not isinstance(e,dict):continue
        if e.get('origin') not in origins or not isinstance(e.get('source_ref'),str) or not e['source_ref']:err('invalid_evidence')
        if 'transform' in e:
            t=e['transform']
            if not shape(t,['id','version','config_sha256','dependencies']):continue
            if not all(isinstance(t.get(x),str) and t[x] for x in ['id','version']) or not isinstance(t.get('config_sha256'),str) or not re.fullmatch('[0-9a-f]{64}',t['config_sha256']):err('invalid_transform')
            if not isinstance(t.get('dependencies'),list) or not all(isinstance(x,str) for x in t['dependencies']):err('invalid_transform')
        elif e.get('origin') in ['extracted','inferred']:err('missing_transform')
    for a in d['annotations']:
        if not isinstance(a,dict):continue
        if typed.get(a.get('target')) not in ['regions','contents']:err('dangling_reference')
        term=a.get('term')
        if not isinstance(term,str) or ':' not in term or term.split(':',1)[0] not in vocabs:err('unknown_term')
        if a.get('origin') not in origins or a.get('status') not in ['supported','disputed','asserted_without_evidence'] or not isinstance(a.get('value'),str):err('invalid_annotation')
        ev=a.get('evidence')
        if not isinstance(ev,list):err('invalid_annotation');continue
        if any(typed.get(x)!='evidence' for x in ev):err('dangling_reference')
        if a.get('status')=='supported' and not ev:err('missing_support')
        if a.get('status')=='asserted_without_evidence' and ev:err('invalid_annotation')
    def check_values(x):
        if isinstance(x,str):
            if unicodedata.normalize('NFC',x)!=x:err('not_nfc')
        elif isinstance(x,dict):
            for k,v in x.items():
                if not k.isascii():err('non_ascii_key')
                check_values(v)
        elif isinstance(x,list):
            for v in x:check_values(v)
        elif x is None or isinstance(x,float) or isinstance(x,bool):err('invalid_scalar')
        elif not isinstance(x,int):err('invalid_scalar')
    check_values(d)
    return sorted(errors)
def main():
    if len(sys.argv)>1 and sys.argv[1]=='test':
        base=Path(__file__).parent/'fixtures';count=0
        for status in ('valid','invalid'):
            for p in sorted((base/status).glob('*.json')):
                errs=validate(load(p));expected=status=='invalid'
                assert bool(errs)==expected,(p,errs)
                if expected:
                    reason=json.loads((base/'expected.json').read_text()).get(p.name)
                    assert reason in errs,(p,reason,errs)
                else:
                    d=load(p); assert canonical(load(p))==canonical(json.loads(canonical(d)))
                count+=1
        print('PASS',count,'descriptor fixtures; this is not actual PDF/EPUB extraction conformance')
    else:
        p=sys.argv[1]
        try:result=validate(load(p))
        except (Duplicate,ValueError,json.JSONDecodeError,UnicodeError) as e: result=['parse_error:'+str(e)]
        print(json.dumps({'status':'invalid' if result else 'valid','reasons':result},sort_keys=True))
        if result:sys.exit(1)
if __name__=='__main__':main()
