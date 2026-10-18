// Reads a Raid Composition link and draws the roster as a 1200x630 SVG for link previews (Discord, iMessage...).
// Up to 20 players in at most 4 groups: each group's members by name (the player's name, or the spec's), with the spec
// icon. Bigger raids: all 8 groups as columns of spec icons ringed in their class colour.
import { RC_CODE, SPECS, CLASS_ORDER } from "./specs.js";

// The link's query, as the page reads it (tc/template2.html: rcDecode / rcClean): one character per slot, then
// optionally "~" and each slot's player name, comma-separated, spaces as "_".
const clean = v => v.normalize("NFC").replace(/[^\p{L}\p{N} '-]/gu, "").replace(/\s+/g, " ").trim().slice(0, 20);

export function parseRoster(query) {
  let code = query || "";
  const names = Array(40).fill("");
  const t = code.indexOf("~");
  if (t >= 0) {
    code.slice(t + 1).split(",").slice(0, 40).forEach((v, i) => { names[i] = clean(v.replace(/_/g, " ")); });
    code = code.slice(0, t);
  }
  const slots = Array(40).fill(-1);
  [...code.slice(0, 40)].forEach((ch, i) => { const si = RC_CODE.indexOf(ch); if (si >= 0) slots[i] = si; });
  return { slots, names };
}

export const playerCount = ({ slots }) => slots.filter(si => si >= 0).length;

// "10 players: 3 Druids, 2 Paladins, 1 Priest", for the preview's description
export function describe(roster) {
  const n = playerCount(roster);
  const per = {};
  roster.slots.forEach(si => { if (si >= 0) per[SPECS[si].cls] = (per[SPECS[si].cls] || 0) + 1; });
  const parts = CLASS_ORDER.filter(c => per[c]).sort((a, b) => per[b] - per[a]).map(c => `${per[c]} ${c}${per[c] > 1 ? "s" : ""}`);
  return `${n} player${n === 1 ? "" : "s"}${parts.length ? ": " + parts.join(", ") : ""}`;
}

// every spec icon the roster needs, so the caller can fetch them once
export const iconsOf = ({ slots }) => [...new Set(slots.filter(si => si >= 0).map(si => SPECS[si].icon))];

const W = 1200, H = 630;
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
// DejaVu Sans Bold runs about 0.69em a character; shorten a name that won't fit, with an ellipsis
const fit = (s, px, size) => { const max = Math.floor(px / (size * 0.69)); return s.length <= max ? s : s.slice(0, Math.max(1, max - 1)) + "…"; };

const FONT = `font-family="DejaVu Sans" font-weight="bold"`;
// class-coloured text with a black outline, like the page's names
const label = (x, y, size, color, text, anchor = "start") =>
  `<text x="${x}" y="${y}" font-size="${size}" ${FONT} fill="${color}" stroke="#000" stroke-width="${Math.max(3, size / 7)}" stroke-linejoin="round" paint-order="stroke" text-anchor="${anchor}">${esc(text)}</text>`;

// an icon (a data: URI) with a black border and a ring in the class colour
const icon = (x, y, size, href, color, ring) =>
  `<rect x="${x - ring - 1}" y="${y - ring - 1}" width="${size + 2 * ring + 2}" height="${size + 2 * ring + 2}" rx="4" fill="#000"/>` +
  `<rect x="${x - ring / 2 - 1}" y="${y - ring / 2 - 1}" width="${size + ring + 2}" height="${size + ring + 2}" rx="3" fill="none" stroke="${color}" stroke-width="${ring}"/>` +
  (href ? `<image x="${x}" y="${y}" width="${size}" height="${size}" href="${href}" preserveAspectRatio="xMidYMid slice"/>` : `<rect x="${x}" y="${y}" width="${size}" height="${size}" fill="#222"/>`);

const empty = (x, y, w, h) => `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="4" fill="#ffffff08" stroke="#ffffff1c" stroke-width="1.5"/>`;

// icons: { iconName: "data:image/jpeg;base64,..." } (a missing one is drawn as a grey square)
export function rosterSvg(roster, icons = {}) {
  const { slots, names } = roster;
  const n = playerCount(roster);
  const groups = [...Array(8).keys()].filter(g => slots.slice(g * 5, g * 5 + 5).some(si => si >= 0));
  const named = n <= 20 && groups.length <= 4;
  let body = "";

  if (named) {
    const shown = groups.length ? groups : [0];
    const cols = shown.length === 1 ? 1 : 2, rows = Math.ceil(shown.length / 2);
    const top = 104, bottom = 606, gapX = 40, gapY = 18;
    const cw = cols === 1 ? 640 : (W - 80 - gapX) / 2;
    const x0 = cols === 1 ? (W - cw) / 2 : 40;
    const bh = (bottom - top - (rows - 1) * gapY) / rows;       // one group's block: title, then 5 member rows
    const titleH = rows === 1 ? 40 : 30, rowH = (bh - titleH) / 5;
    const isz = Math.round(rowH * 0.74), fs = Math.round(rowH * 0.5);
    shown.forEach((g, k) => {
      const gx = x0 + (k % cols) * (cw + gapX), gy = top + Math.floor(k / cols) * (bh + gapY);
      body += label(gx + cw / 2, gy + titleH * 0.72, Math.round(titleH * 0.66), "#ffd75a", `Group ${g + 1}`, "middle");
      for (let j = 0; j < 5; j++) {
        const i = g * 5 + j, si = slots[i], ry = gy + titleH + j * rowH + 3, rh = rowH - 6;
        if (si < 0) { body += empty(gx, ry, cw, rh); continue; }
        const sp = SPECS[si], pad = (rh - isz) / 2;
        body += `<rect x="${gx}" y="${ry}" width="${cw}" height="${rh}" rx="4" fill="#2a1c0f" stroke="#000" stroke-width="1.5"/>`;
        body += `<rect x="${gx + 1}" y="${ry + 1}" width="${cw - 2}" height="${rh / 2}" rx="3" fill="#ffffff0d"/>`;
        body += icon(gx + pad + 2, ry + pad, isz, icons[sp.icon], sp.color, 2);
        const tx = gx + pad + 2 + isz + 14;
        body += label(tx, ry + rh / 2 + fs * 0.36, fs, sp.color, fit(names[i] || sp.name, gx + cw - tx - 12, fs));
      }
    });
  } else {
    // 8 columns, one per group, of spec icons in their class colours
    const isz = 76, ring = 4, gapX = (W - 80 - 8 * (isz + 2 * ring + 2)) / 7, top = 140, rowH = 90;
    for (let g = 0; g < 8; g++) {
      const cx = 40 + g * (isz + 2 * ring + 2 + gapX), ix = cx + ring + 1;
      body += label(cx + (isz + 2 * ring + 2) / 2, top - 18, 24, "#ffd75a", `Group ${g + 1}`, "middle");
      for (let j = 0; j < 5; j++) {
        const si = slots[g * 5 + j], y = top + j * rowH;
        if (si < 0) { body += empty(ix - ring - 1, y - ring - 1, isz + 2 * ring + 2, isz + 2 * ring + 2); continue; }
        const sp = SPECS[si];
        body += icon(ix, y, isz, icons[sp.icon], sp.color, ring);
      }
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2c2e34"/><stop offset=".45" stop-color="#1c1d21"/><stop offset="1" stop-color="#0f1012"/></linearGradient></defs>
<rect width="${W}" height="${H}" fill="url(#bg)"/>
<rect x="6" y="6" width="${W - 12}" height="${H - 12}" rx="6" fill="none" stroke="#000" stroke-width="3"/>
<rect x="10" y="10" width="${W - 20}" height="${H - 20}" rx="4" fill="none" stroke="#b8913f" stroke-width="2"/>
${label(40, 66, 36, "#ffd75a", "Raid Composition")}
${label(W - 40, 66, 30, "#e8e2d0", `${n} / 40 players`, "end")}
<line x1="40" y1="84" x2="${W - 40}" y2="84" stroke="#b8913f" stroke-opacity=".55" stroke-width="2"/>
${body}
${label(W - 26, H - 20, 17, "#9a9aa2", "foreverinfo.io", "end")}
</svg>`;
}
