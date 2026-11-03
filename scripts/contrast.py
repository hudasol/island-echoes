"""WCAG contrast check for the colour pairs in a stylesheet.

    python scripts/contrast.py web/educator.css

Reads the custom properties of the first :root block (light) and of the dark scheme override, then tests the pairs
listed in PAIRS. Text needs 4.5 : 1, interface parts and large text need 3 : 1. Exit status 1 if any pair fails.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# (foreground, background, minimum ratio, what it is)
PAIRS = [
    ("ink", "paper", 4.5, "body text"),
    ("soft", "paper", 4.5, "secondary text"),
    ("soft", "wash", 4.5, "secondary text on a tint"),
    ("ink", "wash", 4.5, "text on a tint"),
    ("link", "paper", 4.5, "links"),
    ("link", "wash", 4.5, "links on a tint"),
    ("rose-dark", "paper", 4.5, "button text"),
    ("rose", "paper", 3.0, "button outline and focus ring"),
    ("sakura", "paper", 1.0, "decorative rule only (no text, no meaning)"),
]


def lum(hex_: str) -> float:
    h = hex_.lstrip("#")
    rgb = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def ratio(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def parse(css: str) -> tuple[dict[str, str], dict[str, str]]:
    def props(block: str) -> dict[str, str]:
        return {m.group(1): m.group(2) for m in re.finditer(r"--([a-z-]+):\s*(#[0-9A-Fa-f]{6})", block)}

    root = re.search(r":root\s*\{([^}]*)\}", css)
    dark = re.search(r"prefers-color-scheme:\s*dark\)\s*\{\s*:root\s*\{([^}]*)\}", css)
    light = props(root.group(1)) if root else {}
    dk = {**light, **props(dark.group(1))} if dark else {}
    # aliases such as --paper: var(--pearl)
    for table in (light, dk):
        for src, name in (("paper", "pearl"), ("ink", "plum"), ("soft", "plum-soft"), ("link", "rose"), ("accent", "sakura")):
            if name in table:
                table[src] = table[name]
    return light, dk


def check(path: Path) -> list[str]:
    light, dark = parse(path.read_text(encoding="utf-8"))
    failures = []
    for scheme, table in (("light", light), ("dark", dark)):
        for fg, bg, minimum, what in PAIRS:
            if fg not in table or bg not in table:
                failures.append(f"{scheme}: missing {fg} or {bg}")
                continue
            r = ratio(table[fg], table[bg])
            if r < minimum:
                failures.append(f"{scheme}: {what} {fg} on {bg} is {r:.2f}, needs {minimum}")
    return failures


if __name__ == "__main__":
    bad = check(Path(sys.argv[1] if len(sys.argv) > 1 else "web/educator.css"))
    print("\n".join(bad) if bad else "all pairs pass")
    sys.exit(1 if bad else 0)
