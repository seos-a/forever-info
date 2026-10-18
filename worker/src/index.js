// Cloudflare Worker in front of foreverinfo.io/raid* (every other address goes straight to GitHub Pages).
//  - /raid?<code> (or /raid.html?<code>): the page from GitHub Pages, with its link-preview tags pointing at a picture
//    of that roster, so a shared raid link shows the raid instead of the site logo
//  - /raid-preview.png?<code>: that picture, drawn here and kept in Cloudflare's cache
//  - POST /raid-share (body: a raid code): stores the roster in KV under a short id and answers {"url": ".../raid/<id>"},
//    for the page's Copy Link; the same roster always gets the same id
//  - /raid/<id>: sends the visitor (or a chat app) on to /raid?<code>
// If anything goes wrong the visitor still gets the normal page.
import { Resvg, initWasm } from "@resvg/resvg-wasm";
import resvgWasm from "@resvg/resvg-wasm/index_bg.wasm";
import fontData from "./DejaVuSans-Bold.ttf";
import { parseRoster, encodeRoster, playerCount, describe, iconsOf, rosterSvg } from "./roster.js";

const PREVIEW_VERSION = "2";   // bump when the picture's design changes, so chat apps fetch the new one

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

// a short id for a roster: 7 letters and digits from its SHA-256, so sharing the same raid twice gives the same link
const B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
async function shortId(code) {
  const h = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(code)));
  let id = ""; for (let i = 0; i < 7; i++) id += B62[h[i] % 62];
  return id;
}

async function share(request, env) {
  if (!env.RAID_LINKS) return Response.json({ error: "short links aren't set up" }, { status: 503 });   // the page then copies the long link
  const body = (await request.text()).slice(0, 2000);
  const roster = parseRoster(body.trim());
  if (!playerCount(roster)) return Response.json({ error: "empty raid" }, { status: 400 });
  const code = encodeRoster(roster), id = await shortId(code);
  if ((await env.RAID_LINKS.get(id)) !== code) await env.RAID_LINKS.put(id, code);
  return Response.json({ url: `https://foreverinfo.io/raid/${id}` }, { headers: { "cache-control": "no-store" } });
}

async function openShort(id, env) {
  const code = env.RAID_LINKS && /^[0-9A-Za-z]{7}$/.test(id) ? await env.RAID_LINKS.get(id) : null;
  // names may hold any letters: percent-encode them for the address, as the page's own links do
  return Response.redirect(code ? `https://foreverinfo.io/raid?${encodeURIComponent(code).replace(/%2C/g, ",").replace(/%7E/gi, "~")}` : "https://foreverinfo.io/raid", 302);
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const origin = new URL(url.pathname + url.search, env.ORIGIN);
    try {
      if (url.pathname === "/raid-preview.png") return await previewPng(url, env, ctx);
      if (url.pathname === "/raid-share" && request.method === "POST") return await share(request, env);
      const short = url.pathname.match(/^\/raid\/([0-9A-Za-z]{7})\/?$/);
      if (short) return await openShort(short[1], env);
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
