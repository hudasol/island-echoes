(() => {
  "use strict";
  const $ = (id) => document.getElementById(id);
  const pct = (x) => (x == null ? "n/a" : (100 * x).toFixed(1) + "%");
  const ms = (d) => (!d || d.p50 == null ? "n/a" : `${Math.round(d.p50)} / ${Math.round(d.p95)} ms`);
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };

  function card(value, label) { const c = el("div", "card"); c.append(el("div", "v", String(value)), el("div", "l", label)); return c; }

  function table(title, rows, head) {
    const wrap = el("div"); wrap.append(el("h2", null, title));
    if (!rows.length) { wrap.append(el("p", "muted", "Nothing recorded in this window.")); return wrap; }
    const t = el("table"), th = el("tr");
    head.forEach((h) => th.append(el("th", null, h))); t.append(th);
    rows.forEach((r) => { const tr = el("tr"); r.forEach((c) => { const td = el("td"); if (c instanceof Node) td.append(c); else td.textContent = c; tr.append(td); }); t.append(tr); });
    wrap.append(t); return wrap;
  }
  function counts(obj) {
    const max = Math.max(1, ...Object.values(obj));
    return Object.entries(obj).map(([k, v]) => { const b = el("span", "bar"); b.style.width = Math.round((v / max) * 160) + "px"; const c = el("span"); c.append(b, document.createTextNode(" " + v)); return [k, c]; });
  }

  async function load() {
    const days = $("days").value;
    $("status").textContent = "Loading…";
    try {
      const r = await fetch(`/api/stats?days=${days}`); if (!r.ok) throw new Error(r.status === 429 ? "Too many requests. Wait a moment." : "Could not load statistics.");
      const s = await r.json();
      if (!s.events) { $("status").textContent = "No activity recorded in this window yet."; $("cards").hidden = $("tables").hidden = true; return; }
      $("status").textContent = `${s.events} events in the last ${s.window_days} days. Retrieval: ${s.retrieval_mode}. Model: ${s.llm || "none (library only)"}.`;
      const L = s.library, C = s.chat, cards = $("cards"), tables = $("tables");
      cards.replaceChildren(
        card(L.lookups, "library lookups"), card(pct(L.no_answer_rate), "searches the library could not answer"),
        card(ms(L.latency_ms), "library latency p50 / p95"), card(C.turns, "chat turns"), card(pct(C.answer_rate), "chat answer rate"),
        card(pct(C.grounded_sentence_rate), "sentences passing every source check"), card(pct(C.repair_rate), "answers needing a repair retry"),
        card(ms(C.latency_ms.total), "chat latency p50 / p95"));
      tables.replaceChildren(
        table("Library result quality", counts(L.quality), ["Quality", "Searches"]),
        table("Activity by island", counts(s.by_island), ["Island", "Events"]),
        table("Activity by day (UTC)", counts(s.by_day), ["Day", "Events"]),
        table("Chat models", counts(C.by_model), ["Provider:model", "Turns"]),
        ...(s.unanswered_questions ? [table("Questions the library could not answer", s.unanswered_questions.map((u) => [u.island, u.question]), ["Island", "Question"])] : []));
      cards.hidden = tables.hidden = false;
    } catch (e) { $("status").textContent = e.message; }
  }
  $("days").addEventListener("change", load);
  load();
})();
