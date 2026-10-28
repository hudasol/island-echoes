"""Run axe-core against the running app and write docs/ACCESSIBILITY.md.

    python scripts/dev.py run                  # in one terminal
    cd web && npm ci                           # once, installs axe-core
    python scripts/a11y.py                     # http://localhost:8000 by default

Needs Playwright with Chromium (pip install playwright; playwright install chromium).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AXE = ROOT / "web" / "node_modules" / "axe-core" / "axe.min.js"
OUT = ROOT / "docs" / "ACCESSIBILITY.md"
TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"]
VIEWPORTS = {"desktop": (1440, 860), "phone": (390, 800)}


def audit(page, axe_source: str) -> dict:
    page.evaluate(axe_source)
    return page.evaluate(f"axe.run(document, {{runOnly: {{type: 'tag', values: {json.dumps(TAGS)}}}}})")


def states(page, base: str):
    """Yield (name, prepare) pairs: each prepares the page for one audit."""

    def start():
        page.goto(base + "/")
        page.wait_for_selector("#ledger tbody tr", state="attached")
        page.wait_for_timeout(800)

    def island():
        page.goto(base + "/#socotra")
        page.reload()
        page.wait_for_selector("#island-name:not(:empty)")
        page.wait_for_timeout(1500)

    def library():
        island()
        page.click("#tab-library")
        page.wait_for_selector(".lib-card")
        page.wait_for_timeout(300)

    def about():
        start()
        page.evaluate("document.getElementById('about').showModal()")
        page.wait_for_timeout(300)

    def ops():
        page.goto(base + "/stats.html")
        page.wait_for_selector("#data-body table")
        page.wait_for_timeout(800)

    return [
        ("Start view", start),
        ("Island, field agent tab", island),
        ("Island, library tab", library),
        ("Credits dialog", about),
        ("Operations page", ops),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default="http://localhost:8000")
    a = ap.parse_args()
    if not AXE.exists():
        print("axe-core is missing: run `npm ci` in web/", file=sys.stderr)
        return 2
    from playwright.sync_api import sync_playwright

    axe_source = AXE.read_text(encoding="utf-8")
    rows, found = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        for vp, (w, h) in VIEWPORTS.items():
            page = browser.new_page(viewport={"width": w, "height": h})
            for name, prepare in states(page, a.base):
                prepare()
                res = audit(page, axe_source)
                rows.append((name, vp, len(res["violations"]), len(res["passes"]), len(res["incomplete"])))
                for v in res["violations"]:
                    found.append((name, vp, v["id"], v["impact"], len(v["nodes"]), v["help"]))
            page.close()
        browser.close()
    lines = [
        "# Accessibility",
        "",
        f"Automated audit with axe-core {json.loads((ROOT / 'web' / 'node_modules' / 'axe-core' / 'package.json').read_text())['version']} "
        f"(WCAG 2.0 to 2.2 A and AA rules plus best practices), run {dt.date.today().isoformat()} by `python scripts/a11y.py`.",
        "",
        "| State | Viewport | Violations | Rules passed | Needs review |",
        "|---|---|---|---|---|",
        *[f"| {n} | {v} | {x} | {ps} | {inc} |" for n, v, x, ps, inc in rows],
        "",
    ]
    if found:
        lines += [
            "## Violations",
            "",
            "| State | Viewport | Rule | Impact | Elements | Description |",
            "|---|---|---|---|---|---|",
            *[f"| {n} | {v} | `{i}` | {imp} | {c} | {hlp} |" for n, v, i, imp, c, hlp in found],
            "",
        ]
    lines += [
        "## Built in",
        "",
        "- The island list is a keyboard alternative to the globe; tabs and creature switching work by keyboard.",
        "- Motion can be paused, and `prefers-reduced-motion` starts it paused.",
        "- Colour pairs, focus rings, forced colours and increased contrast modes are styled explicitly.",
        "- Tables on the start view and the operations page use real headers and row scopes, and plots carry text labels.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
