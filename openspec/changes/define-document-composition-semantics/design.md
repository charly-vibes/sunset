# Design: minimal categorical semantics for document descriptions

## 1. Two categories, not one
1. **Schema**: a small category `K` of types and functional reference arrows, with a document instance `I: K -> FinSet`. Non-functional relationships are **reified spans**, e.g. `Region <- Membership -> View` and `Region <- Support -> Claim`. A single region can participate in multiple views.
2. **Transformations**: a distinct category (or effectful composition setting) of typed partial mappings between conforming instances. Use explicitly declared domains/scopes; errors and unknowns are not successful arrows. Composition requires matching interfaces and compatible scopes, and has identity/associativity only where defined.
3. **Part assembly** is **not** morphism composition. It is a partial operation on region sets, declared bindings, and order constraints. Model its domain and laws rather than calling it a categorical coproduct without proof.

## 2. Assembly
A view-local assembly `A ⊕_v B` combines region identities and declared typed edges **only when** their namespace, boundary contracts, containment and ordering constraints are jointly satisfiable. Shared IDs designate the **same** region, not duplicate copies. If those shared IDs carry contradictory intrinsic claims, fail with a witness. Do not force an order between otherwise unrelated parts. The empty assembly is the identity **modulo canonical representation**. Associativity holds for triples that are jointly compatible and whose combined constraints do not depend on assembly grouping; composition failing at one bracket grouping while succeeding at the other is an implementation bug. A separately declared reading order is generally noncommutative. The union of claims does not imply that composed meaning is the union of text interpretations.

## 3. Hierarchies and views
Views are named scoped relationships. A `contains` relation is acyclic and antisymmetric inside a *hierarchical view*, with root policy explicit. Multiple named views can share nodes and disagree without forcing one canonical hierarchy. Nonhierarchical edges (`continues`, `references`, `captionOf`) are not converted into parent pointers. View projection/restriction retains identities and exactly those edges whose endpoints belong to the projection; it reports omitted membership and evidence. Refinement must not silently retract observable established edges; conflict or explicit supersession is required. Partial reading order is represented by a DAG; a linearization is an explicitly labeled choice, not a fact about the document.

## 4. Geometry
Spatial anchors are **typed and scoped**: `pdf-page` (declared page box, units, origin, rotation/transform), `image-pixel` (dimension and origin), `epub-dom` (spine resource + selector, not global XY), and transient `viewport` (render context pinned). Relations such as above/overlap are derived only when operands share a compatible frame or an explicit transform. The outcome of such a predicate is `true | false | unknown` with reason; no invention based on disjoint or incomparable frames. Rendered positions are not semantic identity. Native PDF text/image/vector observations and OCR may coexist on the same page without duplication claims.

## 5. Scoped meaning
Annotations are claims with explicit `target`, `predicate`, `value`, `authority/evidence`, and status; they do not become true merely because they are inside a region. Scope rules specify **which context bindings are available**, and whether a binding is inherited, shadowed, disputed, or unavailable. A parent author attribution does not automatically apply to quotations or nested works. A publication issue date may be available as *publication context*, but is not a poem's narrated date without a domain rule. Combining contexts from two views retains contradictions, never arbitrarily chooses a winner. Interpretation is a deterministic function of pinned observation bundle, descriptor/ruleset, version and scope to a result including uncertainty or conflict. Meaning propagation is NOT free-form natural-language inference.

## 6. Preservation and falsification
A transformation advertises observable set `O`. A preservation claim is `obs_O(f(x)) ~_O obs_O(x)` under a declared equivalence, not an unconditional PDF=EPUB equality. A counterexample is source + minimal affected IDs + rule + expected/actual + dependent versions and loss metadata. `text-only` flattening cannot preserve column-based debit/credit meaning without supplementary layout evidence. Comparison verdicts include `pass`, `fail`, `unknown`, `not-applicable`; `unknown` cannot pass a strict policy.

## 7. Architectural guardrails
- Keep six core primitives; add typed vocabularies/laws, not runtime classes for each mathematical abstraction.
- No mandatory total order, single document tree, global coordinate space, or universal semantic inheritance.
- Prefer schema and compatibility checks executable over very broad prose.
- Wild's assembly compatibility/certification pattern informs *verification discipline*, not the actual document semantics.
- Specodelic's Intent/Constraints/Model/Properties is a specification format; prose predicates still need separate executable checkers.

## 8. Mapping into existing Sunset
Before integrating, inspect current DSC 0.3: determine how regions, views, geometry locators, evidence links, scope, and unknown outcomes are serialized. If fields already exist, standardize their laws without changing the wire schema. If not, document a narrowly scoped extension proposal and migration strategy. Do not silently introduce breaking changes.
