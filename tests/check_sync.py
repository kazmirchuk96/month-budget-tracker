from playwright.sync_api import sync_playwright
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
import json

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':420,'height':1200}, device_scale_factor=2)
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))

    # In-memory fake Apps Script backend served from a route intercept.
    store = {}
    def handle_route(route):
        req = route.request
        url = req.url
        if req.method == 'GET':
            if 'action=getall' in url:
                route.fulfill(status=200, content_type='application/json', body=json.dumps({"items": store}))
                return
        if req.method == 'POST':
            body = json.loads(req.post_data)
            if body.get('action') == 'set':
                store[body['key']] = body['value']
            route.fulfill(status=200, content_type='application/json', body=json.dumps({"ok": True}))
            return
        route.fulfill(status=404, body='not found')

    page.route('https://fake-apps-script.example.com/exec**', handle_route)

    page.goto('file://' + str(BASE_DIR / 'budget-tracker.html'))
    page.wait_for_timeout(500)
    # Dismiss first-launch onboarding modal if present (fresh localStorage in this test)
    cancel_btn = page.query_selector('#app-modal-cancel')
    if cancel_btn and cancel_btn.is_visible():
        cancel_btn.click()
        page.wait_for_timeout(200)

    # Open settings, set sync URL, save.
    page.click('#menu-btn'); page.wait_for_timeout(150)
    page.click('#open-settings'); page.wait_for_timeout(200)
    page.fill('#set-sync-url', 'https://fake-apps-script.example.com/exec')
    page.click('#settings-save')
    page.wait_for_timeout(800)
    page.screenshot(path='screenshot_sync1.png')
    print("store after save:", list(store.keys()))

    # Enter today's actual to trigger a save+sync
    page.fill('.pill-input', '1500')
    page.locator('.pill-input').first.blur()
    page.wait_for_timeout(800)
    print("store after entry:", {k: (v[:60] if isinstance(v,str) else v) for k,v in store.items()})

    # Now reload page fresh (simulating a different device) - it should pull from remote store.
    page.evaluate("localStorage.clear()")
    page.reload()
    page.wait_for_timeout(1200)
    page.screenshot(path='screenshot_sync2.png')
    hero = page.query_selector('.pill-input')
    print("After reload (fresh localStorage) actual value in stepper:", hero.input_value() if hero else None)
    sync_badge = page.query_selector('#sync-badge')
    print("sync badge text:", sync_badge.inner_text() if sync_badge else None)

    print("ERRORS:", errors)
    browser.close()
