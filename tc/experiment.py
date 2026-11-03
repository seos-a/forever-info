"""Builds the Simulations page (foreverinfo.io/sims): the "Forever Race/Spec Comparison" dashboard
(https://claude.ai/artifact/KhLhWEBf6f1ceiUyotPXUB, DPS / Healing / Tanks race sims) as a standalone page.

experiment/ holds a copy of the dashboard's files: page.html (its index.html), the scripts it loads
(healing.js, ability_icons.js, race_icons.js) and data/<dataset id>.json (each dataset's rows). The page is written
for the dashboard's runtime, so RUNTIME below stands in for the parts it uses (dash.data / calc / onData / params /
setParams) and the CSS gives values to the dashboard's theme tokens. To update it, copy the dashboard's files and
datasets into experiment/ again and rebuild. Called by build.py, which adds the analytics snippet."""
import base64, json, os, re

# the dashboard's params document (dash/params): every filter's starting value
PARAMS = {"bestFight": "all", "gear": "sims", "specTab": "abilities", "build": "all", "detailFight": "all", "detailMark": "all", "detailRace": "all", "detailSpec": "Beast Mastery Hunter",
          "faction": "All", "gainFight": "all", "gainTargets": "1", "gainSpec": "Beast Mastery Hunter", "hBestFight": "all", "hDetailCls": "priest", "hDetailFight": "all",
          "hDetailMark": "all", "hDetailRace": "all", "hFaction": "All", "hGainCls": "priest", "hGainFight": "all", "hLineCls": "priest",
          "hMatrixFight": "all", "hMetric": "pct", "hRankFight": "all", "lineSpec": "Beast Mastery Hunter", "matrixFight": "all", "matrixTargets": "1", "metric": "pct",
          "rankFight": "all", "tBestFight": "all", "tBuild": "all", "tDetailFight": "all", "tDetailMark": "all", "tDetailRace": "all",
          "tDetailSpec": "Protection Warrior", "tFaction": "All", "tGainFight": "all", "tGainTargets": "1", "tGainSpec": "Protection Warrior", "tLineSpec": "Protection Warrior",
          "tMatrixFight": "all", "tMeasure": "dps", "tMetric": "pct", "tRankFight": "all", "tab": "dps"}

RUNTIME = """
(function(){
const raw = window.__DATA, cache = {}, calcs = {}, subs = [], TABS = ['dps', 'healing', 'tanks'];
const params = Object.assign({}, window.__PARAMS);
const h = location.hash.slice(1); if (TABS.includes(h)) params.tab = h;   // /sims#healing opens the Healing tab
const run = (fn) => { try { fn(); } catch (e) { console.error(e); } };
// the corner stamp names the Healing tab's own sim while that tab is open
let stampDps = null;
const stamp = () => { const el = document.querySelector('.xp-stamp'); if (!el) return; if (stampDps == null) stampDps = el.innerHTML; el.innerHTML = params.tab === 'healing' ? el.dataset.heal : stampDps; };
const redraw = () => { subs.forEach(run); stamp(); };
addEventListener('DOMContentLoaded', stamp);
window.dash = {
  colors: ['#5b9bd5', '#e07b53', '#6dbb6a', '#b07cc6', '#d9b44a', '#4fb3b0', '#c9805b', '#8a8fd6'],
  // like the dashboard: nested values reach the page as JSON text
  // The DPS tab's gear switch: with "Classic pre-raid" picked, each dataset that has a pb_ copy (sims, targets,
  // breakdown, apm) is read from it instead, and every calc built on them is worked out again.
  data(id) {
    if (params.gear === 'classic' && raw['pb_' + id]) id = 'pb_' + id;
    const key = params.gear === 'classic' ? 'classic|' + id : id;
    if (cache[key]) return cache[key];
    if (raw[id]) return cache[key] = { status: 'ok', data: raw[id].map((r) => { const o = {}; for (const k in r) o[k] = r[k] !== null && typeof r[k] === 'object' ? JSON.stringify(r[k]) : r[k]; return o; }),
      columns: Object.keys(raw[id][0] || {}), meta: [], refreshing: false };
    const c = calcs[id]; if (!c) return { status: 'missing', data: [], meta: [] };
    return cache[key] = { status: 'ok', data: c.fn(...c.inputs.map((i) => dash.data(i).data)), meta: [] };
  },
  calc(id, o) { calcs[id] = o; },
  loader() {},
  onData(fn) { subs.push(fn); run(fn); },
  params() { return params; },
  setParams(p) { Object.assign(params, p); if (p.tab) history.replaceState(null, '', p.tab === 'dps' ? location.pathname + location.search : '#' + p.tab); redraw(); },
  resetParams() { Object.keys(params).forEach((k) => delete params[k]); Object.assign(params, window.__PARAMS); redraw(); },
  setLink() {}, refresh() {},
};
let w = innerWidth, t; addEventListener('resize', () => { if (innerWidth === w) return; w = innerWidth; clearTimeout(t); t = setTimeout(redraw, 150); });
})();
"""

CSS = """
:root{color-scheme:dark;--rem:1;
  --color-bg:#000000;--color-panel:#141413;--color-fg:#ecebe4;--color-fg-muted:#9a978e;--color-border-line:#ffffff17;
  --color-ok:#6dbb6a;--color-warn:#e0a83c;--color-bad:#e05a4f;
  --font-anthropic-sans:ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;--font-anthropic-serif:ui-serif,Georgia,"Times New Roman",serif;
  --cds-border:#ffffff17;--cds-chart-grid:#ffffff14;--cds-chart-muted:#5f5e5a;--cds-chart-reference:#97958d;--cds-chart-status-critical:#d03b3b;
  --cds-dur-slow:.45s;--cds-font-size-body:.875rem;--cds-font-size-caption:.75rem;--cds-font-size-heading:.9375rem;--cds-font-size-title:1.375rem;
  --cds-font-weight-medium:500;--cds-gap-xs:.375rem;--cds-gap-sm:.5rem;--cds-gap-md:1rem;--cds-gap-lg:1.75rem;
  --cds-pad-xs:.25rem;--cds-pad-sm:.5rem;--cds-pad-md:.75rem;--cds-pad-lg:1rem;--cds-radius:.5rem;
  --cds-shadow-popover:0 8px 24px #00000052,0 2px 6px #0003;--cds-surface-popover:#1f1e1c;--cds-text-secondary:#c3c2b7}
html{background:var(--color-bg)}
body{margin:0;background:var(--color-bg);color:var(--color-fg);font-family:var(--font-anthropic-sans);font-size:14px;line-height:1.45;-webkit-text-size-adjust:100%}
#dash-root{max-width:1400px;margin:0 auto;padding:16px 16px 52px;box-sizing:border-box}
@media (max-width:600px){#dash-root{padding:10px 10px 52px}}
/* back to the main site: the red WoW menu button its "Sims" link uses (template2.html's .xp-link), as the login screen's
   "Quit", in the page's bottom right corner */
.xp-quit{position:absolute;right:10px;bottom:8px;z-index:30;width:104px;height:18px;padding:0 0 2px;box-sizing:border-box;   /* the word 1px above the middle, as .xp-link */
  display:flex;align-items:center;justify-content:center;font:700 11px/1 Verdana,Tahoma,"DejaVu Sans",Geneva,sans-serif;
  color:#ffd100;text-decoration:none;text-shadow:1px 1px 0 #000,0 0 3px #000;border-radius:3px;
  background:linear-gradient(180deg,#c21a10 0%,#8e0c06 45%,#6a0703 55%,#4a0402 100%);border:1px solid #000;
  box-shadow:inset 0 1px 0 #ff6a4a66,inset 0 0 6px #000a,0 0 0 1px #8d8d8d,0 0 0 2px #3a3a3a,0 0 0 3px #000,0 2px 5px #000}
.xp-quit:hover{color:#fff;background:linear-gradient(180deg,#e0281a 0%,#a8140a 45%,#7e0c05 55%,#580703 100%)}
.xp-quit:active{background:linear-gradient(180deg,#4a0402 0%,#6a0703 45%,#8e0c06 100%);padding:2px 0 0}
@media (max-width:600px){#dash-root{padding-bottom:84px}.xp-quit{right:auto;left:50%;margin-left:-52px;bottom:46px}}   /* phones: centered above the stamp */
/* the WoWSims build the sims ran on, in the page's bottom left corner like the main site's beta version (the WoW login screen) */
body{position:relative;min-height:100vh}
.xp-stamp{position:absolute;left:0;right:0;bottom:8px;z-index:30;font:11px/1.35 Verdana,Tahoma,sans-serif;color:#ffd100;text-shadow:1px 1px 0 #000,-1px 0 0 #000,0 -1px 0 #000,0 0 3px #000;pointer-events:none;white-space:nowrap;text-align:left;padding-left:10px}
@media (max-width:600px){.xp-stamp{text-align:center;padding-left:0}}   /* phones: centered, under the Quit button */
"""

# The WoWSims Forever commit the DPS and tank sims ran on, and its date (shown bottom left). WoWSims has no release
# number for it: its version tags stop at v0.0.140 (September), on another line of history.
SIMS_BUILD, SIMS_DATE = '376a6aa', 'Oct 30 2026'
# The Healing tab's sim (ForeverHealing-TC): the game build its data is from and the day that data was updated, shown in
# the same corner while the Healing tab is open.
HEAL_BUILD, HEAL_DATE = '70707 + Oct 30 hotfix', 'Oct 31 2026'


def build(head_extra=''):
    D = 'experiment/'
    # the main site's background (bg.jpg, which build.py embeds there too): along the top, 540px tall, repeated across
    bg = ''
    if os.path.exists('bg.jpg'):
        bg = ('body{background:url("data:image/jpeg;base64,' + base64.b64encode(open('bg.jpg', 'rb').read()).decode()
              + '") top center/auto 540px repeat-x,var(--color-bg)}')
    page = open(D + 'page.html', encoding='utf-8').read()
    data = {f[:-5]: json.load(open(D + 'data/' + f, encoding='utf-8')) for f in sorted(os.listdir(D + 'data')) if f.endswith('.json')}
    # The sims call the bear tank "Feral Bear"; the Tanks tab names it Feral Druid (its icon stays the bear's: page.html's
    # TANK_ICON, apm.js). The DPS tab's cat "Feral Druid" is in other datasets, and the APM rows are told apart by role.
    for k, rows in data.items():
        if k.startswith('tank'):
            data[k] = json.loads(json.dumps(rows, ensure_ascii=False).replace('"Feral Bear"', '"Feral Druid"'))
        elif k in ('apm', 'pb_apm'):
            for r in rows:
                if r.get('role') == 'tank' and r.get('spec') == 'Feral Bear':
                    r['spec'] = 'Feral Druid'
    # the dashboard runs the page's scripts once its markup is in place, each in its own scope; a script file loads once
    scripts, seen = [], set()
    def take(m):
        src = re.search(r'src="([^"]+)"', m.group(1))
        if src:
            if src.group(1) not in seen:
                seen.add(src.group(1)); scripts.append(open(D + src.group(1), encoding='utf-8').read())
        else:
            scripts.append(m.group(2))
        return ''
    markup = re.sub(r'<script([^>]*)>(.*?)</script>', take, page, flags=re.S)
    js = ''.join('<script>\n(() => {\n' + s.replace('</script', '<\\/script') + '\n})();\n</script>\n' for s in scripts)
    blob = json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Simulations – Forever Info</title>
<meta name="robots" content="noindex">
<link rel="icon" type="image/png" sizes="32x32" href="favicon.png">
<style>{CSS}{bg}</style>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<!-- Wowhead's tooltips on the Character setup's item, enchant and buff links (left as the page draws them) -->
<script>const whTooltips = {{colorLinks: false, iconizeLinks: false, renameLinks: false}};</script>
<script src="https://wow.zamimg.com/js/tooltips.js" async></script>
<script>window.__PARAMS = {json.dumps(PARAMS)}; window.__DATA = {blob};</script>
<script>{RUNTIME}</script>
{head_extra}</head>
<body>
<div id="dash-root">
{markup}
</div>
<div class="xp-stamp" data-heal="ForeverHealing-TC Build {HEAL_BUILD} (Beta)<br>{HEAL_DATE}">WoWSims Version {SIMS_BUILD} (Beta)<br>{SIMS_DATE}</div>
<a class="xp-quit" href="/">Quit</a>
{js}</body>
</html>
"""
