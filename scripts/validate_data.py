"""Structural checks for data/islands/*.json. Exit code 1 if anything is wrong."""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.data.islands import IslandStore  # noqa: E402

EXPECTED_SLUGS = {
    "cocos-keeling", "galapagos", "socotra", "tristan-da-cunha", "pitcairn", "clipperton", "bouvet",
}
QUOTE = re.compile(r'["“”]([^"“”]+)["“”]')


def main() -> int:
    settings = get_settings()
    store = IslandStore.load(settings.islands_dir)
    errors: list[str] = []

    missing = EXPECTED_SLUGS - set(store.islands)
    extra = set(store.islands) - EXPECTED_SLUGS
    if missing or extra:
        errors.append(f"island set mismatch: missing={sorted(missing)} extra={sorted(extra)}")

    types = Counter()
    prefixes: dict[str, str] = {}
    for isl in store.islands.values():
        prefixes[isl.prefix] = isl.slug if isl.prefix not in prefixes else errors.append(f"prefix clash {isl.prefix}") or ""
        slugs = {c.slug for c in isl.creatures}
        if len(isl.facts) < 30:
            errors.append(f"{isl.slug}: only {len(isl.facts)} facts")
        for c in isl.creatures:
            types[c.creature_type] += 1
            n = sum(1 for f in isl.facts if f.subject == c.slug)
            if n < 6:
                errors.append(f"{isl.slug}/{c.slug}: only {n} creature facts")
        for f in isl.facts:
            if not f.id.startswith(isl.prefix + "-"):
                errors.append(f"{f.id}: wrong prefix for {isl.slug}")
            if f.subject != "island" and f.subject not in slugs:
                errors.append(f"{f.id}: unknown subject {f.subject}")
            if (f.subject != "island") != (f.category == "creature"):
                errors.append(f"{f.id}: category/subject mismatch")
            if not f.source_url.startswith(("http://", "https://")):
                errors.append(f"{f.id}: bad source url")
            for q in QUOTE.findall(f.statement + " " + f.evidence_note):
                if len(q.split()) >= 15:
                    errors.append(f"{f.id}: quoted passage of {len(q.split())} words")
        lat, lon = isl.pin.lat, isl.pin.lon
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            errors.append(f"{isl.slug}: pin out of range")

    for t in ("bird", "marine", "reptile", "mammal"):
        if not types[t]:
            errors.append(f"no creature of type {t}")

    total = len(store.all_facts())
    print(f"{len(store.islands)} islands, {total} facts, creatures by type: {dict(types)}")
    for e in errors:
        print("ERROR:", e)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
