"""
Regenerates budget-tracker.test.html — a copy of budget-tracker.html with
window.__test hooks injected, used by check_conflict.py / check_monthnav.py /
check_batch2.py for white-box testing of internal sync/state functions.

Run from anywhere; it resolves paths relative to the project root
(one level above this tests/ folder). Never edit budget-tracker.test.html
by hand or commit it — it's a derived, throwaway build artifact.

Usage: python3 tests/make_test_build.py
"""
import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
src = BASE_DIR / 'budget-tracker.html'
dst = BASE_DIR / 'budget-tracker.test.html'

content = src.read_text()
marker = '})();\n</script>'
inject = (
    "  window.__test = { ensureMonth: ensureMonth, saveMonth: saveMonth, "
    "storage: storage, loadAndSync: loadAndSync };\n"
)
if marker not in content:
    raise SystemExit(
        "Marker not found — budget-tracker.html structure changed; "
        "update the marker in this script to match."
    )
content = content.replace(marker, inject + marker)
dst.write_text(content)
print(f"Wrote {dst}")
