// Draws sample raid previews to worker/out/*.png (needs node, `npm install`, and src/RobotoCondensed-ExtraBold.ttf).
// Icons come from the live site, as the Worker fetches them.
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { Resvg, initWasm } from "@resvg/resvg-wasm";
import { parseRoster, describe, iconsOf, rosterSvg } from "../src/roster.js";

await initWasm(await readFile(new URL("../node_modules/@resvg/resvg-wasm/index_bg.wasm", import.meta.url)));
const font = await readFile(new URL("../src/RobotoCondensed-ExtraBold.ttf", import.meta.url));
await mkdir(new URL("../out/", import.meta.url), { recursive: true });

const SAMPLES = {
  "ten": "1pg4jae09k",
  "ten-named": "1pg4jae09k~Happy_Gilmore,Real_American,Brad_Hill,,Matthew_Rose,Tanky,,Bubbles,Seos",
  "twenty": "1pg4jae09kbqd5c8f2hr~Bearington",
  "one-group": "b",
  "long-names": "rpgj4al0ek~Michelangelo_Michelangelo,Real_American,Lost_Lover,Stoop_Kid,Matthew_Rose,Michelangelo_Michelangelo,Fel_Collinz,Lil_Chub,Paindo_French,Gentle_Milk",
  "long-twenty": "1pg4jae09kbqd5c8f2hr~Michelangelo_Michelangelo",
  "forty": "1pg4jae09kbqd5c8f2hr" + "0369cfilor" + "1pg4jae09k",
  "spread": "1----p----g----4----j",
};

for (const [name, q] of Object.entries(SAMPLES)) {
  const roster = parseRoster(q);
  const icons = {};
  for (const ic of iconsOf(roster)) {
    const r = await fetch(`https://foreverinfo.io/images/icons/${ic}.jpg`);
    if (r.ok) icons[ic] = "data:image/jpeg;base64," + Buffer.from(await r.arrayBuffer()).toString("base64");
  }
  const svg = rosterSvg(roster, icons);
  const png = new Resvg(svg, { font: { fontBuffers: [font], loadSystemFonts: false, defaultFontFamily: "Roboto Condensed" } }).render().asPng();
  await writeFile(new URL(`../out/${name}.png`, import.meta.url), png);
  console.log(`${name}: ${describe(roster)} (${png.length} bytes)`);
}
