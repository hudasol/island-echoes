/* Island Echoes "Ask an island" widget. Include with:
 *   <script src="https://island-echoes.onrender.com/embed.js" data-island="socotra"></script>
 * It searches the sourced library through the public read only API and shows each result with its publisher, link,
 * retrieval date and confidence label. A question the sources cannot answer returns nothing. No cookies, no tracking. */
(function () {
  "use strict";
  var script = document.currentScript;
  if (!script) return;
  var base = new URL(script.src).origin;
  var island = script.getAttribute("data-island") || "socotra";
  var host = document.createElement("div");
  script.parentNode.insertBefore(host, script.nextSibling);
  var root = host.attachShadow({ mode: "open" });
  root.innerHTML =
    '<style>' +
    ':host{display:block;font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;color:#3B1F2C}' +
    '.box{max-width:560px;border:1px solid #E7B9C8;border-top:4px solid #F2A9BE;background:#FFF8FA;border-radius:6px;padding:14px 16px}' +
    'h2{font:500 18px Georgia,serif;margin:0 0 8px}form{display:flex;gap:8px}' +
    'input{flex:1;min-width:0;padding:7px 9px;border:1px solid #6A3B50;border-radius:4px;font:inherit;background:#fff;color:#3B1F2C}' +
    'button{padding:7px 12px;border:1px solid #8E2650;background:#8E2650;color:#fff;border-radius:4px;font:inherit;cursor:pointer}' +
    'input:focus-visible,button:focus-visible,a:focus-visible{outline:3px solid #8E2650;outline-offset:2px}' +
    'ol{padding-left:20px;margin:12px 0 0}li{margin:0 0 10px}small{display:block;color:#6A3B50}a{color:#8E2650}' +
    '.none{margin:12px 0 0;color:#6A3B50}.foot{margin-top:10px;font-size:12px;color:#6A3B50}' +
    '@media (prefers-color-scheme:dark){:host{color:#FBEAF0}.box{background:#2A1520;border-color:#5E3A4B}input{background:#38202C;color:#FBEAF0;border-color:#D9B3C3}' +
    'small,.none,.foot{color:#D9B3C3}a{color:#F7B4C9}button{background:#F7B4C9;border-color:#F7B4C9;color:#2A1520}}' +
    '</style>' +
    '<div class="box"><h2>Ask an island</h2>' +
    '<form><label class="sr" style="position:absolute;left:-9999px" for="q">Question about the island</label>' +
    '<input id="q" type="search" maxlength="200" placeholder="What is the highest point?" autocomplete="off">' +
    '<button type="submit">Search</button></form>' +
    '<div class="out" aria-live="polite"></div>' +
    '<p class="foot">Answers are quoted from cited sources. <a href="' + base + '/" target="_blank" rel="noopener">Island Echoes</a>, an independent project, not a NASA product.</p></div>';
  var form = root.querySelector("form"), input = root.querySelector("input"), out = root.querySelector(".out");

  function text(tag, str, cls) { var e = document.createElement(tag); e.textContent = str; if (cls) e.className = cls; return e; }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    var q = input.value.trim();
    if (!q) return;
    out.replaceChildren(text("p", "Searching.", "none"));
    fetch(base + "/api/v1/library/search?island=" + encodeURIComponent(island) + "&limit=3&q=" + encodeURIComponent(q))
      .then(function (r) {
        if (r.status === 429) throw new Error("Too many questions. Wait " + (r.headers.get("Retry-After") || "a minute") + " seconds.");
        if (!r.ok) throw new Error("The library is unavailable right now.");
        return r.json();
      })
      .then(function (d) {
        if (!d.results.length || d.quality === "none") { out.replaceChildren(text("p", "No source in this library answers that.", "none")); return; }
        var ol = document.createElement("ol");
        d.results.forEach(function (e) {
          var li = document.createElement("li");
          li.appendChild(text("span", e.text));
          var meta = document.createElement("small");
          var a = document.createElement("a");
          a.href = e.source_url; a.textContent = e.publisher; a.target = "_blank"; a.rel = "noopener noreferrer";
          meta.appendChild(a);
          meta.appendChild(document.createTextNode(", retrieved " + e.as_of + ", " + e.confidence + " confidence"));
          li.appendChild(meta);
          ol.appendChild(li);
        });
        out.replaceChildren(ol);
      })
      .catch(function (err) { out.replaceChildren(text("p", err.message, "none")); });
  });
})();
