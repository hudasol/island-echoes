"""Label aware number check for evidence that holds NASA POWER tables.

The main validator accepts a number if it appears anywhere in the cited evidence. A POWER evidence item is a table
(`Name (CODE, unit): JAN v, FEB v, ..., ANN v`), so a sentence can quote the right table and the wrong cell. This
module binds each table value in a sentence to the month or annual label nearest to it, narrowed to the parameter the
sentence names, and checks it against the same cell. A month named with a superlative ("wettest") must be the
maximum or minimum of its row. It only ever adds issues.
"""

from __future__ import annotations

import re

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
         "November", "December"]
_LABEL_RE = re.compile(
    r"\b(?:" + "|".join(_FULL) + "|" + "|".join(MONTHS) + "|" + "|".join(m.title() for m in MONTHS) + r")\b"
    r"|\b(?:annual(?:ly)?|ANN|yearly|a year|per year|each year|over the year)\b",
    re.I,
)
_ROW_RE = re.compile(r"^(?P<name>[^\n(]+)\((?P<code>[A-Z0-9_]+), [^)]+\): (?P<cells>.+)$", re.M)
_CELL_RE = re.compile(r"\b(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC|ANN) (-?\d+(?:\.\d+)?)")
_NUM_RE = re.compile(r"(?<![A-Za-z\d.])-?\d+(?:\.\d+)?(?![\d])")

# parameter families: words in a sentence, and the POWER codes they select
_FAMILIES = {
    "temp": (r"temperatures?|warm\w*|hot\w*|cold\w*|cool\w*|°C", ("T2M", "T2M_MAX", "T2M_MIN")),
    "rain": (r"rain\w*|precipitation|wet\w*|dri\w*|dry", ("PRECTOTCORR",)),
    "wind": (r"wind\w*|calm\w*", ("WS10M",)),
    "humid": (r"humid\w*", ("RH2M",)),
}
_MAX_WORDS = re.compile(r"\b(wettest|rainiest|warmest|hottest|windiest|most|highest|greatest|largest|peaks?|peaking)\b", re.I)
_MIN_WORDS = re.compile(r"\b(driest|coldest|coolest|calmest|least|lowest|fewest|smallest)\b", re.I)


def _fmt(v: float) -> str:
    return f"{v:g}"


def parse_rows(evidence_text: str) -> dict[str, dict[str, float]]:
    """{code: {label: value}} for every POWER table row in the text."""
    rows = {}
    for m in _ROW_RE.finditer(evidence_text):
        cells = {lab: float(v) for lab, v in _CELL_RE.findall(m.group("cells"))}
        if len(cells) >= 12:
            rows[m.group("code")] = cells
    return rows


def _label(token: str) -> str:
    t = token.lower()
    for i, full in enumerate(_FULL):
        if t in (full.lower(), MONTHS[i].lower()):
            return MONTHS[i]
    return "ANN"


def _family_codes(text: str, pos: int | None, rows: dict) -> list[str]:
    """Codes of the parameter family named nearest to `pos` (or anywhere, if pos is None); all rows if none named."""
    best: tuple[int, tuple[str, ...]] | None = None
    for pattern, codes in _FAMILIES.values():
        for m in re.finditer(r"\b(?:" + pattern + r")", text, re.I):
            d = 0 if pos is None else abs(m.start() - pos)
            if best is None or d < best[0]:
                best = (d, codes)
    codes = [c for c in rows if best and c in best[1]] or list(rows)
    low = text.lower()
    if "maximum" in low or "daily max" in low:
        codes = [c for c in codes if c != "T2M" and c != "T2M_MIN"] or codes
    if "minimum" in low or "daily min" in low:
        codes = [c for c in codes if c != "T2M" and c != "T2M_MAX"] or codes
    return codes


def table_issues(sentence: str, cited_text: str) -> list[str]:
    rows = parse_rows(cited_text)
    if not rows:
        return []
    issues: list[str] = []
    labels = [(m.start(), m.end(), _label(m.group())) for m in _LABEL_RE.finditer(sentence)]
    values = {v for r in rows.values() for v in r.values()}
    bound: list[tuple[float, str, list[str]]] = []
    for m in _NUM_RE.finditer(sentence):
        n = float(m.group())
        if n not in values or not labels:
            continue
        # nearest label; on a tie the preceding one wins ("JAN 28.87, FEB ...")
        start, end, lab = min(labels, key=lambda lb: (min(abs(m.start() - lb[1]), abs(lb[0] - m.end())), lb[0] > m.start()))
        codes = _family_codes(sentence, m.start(), rows)
        bound.append((n, lab, codes))
        if any(rows[c].get(lab) == n for c in codes):
            continue
        where = sorted({lb for c in codes for lb, v in rows[c].items() if v == n}, key=(MONTHS + ["ANN"]).index)
        if where and any(lab in rows[c] for c in codes):
            # name the right cell, so the repair retry can state it (the retry is checked again in full)
            right = "; ".join(f"{c} {lab} is {_fmt(rows[c][lab])}" for c in codes if lab in rows[c])
            issues.append(f"{m.group()} is the {', '.join(where)} value in the cited table, not {lab} ({right})")

    months = {lab for _, _, lab in labels if lab != "ANN"}
    hi, lo = bool(_MAX_WORDS.search(sentence)), bool(_MIN_WORDS.search(sentence))
    if len(months) == 1 and hi != lo:
        month = next(iter(months))
        codes = _family_codes(sentence, None, rows)
        quoted = [c for n, lab, cs in bound if lab == month for c in cs if rows[c].get(month) == n]
        codes = [c for c in codes if c in quoted] or codes
        ok, right = False, []
        for c in codes:
            monthly = {k: v for k, v in rows[c].items() if k != "ANN"}
            target = max(monthly.values()) if hi else min(monthly.values())
            ok = ok or monthly.get(month) == target
            right.append(f"in {c} it is {', '.join(k for k, v in monthly.items() if v == target)} at {_fmt(target)}")
        if not ok:
            issues.append(f"{month} is not the {'highest' if hi else 'lowest'} month in the cited table ({'; '.join(right)})")
    return issues
