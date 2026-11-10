// Service worker (live tagging and presentations offline): static assets cache-first, live pages
// network-first with a cached fallback so the courtside page reloads without connection.
// Presentations packed for offline use (addendum 01, 4.1) live in their own caches "hb-pres-<id>",
// filled explicitly by the app; their media, data and presenter page are served from there when
// the network is gone. Other API data is never cached.
const CACHE = "hb-live-v1";
const PACKED = /^\/v1\/orgs\/[^/]+\/(videos\/[^/]+\/media\/|presentations\/[^/]+$|slides\/[^/]+\/image$|plays\/[^/]+$)/;

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE && !k.startsWith("hb-pres-")).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/_next/static/")) {
    event.respondWith(
      caches.match(req).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            if (res.ok) caches.open(CACHE).then((c) => c.put(req, res.clone()));
            return res;
          }),
      ),
    );
    return;
  }
  if (PACKED.test(url.pathname) || (req.mode === "navigate" && /\/presentations\/[^/]+\/present$/.test(url.pathname))) {
    // network first; packed presentations answer from their cache when offline
    event.respondWith(fetch(req).catch(() => caches.match(req, { ignoreSearch: false }).then((hit) => hit || Response.error())));
    return;
  }
  // Spieltag (and its old address /live) works offline
  if (req.mode === "navigate" && /\/matches\/[^/]+\/(live|matchday)$/.test(url.pathname)) {
    event.respondWith(
      fetch(req)
        .then((res) => {
          if (res.ok) caches.open(CACHE).then((c) => c.put(req, res.clone()));
          return res;
        })
        .catch(() => caches.match(req).then((hit) => hit || Response.error())),
    );
  }
});
