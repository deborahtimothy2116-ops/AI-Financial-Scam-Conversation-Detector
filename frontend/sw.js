/* ScamShield service worker: receives messages and screenshots shared from other apps. */
const INBOX = "scamshield-share-inbox";

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method === "POST" && url.pathname === "/share-target") {
    event.respondWith(receiveShare(event.request));
  }
});

// Store what was shared, then open the app, which picks it up and scans it.
async function receiveShare(request) {
  const form = await request.formData();
  const text = [form.get("title"), form.get("text"), form.get("url")].filter(Boolean).join("\n").trim();
  const file = form.get("file");
  const cache = await caches.open(INBOX);
  await cache.put("/shared/text", new Response(text));
  if (file && typeof file !== "string" && file.size) {
    await cache.put("/shared/file", new Response(file, { headers: { "Content-Type": file.type, "X-File-Name": encodeURIComponent(file.name || "screenshot") } }));
  } else {
    await cache.delete("/shared/file");
  }
  return Response.redirect("/?shared=1", 303);
}
