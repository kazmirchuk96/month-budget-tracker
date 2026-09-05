from playwright.sync_api import sync_playwright
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
import json

with sync_playwright() as p:
    browser = p.chromium.launch()

    store = {}
    def handle_route(route):
        req = route.request
        url = req.url
        if req.method == 'GET' and 'action=getall' in url:
            route.fulfill(status=200, content_type='application/json', body=json.dumps({"items": store}))
            return
        if req.method == 'POST':
            body = json.loads(req.post_data)
            if body.get('action') == 'set':
                store[body['key']] = body['value']
            route.fulfill(status=200, content_type='application/json', body=json.dumps({"ok": True}))
            return
        route.fulfill(status=404, body='not found')

    # Device A: configure sync + enter an expense.
    ctxA = browser.new_context(viewport={'width':420,'height':1200})
    pageA = ctxA.new_page()
    pageA.route('https://fake-apps-script.example.com/exec**', handle_route)
    pageA.goto('file://' + str(BASE_DIR / 'budget-tracker.html'))
    pageA.wait_for_timeout(400)
    cancel_btn = pageA.query_selector('#app-modal-cancel')
    if cancel_btn and cancel_btn.is_visible():
        cancel_btn.click()
        pageA.wait_for_timeout(200)
    pageA.click('#menu-btn'); pageA.wait_for_timeout(150)
    pageA.click('#open-settings'); pageA.wait_for_timeout(200)
    pageA.fill('#set-sync-url', 'https://fake-apps-script.example.com/exec')
    pageA.click('#settings-save')
    pageA.wait_for_timeout(800)
    pageA.fill('.pill-input', '1500')
    pageA.locator('.pill-input').first.blur()
    pageA.wait_for_timeout(800)
    print("Store keys after device A:", list(store.keys()))
    d = json.loads(store['month:2026-08'])
    print("Device A day16 actual:", d['days'].get('16'))

    # Device B: brand-new browser context (empty storage), but user has pasted the SAME sync URL already
    # (simulating: they configured it once via settings before any data existed locally).
    ctxB = browser.new_context(viewport={'width':420,'height':1200})
    pageB = ctxB.new_page()
    pageB.route('https://fake-apps-script.example.com/exec**', handle_route)
    pageB.add_init_script("localStorage.setItem('fin-tracker:weburl','https://fake-apps-script.example.com/exec');")
    errorsB = []
    pageB.on('pageerror', lambda exc: errorsB.append(str(exc)))
    pageB.goto('file://' + str(BASE_DIR / 'budget-tracker.html'))
    pageB.wait_for_timeout(1500)
    stepper_val = pageB.locator('.pill-input').first.input_value()
    print("Device B stepper value after pull:", stepper_val)
    badge = pageB.query_selector('#sync-badge').inner_text()
    print("Device B sync badge (should be empty/done, not stuck):", repr(badge))
    print("Device B errors:", errorsB)

    # Verify device A's data was NOT clobbered by device B's initial load.
    d2 = json.loads(store['month:2026-08'])
    print("Store day16 actual AFTER device B loaded:", d2['days'].get('16'))

    pageB.screenshot(path='screenshot_deviceB.png')
    browser.close()
