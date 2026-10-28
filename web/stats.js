(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const get = async (path) => { const r = await fetch(path); if (!r.ok) throw new Error(`${path}: ${r.status}`); return r.json(); };
  const f2 = (x) => x.toFixed(2);
  const pct = (x) => (x == null ? "n/a" : `${(100 * x).toFixed(1)}%`);
  const MODE = { bm25: "BM25 keyword", dense: "Dense (bge-small)", hybrid: "Hybrid, rank fusion", random: "Random order", "file-order": "File order", overlap: "Word overlap" };
  const FLOORS = new Set(["random", "file-order", "overlap"]);

  /* Wilson score interval for k of n, the interval the evaluation report uses for proportions. */
  function wilson(k, n, z = 1.96) {
    if (!n) return [0, 0];
    const p = k / n, d = 1 + (z * z) / n, c = p + (z * z) / (2 * n), h = z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n));
    return [(c - h) / d, (c + h) / d];
  }

  function table(head, rows, opts = {}) {
    const t = el("table");
    if (opts.caption) t.append(el("caption", null, opts.caption));
    const thead = el("thead"), hr = el("tr");
    head.forEach(([label, cls]) => { const th = el("th", cls, label); th.scope = "col"; hr.append(th); });
    thead.append(hr); t.append(thead);
    const tb = el("tbody");
    rows.forEach((r) => {
      const tr = el("tr", r.cls);
      r.cells.forEach((c, i) => {
        const cell = el(i === 0 ? "th" : "td", head[i][1]);
        if (i === 0) cell.scope = "row";
        if (c instanceof Node) cell.append(c); else cell.textContent = c;
        tr.append(cell);
      });
      tb.append(tr);
    });
    t.append(tb);
    if (opts.foot) { const tf = el("tfoot"), tr = el("tr"); opts.foot.forEach((c, i) => { const cell = el(i === 0 ? "th" : "td", head[i][1]); if (i === 0) cell.scope = "row"; if (c instanceof Node) cell.append(c); else cell.textContent = c; tr.append(cell); }); tf.append(tr); t.append(tf); }
    return t;
  }
  const withSub = (main, sub) => { const f = document.createDocumentFragment(); f.append(main); if (sub) f.append(el("span", "sub", sub)); return f; };

  /* A dot and whisker: the point estimate and its interval on a 0 to 1 axis. */
  function range(mean, lo, hi, label) {
    const r = el("div", "range"); r.setAttribute("role", "img"); r.setAttribute("aria-label", label);
    const ci = el("span", "ci"), pt = el("span", "pt");
    ci.style.left = `${100 * lo}%`; ci.style.width = `${Math.max(0.5, 100 * (hi - lo))}%`; pt.style.left = `${100 * mean}%`;
    r.append(ci, pt); return r;
  }
  const valueCell = (mean, lo, hi) => { const s = el("span", "num-cell", f2(mean)); s.append(el("small", null, `${f2(lo)} to ${f2(hi)}`)); return s; };
  const countCell = (k, n) => { const s = el("span", "num-cell", `${k}/${n}`); s.append(el("small", null, `${Math.round((100 * k) / n)}%`)); return s; };

  /* ---------------- data set ---------------- */
  function renderData(ov) {
    const key = el("div", "key");
    [["h", "High"], ["m", "Medium"], ["l", "Low"]].forEach(([c, l]) => { const s = el("span"); const b = el("b"); b.className = c; b.style.background = `var(--${{ h: "high", m: "med", l: "low" }[c]})`; s.append(b, l); key.append(s); });
    const rows = ov.islands.map((i) => {
      const bar = el("div", "stack"); bar.setAttribute("role", "img");
      bar.setAttribute("aria-label", `${i.confidence.high} high, ${i.confidence.medium} medium, ${i.confidence.low} low confidence facts`);
      [["h", i.confidence.high], ["m", i.confidence.medium], ["l", i.confidence.low]].forEach(([c, n]) => { const s = el("i", c); s.style.width = `${(100 * n) / i.facts}%`; bar.append(s); });
      return { cells: [withSub(document.createTextNode(i.name), i.creatures.map((c) => c.name).join(", ")), String(i.facts), bar, String(i.sources), i.power_as_of || "none", i.gbif_as_of || "none"] };
    });
    const t = ov.totals, share = pct(t.wikipedia_share);
    const head = [["Island"], ["Facts", "n"], ["Confidence label"], ["Sources", "n hide-sm"], ["NASA POWER as of", "n hide-sm"], ["GBIF as of", "n hide-sm"]];
    const tbl = table(head, rows, { foot: ["All islands", String(t.facts), `${t.confidence.high} high, ${t.confidence.medium} medium, ${t.confidence.low} low`, String(t.distinct_sources), "", ""] });
    tbl.querySelectorAll("tbody td:nth-child(5), tbody td:nth-child(6), tbody td:nth-child(4)").forEach((c) => c.classList.add("n"));
    $("data-body").replaceChildren(key, tbl,
      el("p", "note", `${share} of facts cite Wikipedia. The confidence label is the compiler's judgement of how directly the source supports the statement. Conservation categories come from GBIF's copy of the IUCN Red List.`));
  }

  /* ---------------- retrieval ---------------- */
  function retrievalTable(set, name, caption) {
    const head = [["Ranking"], ["hit@1", "n"], ["hit@5 with 95% interval"], ["", "n"], ["MRR", "n"]];
    head[3] = ["", "n hide-sm"];
    const ordered = [...set.modes].sort((a, b) => (FLOORS.has(a.mode) - FLOORS.has(b.mode)));
    const rows = ordered.map((m) => ({
      cls: FLOORS.has(m.mode) ? "floor" : "",
      cells: [MODE[m.mode] || m.mode, f2(m["hit@1"].mean),
        range(m["hit@5"].mean, m["hit@5"].ci[0], m["hit@5"].ci[1], `${MODE[m.mode]}: hit at 5 is ${f2(m["hit@5"].mean)}, interval ${f2(m["hit@5"].ci[0])} to ${f2(m["hit@5"].ci[1])}`),
        valueCell(m["hit@5"].mean, m["hit@5"].ci[0], m["hit@5"].ci[1]), f2(m.mrr.mean)],
    }));
    const tbl = table(head, rows, { caption: `${caption} (${set.n} questions)` });
    tbl.querySelectorAll("tbody td:nth-child(2), tbody td:nth-child(5)").forEach((c) => c.classList.add("n"));
    tbl.querySelectorAll("tbody td:nth-child(4)").forEach((c) => c.classList.add("hide-sm"));
    return tbl;
  }
  function renderRetrieval(ev) {
    const box = $("retrieval-body"); box.replaceChildren();
    const grid = el("div", "grid2");
    if (ev.retrieval.heldout) box.append(retrievalTable(ev.retrieval.heldout, "heldout", "Held out set, never used for tuning"));
    if (ev.retrieval.dev) box.append(retrievalTable(ev.retrieval.dev, "dev", "Development set, used while building"));
    const pairs = ev.retrieval.heldout?.paired || [];
    if (pairs.length) {
      const rows = pairs.map((p) => ({ cells: [`${MODE[p.a]} against ${MODE[p.b]}`, String(p.only_a), String(p.only_b), p.p < 0.001 ? "< 0.001" : p.p.toFixed(3)] }));
      const tbl = table([["Paired comparison on hit@5"], ["Only first right", "n"], ["Only second right", "n"], ["Exact p", "n"]], rows, { caption: "Exact McNemar test on the held out questions" });
      tbl.querySelectorAll("tbody td").forEach((c) => c.classList.add("n"));
      box.append(tbl);
    }
    void grid;
  }

  /* ---------------- end to end answers ---------------- */
  function renderAnswers(ev) {
    const rows = ev.baselines;
    if (!rows.length) { $("answers-body").replaceChildren(el("p", "empty", "No end to end runs are stored.")); return; }
    const model = rows.find((r) => r.system === "full")?.model || "";
    $("answers-body").dataset.model = model;
    const head = [["System"], ["Questions passed, 95% interval"], ["", "n hide-sm"], ["False refusals", "n"], ["Refusal accuracy", "n hide-sm"], ["Key fact recall", "n hide-sm"]];
    const body = rows.map((r) => {
      const p = r.passed, [lo, hi] = wilson(p.k, p.n);
      return {
        cells: [withSub(document.createTextNode(r.label), r.system === "refuse-all" ? "no model" : `${r.model.replace(/^llamacpp:/, "")}${r.retrieval ? `, ${r.retrieval} retrieval` : ", no retrieval"}`),
          range(p.k / p.n, lo, hi, `${r.label}: ${p.k} of ${p.n} passed`), valueCell(p.k / p.n, lo, hi),
          `${r.false_refusals.k}/${r.false_refusals.n}`, `${r.refusal_accuracy.k}/${r.refusal_accuracy.n}`, `${r.key_fact_recall.k}/${r.key_fact_recall.n}`],
      };
    });
    const tbl = table(head, body);
    tbl.querySelectorAll("tbody td:nth-child(4), tbody td:nth-child(5), tbody td:nth-child(6)").forEach((c) => c.classList.add("n"));
    tbl.querySelectorAll("tbody td:nth-child(3)").forEach((c) => c.classList.add("hide-sm"));
    tbl.querySelectorAll("tbody td:nth-child(5), tbody td:nth-child(6)").forEach((c) => c.classList.add("hide-sm"));
    $("answers-body").replaceChildren(tbl, el("p", "note", `A question passes when every check on it holds: answered or refused as it should, required values present, nothing outside the cited sources. False refusals are answerable questions the system declined. Model runs at commit ${(rows.find((r) => r.system === "full") || rows[0]).commit}.`));
  }

  /* ---------------- traffic ---------------- */
  function spark(byDay) {
    const days = Object.keys(byDay).sort(); if (days.length < 2) return null;
    const vals = days.map((d) => byDay[d]), hi = Math.max(...vals), NS = "http://www.w3.org/2000/svg", svg = document.createElementNS(NS, "svg");
    svg.setAttribute("viewBox", "0 0 100 36"); svg.setAttribute("preserveAspectRatio", "none"); svg.setAttribute("class", "spark"); svg.setAttribute("role", "img");
    svg.setAttribute("aria-label", `Requests per day, ${days[0]} to ${days[days.length - 1]}, peak ${hi}`);
    const p = document.createElementNS(NS, "path");
    p.setAttribute("d", vals.map((v, i) => `${i ? "L" : "M"}${((i / (vals.length - 1)) * 100).toFixed(1)} ${(34 - (v / hi) * 32).toFixed(1)}`).join(" "));
    svg.append(p); return svg;
  }
  const lat = (d) => (!d || d.p50 == null ? "none" : `${Math.round(d.p50)} / ${Math.round(d.p95)} ms`);
  async function loadTraffic() {
    const box = $("traffic-body");
    try {
      const s = await get(`/api/stats?days=${$("days").value}`);
      if (!s.events) { box.replaceChildren(el("p", "empty", "No requests recorded in this window.")); return; }
      const L = s.library, C = s.chat;
      const rows = [
        ["Library lookups", String(L.lookups)], ["Library searches with no answer", `${L.searches ? pct(L.no_answer_rate) : "no searches"}`],
        ["Library latency, median / p95", lat(L.latency_ms)], ["Chat turns", String(C.turns)],
        ["Chat answer rate", C.turns ? pct(C.answer_rate) : "no turns"], ["Sentences passing every source check", C.turns ? pct(C.grounded_sentence_rate) : "no turns"],
        ["Answers that needed a repair", C.turns ? pct(C.repair_rate) : "no turns"], ["Chat latency, median / p95", lat(C.latency_ms.total)],
      ].map(([k, v]) => ({ cells: [k, v] }));
      const left = table([["Measure"], ["Value", "n"]], rows, { caption: `${s.events} requests in ${s.window_days} ${s.window_days === 1 ? "day" : "days"}` });
      left.querySelectorAll("tbody td").forEach((c) => c.classList.add("n"));
      const isl = Object.entries(s.by_island).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({ cells: [k, String(v)] }));
      const right = isl.length ? table([["Island"], ["Requests", "n"]], isl, { caption: "By island" }) : el("div");
      right.querySelectorAll?.("tbody td").forEach((c) => c.classList.add("n"));
      const grid = el("div", "grid2"); grid.append(left, right);
      const sp = spark(s.by_day);
      box.replaceChildren(grid, ...(sp ? [sp] : []));
    } catch (e) { box.replaceChildren(el("p", "empty", `Traffic could not be read. ${e.message}`)); }
  }

  async function boot() {
    const [health, ov, ev] = await Promise.allSettled([get("/api/health"), get("/api/overview"), get("/api/evaluation")]);
    if (health.status === "fulfilled") {
      const h = health.value;
      $("deck").textContent = `v${h.version} · ${h.islands} islands · retrieval ${h.retrieval_mode} · chat ${h.chat_enabled ? h.llm : "off"} · up ${Math.round(h.uptime_s / 60)} min`;
      $("build").textContent = `Island Echoes ${h.version}`;
    } else $("deck").textContent = "The server did not answer.";
    if (ov.status === "fulfilled") renderData(ov.value); else $("data-body").replaceChildren(el("p", "empty", "The data set summary is unavailable."));
    if (ev.status === "fulfilled") {
      renderRetrieval(ev.value); renderAnswers(ev.value);
      const m = $("answers-body").dataset.model;
      if (m) document.querySelector("#answers .lead").textContent = `Thirty frozen questions, one model (${m.replace(/^llamacpp:/, "")}, run through llama.cpp), identical scoring. Each row changes one component.`;
    } else { $("retrieval-body").replaceChildren(el("p", "empty", "No evaluation summary is installed.")); $("answers-body").replaceChildren(el("p", "empty", "No evaluation summary is installed.")); }
    $("days").addEventListener("change", loadTraffic); loadTraffic();
  }
  boot();
})();
