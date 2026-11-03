"""Deterministic answers to numeric NASA POWER questions.

A question that asks for a month, a monthly extreme, an annual value or a comparison between two islands is answered by
code that reads the stored POWER climatology, so the number and the month come from the table and not from free text
generation. The answer cites the same evidence identifier the retrieval layer would have shown to a model. Questions
that do not ask for such a value return None and follow the normal path.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import power as power_mod
from .islands import IslandStore
from .models import Island
from .sources import SourceStore, SourceUnavailable

MONTH_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# (regex on the lower cased question, kind of extreme, power parameter key, spoken name of the extreme)
EXTREMES: list[tuple[str, str, str, str]] = [
    (r"\bwarmest|\bhottest|\bmost warm", "max", "temp", "warmest"),
    (r"\bcoldest|\bcoolest|\bchilliest|\bmost cold", "min", "temp", "coldest"),
    (r"\bwettest|\bmost rain|\bmost precipitation|\brainiest|\bheaviest rain", "max", "rain", "wettest"),
    (r"\bdriest|\bleast rain|\bleast precipitation|\bleast wet|\blowest rain", "min", "rain", "driest"),
    (r"\bwindiest|\bmost wind|\bstrongest wind|\bhighest wind", "max", "wind", "windiest"),
    (r"\bcalmest|\bleast wind|\bweakest wind|\blowest wind", "min", "wind", "calmest"),
    (r"\bmost humid|\bhighest humidity|\bmost damp", "max", "humidity", "most humid"),
    (r"\bleast humid|\blowest humidity|\bdriest air", "min", "humidity", "least humid"),
]
PARAM_WORDS: list[tuple[str, str]] = [
    (r"\btemperature|\bwarm|\bhot\b|\bcold\b|\bcool\b", "temp"),
    (r"\brain|\bprecipitation|\bwet\b|\bdry\b|\bdrizzle", "rain"),
    (r"\bwind|\bbreez|\bcalm\b", "wind"),
    (r"\bhumid|\bdamp", "humidity"),
]
PARAM_PHRASE = {"temp": "air temperature", "rain": "rainfall", "wind": "wind speed at 10 m", "humidity": "relative humidity"}
COMPARE = re.compile(r"\bcompar|\bhigher|\blower|\bwarmer|\bcolder|\bwetter|\bdrier|\bwindier|\bmore humid|\bless humid|\bversus\b|\bvs\b", re.I)
ANNUAL = re.compile(r"\bannual|\bper year|\bper annum|\bthe year\b|\byearly|\bon average|\baverage\b|\bmean\b", re.I)
SOURCE_HINT = re.compile(r"\bnasa|\bpower\b|\bclimat|\bsensor|\binstrument|\bmonth|\bannual|\baverage|\bmean\b", re.I)


@dataclass
class ClimateAnswer:
    sentences: list[dict]  # {"text", "kind", "cites"}
    evidence_ids: list[str]
    route: str


def _norm(s: str) -> str:
    import unicodedata

    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


class ClimateTool:
    def __init__(self, islands: IslandStore, sources: SourceStore):
        self.islands, self.sources = islands, sources

    # ---- parsing -----------------------------------------------------
    def _islands_named(self, question: str) -> list[Island]:
        q = _norm(question)
        out = []
        for isl in self.islands.islands.values():
            names = [isl.name, *isl.alt_names]
            keys = {_norm(re.sub(r"\(.*?\)", "", n)).replace("islands", "").replace("island", "").strip() for n in names}
            keys = {k for k in keys if len(k) >= 4}
            if any(re.search(r"\b" + re.escape(k), q) for k in keys):
                out.append(isl)
        return out

    @staticmethod
    def _months_in(question: str) -> list[int]:
        q = question.lower()
        found = []
        for i, name in enumerate(MONTH_FULL):
            if re.search(r"\b" + name.lower() + r"\b", q):
                found.append(i)
        return found

    @staticmethod
    def _param(question: str) -> str | None:
        q = question.lower()
        hits = [key for pat, key in PARAM_WORDS if re.search(pat, q)]
        return hits[0] if hits else None

    def _item(self, isl: Island, key: str) -> dict | None:
        try:
            summary = self.sources.power_summary(isl)
        except SourceUnavailable:
            return None
        for it in summary["items"]:
            if it["key"] == key:
                return {**it, "period": summary["period"], "as_of": summary["as_of"]}
        return None

    # ---- answering ---------------------------------------------------
    def answer(self, island: Island, question: str) -> ClimateAnswer | None:
        q = question.lower()
        if not SOURCE_HINT.search(q):
            return None
        named = self._islands_named(question)
        months = self._months_in(question)

        for pat, kind, key, word in EXTREMES:
            if re.search(pat, q):
                return self._extreme(named[0] if named else island, key, kind, word)

        param = self._param(question)
        if param is None:
            return None
        if COMPARE.search(q) and len({i.slug for i in [island, *named]}) >= 2:
            others = [i for i in named if i.slug != island.slug] or []
            a = island if (not named or island.slug in {i.slug for i in named}) else named[0]
            b = others[0] if others else None
            if b is None:
                return None
            return self._compare(a, b, param)
        if months and len(months) == 1:
            return self._month(named[0] if named else island, param, months[0])
        if ANNUAL.search(q) and not months and re.search(r"\bnasa|\bpower|\bclimat|\bannual|\bper year|\bsensor", q):
            return self._annual(named[0] if named else island, param)
        return None

    @staticmethod
    def _v(x: float) -> str:
        return power_mod._fmt(x)

    def _extreme(self, isl: Island, key: str, kind: str, word: str) -> ClimateAnswer | None:
        it = self._item(isl, key)
        if not it or any(v is None for v in it["monthly"]):
            return None
        vals = it["monthly"]
        target = max(vals) if kind == "max" else min(vals)
        months = [MONTH_FULL[i] for i, v in enumerate(vals) if v == target]
        eid = it["evidence_id"]
        unit = it["unit"]
        label = PARAM_PHRASE[key]
        mtxt = " and ".join(months)
        verb = "is" if len(months) == 1 else "are tied as"
        text = f"In the NASA POWER climatology for {isl.name}, the {word} month {verb} {mtxt}, with a monthly mean {label} of {self._v(target)} {unit}."
        return ClimateAnswer([{"text": text, "kind": "fact", "cites": [eid]}], [eid], f"extreme:{key}:{kind}")

    def _month(self, isl: Island, key: str, m: int) -> ClimateAnswer | None:
        it = self._item(isl, key)
        if not it or it["monthly"][m] is None:
            return None
        eid = it["evidence_id"]
        text = f"In the NASA POWER climatology for {isl.name}, the monthly mean {PARAM_PHRASE[key]} in {MONTH_FULL[m]} is {self._v(it['monthly'][m])} {it['unit']}."
        return ClimateAnswer([{"text": text, "kind": "fact", "cites": [eid]}], [eid], f"month:{key}")

    def _annual(self, isl: Island, key: str) -> ClimateAnswer | None:
        it = self._item(isl, key)
        if not it or it["value"] is None:
            return None
        eid = it["evidence_id"]
        text = f"In the NASA POWER climatology for {isl.name}, the annual {PARAM_PHRASE[key]} is {self._v(it['value'])} {it['unit']}."
        return ClimateAnswer([{"text": text, "kind": "fact", "cites": [eid]}], [eid], f"annual:{key}")

    def _compare(self, a: Island, b: Island, key: str) -> ClimateAnswer | None:
        ia, ib = self._item(a, key), self._item(b, key)
        if not ia or not ib or ia["value"] is None or ib["value"] is None:
            return None
        va, vb = ia["value"], ib["value"]
        if va == vb:
            rel = "the same as"
        else:
            rel = "higher than" if va > vb else "lower than"
        text = (
            f"In the NASA POWER climatology the annual {PARAM_PHRASE[key]} on {a.name} is {self._v(va)} {ia['unit']}, which is {rel} "
            f"{b.name}, at {self._v(vb)} {ib['unit']}."
        )
        ids = [ia["evidence_id"], ib["evidence_id"]]
        return ClimateAnswer([{"text": text, "kind": "fact", "cites": ids}], ids, f"compare:{key}")
