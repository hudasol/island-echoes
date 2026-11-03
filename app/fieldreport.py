"""A shareable field report for one creature: a static page and an image card.

Every sentence is a sourced fact (the same selection the narration uses), listed with its citation, the
data retrieval date and the IUCN code held by GBIF. The page has no script, no cookie and no tracker, and
the card is a self contained SVG, so sharing it sends nothing back to anyone.
"""

from __future__ import annotations

import html
import textwrap

from .data.islands import IslandStore
from .data.models import Creature, Island
from .data.sources import SourceStore, SourceUnavailable
from .narration import narration_for

PINK = {"pearl": "#FFF8FA", "wash": "#FCE9EF", "sakura": "#F2A9BE", "plum": "#3B1F2C", "soft": "#6A3B50", "rose": "#8E2650"}


def _e(x: object) -> str:
    return html.escape(str(x), quote=True)


def build_report(island: Island, creature: Creature, store: IslandStore, sources: SourceStore, saved: dict) -> dict:
    sentences = narration_for(store, island, creature, saved)
    facts, refs = [], []
    for s in sentences:
        if s["kind"] != "fact":
            continue
        cites = []
        for fid in s["cites"]:
            f = store.fact(fid)
            if f.id not in [r["id"] for r in refs]:
                refs.append({"n": len(refs) + 1, "id": f.id, "publisher": f.publisher, "title": f.source_title, "url": f.source_url, "retrieved": f.retrieved, "confidence": f.confidence})
            cites.append(next(r["n"] for r in refs if r["id"] == f.id))
        facts.append({"text": s["text"], "cites": cites})
    try:
        iucn = sources.conservation(island, creature.slug)
    except SourceUnavailable:
        iucn = None
    retrieved = sorted({r["retrieved"] for r in refs})
    return {
        "island": island.slug, "island_name": island.name, "creature": creature.slug, "name": creature.common_name,
        "scientific": creature.scientific_name, "type": creature.creature_type, "iucn": iucn,
        "facts": facts, "references": refs, "data_date": retrieved[-1] if retrieved else None,
    }


def render_html(rep: dict, base: str = "") -> str:
    iucn = rep["iucn"]
    tag = f"IUCN Red List {_e(iucn['category'])} ({_e(iucn['code'])}), via GBIF, as of {_e(iucn['as_of'])}" if iucn else "No IUCN category is held by GBIF for this creature"
    card = f"{base}/report/{_e(rep['island'])}/{_e(rep['creature'])}.svg"
    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{_e(rep['name'])} on {_e(rep['island_name'])}: field report</title>",
        f'<meta name="description" content="A sourced field report on the {_e(rep["name"])}, {_e(rep["island_name"])}. Independent, not a NASA product.">',
        f'<meta property="og:title" content="{_e(rep["name"])} on {_e(rep["island_name"])}"><meta property="og:image" content="{card}">',
        '<meta name="robots" content="noindex"><link rel="stylesheet" href="/fonts.css"><link rel="stylesheet" href="/educator.css"></head><body>',
        '<header class="bar"><a class="back" href="/">Island Echoes</a></header><main>',
        f"<h1>{_e(rep['name'])}</h1><p class=\"deck\"><i>{_e(rep['scientific'])}</i> · {_e(rep['island_name'])}</p>",
        f'<p class="creature"><span>{tag}</span></p>',
        f'<img src="{card}" width="600" height="315" alt="Share card for the {_e(rep["name"])}: name, IUCN code, and the first sourced fact." style="max-width:100%;height:auto">',
        "<section><h2>Field report</h2><ol class=\"facts\">",
    ]
    for f in rep["facts"]:
        marks = " ".join(f'<a class="cite" href="#ref{n}">[{n}]</a>' for n in f["cites"])
        out.append(f"<li><span>{_e(f['text'])}</span> {marks}</li>")
    out.append("</ol></section><section><h2>Sources</h2><ol class=\"refs\">")
    for r in rep["references"]:
        out.append(f'<li id="ref{r["n"]}">{_e(r["publisher"])}. {_e(r["title"])}. <a href="{_e(r["url"])}" rel="noopener noreferrer">{_e(r["url"])}</a>. Retrieved {_e(r["retrieved"])}. Confidence: {_e(r["confidence"])}.</li>')
    out.append("</ol></section>")
    if rep["data_date"]:
        out.append(f"<p class=\"deck\">Data as of {_e(rep['data_date'])}.</p>")
    out.append("<p class=\"deck\">Island Echoes is an independent open data project, not a NASA product. This page sets no cookies and loads no tracking.</p></main></body></html>")
    return "".join(out)


def render_svg(rep: dict) -> str:
    iucn = rep["iucn"]
    code = iucn["code"] if iucn else "n/a"
    first = rep["facts"][0]["text"] if rep["facts"] else ""
    lines = textwrap.wrap(first, 54)[:4]
    if len(textwrap.wrap(first, 54)) > 4:
        lines[-1] = lines[-1].rstrip(".,; ") + " ..."
    p = PINK
    body = "".join(f'<text x="48" y="{214 + i * 30}" font-size="22" fill="{p["plum"]}">{_e(line)}</text>' for i, line in enumerate(lines))
    date = _e(rep["data_date"] or "undated")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" '
        f'aria-label="{_e(rep["name"])}, IUCN {_e(code)}">'
        f'<rect width="1200" height="630" fill="{p["pearl"]}"/><rect width="1200" height="14" fill="{p["sakura"]}"/>'
        '<g font-family="Georgia, serif" transform="scale(1)">'
        f'<text x="48" y="96" font-size="54" fill="{p["plum"]}">{_e(rep["name"])}</text>'
        f'<text x="48" y="140" font-size="26" font-style="italic" fill="{p["soft"]}">{_e(rep["scientific"])} · {_e(rep["island_name"])}</text>'
        f'<rect x="900" y="48" width="252" height="96" rx="10" fill="{p["wash"]}" stroke="{p["sakura"]}" stroke-width="3"/>'
        f'<text x="1026" y="88" font-size="20" text-anchor="middle" fill="{p["soft"]}">IUCN Red List</text>'
        f'<text x="1026" y="128" font-size="40" text-anchor="middle" fill="{p["rose"]}">{_e(code)}</text>'
        f'<g transform="translate(0,-20)">{body}</g>'
        f'<text x="48" y="560" font-size="20" fill="{p["soft"]}">Data as of {date}. Sources are cited at island-echoes.onrender.com</text>'
        f'<text x="48" y="596" font-size="18" fill="{p["soft"]}">Independent open data project, not a NASA product.</text>'
        "</g></svg>"
    )
