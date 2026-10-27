# Purpose: Verify real-PDF composition reports retain partial human evidence.
# Responsibilities: Check assembly laws, source pins, and honest unknown/loss outcomes.
# Rationale: sunset-905.3 needs executed comparisons, not inferred conformance.
import json
import runpy
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / 'hitl/sunset-905.3/run_composition.py'


@pytest.fixture(scope='module')
def run(tmp_path_factory):
    runner = runpy.run_path(str(SCRIPT))
    out = tmp_path_factory.mktemp('returned-composition')
    result = runner['run'](REPO, out)
    return result, out


def test_real_pdf_parts_obey_laws_without_inventing_structure(run):
    result, out = run
    assert len(result['carriers']) == 3
    assert result['epub'] == 'owner-waived'
    assert result['real_carrier_conformance'] is False
    for carrier in result['carriers']:
        assert carrier['source_sha256']
        assert len(carrier['outputs']) == 2
        for output in carrier['outputs']:
            assert output['schema_errors'] == []
            assert output['canonical_readers_agree'] is True
            assert output['laws']['identity'] is True
            assert output['laws']['associativity'] is True
            assert output['laws']['records_preserved'] is True
            assert output['laws']['no_invented_relations'] is True
            assert (out / output['descriptor_path']).is_file()


def test_all_human_regions_remain_source_attributed_losses_not_false_matches(run):
    result, out = run
    total = 0
    for carrier in result['carriers']:
        for sheet in carrier['human_comparisons']:
            raw = json.loads((REPO / sheet['sheet_path']).read_text())
            assert sheet['sheet_sha256']
            assert sheet['reading_order']['class'] == 'UNKNOWN'
            assert len(sheet['region_geometry']) == len(raw['structure'])
            total += len(raw['structure'])
            for row, region in zip(sheet['region_geometry'], raw['structure']):
                assert row['page'] == region['page']
                assert row['bbox'] == region['bbox']
                assert row['class'] == 'LOSS'
                assert row['source_ref'].startswith('sha256:' + carrier['source_sha256'])
            for field in ('relations', 'annotations', 'losses', 'uncertainties'):
                assert sheet['sections'][field] == 'UNKNOWN'
    assert total == 203


def test_projection_refuses_new_geometry_instead_of_reporting_false_losses():
    runner = runpy.run_path(str(SCRIPT))
    sheet = {'structure': [], 'page_inventory': []}
    output = {'regions': [{'kind': 'page', 'geometry': {'x': 0}}], 'selectors': []}
    with pytest.raises(ValueError, match='source-frame mapping'):
        runner['compare_human'](sheet, 'f' * 64, [output, output])


def test_real_output_conflicts_have_finite_witnesses(run):
    result, _ = run
    for carrier in result['carriers']:
        for output in carrier['outputs']:
            refusal = output['injected_conflict']
            assert refusal['status'] == 'refused'
            assert refusal['rule'] == 'same_id_conflicting_claims'
            assert refusal['smallest']
