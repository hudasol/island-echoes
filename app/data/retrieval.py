"""Retrieval over the island facts (BM25) plus intent routing to NASA POWER and GBIF evidence.

Design note: lexical scores on a ~40-fact corpus are a poor yes/no gate (they refuse answerable
questions and accept off-topic ones), so retrieval only short-circuits when there is essentially no
term overlap. Whether the retrieved evidence actually answers the question is decided downstream by
the model under citation validation, and measured by the eval.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from .islands import IslandStore
from .models import Evidence, Island
from .sources import SourceStore, SourceUnavailable

STOP = set(
    """a an and are as at be been but by can did do does for from had has have how i if in is it its
    me my of on or our so than that the their them then there these they this to us was we were what
    when where which who whom why will with would you your tell about please could should like some any here many much name give list show find know say fahrenheit kelvin miles mph inches feet affect happen happened fall falls get gets go goes make makes use used""".split()
)

# (pattern on the lower-cased query, words added to the query)
SYNONYM_PATTERNS: list[tuple[str, list[str]]] = [
    (r"\brain|\bwet\b|\bdrizzle", ["rainfall", "precipitation"]),
    (r"\bhot\b|\bwarm|\bheat", ["temperature", "warm"]),
    (r"\bcold|\bcool\b|\bfreez", ["temperature", "cool"]),
    (r"\bweather", ["climate", "temperature", "rainfall"]),
    (r"\blineage|\bdescendant|\bsurviv", ["ancestry", "hybrid", "descendant"]),
    (r"\bwater (quality|pollution)|\bpollut|\bplastic|\bdirty", ["pollution", "plastic", "debris", "quality"]),
    (r"\bendangered|\bthreatened|\brare\b|\bextinct", ["status", "listed", "vulnerable", "endangered", "critically"]),
    (r"\beat\w*|\bfood|\bfeed|\bhunt|\bprey|\bdiet", ["diet", "feed", "food", "eat"]),
    (r"\blive[sd]?\b|\bliving|\binhabit|\bresident|\bpeople|\bcitizens", ["population", "inhabitants", "residents", "settlement"]),
    (r"\bbig\b|\blarge|\bsize|\barea\b", ["area", "km2", "size"]),
    (r"\btall|\bhigh\b|\bheight|\bmountain|\bpeak|\bsummit", ["elevation", "peak", "height", "highest"]),
    (r"\bold\b|\bage\b|\bhow long", ["age", "years", "history"]),
    (r"\bendanger|\bthreatened|\bextinct|\bsurviv|\bstatus", ["iucn", "status", "threatened", "extinct", "endangered"]),
    (r"\bthreat|\bdanger|\bdecline|\brisk|\bpredat|\binvasive|\bpoach", ["threats", "decline", "predators", "invasive", "threatened"]),
    (r"\bprotect|\bconserv|\bsave|\brescue|\breserve|\brestor", ["conservation", "protected", "reserve", "restoration"]),
    (r"\bdiscover|\bfound(ed)?\b|\bfirst\b|\bsettl|\bcolon|\bexplor|\bannex|\brules?\b|\bruled\b|\bruler|\bruling|\bgovern|\bhistor", ["history", "discovered", "settled", "ruled", "claimed"]),
    (r"\bvolcan|\beruption|\bcrater|\blava", ["volcanic", "eruption", "crater", "geology"]),
    (r"\bfar\b|\bdistance|\bnearest|\bclosest|\bremote", ["distance", "km", "nearest", "kilometres"]),
    (r"\bwhere\b|\blocated|\bcoordinate|\blatitude|\blongitude", ["location", "located", "coordinates"]),
    (r"\bnest|\bbreed|\bpup|\bchick|\begg|\bmat(e|ing)", ["breeding", "nest", "pups", "eggs"]),
    (r"\bweigh|\bmass\b|\bheavy", ["weight", "mass", "kg"]),
    (r"\bbirth|\bborn\b|\bpopulation", ["population", "individuals", "estimate"]),
    (r"\bice\b|\bicy\b|\bglaci|\bsnow|\bfrozen", ["ice", "glacier", "glaciated", "covered"]),
    (r"\brules?\b|\bruler|\bruled\b|\bgovern|\bwho controls|\bcontrol|\bowns?\b|\bbelongs?|\bsovereign|\bcapital\b", ["governorate", "control", "controlled", "sovereignty", "sultanate", "territory", "administered", "capital"]),
    (r"\bspeak|\blanguage|\bspoken|\btongue|\bdialect", ["language", "spoken", "speak", "dialect"]),
    (r"\bisolat", ["remote", "isolated", "distance", "nearest", "km"]),
    (r"\bcountry\b|\bnation", ["country", "territory", "sovereignty", "governorate", "administered"]),
    (r"\bmutin", ["mutineers", "mutiny", "bounty"]),
    (r"\bsupply|\bdrinking|\bfreshwater|\bfresh water|\bwells?\b|\breservoir", ["freshwater", "drinking", "wells", "springs", "reservoir", "rainwater", "groundwater"]),
    (r"\bhow many\b.*\b(left|remain|survive|alive|exist)|\b(left|remain\w*|surviv\w*)\b.*\bhow many\b|\bhow many (of you|are there)|\bnumber of (you|your)", ["population", "estimated", "individuals", "survey", "mature"]),
]

# country <-> adjective pairs: "Australian" in a question should find "Australia" in a fact, and back
DEMONYMS: list[tuple[str, str]] = [
    ("australia", "australian"), ("norway", "norwegian"), ("ecuador", "ecuadorian"), ("yemen", "yemeni"),
    ("mexico", "mexican"), ("portugal", "portuguese"), ("france", "french"), ("netherlands", "dutch"),
    ("britain", "british"), ("england", "english"), ("germany", "german"), ("italy", "italian"),
    ("tahiti", "tahitian"), ("polynesia", "polynesian"), ("america", "american"), ("africa", "african"),
    ("india", "indian"), ("japan", "japanese"), ("spain", "spanish"),
]

CATEGORY_PATTERNS: dict[str, str] = {
    "threats": r"\bthreat|\bdanger|\bdecline|\brisk|\bpredat|\binvasive|\bpoach|\bbycatch",
    "conservation": r"\bprotect|\bconserv|\bsave|\brescue|\breserve|\brestor|\brecover",
    "history": r"\bhistor|\bdiscover|\bfound(ed)?\b|\bsettl|\bcolon|\bexplor|\bannex|\bruled?\b|\bcentur",
    "people_governance": r"\bwho lives|\bpopulation|\binhabit|\bresident|\bgovern|\bsovereign|\bpeople|\bliv(e|es|ing)\b",
    "terrain": r"\bmountain|\bpeak|\btall|\bhigh\b|\belevation|\bhill|\bbeach|\blagoon|\bcliff|\bterrain",
    "geology": r"\bvolcan|\bgeolog|\brock|\beruption|\bcrater|\bformed|\borigin",
    "ecology": r"\beat|\bdiet|\bfeed|\bhabitat|\becosystem|\bplants?\b|\bwildlife|\bnest|\bbreed",
    "location": r"\bwhere\b|\blocated|\bcoordinate|\blatitude|\blongitude|\bdistance|\bfar\b|\bnearest",
}

CLIMATE_TOPICS: dict[str, set[str]] = {
    "TEMP": {"temperature", "temperatures", "hot", "warm", "warmest", "cold", "coldest", "cool", "degrees", "celsius", "heat", "freezing"},
    "PRECIP": {"rain", "rainfall", "precipitation", "wet", "wettest", "dry", "driest", "drizzle", "monsoon", "rainy"},
    "WIND": {"wind", "windy", "winds", "breeze", "gale", "gusts"},
    "HUMID": {"humidity", "humid", "muggy", "damp"},
}
CLIMATE_GENERIC = {"climate", "weather", "season", "seasons", "seasonal", "monthly", "sensor", "sensors"}
SPECIES_INTENT = {
    "gbif", "records", "record", "sightings", "sighting", "occurrence", "occurrences", "observed",
    "observations", "observation", "taxonomy", "classification", "family", "genus", "kingdom",
    "phylum", "usagekey", "lineage", "backbone", "scientific",
}
FIRST_PERSON = {"you", "your", "yours", "yourself"}

MIN_OVERLAP_SCORE = 1.0  # below this there is effectively no shared vocabulary with any fact


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def _stem(w: str) -> str:
    """Tiny suffix stemmer. Plural/past/-ing forms and their base word must land on the same stem
    (tortoise/tortoises, evacuate/evacuated, cave/caves), so a trailing silent 'e' is dropped last."""
    if w.isdigit() or len(w) <= 3:
        return w
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif w.endswith(("sses", "shes", "ches", "xes", "zes")):
        w = w[:-2]
    elif w.endswith("s") and not w.endswith(("ss", "us", "is")):
        w = w[:-1]
    if len(w) > 6 and w.endswith("ing"):
        w = w[:-3]
    elif len(w) > 5 and w.endswith("ed"):
        w = w[:-2]
    if len(w) > 4 and w.endswith("e"):
        w = w[:-1]
    return w


def _norm(text: str) -> str:
    return _strip_accents(text).lower().replace("km²", "km2").replace("°", " deg ")


# prefix -> characters to strip, so compound forms also match their base word
_PREFIXES = {"micro": 5, "macro": 5, "mega": 4, "nano": 4, "super": 5, "anti": 4, "unin": 2}


def tokenize(text: str) -> list[str]:
    """Stemmed content words. "macroplastic" also yields "plastic" and "uninhabited" also yields "inhabited"."""
    out: list[str] = []
    for t in re.findall(r"[a-z0-9]+", _norm(text)):
        if t in STOP:
            continue
        out.append(_stem(t))
        for pre, n in _PREFIXES.items():
            if t.startswith(pre) and len(t) - n >= 4:
                out.append(_stem(t[n:]))
    return out


def expand(query: str, vocab: set[str] | None = None) -> list[str]:
    q = _norm(query)
    toks = tokenize(q)
    for pat, words in SYNONYM_PATTERNS:
        if re.search(pat, q):
            for w in words:
                toks.extend(tokenize(w))
    words = set(re.findall(r"[a-z]+", q))
    for country, adjective in DEMONYMS:
        if country in words or adjective in words:
            toks.extend(tokenize(f"{country} {adjective}"))
    # "1500s" / "1990s": match any indexed year in that range
    if vocab:
        for m in re.finditer(r"\b(\d{4})s\b", q):
            s = m.group(1)
            prefix = s[:2] if s.endswith("00") else s[:3] if s.endswith("0") else s
            toks.extend(v for v in vocab if len(v) == 4 and v.isdigit() and v.startswith(prefix))
    return toks


_INTENT_WORDS = set().union(*CLIMATE_TOPICS.values(), CLIMATE_GENERIC, SPECIES_INTENT)
STRONG_COVERAGE = 0.6   # share of the question's weighted words a fact must cover to count as an answer
PARTIAL_COVERAGE = 0.4  # below this a fact is not shown at all
MAX_UNKNOWN_SHARE = 0.5  # if this share or more of the question is unknown to the library, nothing is shown


@dataclass
class _Term:
    stem: str
    alts: set[str]
    weight: float
    known: bool


def query_terms(query: str, index: BM25, skip: set[str] | None = None, names: set[str] | None = None) -> list[_Term]:
    """The question's content words with the stems that count as a match for each.

    A word is "known" when the island's facts contain it (or a synonym the patterns add for it). Unknown
    words, such as "president" or "Tokyo", carry the highest weight, so a question built around words the
    library has never seen cannot be rescued by one shared common word.
    """
    q = _norm(query)
    max_idf = max(index.idf.values(), default=1.0)
    terms: dict[str, _Term] = {}
    for m in re.finditer(r"[a-z0-9]+", q):
        w = m.group(0)
        st = _stem(w)
        if w in STOP or st in STOP or (skip and st in skip):
            continue
        alts = {st}
        for pat, words in SYNONYM_PATTERNS:
            for pm in re.finditer(pat, q):
                if pm.start() < m.end() and pm.end() > m.start():
                    for x in words:
                        alts.update(tokenize(x))
        for country, adjective in DEMONYMS:
            if w in (country, adjective):
                alts.update(tokenize(f"{country} {adjective}"))
        present = [index.idf[a] for a in alts if a in index.idf]
        known = bool(present)
        if not known and (st in (names or ()) or w in _INTENT_WORDS):  # climate/species wording is answered by live NASA POWER / GBIF data
            known, present = True, [max_idf * 0.5]
        terms[st] = _Term(st, alts, max(present) if known else max_idf, known)
    return list(terms.values())


@dataclass
class _Doc:
    evidence: Evidence
    tokens: list[str]
    tf: Counter


class BM25:
    def __init__(self, docs: list[Evidence], k1: float = 1.4, b: float = 0.75):
        self.k1, self.b = k1, b
        self.docs = [_Doc(e, (t := tokenize(e.text)), Counter(t)) for e in docs]
        self.avgdl = sum(len(d.tokens) for d in self.docs) / max(len(self.docs), 1)
        df: Counter = Counter()
        for d in self.docs:
            df.update(set(d.tokens))
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - c + 0.5) / (c + 0.5)) for t, c in df.items()}
        self.vocab = set(df)

    def score(self, qtoks: list[str], boost: dict[str, float] | None = None) -> list[tuple[float, Evidence]]:
        out = []
        for d in self.docs:
            s, dl = 0.0, len(d.tokens)
            for t in set(qtoks):
                f = d.tf.get(t, 0)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0 and boost:
                s *= boost.get(d.evidence.id, 1.0)
            out.append((s, d.evidence))
        out.sort(key=lambda x: -x[0])
        return out


@dataclass
class RetrievalResult:
    evidence: list[Evidence]
    top_score: float
    has_evidence: bool
    intents: set[str] = field(default_factory=set)
    notes: list[str] = field(default_factory=list)


@dataclass
class LibraryResult:
    results: list[Evidence]
    counts: dict[str, int]
    total: int
    notes: list[str] = field(default_factory=list)
    quality: str = "browse"  # browse | strong | partial | none
    partial_ids: set[str] = field(default_factory=set)


class Retriever:
    def __init__(self, islands: IslandStore, sources: SourceStore, k: int = 12):
        self.islands, self.sources, self.k = islands, sources, k
        self._index: dict[tuple[str, str], BM25] = {}

    def _bm25(self, island: Island, creature_slug: str) -> BM25:
        key = (island.slug, creature_slug)
        if key not in self._index:
            docs = [
                self.islands.fact_to_evidence(island, f)
                for f in island.facts
                if f.subject in ("island", creature_slug)
            ]
            self._index[key] = BM25(docs)
        return self._index[key]

    def _live(self, island: Island, creature, raw_words: set[str]) -> tuple[list[Evidence], set[str], list[str]]:
        """NASA POWER and GBIF evidence pulled in by the words of the question."""
        intents: set[str] = set()
        notes: list[str] = []
        extra: list[Evidence] = []
        topics = [t for t, words in CLIMATE_TOPICS.items() if raw_words & words]
        if topics or raw_words & CLIMATE_GENERIC:
            intents.add("climate")
            try:
                extra += self.sources.power_evidence(island, topics or None)
            except SourceUnavailable:
                notes.append("NASA POWER data is unavailable right now")
        if raw_words & SPECIES_INTENT:
            intents.add("species")
            try:
                extra += self.sources.gbif_evidence(island, creature.slug)
            except SourceUnavailable:
                notes.append("GBIF data is unavailable right now")
        return extra, intents, notes

    @staticmethod
    def _unknown_entity(query: str, index: BM25, skip: set[str]) -> bool:
        """True when the question names a capitalised word (not the first word) that no fact contains."""
        for m in list(re.finditer(r"[A-Za-z\u00c0-\u024f]+", query))[1:]:
            w = m.group(0)
            if not w[0].isupper() or len(w) < 3:
                continue
            st = _stem(_strip_accents(w).lower())
            if st in STOP or st in skip or st in index.vocab:
                continue
            return True
        return False

    def library(
        self, island_slug: str, query: str, category: str | None = None, creature_slug: str | None = None, limit: int = 40
    ) -> LibraryResult:
        """Keyword search over every fact of an island (all creatures), for the browsable library.

        An empty query lists the island's facts in file order. Climate and species words also bring in
        live NASA POWER and GBIF entries for the selected creature.
        """
        island = self.islands.get(island_slug)
        creature = island.creature(creature_slug)
        key = (island.slug, "*")
        if key not in self._index:
            self._index[key] = BM25([self.islands.fact_to_evidence(island, f) for f in island.facts])
        index = self._index[key]
        q = _norm(query).strip()
        notes: list[str] = []
        quality, partial_ids = "browse", set()
        if not q:
            matched = [e for e in (d.evidence for d in index.docs)]
        else:
            raw_words = set(re.findall(r"[a-z0-9]+", q))
            cats = {c for c, pat in CATEGORY_PATTERNS.items() if re.search(pat, q)}
            boost = {d.evidence.id: 1.25 for d in index.docs if d.evidence.category in cats}
            ranked = index.score(expand(query, index.vocab), boost)
            top = ranked[0][0] if ranked else 0.0
            skip = set(tokenize(" ".join([island.name, island.slug.replace("-", " "), *island.alt_names])))
            names = set(tokenize(" ".join(f"{c.common_name} {c.scientific_name}" for c in island.creatures)))
            terms = query_terms(query, index, skip, names)
            total_w = sum(t.weight for t in terms) or 1.0
            unknown_share = sum(t.weight for t in terms if not t.known) / total_w
            if self._unknown_entity(query, index, skip | names):
                unknown_share = 1.0  # a capitalised name the library has never seen: the question is about something else
            by_id = {d.evidence.id: d for d in index.docs}
            matched, strong = [], 0
            if not terms and top < MIN_OVERLAP_SCORE and cats:
                # "where is X": no content words left, so answer with the facts of the category the question asks for
                for _, e in ranked:
                    if e.category in cats and len(matched) < 5:
                        matched.append(e)
                        strong += 1
            elif not terms and top >= MIN_OVERLAP_SCORE:
                # the question only names the island or its creature, or asks "where"/"who": rank by the expanded query
                for sc, e in ranked:
                    if sc < 0.3 * top:
                        break
                    matched.append(e)
                    strong += 1
            elif unknown_share < MAX_UNKNOWN_SHARE and top >= MIN_OVERLAP_SCORE:
                # when every word of the question is known, the unknown-word guard has nothing to catch, so a
                # fact may cover a smaller share of the (idf-weighted) words and still count
                strong_at, partial_at = (0.45, 0.2) if unknown_share == 0 else (STRONG_COVERAGE, PARTIAL_COVERAGE)
                for sc, e in ranked:
                    if sc < 0.3 * top:
                        break
                    toks = by_id[e.id].tf
                    cov = sum(t.weight for t in terms if t.alts & toks.keys()) / total_w
                    if cov >= strong_at:
                        matched.append(e)
                        strong += 1
                    elif cov >= partial_at:
                        matched.append(e)
                        partial_ids.add(e.id)
            live: list[Evidence] = []
            if unknown_share < MAX_UNKNOWN_SHARE:
                live, _, notes = self._live(island, creature, raw_words)
            matched = live + matched
            quality = "strong" if (strong or live) else "partial" if matched else "none"
            if quality == "none":
                notes.append("No entry in this island's library covers the words of the question")
        counts: Counter = Counter(e.category for e in matched)
        if category:
            matched = [e for e in matched if e.category == category]
        return LibraryResult(results=matched[:limit], counts=dict(counts), total=len(matched), notes=notes,
                             quality=quality, partial_ids=partial_ids)

    def search(self, island_slug: str, query: str, creature_slug: str | None = None) -> RetrievalResult:
        island = self.islands.get(island_slug)
        creature = island.creature(creature_slug)
        index = self._bm25(island, creature.slug)
        q = _norm(query)
        raw_words = set(re.findall(r"[a-z0-9]+", q))

        boost: dict[str, float] = {}
        first_person = bool(raw_words & FIRST_PERSON)
        cats = {c for c, pat in CATEGORY_PATTERNS.items() if re.search(pat, q)}
        for d in index.docs:
            e = d.evidence
            m = 1.0
            if first_person and e.subject == creature.slug:
                m *= 1.3
            if e.category in cats:
                m *= 1.25
            if m != 1.0:
                boost[e.id] = m

        ranked = index.score(expand(query, index.vocab), boost)
        top = ranked[0][0] if ranked else 0.0
        picked = [e for s, e in ranked[: self.k] if s > 0] if top >= MIN_OVERLAP_SCORE else []
        if picked:
            # category questions ("what threatens you?") also pull the best facts of that category
            have = {e.id for e in picked}
            for cat in sorted(cats)[:2]:
                extra_cat = [e for _, e in ranked if e.category == cat and e.id not in have][:3]
                picked += extra_cat
                have.update(e.id for e in extra_cat)

        extra, intents, notes = self._live(island, creature, raw_words)

        evidence = extra + picked
        return RetrievalResult(
            evidence=evidence,
            top_score=top,
            has_evidence=bool(evidence),
            intents=intents,
            notes=notes,
        )
