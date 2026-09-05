from playwright.sync_api import sync_playwright
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
import json

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 420, 'height': 1400}, device_scale_factor=2)
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto('file://' + str(BASE_DIR / 'budget-tracker.test.html'))
    page.wait_for_timeout(400)
    cb = page.query_selector('#app-modal-cancel')
    if cb and cb.is_visible(): cb.click(); page.wait_for_timeout(200)

    # Seed two past months with some entered days.
    page.evaluate("""
      async () => {
        var m1 = window.__test.ensureMonth('2026-06');
        m1.days['10'] = { actual: 1500 };
        m1.days['20'] = { actual: 800 };
        await window.__test.saveMonth('2026-06');
        var m2 = window.__test.ensureMonth('2026-07');
        m2.days['5'] = { actual: 3000 };
        await window.__test.saveMonth('2026-07');
      }
    """)
    page.reload()
    page.wait_for_timeout(500)
    cb = page.query_selector('#app-modal-cancel')
    if cb and cb.is_visible(): cb.click(); page.wait_for_timeout(200)

    nav_text = page.query_selector('#month-nav').inner_text()
    print('month-nav initial:', repr(nav_text))

    # Click '‹' (older) twice, expect Липень then Червень.
    page.click('#month-nav button >> nth=0')
    page.wait_for_timeout(600)
    print('after 1x ‹:', page.query_selector('#month-nav').inner_text().replace('\\n', ' '))
    months_list_visible = page.query_selector('#months-list').is_visible()
    print('months-list visible:', months_list_visible)

    page.click('#month-nav button >> nth=0')
    page.wait_for_timeout(600)
    print('after 2x ‹:', page.query_selector('#month-nav').inner_text().replace('\\n', ' '))

    # Click '›' (newer) to go back.
    page.click('#month-nav button >> nth=1')
    page.wait_for_timeout(600)
    print('after 1x ›:', page.query_selector('#month-nav').inner_text().replace('\\n', ' '))

    page.click('#month-nav button >> nth=1')
    page.wait_for_timeout(600)
    print('after 2x › (back to current):', page.query_selector('#month-nav').inner_text().replace('\\n', ' '))

    page.screenshot(path='check_monthnav.png', full_page=True)
    print('ERRORS:', errors)
    browser.close()
