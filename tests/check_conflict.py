from playwright.sync_api import sync_playwright
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
import json

# Fake backend shared in-memory store, simulating the Google Sheet.
STORE = {}

def handle_route(route):
    url = route.request.url
    if route.request.method == 'GET' and 'action=getall' in url:
        route.fulfill(status=200, content_type='application/json', body=json.dumps({'items': dict(STORE)}))
        return
    if route.request.method == 'POST':
        body = json.loads(route.request.post_data)
        if body.get('action') == 'set':
            STORE[body['key']] = body['value']
            route.fulfill(status=200, content_type='application/json', body=json.dumps({'ok': True}))
            return
    route.fulfill(status=200, content_type='application/json', body=json.dumps({'error': 'unknown'}))

TEST_URL = 'file://' + str(BASE_DIR / 'budget-tracker.test.html')

with sync_playwright() as p:
    browser = p.chromium.launch()

    # --- Device A: writes day 5 = 1000, pushes to remote (updatedAt = T1) ---
    ctxA = browser.new_context(viewport={'width': 420, 'height': 1200})
    pageA = ctxA.new_page()
    pageA.route('**/macros/**', handle_route)
    errorsA = []
    pageA.on('pageerror', lambda exc: errorsA.append(str(exc)))
    pageA.goto(TEST_URL)
    pageA.wait_for_timeout(500)
    cbA = pageA.query_selector('#app-modal-cancel')
    if cbA and cbA.is_visible(): cbA.click(); pageA.wait_for_timeout(200)
    pageA.evaluate("localStorage.setItem('fin-tracker:weburl', 'https://script.google.com/macros/s/FAKE/exec');")
    pageA.evaluate("""
      async () => {
        var m = window.__test.ensureMonth('2026-08');
        m.days['5'] = { actual: 1000 };
        await window.__test.saveMonth('2026-08');
      }
    """)
    pageA.wait_for_timeout(500)
    print('STORE after device A push:', json.dumps(STORE, ensure_ascii=False, indent=2)[:400])

    # --- Device B: fresh device, loads (pulls A's data), then independently overwrites day 5 = 2000 and pushes (updatedAt = T2 > T1) ---
    ctxB = browser.new_context(viewport={'width': 420, 'height': 1200})
    pageB = ctxB.new_page()
    pageB.route('**/macros/**', handle_route)
    errorsB = []
    pageB.on('pageerror', lambda exc: errorsB.append(str(exc)))
    pageB.goto(TEST_URL)
    pageB.wait_for_timeout(500)
    cbB = pageB.query_selector('#app-modal-cancel')
    if cbB and cbB.is_visible(): cbB.click(); pageB.wait_for_timeout(200)
    pageB.evaluate("localStorage.setItem('fin-tracker:weburl', 'https://script.google.com/macros/s/FAKE/exec');")
    pageB.evaluate("async () => { await window.__test.loadAndSync(); }")
    pageB.wait_for_timeout(800)
    pulled_by_B = pageB.evaluate("() => { var m = window.__test.ensureMonth('2026-08'); return m.days['5'] && m.days['5'].actual; }")
    print('Device B pulled day-5 actual from A (expect 1000):', pulled_by_B)
    pageB.evaluate("""
      async () => {
        var m = window.__test.ensureMonth('2026-08');
        m.days['5'] = { actual: 2000 };
        await window.__test.saveMonth('2026-08');
      }
    """)
    pageB.wait_for_timeout(500)
    print('STORE after device B push (expect 2000):', json.loads(STORE.get('month:2026-08', '{}')).get('days', {}).get('5'))

    # --- Device A comes back online (no new local edits since T1) and syncs.
    # A's local updatedAt (T1) is OLDER than remote's (T2 from B) -> A should simply
    # pull B's newer value. Since local < remote here, this is NOT flagged as a conflict. ---
    pageA.evaluate("() => { window.__badgeLog = []; const el = document.getElementById('sync-badge'); new MutationObserver(() => window.__badgeLog.push(el.textContent)).observe(el, {childList:true, characterData:true, subtree:true}); }")
    pageA.evaluate("async () => { await window.__test.loadAndSync(); }")
    pageA.wait_for_timeout(1000)
    localA_after = pageA.evaluate("() => { var m = window.__test.ensureMonth('2026-08'); return m.days['5'].actual; }")
    print('Device A local day-5 actual after re-sync (expect 2000, pulled from B):', localA_after)
    print('Device A sync-badge history (expect no conflict warning):', pageA.evaluate("() => window.__badgeLog"))

    # --- Genuine conflict: give A's local cache a synthetic future updatedAt with a
    # DIFFERENT value than what's in STORE (simulating an offline edit made after the
    # last successful sync), then sync again. Expect: A keeps its (newer) local value,
    # flags the badge warning, and self-heals by pushing its version back to STORE so
    # both sides converge without silent data loss. ---
    pageA.evaluate("""
      () => {
        var STORAGE_PREFIX = 'fin-tracker:';
        var newer = new Date(Date.now() + 3600000).toISOString();
        var m = window.__test.ensureMonth('2026-08');
        m.days['5'] = { actual: 3333 };
        m.updatedAt = newer;
        localStorage.setItem(STORAGE_PREFIX + 'month:2026-08', JSON.stringify(m));
      }
    """)
    pageA.evaluate("() => { window.__badgeLog2 = []; const el = document.getElementById('sync-badge'); new MutationObserver(() => window.__badgeLog2.push(el.textContent)).observe(el, {childList:true, characterData:true, subtree:true}); }")
    pageA.evaluate("async () => { await window.__test.loadAndSync(); }")
    pageA.wait_for_timeout(2000)
    localA_final = pageA.evaluate("() => { var m = window.__test.ensureMonth('2026-08'); return m.days['5'].actual; }")
    print('Device A local day-5 actual after conflict reload (expect kept at 3333):', localA_final)
    print('STORE day-5 value after self-heal push (expect 3333, pushed back to remote):', json.loads(STORE.get('month:2026-08', '{}')).get('days', {}).get('5'))
    print('Device A sync-badge history for conflict case (expect a warning entry then cleared):', pageA.evaluate("() => window.__badgeLog2"))

    print('Console/page errors A:', errorsA)
    print('Console/page errors B:', errorsB)

    browser.close()
