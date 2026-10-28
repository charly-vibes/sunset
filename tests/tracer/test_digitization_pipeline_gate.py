# Purpose: Verify the TDD/RO5U pipeline executes the document corpus quality gate.
# Responsibilities: Pin repository-appropriate ship oracle configuration and
#   prove the executable wrapper propagates real fixture success and failure.
# Rationale: sunset-0y1 replaces the inapplicable Cargo release oracle.
from pathlib import Path
import shutil
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parents[2]
ORACLE = ROOT / '.wai/resources/oracles/spec-corpus.sh'


def test_tdd_ro5_ship_gate_targets_spec_corpus():
    pipeline = tomllib.loads((ROOT / '.wai/resources/pipelines/tdd-ro5.toml').read_text())
    ship = next(step for step in pipeline['steps'] if step['id'] == 'ship-close')
    names = {oracle['name'] for oracle in ship['gate']['oracles']}
    assert 'spec-corpus' in names
    assert 'release-docs-fresh' not in names


def test_corpus_oracle_accepts_real_fixtures_and_rejects_a_broken_one(tmp_path):
    assert ORACLE.is_file(), 'repository-appropriate oracle is missing'
    bundle = ROOT / 'spec/document-model-specodelic-v3'
    shutil.copy(bundle / 'validator.py', tmp_path / 'validator.py')
    shutil.copytree(bundle / 'fixtures', tmp_path / 'fixtures')
    (tmp_path / 'justfile').write_text('spec-check:\n    python3 validator.py test\n')
    result = subprocess.run([str(ORACLE), 'unused-artifact'], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'PASS 11 descriptor fixtures' in result.stdout
    valid = next((tmp_path / 'fixtures/valid').glob('*.json'))
    valid.write_text('{}')
    result = subprocess.run([str(ORACLE), 'unused-artifact'], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode != 0, result.stdout + result.stderr
