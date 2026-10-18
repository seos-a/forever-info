// Reads a Raid Composition link and draws the roster as a 1200x630 PNG-ready SVG for link previews (Discord,
// iMessage...), in Wowhead's flat dark style: just the groups, nothing else.
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
  slots.forEach((si, i) => { if (si < 0) names[i] = ""; });   // a name needs a member under it
  return { slots, names };
}

// the roster back in link form, as the page writes it (rcEncode)
export function encodeRoster({ slots, names }) {
  const c = slots.map(si => (si < 0 ? "-" : RC_CODE[si])).join("").replace(/-+$/, "");
  const n = names.join(",").replace(/,+$/, "");
  return c + (n ? "~" + n.replace(/ /g, "_") : "");
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

const W = 1200, H = 630, M = 32;   // picture size, outer margin
const BG = "#121212", ROW = "#1e1e1e", ROW_EDGE = "#343434", TITLE = "#c8c8c8";
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
// DejaVu Sans Bold runs about 0.69em a character; shorten a name that won't fit, with an ellipsis
const fit = (s, px, size) => { const max = Math.floor(px / (size * 0.69)); return s.length <= max ? s : s.slice(0, Math.max(1, max - 1)) + "…"; };

// plain bold text with a faint dark shadow, as on Wowhead
const text = (x, y, size, color, s, anchor = "start") =>
  `<text x="${x + 1}" y="${y + 2}" font-size="${size}" font-family="DejaVu Sans" font-weight="bold" fill="#000" fill-opacity=".75" text-anchor="${anchor}">${esc(s)}</text>` +
  `<text x="${x}" y="${y}" font-size="${size}" font-family="DejaVu Sans" font-weight="bold" fill="${color}" text-anchor="${anchor}">${esc(s)}</text>`;

// an icon (a data: URI, or a grey square when missing) with a black border; ring > 0 adds a class-coloured ring
const icon = (x, y, size, href, color = "", ring = 0) =>
  `<rect x="${x - ring - 1}" y="${y - ring - 1}" width="${size + 2 * ring + 2}" height="${size + 2 * ring + 2}" rx="${ring ? 4 : 2}" fill="#000"/>` +
  (ring ? `<rect x="${x - ring / 2 - 1}" y="${y - ring / 2 - 1}" width="${size + ring + 2}" height="${size + ring + 2}" rx="3" fill="none" stroke="${color}" stroke-width="${ring}"/>` : "") +
  (href ? `<image x="${x}" y="${y}" width="${size}" height="${size}" href="${href}" preserveAspectRatio="xMidYMid slice"/>` : `<rect x="${x}" y="${y}" width="${size}" height="${size}" fill="#2a2a2a"/>`);

const row = (x, y, w, h, filled) =>
  `<rect x="${x + .5}" y="${y + .5}" width="${w - 1}" height="${h - 1}" rx="3" fill="${filled ? ROW : "none"}" stroke="${filled ? ROW_EDGE : "#262626"}" stroke-width="1"/>`;

// icons: { iconName: "data:image/jpeg;base64,..." }
export function rosterSvg(roster, icons = {}) {
  const { slots, names } = roster;
  const n = playerCount(roster);
  const groups = [...Array(8).keys()].filter(g => slots.slice(g * 5, g * 5 + 5).some(si => si >= 0));
  let body = "";

  if (n <= 20 && groups.length <= 4) {
    // the groups that have someone in them, two across
    const shown = groups.length ? groups : [0];
    const cols = shown.length === 1 ? 1 : 2, rows = Math.ceil(shown.length / 2);
    const gapX = 32, gapY = 28;
    const cw = cols === 1 ? 640 : (W - 2 * M - gapX) / 2, x0 = cols === 1 ? (W - cw) / 2 : M;
    const bh = (H - 2 * M - (rows - 1) * gapY) / rows;            // one group: its title, then 5 rows
    const th = rows === 1 ? 50 : 36, rh = (bh - th) / 5, gap = rows === 1 ? 10 : 6;
    const fs = Math.min(42, Math.round((rh - gap) * 0.5)), isz = Math.round((rh - gap) * 0.72);
    shown.forEach((g, k) => {
      const gx = x0 + (k % cols) * (cw + gapX), gy = M + Math.floor(k / cols) * (bh + gapY);
      body += text(gx + cw / 2, gy + th * 0.62, Math.round(th * 0.56), TITLE, `Group ${g + 1}`, "middle");
      for (let j = 0; j < 5; j++) {
        const i = g * 5 + j, si = slots[i], ry = gy + th + j * rh, h = rh - gap;
        body += row(gx, ry, cw, h, si >= 0);
        if (si < 0) continue;
        const sp = SPECS[si], pad = (h - isz) / 2;
        body += icon(gx + pad, ry + pad, isz, icons[sp.icon]);
        const tx = gx + pad + isz + Math.round(isz * 0.3);
        body += text(tx, ry + h / 2 + fs * 0.36, fs, sp.color, fit(names[i] || sp.name, gx + cw - tx - 12, fs));
      }
    });
  } else {
    // 8 columns, one per group, of spec icons ringed in their class colours
    const isz = 88, ring = 4, cell = isz + 2 * ring + 2, gapX = (W - 2 * M - 8 * cell) / 7, th = 46, rowH = (H - 2 * M - th) / 5;
    for (let g = 0; g < 8; g++) {
      const cx = M + g * (cell + gapX), ix = cx + ring + 1;
      body += text(cx + cell / 2, M + 26, 25, TITLE, `Group ${g + 1}`, "middle");
      for (let j = 0; j < 5; j++) {
        const si = slots[g * 5 + j], y = M + th + j * rowH + (rowH - cell) / 2 + ring + 1;
        if (si < 0) { body += row(cx, y - ring - 1, cell, cell, false); continue; }
        body += icon(ix, y, isz, icons[SPECS[si].icon], SPECS[si].color, ring);
      }
    }
  }

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<rect width="${W}" height="${H}" fill="${BG}"/>
${body}
</svg>`;
}
