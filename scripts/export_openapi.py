"""Write the OpenAPI description of the public API to docs/openapi.json.

    python scripts/export_openapi.py          # rewrite the file
    python scripts/export_openapi.py --check  # exit 1 if the committed file is out of date
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
OUT = ROOT / "docs" / "openapi.json"


def current() -> str:
    from app.main import create_app

    return json.dumps(create_app().openapi(), indent=1, sort_keys=True) + "\n"


if __name__ == "__main__":
    text = current()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text(encoding="utf-8") == text else 1)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT}")
