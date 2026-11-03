"""Educator pack: a printable lesson sheet per island, built only from the cited fact files and the stored datasets.

Nothing here is generated text. Facts are selected by category and confidence, shown with a number that points to the
source list, and the discussion questions are fixed stems that name the numbered facts they refer to.
"""

from __future__ import annotations

import html
from datetime import date

from .data.islands import IslandStore
from .data.models import Fact, Island
from .data.sources import SourceStore, SourceUnavailable

SECTIONS: list[tuple[str, tuple[str, ...], str]] = [
    ("Where it is", ("location",), "Position and distance"),
    ("Land and sea", ("terrain", "geology", "water"), "Shape of the island and the water around it"),
    ("People and history", ("history", "people_governance"), "Who has lived here and who governs it"),
    ("Living things", ("ecology", "species", "creature"), "Plants, animals and the field agent"),
    ("Pressures and protection", ("threats", "conservation"), "What puts the island at risk and what is being done"),
]
PER_SECTION = 4
RANK = {"high": 0, "medium": 1, "low": 2}

QUESTION_STEMS: dict[str, str] = {
    "Where it is": "Fact {a} gives the position of the island. How would the distance to the nearest land change what people can bring in or send out?",
    "Land and sea": "Compare facts {a} and {b}. Which feature of the land or water is most likely to shape where animals can live, and why?",
    "People and history": "Facts {a} and {b} describe the human history. Which event changed the island most, and what in the sources supports your choice?",
    "Living things": "Fact {a} describes a living thing on the island. What would you need to measure to know whether its numbers are rising or falling?",
    "Pressures and protection": "Facts {a} and {b} describe pressures or protection. Which pressure could local action reduce, and which could it not?",
}


def _pick(facts: list[Fact], categories: tuple[str, ...], subject_ok: set[str]) -> list[Fact]:
    pool = [f for f in facts if f.category in categories and f.subject in subject_ok]
    pool.sort(key=lambda f: (RANK[f.confidence], f.id))
    return pool[:PER_SECTION]


def build_sheet(island: Island, store: IslandStore, sources: SourceStore) -> dict:
    creature_slugs = {c.slug for c in island.creatures}
    subject_ok = {"island", *creature_slugs}
    refs: dict[str, int] = {}
    ref_list: list[dict] = []

    def ref(f: Fact) -> int:
        key = f.source_url
        if key not in refs:
            refs[key] = len(ref_list) + 1
            ref_list.append({"n": refs[key], "publisher": f.publisher, "title": f.source_title, "url": f.source_url, "retrieved": f.retrieved, "confidence": set()})
        ref_list[refs[key] - 1]["confidence"].add(f.confidence)
        return refs[key]

    sections, numbered = [], 0
    questions = []
    for title, cats, blurb in SECTIONS:
        picked = _pick(island.facts, cats, subject_ok)
        items = []
        for f in picked:
            numbered += 1
            items.append({"n": numbered, "id": f.id, "text": f.statement, "confidence": f.confidence, "ref": ref(f)})
        if items:
            sections.append({"title": title, "blurb": blurb, "facts": items})
            a, b = items[0]["n"], items[min(1, len(items) - 1)]["n"]
            questions.append(QUESTION_STEMS[title].format(a=a, b=b))

    readings = None
    try:
        s = sources.power_summary(island)
        readings = {"as_of": s["as_of"], "period": s["period"], "cell": [s["cell_lat"], s["cell_lon"]],
                    "items": [{"label": i["label"], "unit": i["unit"], "annual": i["value"], "monthly": i["monthly"]} for i in s["items"]]}
        questions.append("Use the monthly readings. Which month is the driest and which is the warmest, and how could an animal that breeds in one season use that pattern?")
    except SourceUnavailable:
        pass

    creatures = []
    for c in island.creatures:
        try:
            cons = sources.conservation(island, c.slug)
        except SourceUnavailable:
            cons = None
        creatures.append({"name": c.common_name, "scientific": c.scientific_name, "type": c.creature_type, "iucn": cons})
    for r in ref_list:
        r["confidence"] = sorted(r["confidence"], key=lambda x: RANK[x])
    return {
        "island": island.slug, "name": island.name, "territory": island.territory,
        "lat": island.pin.lat, "lon": island.pin.lon, "sections": sections, "readings": readings,
        "creatures": creatures, "questions": questions, "references": ref_list, "built": date.today().isoformat(),
    }


def _e(x: object) -> str:
    return html.escape(str(x), quote=True)


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def render_html(sheet: dict) -> str:
    out = [
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">",
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
        f"<title>{_e(sheet['name'])}: educator sheet</title>",
        "<link rel=\"stylesheet\" href=\"/fonts.css\"><link rel=\"stylesheet\" href=\"/educator.css\"></head><body>",
        "<header class=\"bar\"><a class=\"back\" href=\"/\">Island Echoes</a><nav><button type=\"button\" onclick=\"window.print()\">Print or save as PDF</button>",
        f"<a href=\"/educator/{_e(sheet['island'])}.pdf\">PDF</a></nav></header><main>",
        f"<h1>{_e(sheet['name'])}</h1><p class=\"deck\">{_e(sheet['territory'])} · {sheet['lat']:.2f}, {sheet['lon']:.2f} · educator sheet</p>",
    ]
    for c in sheet["creatures"]:
        iucn = c["iucn"]
        tag = f"IUCN Red List: {_e(iucn['category'])} ({_e(iucn['code'])}), via GBIF, as of {_e(iucn['as_of'])}" if iucn else "IUCN category not held by GBIF"
        out.append(f"<p class=\"creature\"><b>{_e(c['name'])}</b> <i>{_e(c['scientific'])}</i><br><span>{tag}</span></p>")
    for s in sheet["sections"]:
        out.append(f"<section><h2>{_e(s['title'])}</h2><p class=\"blurb\">{_e(s['blurb'])}</p><ol class=\"facts\" start=\"{s['facts'][0]['n']}\">")
        for f in s["facts"]:
            out.append(f"<li><span>{_e(f['text'])}</span> <a class=\"cite\" href=\"#ref{f['ref']}\">[{f['ref']}]</a> <em class=\"conf\">{_e(f['confidence'])} confidence</em></li>")
        out.append("</ol></section>")
    r = sheet["readings"]
    if r:
        out.append(f"<section><h2>NASA POWER readings</h2><p class=\"blurb\">{_e(r['period'])}. Grid cell centred at {r['cell'][0]}, {r['cell'][1]}. Retrieved {_e(r['as_of'])}.</p>")
        out.append("<div class=\"scroll\"><table><thead><tr><th scope=\"col\">Reading</th>" + "".join(f"<th scope=\"col\" class=\"n\">{m}</th>" for m in MONTHS) + "<th scope=\"col\" class=\"n\">Year</th></tr></thead><tbody>")
        for i in r["items"]:
            cells = "".join(f"<td class=\"n\">{'' if v is None else f'{v:g}'}</td>" for v in i["monthly"])
            ann = "" if i["annual"] is None else f"{i['annual']:g}"
            out.append(f"<tr><th scope=\"row\">{_e(i['label'])} ({_e(i['unit'])})</th>{cells}<td class=\"n\">{ann}</td></tr>")
        out.append("</tbody></table></div></section>")
    out.append("<section><h2>Discussion questions</h2><ol>" + "".join(f"<li>{_e(q)}</li>" for q in sheet["questions"]) + "</ol></section>")
    out.append("<section><h2>Sources</h2><ol class=\"refs\">")
    for ref in sheet["references"]:
        out.append(f"<li id=\"ref{ref['n']}\">{_e(ref['publisher'])}: <a href=\"{_e(ref['url'])}\" rel=\"noopener noreferrer\">{_e(ref['title'])}</a>. Retrieved {_e(ref['retrieved'])}. Confidence labels used: {_e(', '.join(ref['confidence']))}.</li>")
    out.append("</ol></section></main>")
    out.append("<footer>Island Echoes is an independent project and not a NASA product. Imagery from NASA GIBS, climate data from the NASA Langley Research Center POWER Project, species records from GBIF.org. Every statement above is quoted from the numbered source.</footer></body></html>")
    return "".join(out)
