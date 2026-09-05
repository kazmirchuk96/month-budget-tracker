from playwright.sync_api import sync_playwright
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
import json

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={'width':420,'height':1600}, device_scale_factor=2)
    errors = []
    page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
    page.on('pageerror', lambda exc: errors.append(str(exc)))
    page.goto('file://' + str(BASE_DIR / 'budget-tracker.html'))
    page.wait_for_timeout(800)

    # Seed data: current month (2026-08) with days 1-15 filled (some overspend), plus a past month July 2026 fully done.
    seed_script = """
    (function(){
      var STORAGE_PREFIX = 'fin-tracker:';
      var aug = {
        budgetUSD: 2200, rateUAH: 44.64,
        mandatory: [{id:'rent',label:'Оренда квартири',amountUAH:15075},{id:'mortgage',label:'Іпотека',amountUAH:11000}],
        days: {
          '1': {actual: 7278, note: 'Оренда+іпотека НЕ тут - тест'},
          '2': {actual: 1523},
          '3': {actual: 5762},
          '4': {actual: 7244},
          '5': {actual: 1311},
          '6': {actual: 2342},
          '7': {actual: 6663},
          '8': {actual: 1600},
          '9': {actual: 1551},
          '10': {actual: 9024, note: 'Купив лінзи на 2 місяці'},
          '11': {actual: 2644},
          '12': {actual: 5091},
          '13': {actual: 2042},
          '14': {actual: 1961},
          '15': {actual: 2548}
        },
        createdAt: new Date().toISOString()
      };
      localStorage.setItem(STORAGE_PREFIX + 'month:2026-08', JSON.stringify(aug));
      var jul = {
        budgetUSD: 2200, rateUAH: 43.8,
        mandatory: [{id:'rent',label:'Оренда квартири',amountUAH:14800},{id:'mortgage',label:'Іпотека',amountUAH:10800}],
        days: {},
        createdAt: new Date().toISOString()
      };
      var N = 31;
      var base = (2200*43.8 - 14800 - 10800)/N;
      for (var d=1; d<=N; d++){ jul.days[d] = { actual: Math.round(base * (d%2===0?1.3:0.7)) }; }
      localStorage.setItem(STORAGE_PREFIX + 'month:2026-07', JSON.stringify(jul));
    })();
    """
    page.evaluate(seed_script)
    page.reload()
    page.wait_for_timeout(1000)

    print("CONSOLE ERRORS:", errors)
    page.screenshot(path='screenshot_seeded_top.png', full_page=False)

    # expand days history
    page.click('#days-toggle')
    page.wait_for_timeout(300)
    page.click('#months-toggle')
    page.wait_for_timeout(300)
    page.screenshot(path='screenshot_seeded_full.png', full_page=True)

    # click a past month row to expand
    page.click('#months-list .row-item')
    page.wait_for_timeout(300)
    page.screenshot(path='screenshot_month_expanded.png', full_page=True)

    print("DONE")
    browser.close()
