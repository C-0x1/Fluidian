/* Fluidian service worker.
 *
 * Keeps the application shell (the page and the runtime's scripts, styles
 * and fonts) available when the network is not, so an installed app opens
 * instantly and can say that it is offline instead of showing a browser
 * error. Scenes, events and AI calls are never cached: they always go to
 * the engine.
 */
const CACHE = "fluidian-shell-v2";

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key !== CACHE) await caches.delete(key);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  const asset = url.pathname.startsWith("/_fluidian/runtime/") || url.pathname === "/favicon.svg";
  if (!asset && request.mode !== "navigate") return;
  if (url.pathname.startsWith("/_fluidian/") && !asset) return;
  const key = asset ? request : "/";            // every route is served by the same shell
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(request);
      if (response.ok) cache.put(key, response.clone());
      return response;
    } catch (error) {
      const hit = await cache.match(key);
      if (hit) return hit;
      throw error;
    }
  })());
});
