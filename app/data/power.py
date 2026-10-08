"""NASA POWER climatology client (monthly means at a point). Public API, no key."""

from __future__ import annotations

import httpx

POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"
PARAMETERS = ["T2M", "T2M_MAX", "T2M_MIN", "PRECTOTCORR", "RH2M", "WS10M"]
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
FILL_VALUE = -999.0

# evidence topic -> (parameters, label, unit string used in the evidence text)
TOPICS: dict[str, tuple[list[str], str]] = {
    "TEMP": (["T2M", "T2M_MAX", "T2M_MIN"], "air temperature at 2 m"),
    "PRECIP": (["PRECTOTCORR"], "corrected precipitation"),
    "WIND": (["WS10M"], "wind speed at 10 m"),
    "HUMID": (["RH2M"], "relative humidity at 2 m"),
}


def fetch_climatology(lat: float, lon: float, *, client: httpx.Client | None = None) -> dict:
    """Fetch the raw POWER climatology response for a point."""
    params = {
        "parameters": ",".join(PARAMETERS),
        "community": "RE",
        "longitude": f"{lon:.4f}",
        "latitude": f"{lat:.4f}",
        "format": "JSON",
    }
    own = client is None
    client = client or httpx.Client(timeout=60)
    try:
        r = client.get(POWER_URL, params=params)
        r.raise_for_status()
        data = r.json()
    finally:
        if own:
            client.close()
    if "properties" not in data or "parameter" not in data["properties"]:
        raise ValueError("unexpected NASA POWER response shape")
    return data


def _fmt(v: float) -> str:
    return f"{v:.2f}".rstrip("0").rstrip(".") if v == v else "n/a"


def topic_text(raw: dict, topic: str, lat: float, lon: float) -> str:
    """Render one topic's monthly table as plain text for the evidence bundle."""
    params, label = TOPICS[topic]
    meta = raw.get("parameters", {})
    period = raw.get("header", {}).get("range", "NASA POWER climatology")
    grid = raw.get("geometry", {}).get("coordinates", [lon, lat])
    lines = [
        f"NASA POWER climatology for the grid cell nearest {lat:.3f}, {lon:.3f} "
        f"(cell centre {grid[1]}, {grid[0]}). Period: {period}. "
        f"Monthly means of {label}; ANN is the annual value exactly as POWER reports it."
    ]
    table = raw["properties"]["parameter"]
    for p in params:
        series = table.get(p)
        if not series:
            continue
        unit = meta.get(p, {}).get("units", "")
        name = meta.get(p, {}).get("longname", p)
        cells = []
        for m in [*MONTHS, "ANN"]:
            v = series.get(m)
            if v is None or v == FILL_VALUE:
                cells.append(f"{m} n/a")
            else:
                cells.append(f"{m} {_fmt(v)}")
        lines.append(f"{name} ({p}, {unit}): " + ", ".join(cells) + ".")
    return "\n".join(lines)
