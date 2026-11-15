"""Execute the real browser adapter in headless Chromium, without npm packages.

Set BROWSER_BINARY to a Chromium executable on platforms without Edge/Chrome.
The game-menu DOM bootstrap is omitted; adapter functions are tested unchanged.
"""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from django.test import SimpleTestCase


class BrowserInventoryJavaScriptTests(SimpleTestCase):
    def test_browser_inventory_adapter(self):
        candidates = [os.environ.get("BROWSER_BINARY"), shutil.which("chromium"),
                      shutil.which("google-chrome"), shutil.which("msedge"),
                      "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
                      "C:/Program Files/Google/Chrome/Application/chrome.exe"]
        browser = next((path for path in candidates if path and Path(path).is_file()), None)
        if browser is None:
            self.skipTest("Set BROWSER_BINARY to run browser inventory JavaScript tests.")
        root = Path(__file__).parent
        scripts = root / "static/game/legacy/js"
        adapter = (scripts / "player-api.js").read_text(encoding="utf-8")
        adapter = adapter.rsplit('if (document.readyState === "loading")', 1)[0]
        sources = [adapter, *( (scripts / name).read_text(encoding="utf-8")
                              for name in ["player.js", "potions.js", "equipment.js"]),
                   (root / "tests_browser_inventory.js").read_text(encoding="utf-8")]
        with tempfile.TemporaryDirectory(prefix="phoenix-inventory-") as directory:
            page = Path(directory) / "test.html"
            page.write_text('<!doctype html><body><pre id="result">RUNNING</pre>' +
                            ''.join('<script>' + source + '</script>' for source in sources), encoding="utf-8")
            result = subprocess.run([browser, "--headless", "--disable-gpu", "--no-first-run",
                                     "--disable-background-networking", "--dump-dom",
                                     f"--user-data-dir={Path(directory) / 'profile'}", page.as_uri()],
                                    capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=45)
            self.assertEqual(result.returncode, 0, result.stderr[-2000:])
            self.assertIn('id="result">PASS: 17 browser inventory checks', result.stdout,
                          result.stdout[-5000:] + result.stderr[-1500:])
