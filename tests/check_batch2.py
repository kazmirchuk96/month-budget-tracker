from playwright.sync_api import sync_playwright
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
import json

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width': 420, 'height': 1600}, device_scale_factor=2)
    errors = []
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto('file://' + str(BASE_DIR / 'budget-tracker.test.html'))
    page.wait_for_timeout(400)
    cb = page.query_selector('#app-modal-cancel')
    if cb and cb.is_visible(): cb.click(); page.wait_for_timeout(200)

    # Seed data: several days this month (streak + week checkpoint), and a
    # couple of past months (year summary).
    page.evaluate("""
      async () => {
        var m = window.__test.ensureMonth('2026-08');
        var plan = 2327; // approx daily plan early in month before redistribution
        for (var d = 12; d <= 16; d++) { m.days[String(d)] = { actual: 1000 }; } // under plan -> streak
        await window.__test.saveMonth('2026-08');
        var m1 = window.__test.ensureMonth('2026-06');
        m1.days['10'] = { actual: 1500 };
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

    # Streak badge
    hero_text = page.query_selector('#hero-wrap').inner_text()
    print('Streak badge present:', '🔥' in hero_text)

    # Week checkpoint
    week_text = page.query_selector('#week-checkpoint').inner_text()
    print('Week checkpoint text:', repr(week_text))

    # Mandatory payments row is now compact (short line + "?" button)
    hero_html_len_ok = 'уже враховані в бюджеті' not in hero_text  # long sentence should be gone from visible text
    print('Mandatory note collapsed (long sentence not in visible hero text):', hero_html_len_ok)

    # Year summary toggle
    page.click('#year-toggle')
    page.wait_for_timeout(300)
    year_text = page.query_selector('#year-summary').inner_text()
    print('Year summary text:', repr(year_text[:300]))

    # Reset button visible label
    reset_visible_text = page.locator('#hero-wrap button', has_text='скинути').count()
    print('Reset button with visible label found:', reset_visible_text)

    # Mandatory changelog: open settings, change budget on a month with entered days, save, reopen settings
    page.click('#menu-btn'); page.wait_for_timeout(150)
    page.click('#open-settings'); page.wait_for_timeout(200)
    # bump a mandatory item amount
    first_amount_input = page.query_selector('.mandatory-row input.amount-input')
    first_amount_input.fill('99999')
    page.click('#settings-save')
    page.wait_for_timeout(300)
    page.click('#menu-btn'); page.wait_for_timeout(150)
    page.click('#open-settings'); page.wait_for_timeout(200)
    changelog_text = page.query_selector('#mandatory-changelog').inner_text()
    print('Mandatory changelog text:', repr(changelog_text))

    # NBU fetch button (network likely blocked in this sandbox -> graceful error expected)
    page.click('#fetch-nbu-rate')
    page.wait_for_timeout(3000)
    nbu_status = page.query_selector('#nbu-rate-status').inner_text()
    print('NBU status text:', repr(nbu_status))

    page.click('#settings-cancel')
    page.wait_for_timeout(200)

    page.screenshot(path='check_batch2_full.png', full_page=True)
    print('ERRORS:', errors)
    browser.close()
