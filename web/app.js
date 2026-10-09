(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const GIBS = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best";
  const dayAgo = (n) => new Date(Date.now() - n * 864e5).toISOString().slice(0, 10);

  // NASA GIBS layers. `time` null means the layer is a static composite.
  const LAYERS = [
    { id: "truecolor", label: "True colour", layer: "VIIRS_SNPP_CorrectedReflectance_TrueColor", matrix: 9, ext: "jpeg", time: dayAgo(4), note: "VIIRS true colour from the Suomi NPP satellite, {d}." },
    { id: "relief", label: "Relief", layer: "BlueMarble_ShadedRelief_Bathymetry", matrix: 8, ext: "jpeg", time: null, note: "Blue Marble shaded relief with sea-floor bathymetry." },
    { id: "night", label: "Night lights", layer: "VIIRS_Black_Marble", matrix: 8, ext: "png", time: "2016-01-01", note: "VIIRS Black Marble night lights, 2016. Few lights on these islands." },
    { id: "sst", label: "Sea temperature", layer: "GHRSST_L4_MUR_Sea_Surface_Temperature", matrix: 7, ext: "png", time: dayAgo(4), note: "GHRSST MUR sea surface temperature, {d}." },
  ];
  const STATUS = { CR: "Critically endangered", EN: "Endangered", VU: "Vulnerable", EX: "Extinct", EW: "Extinct in the wild", NT: "Near threatened", LC: "Least concern", DD: "Data deficient" };
  const SUGGEST = {
    any: ["What is the climate like?", "How many records does GBIF hold for you?", "What threatens you?", "What is the history of this island?"],
    marine: ["How warm is the water?"], bird: ["How windy is it where you fly?"], reptile: ["How much rain falls here?"], mammal: ["How hot does it get?"],
  };

  const statusCode = (s) => /^critically/i.test(s) ? "CR" : /^endangered/i.test(s) ? "EN" : /^vulnerable/i.test(s) ? "VU" : /^extinct in the wild/i.test(s) ? "EW" : /^extinct/i.test(s) ? "EX" : /^near/i.test(s) ? "NT" : "";
  const S = { tab: "agent", lib: { q: "", cat: "" }, islands: [], island: null, creature: null, layer: LAYERS[0], paused: reduced, history: [], busy: false, narration: null, sensorSeq: 0 };
  let globe = null;

  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  const ISSUES = "https://github.com/hudasol/island-echoes/issues/new";
  function reportLink(e) {
    const a = el("a", "report", "Report a problem");
    const body = `Entry: ${e.id}\nSource: ${e.source_url}\nPage: ${location.href}\n\nWhat looks wrong or out of date:\n`;
    a.href = `${ISSUES}?${new URLSearchParams({ title: `Problem with ${e.id}`, body })}`;
    a.target = "_blank"; a.rel = "noopener noreferrer"; a.setAttribute("aria-label", `Report a problem with entry ${e.id}`);
    return a;
  }
  const api = async (path, opts) => {
    const r = await fetch(path, opts);
    if (!r.ok) { let d = ""; try { d = (await r.json()).detail; } catch (_) {} const e = new Error(d || `Request failed (${r.status})`); e.status = r.status; throw e; }
    return r.json();
  };

  /* ---------------- globe ---------------- */
  function tileUrl(l) {
    const t = l.time ? `${l.time}/` : "";
    return (x, y, z) => `${GIBS}/${l.layer}/default/${t}GoogleMapsCompatible_Level${l.matrix}/${z}/${y}/${x}.${l.ext}`;
  }
  function applyLayer(l) {
    S.layer = l;
    document.querySelectorAll("#layer-buttons button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.id === l.id)));
    $("layer-note").textContent = l.note.replace("{d}", l.time || "") + " Source: NASA GIBS.";
    $("attribution").textContent = `Imagery: ${l.label}${l.time ? `, ${l.time}` : ""}, NASA GIBS. Climate: NASA POWER. Species records: GBIF. Not a NASA product.`;
    if (globe) { globe.globeTileEngineClearCache?.(); globe.globeTileEngineMaxLevel(Math.min(l.matrix - 1, 8)); globe.globeTileEngineUrl(tileUrl(l)); }
  }
  function initGlobe(host) {
    try {
      globe = Globe({ animateIn: !reduced })(host)
        .backgroundColor("rgba(0,0,0,0)")
        .atmosphereColor("#2C8C99").atmosphereAltitude(0.18)
        .globeTileEngineMaxLevel(6)
        .htmlElementsData(S.islands).htmlLat("lat").htmlLng("lon").htmlAltitude(0.005)
        .htmlElement((d) => {
          const b = el("button", "pin"); b.type = "button"; b.dataset.slug = d.slug;
          b.setAttribute("aria-label", `${d.name}, ${d.territory}`); b.setAttribute("aria-pressed", "false");
          b.append(el("span", "tip", d.name));
          b.addEventListener("click", () => select(d.slug));
          return b;
        })
        .ringsData([]).ringColor(() => (t) => `rgba(244,182,63,${1 - t})`).ringMaxRadius(3).ringPropagationSpeed(2).ringRepeatPeriod(1400);
      globe.pointOfView({ lat: -8, lng: 40, altitude: 2.6 }, 0);
      const c = globe.controls(); c.autoRotate = !reduced; c.autoRotateSpeed = 0.35; c.minDistance = 140; c.enableDamping = true;
      const resize = () => globe.width(host.clientWidth).height(host.clientHeight);
      new ResizeObserver(resize).observe(host); resize();
      applyLayer(S.layer);
    } catch (err) {
      const e = $("globe-error"); e.hidden = false; e.textContent = "The 3D globe needs WebGL, which this browser has not enabled. The island list and field agent still work.";
    }
  }
  function flyTo(isl) {
    if (!globe) return;
    globe.controls().autoRotate = false;
    globe.pointOfView({ lat: isl.lat, lng: isl.lon, altitude: 0.8 }, reduced ? 0 : 1800);
    globe.ringsData([isl]).ringLat("lat").ringLng("lon");
    document.querySelectorAll(".pin").forEach((p) => p.setAttribute("aria-pressed", String(p.dataset.slug === isl.slug)));
  }

  /* ---------------- island list ---------------- */
  function buildIndex() {
    const ul = $("island-list");
    S.islands.forEach((isl) => {
      const li = el("li"), b = el("button", "island-btn"); b.type = "button"; b.dataset.slug = isl.slug;
      b.append(el("span", "n", isl.name), el("span", "c", isl.creatures.map((c) => c.common_name).join(", ")));
      b.addEventListener("click", () => select(isl.slug));
      li.append(b); ul.append(li);
    });
    const lb = $("layer-buttons");
    LAYERS.forEach((l) => {
      const b = el("button", null, l.label); b.type = "button"; b.dataset.id = l.id; b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", () => applyLayer(l)); lb.append(b);
    });
  }

  /* ---------------- selecting an island ---------------- */
  async function select(slug, creatureSlug, tab, userPick = true) {
    const isl = S.islands.find((i) => i.slug === slug); if (!isl) return;
    S.island = isl; S.history = []; S.lib = { q: "", cat: "" }; $("library-input").value = "";
    setTab(tab === "library" ? "library" : "agent");
    document.querySelectorAll(".island-btn").forEach((b) => b.setAttribute("aria-current", String(b.dataset.slug === slug)));
    $("globe-hint").hidden = true;
    $("console-empty").hidden = true; $("console-body").hidden = false;
    const con = $("console"); con.classList.add("open"); con.classList.remove("min");
    $("island-name").textContent = isl.name;
    $("island-territory").textContent = isl.territory; $("pin-note").textContent = isl.pin_note;
    flyTo(isl);
    const tabs = $("creature-tabs"); tabs.replaceChildren();
    isl.creatures.forEach((c) => {
      const b = el("button", null, c.common_name); b.type = "button"; b.setAttribute("role", "tab"); b.dataset.slug = c.slug;
      b.addEventListener("click", () => pickCreature(c.slug)); tabs.append(b);
    });
    pickCreature(creatureSlug || isl.creatures[0].slug);
    con.scrollTop = 0;
    if (userPick) $("island-name").focus({ preventScroll: true });
  }

  function pickCreature(slug) {
    const c = S.island.creatures.find((x) => x.slug === slug); S.creature = c; S.history = [];
    document.querySelectorAll("#creature-tabs button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.slug === slug)));
    syncTabStops($("creature-tabs"));
    $("creature-name").textContent = c.common_name;
    const code = statusCode(c.iucn_status), chip = $("status-chip");
    chip.textContent = STATUS[code] || c.iucn_status; chip.dataset.s = code;
    $("status-detail").textContent = `Status as reported: ${c.iucn_status}. ${c.status_note || ""}`;
    const cv = $("creature-canvas");
    cv.setAttribute("aria-label", `Decorative animation of a ${c.common_name} (${c.scientific_name}), a ${c.creature_type}. The facts are in the text below.`);
    Creatures.start(cv, c.creature_type, S.paused);
    $("log").replaceChildren(); $("ask-log").replaceChildren();
    suggestions(); askSuggestions();
    loadNarration();
    loadSensors(S.island, slug);
    runLibrary(true);
  }

  /* ---------------- sensors ---------------- */
  function spark(vals) {
    const v = vals.filter((x) => x != null); if (v.length < 2) return null;
    const lo = Math.min(...v), hi = Math.max(...v), rng = hi - lo || 1, W = 120, H = 26;
    const pts = vals.map((x, i) => [i * (W / 11), x == null ? null : H - 3 - ((x - lo) / rng) * (H - 6)]);
    const NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`); svg.setAttribute("preserveAspectRatio", "none"); svg.setAttribute("aria-hidden", "true");
    const p = document.createElementNS(NS, "path");
    p.setAttribute("d", pts.filter((q) => q[1] != null).map((q, i) => `${i ? "L" : "M"}${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join(" "));
    svg.append(p);
    return svg;
  }
  async function loadSensors(isl, creature) {
    const seq = ++S.sensorSeq, grid = $("sensor-grid"), note = $("sensor-note");
    grid.replaceChildren(); note.textContent = "Reading NASA POWER…"; $("sensor-warning").hidden = true;
    try {
      const d = await api(`/api/islands/${isl.slug}/sensors${creature ? `?creature=${encodeURIComponent(creature)}` : ""}`);
      if (seq !== S.sensorSeq) return;
      d.items.forEach((s) => {
        const box = el("div", "sensor"), v = el("div", "v", s.value == null ? "n/a" : String(s.value));
        v.append(el("small", null, s.unit));
        box.append(el("div", "l", s.label), v);
        const sp = spark(s.monthly); if (sp) { box.append(sp); const m = el("div", "m"); m.append(el("span", null, "Jan"), el("span", null, "Dec")); box.append(m); }
        grid.append(box);
      });
      note.textContent = `Annual means, ${d.period}, NASA POWER grid cell ${d.cell_lat.toFixed(1)}, ${d.cell_lon.toFixed(1)}. Data as of ${d.as_of}.`;
      $("sensor-warning").textContent = d.warning || ""; $("sensor-warning").hidden = !d.warning;
    } catch (e) {
      if (seq !== S.sensorSeq) return;
      note.textContent = "Sensor readings are unavailable right now. " + e.message;
    }
  }

  /* ---------------- rendering cited sentences ---------------- */
  function renderSentences(into, sentences, evidence, onCite) {
    const order = []; evidence.forEach((e) => { if (!order.includes(e.id)) order.push(e.id); });
    sentences.forEach((s, i) => {
      if (i) into.append(" ");
      const span = el("span", s.kind === "voice" ? "s-voice" : "s-fact", s.text);
      into.append(span);
      s.cites.forEach((id) => {
        const sup = el("sup", "cite"), a = el("a", null, `[${order.indexOf(id) + 1 || "?"}]`);
        a.href = "#"; a.title = id; a.addEventListener("click", (ev) => { ev.preventDefault(); onCite(id); });
        sup.append(a); into.append(sup);
      });
    });
  }
  function evidenceCard(e) {
    const d = el("div", "ev"); d.dataset.id = e.id;
    const head = el("div"); head.append(el("b", null, e.id), ` ${e.title}`);
    const body = el("div", null, e.text);
    const src = el("span", "src"), a = el("a", null, `${e.publisher}: ${e.source_title}`);
    a.href = e.source_url; a.target = "_blank"; a.rel = "noopener noreferrer";
    src.append(a, ` · retrieved ${e.as_of}` + (e.confidence ? ` · ${e.confidence} confidence` : ""));
    src.append(" · ", reportLink(e));
    d.append(head, body, src);
    return d;
  }
  function evidenceBlock(evidence) {
    const box = el("div", "evidence");
    const flash = (id) => { const t = box.querySelector(`[data-id="${CSS.escape(id)}"]`); if (t) { t.scrollIntoView({ block: "nearest", behavior: reduced ? "auto" : "smooth" }); t.classList.add("flash"); setTimeout(() => t.classList.remove("flash"), 1600); } };
    const cited = evidence.filter((e) => e.cited !== false);
    cited.forEach((e, i) => { const c = evidenceCard(e); c.querySelector("b").textContent = `[${i + 1}] ${e.id}`; box.append(c); });
    const rest = evidence.filter((e) => e.cited === false);
    if (rest.length) {
      const det = el("details"), sum = el("summary", null, `${rest.length} retrieved, not cited`); det.append(sum);
      rest.forEach((e) => det.append(evidenceCard(e))); box.append(det);
    }
    return { box, flash };
  }

  /* ---------------- narration ---------------- */
  async function loadNarration() {
    const t = $("narration-text"); t.textContent = "Tuning in…"; S.narration = null;
    speechSynthesis?.cancel?.();
    const isl = S.island.slug, cr = S.creature.slug;
    try {
      const d = await api(`/api/islands/${isl}/narration?creature=${encodeURIComponent(cr)}`);
      if (S.creature.slug !== cr) return;
      S.narration = d; t.replaceChildren();
      const ev = d.evidence.map((e) => ({ ...e, cited: true })), { box, flash } = evidenceBlock(ev);
      renderSentences(t, d.sentences, ev, flash);
      const det = el("details", "evidence"); det.append(el("summary", "muted small", `Sources for this report (${ev.length})`)); det.append(...box.children); t.append(det);
      det.addEventListener("toggle", () => {});
    } catch (e) { t.textContent = "The field report could not be loaded. " + e.message; }
  }
  function speak() {
    if (!("speechSynthesis" in window) || !S.narration) return;
    if (speechSynthesis.speaking) { speechSynthesis.cancel(); $("speak").textContent = "Read aloud"; return; }
    const u = new SpeechSynthesisUtterance(S.narration.sentences.map((s) => s.text).join(" "));
    u.rate = 0.95; u.onend = u.onerror = () => ($("speak").textContent = "Read aloud");
    speechSynthesis.speak(u); $("speak").textContent = "Stop";
  }


  /* ---------------- library ---------------- */
  const CATS = [
    ["species", "Species"], ["water", "Water and ocean"], ["climate", "Climate"], ["ecology", "Ecology"],
    ["creature", "Featured creature"], ["threats", "Threats"], ["conservation", "Conservation"],
    ["terrain", "Terrain"], ["geology", "Geology"], ["history", "History"], ["people_governance", "People"], ["location", "Location"],
  ];
  const CAT_LABEL = Object.fromEntries(CATS);
  const LIB_IDEAS = ["endangered birds", "coral reefs", "rainfall", "water supply", "plastic pollution", "threats", "history"];
  let libSeq = 0;

  function highlight(node, text, q) {
    const words = [...new Set(q.toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 2))];
    if (!words.length) { node.textContent = text; return; }
    const re = new RegExp(`\\b(${words.map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\w*`, "gi");
    let last = 0;
    for (const m of text.matchAll(re)) {
      node.append(text.slice(last, m.index)); const mk = el("mark", null, m[0]); node.append(mk); last = m.index + m[0].length;
    }
    node.append(text.slice(last));
  }
  function libCard(e, q, i, partial) {
    const c = el("article", "lib-card"), meta = el("div", "meta");
    meta.append(el("span", "k", e.kind === "fact" ? (CAT_LABEL[e.category] || e.category) : e.kind === "power" ? "NASA POWER" : "GBIF"));
    if (e.kind !== "fact") meta.append(el("span", "badge live", "live data"));
    if (partial) meta.append(el("span", "badge partial", "partial match"));
    if (e.kind === "fact") meta.append(el("span", `badge conf-${e.confidence}`, `${e.confidence[0].toUpperCase()}${e.confidence.slice(1)} confidence`));
    meta.append(el("span", null, e.id));
    const p = el("p"); highlight(p, e.text, q);
    const src = el("div", "src"), a = el("a", null, `${e.publisher}: ${e.source_title}`);
    a.href = e.source_url; a.target = "_blank"; a.rel = "noopener noreferrer";
    src.append(el("span", "ref", `Reference [${i}]: `), a, ` (retrieved ${e.as_of}) · `, reportLink(e));
    c.append(meta, p, src); return c;
  }
  async function runLibrary(first) {
    if (!S.island) return;
    const seq = ++libSeq, { q, cat } = S.lib, box = $("lib-results"), sum = $("lib-summary");
    sum.textContent = "Searching…";
    const params = new URLSearchParams({ island: S.island.slug, q, limit: "60" });
    if (cat) params.set("category", cat);
    if (S.creature) params.set("creature", S.creature.slug);
    try {
      const d = await api(`/api/library/search?${params}`);
      if (seq !== libSeq) return;
      const cats = $("lib-cats"); cats.replaceChildren();
      const all = Object.values(d.counts).reduce((x, y) => x + y, 0);
      [["", "All", all], ...CATS.map(([k, l]) => [k, l, d.counts[k] || 0])].forEach(([k, l, n]) => {
        const b = el("button", null, l); b.type = "button"; b.setAttribute("aria-pressed", String(cat === k)); b.disabled = !n && cat !== k;
        b.append(el("span", "n", String(n))); b.addEventListener("click", () => { S.lib.cat = k; runLibrary(); }); cats.append(b);
      });
      box.replaceChildren();
      if (!d.results.length) {
        box.append(el("p", "lib-empty", q
          ? `The library for ${S.island.name} has nothing that matches "${q}". The sources may not cover it. Try a different word, or clear the category filter.`
          : "No entries in this category."));
        sum.textContent = d.notes.join(". ");
      } else {
        sum.textContent = `${d.total} ${d.total === 1 ? "entry" : "entries"}${q ? ` for "${q}"` : ""}${cat ? ` in ${CAT_LABEL[cat]}` : ""}. ` + d.notes.join(". ");
        const part = new Set(d.partial_ids || []); d.results.forEach((e, i) => box.append(libCard(e, q, i + 1, part.has(e.id))));
        if (d.quality === "partial") sum.textContent = "Closest entries only. They match part of your question, and the library may not answer it. " + sum.textContent;
      }
    } catch (e) { if (seq === libSeq) { sum.textContent = ""; box.replaceChildren(el("p", "lib-empty", "The library could not be loaded. " + e.message)); } }
  }
  function libIdeas() {
    const box = $("lib-suggestions"); if (box.childElementCount) return;
    LIB_IDEAS.forEach((q) => { const b = el("button", null, q); b.type = "button"; b.addEventListener("click", () => { $("library-input").value = q; S.lib = { q, cat: "" }; runLibrary(); }); box.append(b); });
  }


  /* ---------------- tabs ---------------- */
  function setTab(name) {
    S.tab = name;
    ["agent", "library"].forEach((t) => {
      $("pane-" + t).hidden = t !== name; $("tab-" + t).setAttribute("aria-selected", String(t === name));
    });
    syncTabStops(document.querySelector(".panel-tabs"));
    if (S.island) history.replaceState(null, "", `#${S.island.slug}${name === "library" ? "/library" : ""}`);
  }

  /* ---------------- ask: answers come from the library ---------------- */
  const ASK_IDEAS = ["What is the climate like?", "Which species are endangered here?", "How warm is the water?", "What threatens the wildlife?", "What is the history of this island?"];
  function askSuggestions() {
    const box = $("ask-suggestions"); box.replaceChildren();
    ASK_IDEAS.forEach((q) => { const b = el("button", null, q); b.type = "button"; b.addEventListener("click", () => askLibrary(q)); box.append(b); });
  }
  // NASA POWER entries hold full monthly tables; in an answer show only the annual means (the table stays in the source card).
  function compactPower(t) {
    const parts = [...t.matchAll(/([A-Z][A-Za-z0-9 ]+?) \((\w+), ([^)]+)\): (?:[A-Z]{3} -?[\d.]+, )*ANN (-?\d+(?:\.\d+)?)/g)].map((m) => `${m[1].trim().toLowerCase()} ${m[4]} ${m[3] === "C" ? "°C" : m[3]}`);
    return parts.length ? `NASA POWER annual means for this island's grid cell: ${parts.join("; ")}. The monthly values are in the source below.` : t;
  }
  async function askLibrary(text) {
    text = text.trim(); if (!text || S.askBusy || !S.island) return;
    S.askBusy = true; $("ask-send").disabled = true;
    const log = $("ask-log");
    log.append(el("div", "msg user", text));
    const m = el("div", "msg agent pending"), body = el("div", "body", "Looking in the library…"); m.append(body); log.append(m);
    m.scrollIntoView({ block: "nearest", behavior: reduced ? "auto" : "smooth" });
    try {
      const params = new URLSearchParams({ island: S.island.slug, q: text, limit: "20" });
      if (S.creature) params.set("creature", S.creature.slug);
      const d = await api(`/api/library/search?${params}`);
      m.classList.remove("pending"); body.replaceChildren();
      const facts = d.results.filter((e) => e.kind === "fact"), live = d.results.filter((e) => e.kind !== "fact");
      const items = [...facts.slice(0, 4), ...live.slice(0, facts.length ? 1 : 2)];
      if (!items.length) {
        body.textContent = `The library has nothing on that yet. It has no entry for "${text}" for ${S.island.name}, so I will not guess.`;
        m.append(el("p", "missing", "Try different words, or browse the Library tab to see what is covered."));
      } else {
        body.append(el("p", "lead", d.quality === "partial"
          ? "The library has no entry that answers this directly. These are the closest, and they only match part of your question:"
          : `From the library (${d.total} ${d.total === 1 ? "entry matches" : "entries match"}${d.total > items.length ? `, showing the top ${items.length}` : ""}):`));
        const ev = items.map((e) => ({ ...e, cited: true })), { box, flash } = evidenceBlock(ev);
        ev.forEach((e) => {
          const pt = el("div", "point"); renderSentences(pt, [{ text: e.kind === "power" ? compactPower(e.text) : e.text, kind: "fact", cites: [e.id] }], ev, flash); body.append(pt);
        });
        const det = el("details", "evidence"); det.open = true;
        det.append(el("summary", "muted small", `Sources for this answer (${ev.length})`)); det.append(...box.children); m.append(det);
        if (d.total > items.length) {
          const more = el("button", "linklike more", `See all ${d.total} entries in the Library tab`); more.type = "button";
          more.addEventListener("click", () => { $("library-input").value = text; S.lib = { q: text, cat: "" }; runLibrary(); setTab("library"); }); m.append(more);
        }
      }
    } catch (e) { m.remove(); log.append(el("p", "msg error", e.message)); }
    finally { S.askBusy = false; $("ask-send").disabled = false; }
  }

  /* ---------------- chat ---------------- */
  function suggestions() {
    const box = $("suggestions"); box.replaceChildren();
    [...SUGGEST.any, ...(SUGGEST[S.creature.creature_type] || [])].slice(0, 5).forEach((q) => {
      const b = el("button", null, q); b.type = "button"; b.addEventListener("click", () => ask(q)); box.append(b);
    });
  }
  async function ask(text) {
    text = text.trim(); if (!text || S.busy) return;
    S.busy = true; $("send").disabled = true;
    const log = $("log");
    log.append(el("div", "msg user", text));
    const m = el("div", "msg agent pending"), body = el("div", "body", "Checking the sources…"); m.append(body); log.append(m);
    m.scrollIntoView({ block: "nearest", behavior: reduced ? "auto" : "smooth" });
    try {
      const r = await api("/api/chat", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ island: S.island.slug, creature: S.creature.slug, message: text, history: S.history.slice(-6) }),
      });
      m.classList.remove("pending"); body.textContent = "";
      const shown = r.evidence.filter((e) => e.cited);
      const { box, flash } = evidenceBlock(r.evidence);
      if (r.sentences.length) renderSentences(body, r.sentences, shown, flash);
      if (r.missing) m.append(el("p", "missing", r.missing));
      if (r.evidence.length) m.append(box);
      S.history.push({ role: "user", text }, { role: "agent", text: r.sentences.map((s) => s.text).join(" ").slice(0, 590) || r.missing.slice(0, 590) });
    } catch (e) {
      m.remove();
      log.append(el("p", "msg error", e.status === 429 ? "Too many questions. Wait a moment and ask again." : e.status === 503 ? "Chat is not switched on for this server yet." : e.message));
    } finally { S.busy = false; $("send").disabled = false; }
  }

  /* ---------------- keyboard support for tab lists ---------------- */
  function tabKeys(list) {
    list.addEventListener("keydown", (ev) => {
      const tabs = [...list.querySelectorAll('[role="tab"]')], i = tabs.indexOf(document.activeElement);
      if (i < 0) return;
      const to = { ArrowRight: (i + 1) % tabs.length, ArrowLeft: (i - 1 + tabs.length) % tabs.length, Home: 0, End: tabs.length - 1 }[ev.key];
      if (to == null) return;
      ev.preventDefault(); tabs[to].focus(); tabs[to].click();
    });
  }
  function syncTabStops(list) {
    list.querySelectorAll('[role="tab"]').forEach((t) => t.setAttribute("tabindex", t.getAttribute("aria-selected") === "true" ? "0" : "-1"));
  }

  /* ---------------- wiring ---------------- */
  function wire() {
    tabKeys(document.querySelector(".panel-tabs")); tabKeys($("creature-tabs"));
    const about = $("about");
    $("open-about").addEventListener("click", () => (about.showModal ? about.showModal() : about.setAttribute("open", "")));
    about.addEventListener("click", (ev) => { if (ev.target === about) about.close(); });
    libIdeas();
    $("tab-agent").addEventListener("click", () => setTab("agent"));
    $("tab-library").addEventListener("click", () => setTab("library"));
    $("open-library").addEventListener("click", () => setTab("library"));
    $("ask-form").addEventListener("submit", (e) => { e.preventDefault(); const i = $("ask-input"); const v = i.value; i.value = ""; askLibrary(v); });
    $("library-form").addEventListener("submit", (e) => { e.preventDefault(); S.lib = { q: $("library-input").value.trim(), cat: "" }; runLibrary(); });
    $("chat-form").addEventListener("submit", (e) => { e.preventDefault(); const i = $("chat-input"); const v = i.value; i.value = ""; ask(v); });
    $("speak").addEventListener("click", speak);
    if (!("speechSynthesis" in window)) $("speak").hidden = true;
    const pb = $("pause-anim");
    const syncPause = () => { pb.setAttribute("aria-pressed", String(S.paused)); pb.textContent = S.paused ? "Play motion" : "Pause motion"; };
    pb.addEventListener("click", () => { S.paused = !S.paused; Creatures.setPaused(S.paused); syncPause(); });
    syncPause();
    $("close-console").addEventListener("click", () => {
      speechSynthesis?.cancel?.(); Creatures.stop(); const back = S.island && document.querySelector(`.island-btn[data-slug="${S.island.slug}"]`); S.island = null;
      $("console").classList.remove("open"); $("console-body").hidden = true; $("console-empty").hidden = false;
      document.querySelectorAll(".island-btn").forEach((b) => b.setAttribute("aria-current", "false"));
      document.querySelectorAll(".pin").forEach((p) => p.setAttribute("aria-pressed", "false"));
      globe?.ringsData([]); history.replaceState(null, "", location.pathname); back?.focus();
    });
    $("sheet-handle").addEventListener("click", () => $("console").classList.toggle("min"));
    document.addEventListener("visibilitychange", () => { if (document.hidden) speechSynthesis?.cancel?.(); });
  }

  async function boot() {
    wire();
    try { S.islands = await api("/api/islands"); }
    catch (e) { $("globe-error").hidden = false; $("globe-error").textContent = "Could not reach the Island Echoes server. " + e.message; return; }
    buildIndex(); initGlobe($("globe"));
    api("/api/health").then((h) => { $("chat-details").hidden = !(h.chat_enabled && new URLSearchParams(location.search).has("claude")); }).catch(() => {});
    const [h, t] = location.hash.slice(1).split("/"); if (h && S.islands.some((i) => i.slug === h)) select(h, undefined, t, false);
    if ("serviceWorker" in navigator && location.protocol !== "file:") navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
  boot();
})();
