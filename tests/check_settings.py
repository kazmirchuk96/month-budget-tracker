from playwright.sync_api import sync_playwright
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':420,'height':900}, device_scale_factor=2)
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto('file://' + str(BASE_DIR / 'budget-tracker.html'))
    page.wait_for_timeout(600)
    # Dismiss first-launch onboarding modal if present (fresh localStorage in this test)
    cancel_btn = page.query_selector('#app-modal-cancel')
    if cancel_btn and cancel_btn.is_visible():
        cancel_btn.click()
        page.wait_for_timeout(200)
    page.click('#menu-btn')
    page.wait_for_timeout(200)
    page.click('#open-settings')
    page.wait_for_timeout(300)
    page.screenshot(path='screenshot_settings.png', full_page=False)
    print("ERRORS:", errors)
    browser.close()
