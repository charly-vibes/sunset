"""Purpose: Exercise the offline reader's persistent workspace in a real browser.
Responsibilities: Verify layout, drawing continuity, editing, and step checkpoints.
Rationale: sunset-6ci fixes viewport resets and end-only file saving for readers.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / 'hitl/sunset-905.3'


@pytest.fixture
def reader_page():
    playwright = pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as runtime:
        try:
            browser = runtime.chromium.launch(headless=True)
        except playwright.Error as exc:
            pytest.skip(f'Chromium unavailable: {exc}')
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        page.goto((ROOT / 'templates/observations-spa.html').as_uri())
        page.locator('#welcomeStart').click()
        page.locator('#readerSel').select_option('reader-b')
        page.locator('#carrierSel').select_option('diario-de-poesia-excerpt')
        page.locator('#startReading').click()
        page.locator('#viewerBox input[type=file]').set_input_files(
            ROOT / 'bundle/carriers/diario-de-poesia-excerpt.pdf')
        page.wait_for_function('annPdf && annFrame(1) && document.querySelector("#viewerBox canvas")')
        yield page
        browser.close()


def test_workspace_keeps_page_and_scroll_when_drawing_editing_and_advancing(reader_page):
    page = reader_page
    viewer = page.locator('#viewerCard').bounding_box()
    fields = page.locator('main').bounding_box()
    assert viewer['x'] < fields['x']
    assert viewer['x'] + viewer['width'] <= fields['x'] + 2
    page.evaluate('showStep(3)')
    page.get_by_role('button', name='✏ Draw regions', exact=True).click()
    page.wait_for_function('document.querySelector("#viewerBox .ovl.draw")')
    page.evaluate('document.querySelector(".stage").scrollTop = 240; window.savedCanvas = document.querySelector(".stage canvas")')
    stage = page.locator('.stage').bounding_box()
    x, y = stage['x'] + 100, stage['y'] + 140
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 120, y + 100)
    page.mouse.up()
    assert page.evaluate('state.structure.length') == 1
    assert page.evaluate('document.querySelector(".stage").scrollTop') == 240
    assert page.evaluate('document.querySelector(".stage canvas") === window.savedCanvas')
    field = page.locator('#srow-0 input').first
    field.fill('My region')
    field.press('End')
    assert field.evaluate('(e) => e === document.activeElement')
    assert page.evaluate('document.querySelector(".stage").scrollTop') == 240
    page.locator('#srow-0 select').focus()
    page.locator('#srow-0 select').select_option('heading')
    assert page.locator('#srow-0 select').evaluate('(e) => e === document.activeElement')
    assert page.evaluate('document.querySelector(".stage canvas") === window.savedCanvas')
    with page.expect_download() as saved:
        page.locator('#secNext').click()
    snapshot = json.loads(Path(saved.value.path()).read_text())
    assert snapshot['structure'][0]['label'] == 'My region'
    assert snapshot['structure'][0]['type'] == 'heading'
    assert snapshot['structure'][0]['order_rank'] is None
    assert page.evaluate('document.querySelector(".stage canvas") === window.savedCanvas')
    assert page.evaluate('document.querySelector(".stage").scrollTop') == 240
    for step in range(4, 11):
        page.evaluate('(s) => showStep(s)', step)
        assert page.locator('#saveStep').is_visible()
        assert page.evaluate('document.querySelector(".stage canvas") === window.savedCanvas')
    assert not page.locator('#doneCarrier').is_enabled()
    page.set_viewport_size({'width': 600, 'height': 900})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
    assert page.locator('#viewerCard').is_visible()


def test_viewer_controls_do_not_replace_the_current_step_and_snapshots_resume(reader_page):
    page = reader_page
    page.get_by_role('button', name='Next page ▶', exact=True).click()
    page.wait_for_function('annPage === 2 && annFrame(2)')
    assert page.locator('#secTitle').inner_text() == page.evaluate('SECTION_TITLES.page_inventory')
    page.get_by_role('button', name='+', exact=True).click()
    page.wait_for_function('annZoom > 1 && document.querySelector(".stage canvas").width > 0')
    assert page.locator('#secTitle').inner_text() == page.evaluate('SECTION_TITLES.page_inventory')
    page.evaluate('showStep(3); state.structure.push({label:"",type:"",page:2,depth:0,bbox:null,evidence:"",order_rank:null,order_alternatives:[]}); renderSection("structure")')
    with page.expect_download() as saved:
        page.locator('#saveStep').click()
    snapshot = json.loads(Path(saved.value.path()).read_text())
    assert snapshot['structure'][0]['type'] == ''
    assert snapshot['structure'][0]['order_rank'] is None
    assert snapshot['page_frames']['2']
    page.evaluate('state.structure = []')
    assert page.evaluate('(obj) => importSheetObject(obj)', snapshot) is None
    assert page.evaluate('state.structure.length') == 1
    assert page.locator('#s-section').is_visible()
