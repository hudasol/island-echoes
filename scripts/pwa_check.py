"""Check installability and offline use in headless Chromium.

    python scripts/dev.py run
    python scripts/pwa_check.py [--base http://localhost:8000]

Loads the app, visits an island and its library, goes offline, reloads, and confirms that the shell, the island and the
library entries still render. Exit status 1 on any failure.
"""

from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    base = ap.parse_args().base
    from playwright.sync_api import sync_playwright

    problems: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, service_workers="allow")
        page = ctx.new_page()
        page.goto(base + "/")
        page.wait_for_selector("#ledger tbody tr", state="attached")
        page.evaluate("navigator.serviceWorker.ready.then(() => true)")
        page.wait_for_function("navigator.serviceWorker.controller !== null || true", timeout=10000)
        page.reload()
        page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=15000)
        manifest = page.evaluate("fetch('/manifest.webmanifest').then(r => r.json())")
        if manifest.get("display") != "standalone" or not any(i["sizes"] == "512x512" for i in manifest["icons"]):
            problems.append("manifest is not installable")
        page.goto(base + "/#socotra")
        page.reload()
        page.wait_for_selector("#island-name:not(:empty)")
        page.click("#tab-library")
        page.wait_for_selector(".lib-card")
        online_cards = page.locator(".lib-card").count()
        ctx.set_offline(True)
        page.reload()
        page.wait_for_selector("#island-name:not(:empty)", timeout=15000)
        page.click("#tab-library")
        try:
            page.wait_for_selector(".lib-card", timeout=15000)
            offline_cards = page.locator(".lib-card").count()
            if offline_cards != online_cards:
                problems.append(f"library shows {offline_cards} entries offline, {online_cards} online")
        except Exception:  # noqa: BLE001
            problems.append("library did not render offline")
        ctx.set_offline(False)
        browser.close()
    print("\n".join(problems) if problems else "installable, and the library and last island render offline")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
