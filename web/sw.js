// Cache the app shell so the PWA opens offline; API responses are network-first with cache fallback.
const SHELL = "island-echoes-shell-v12";
const API = "island-echoes-api-v2";
const ASSETS = ["/", "/index.html", "/fonts.css", "/style.css", "/app.js", "/i18n.js", "/creatures.js", "/vendor/globe.bundle.js",
  "/fonts/newsreader-latin-400-normal.woff2", "/fonts/newsreader-latin-500-normal.woff2", "/fonts/newsreader-latin-400-italic.woff2",
  "/fonts/ibm-plex-sans-latin-400-normal.woff2", "/fonts/ibm-plex-sans-latin-500-normal.woff2", "/fonts/ibm-plex-sans-latin-600-normal.woff2",
  "/educator.css", "/manifest.webmanifest", "/icons/icon-192.png", "/icons/icon-512.png"];

self.addEventListener("install", (e) => {
  // no skipWaiting here: the page offers the update and asks this worker to take over (see the message handler)
  e.waitUntil(caches.open(SHELL).then((c) => c.addAll(ASSETS)));
});

self.addEventListener("message", (e) => {
  if (e.data && e.data.type === "SKIP_WAITING") self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => ![SHELL, API].includes(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin) return; // satellite tiles go straight to NASA
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/educator/")) {
    if (url.pathname === "/api/health" || url.pathname === "/api/v1/health") return;
    e.respondWith(
      fetch(req).then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(API).then((c) => c.put(req, copy)); }
        return res;
      }).catch(() => caches.match(req))
    );
    return;
  }
  e.respondWith(caches.match(req).then((hit) => hit || fetch(req)));
});
