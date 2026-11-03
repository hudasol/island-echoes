"""Render the educator sheets to PDF with headless Chromium (Playwright) into web/educator/.

    python scripts/dev.py run          # in one terminal
    python scripts/build_educator_pdfs.py [--base http://localhost:8000]
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "educator"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    args = ap.parse_args()
    from playwright.sync_api import sync_playwright

    slugs = [i["slug"] for i in json.load(urllib.request.urlopen(f"{args.base}/api/islands"))]
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        for slug in slugs:
            page.goto(f"{args.base}/educator/{slug}", wait_until="networkidle")
            page.pdf(path=str(OUT / f"{slug}.pdf"), format="A4", margin={"top": "18mm", "bottom": "18mm", "left": "16mm", "right": "16mm"}, print_background=False)
            print("wrote", OUT / f"{slug}.pdf")
        browser.close()


if __name__ == "__main__":
    main()
