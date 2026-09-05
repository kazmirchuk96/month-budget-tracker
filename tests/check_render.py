from playwright.sync_api import sync_playwright
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
import sys

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':420,'height':1400}, device_scale_factor=2)
    errors = []
    page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto('file://' + str(BASE_DIR / 'budget-tracker.html'))
    page.wait_for_timeout(1500)
    page.screenshot(path='screenshot_full.png', full_page=True)
    print("CONSOLE ERRORS:", errors)
    # quick sanity: check hero num text exists
    hero = page.query_selector('.hero-num')
    print("Hero text:", hero.inner_text() if hero else None)
    browser.close()
