// Cloudflare Worker in front of foreverinfo.io/raid* (every other address goes straight to GitHub Pages).
//  - /raid?<code> (or /raid.html?<code>): the page from GitHub Pages, with its link-preview tags pointing at a picture
//    of that roster, so a shared raid link shows the raid instead of the site logo
//  - /raid-preview.png?<code>: that picture, drawn here and kept in Cloudflare's cache
// If anything goes wrong the visitor still gets the normal page.
import { Resvg, initWasm } from "@resvg/resvg-wasm";
import resvgWasm from "@resvg/resvg-wasm/index_bg.wasm";
import fontData from "./DejaVuSans-Bold.ttf";
import { parseRoster, playerCount, describe, iconsOf, rosterSvg } from "./roster.js";

const PREVIEW_VERSION = "1";   // bump when the picture's design changes, so chat apps fetch the new one

let wasmReady;
const ready = () => (wasmReady ||= initWasm(resvgWasm));

// the query as the page reads it (tc/template2.html: curLink): decoded, and not someone's tracking tag (?fbclid=...)
function rosterQuery(url) {
  let q = url.search.slice(1);
  try { q = decodeURIComponent(q); } catch { return ""; }
  q = q.replace(/&v=\d+$/, "");   // the picture's own version tag (PREVIEW_VERSION)
  return q.includes("=") ? "" : q;
}

const b64 = buf => { let s = ""; const a = new Uint8Array(buf); for (let i = 0; i < a.length; i += 0x8000) s += String.fromCharCode(...a.subarray(i, i + 0x8000)); return btoa(s); };

async function previewPng(url, env, ctx) {
  const cache = caches.default, key = new Request(url.toString());
  const hit = await cache.match(key);
  if (hit) return hit;
  const roster = parseRoster(rosterQuery(url));
  const icons = {};
  await Promise.all(iconsOf(roster).map(async name => {
    const r = await fetch(`${env.ORIGIN}/images/icons/${name}.jpg`, { cf: { cacheTtl: 604800, cacheEverything: true } });
    if (r.ok) icons[name] = "data:image/jpeg;base64," + b64(await r.arrayBuffer());
  }));
  await ready();
  const png = new Resvg(rosterSvg(roster, icons), {
    font: { fontBuffers: [new Uint8Array(fontData)], loadSystemFonts: false, defaultFontFamily: "DejaVu Sans" },
  }).render().asPng();
  const res = new Response(png, { headers: { "content-type": "image/png", "cache-control": "public, max-age=604800" } });
  ctx.waitUntil(cache.put(key, res.clone()));
  return res;
}

// point the page's preview tags at this roster's picture
function withPreview(page, url, roster) {
  const q = url.search.slice(1);
  const img = `https://foreverinfo.io/raid-preview.png?${q}&v=${PREVIEW_VERSION}`;
  const desc = describe(roster);
  const set = v => ({ element(el) { el.setAttribute("content", v); } });
  return new HTMLRewriter()
    .on('meta[property="og:image"]', set(img))
    .on('meta[property="og:image:alt"]', set(`Raid roster: ${desc}`))
    .on('meta[property="og:description"]', set(`${desc}. Plan a WoW Forever raid on Forever Info.`))
    .on('meta[property="og:url"]', set(`https://foreverinfo.io/raid?${q}`))
    .on('meta[name="twitter:image"]', set(img))
    .transform(page);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = new URL(url.pathname + url.search, env.ORIGIN);
    try {
      if (url.pathname === "/raid-preview.png") return await previewPng(url, env, ctx);
      if (url.pathname === "/raid" || url.pathname === "/raid.html") {
        const roster = parseRoster(rosterQuery(url));
        const page = await fetch(origin, request);
        if (!page.ok || !playerCount(roster) || !(page.headers.get("content-type") || "").includes("text/html")) return page;
        return withPreview(page, url, roster);
      }
    } catch (e) {
      console.error(e);
    }
    return fetch(origin, request);
  },
};
