const ROOT = document.querySelector('[data-tab-panel="healing"]');

// The sims call the Skyborne races High Order and Windshaper; the page names them by faction.
const RACE_NAME = { 'High Order Skyborne': 'Alliance Skyborne', 'Windshaper Skyborne': 'Horde Skyborne' };
const RACE_RE = new RegExp(Object.keys(RACE_NAME).join('|'), 'g'), renamed = new WeakMap();
const renameRow = (r) => Object.fromEntries(Object.entries(r).map(([k, v]) => [k, typeof v === 'string' ? v.replace(RACE_RE, (m) => RACE_NAME[m]) : v]));
function rrData(res) {
  if (!res || !Array.isArray(res.data)) return res;
  if (!renamed.has(res.data)) renamed.set(res.data, res.data.map(renameRow));
  return { ...res, data: renamed.get(res.data) };
}
function rrIcons() {
  const icons = window.RACE_ICONS || {};
  for (const [from, to] of Object.entries(RACE_NAME)) if (!icons[to] && icons[from]) icons[to] = icons[from];
  return icons;
}
// Shrinks each card's race name until it fits on its one line.
function fitNames(box) {
  for (const n of box.querySelectorAll('.r')) {
    n.style.fontSize = '';
    if (!n.clientWidth) continue;
    for (let f = 13; n.scrollWidth > n.clientWidth && f > 9; ) n.style.fontSize = --f + 'px';
  }
}
// Calculations: every figure on the page comes from these, worked out from the per-run results.
dash.calc('healByFight', {
  inputs: ['healRuns'],
  title: 'Each race per fight length',
  description: 'Each race’s average effective healing per healer and fight length, its share of the best race (among all races or one faction), its gain over no racials with a standard error from same-seed runs, mana left and time to running out.',
  fn: (runs) => {
    const HEALER = { priest: 'Holy Priest', paladin: 'Holy Paladin', druid: 'Restoration Druid', shaman: 'Restoration Shaman' };
    const groups = new Map();
    for (const r of runs) {
      const k = r.cls + '|' + r.fight;
      if (!groups.has(k)) groups.set(k, new Map());
      // The 40 per-run totals can arrive as JSON text rather than a list.
      const effRuns = (typeof r.effRuns === 'string' ? JSON.parse(r.effRuns) : r.effRuns).map(Number);
      groups.get(k).set(r.race, { ...r, effRuns, manaEnd: +r.manaEnd, oom: +r.oom, over: +r.over });
    }
    const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;
    const se = (a) => { const m = mean(a); return Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - 1) / a.length); };
    const out = [];
    for (const scope of ['All', 'Alliance', 'Horde']) {
      for (const [k, g] of groups) {
        const [cls, fight] = k.split('|');
        const races = [...g.keys()].filter((race) => race === 'No racials' || scope === 'All' || g.get(race).faction === scope);
        const eff = (race) => mean(g.get(race).effRuns);
        const best = races.filter((race) => race !== 'No racials').reduce((a, race) => (a == null || eff(race) > eff(a) ? race : a), null);
        const none = g.get('No racials').effRuns, bestRuns = g.get(best).effRuns;
        for (const race of races) {
          const r = g.get(race), rs = r.effRuns;
          const vsNone = rs.map((x, i) => x - none[i]), vsBest = rs.map((x, i) => x - bestRuns[i]);
          const tie = race !== best && race !== 'No racials' && Math.abs(mean(vsBest)) <= 2 * se(vsBest);
          out.push({
            key: [scope, fight, cls, race].join('|'), scope, fight, length: fight / 60 + ' min', cls, healer: HEALER[cls], race, faction: r.faction,
            hps: Math.round(eff(race) / fight), pct: Math.round((eff(race) / eff(best)) * 10000) / 100,
            gain: Math.round((mean(vsNone) / eff('No racials')) * 10000) / 100, gainSE: Math.round((se(vsNone) / eff('No racials')) * 10000) / 100,
            manaEnd: r.manaEnd, oom: r.oom, overPct: Math.round((r.over / (eff(race) + r.over)) * 1000) / 10,
            status: race === best ? 'Best' : tie ? 'Tie' : '', runs: rs.length,
          });
        }
      }
    }
    return out;
  },
});

dash.calc('healSitStats', {
  inputs: ['healSitRuns'],
  title: 'Each healer per raid situation',
  description: 'Each healer with no racials in each of the sim’s damage presets, at the sim’s normal health and damage (3 minute fights, 40 runs): healing per second with its spread over the runs, share of the raid’s healing, overhealing, time idle, mana left, raid damage per second and raid deaths.',
  fn: (runs) => runs.map((r) => {
    // The 40 per-run totals can arrive as JSON text rather than a list.
    const fight = +r.fight, hps = (typeof r.effRuns === 'string' ? JSON.parse(r.effRuns) : r.effRuns).map((x) => Number(x) / fight).sort((a, b) => a - b);
    const mean = hps.reduce((a, b) => a + b, 0) / hps.length, sd = Math.sqrt(hps.reduce((a, x) => a + (x - mean) ** 2, 0) / (hps.length - 1));
    const q = (p) => { const i = (hps.length - 1) * p, lo = Math.floor(i); return hps[lo] + (hps[Math.ceil(i)] - hps[lo]) * (i - lo); };
    return {
      key: r.preset + '|' + r.cls, preset: r.preset, cls: r.cls, hps: Math.round(mean), hpsSE: Math.round((sd / Math.sqrt(hps.length)) * 10) / 10,
      q1: Math.round(q(0.25)), q3: Math.round(q(0.75)), share: Math.round(((mean * fight) / +r.raidEff) * 1000) / 10,
      overPct: Math.round((+r.over / (mean * fight + +r.over)) * 1000) / 10, idle: Math.round((+r.idle / fight) * 1000) / 10, // the sim gives idle time in seconds
      manaEnd: +r.manaEnd, oom: +r.oom, deaths: +r.deaths, raidDps: Math.round(+r.dmg / fight), raidHps: Math.round(+r.raidEff / fight), runs: hps.length,
    };
  }),
});

dash.calc('healRunGains', {
  inputs: ['healRuns'],
  title: 'Gain over no racials, run by run',
  description: 'Each race’s 40 same-seed runs per healer and fight length: each run’s healing over the matching run with no racials, as a percentage of the no-racials average; quartiles, median, whiskers (runs within 1.5 boxes) and the extremes.',
  fn: (runs) => {
    const eff = (r) => (typeof r.effRuns === 'string' ? JSON.parse(r.effRuns) : r.effRuns).map(Number);
    const by = new Map(runs.map((r) => [r.cls + '|' + r.fight + '|' + r.race, r]));
    const acc = new Map();
    for (const r of runs) {
      if (r.race === 'No racials') continue;
      const none = eff(by.get(r.cls + '|' + r.fight + '|No racials')), avg = none.reduce((a, b) => a + b, 0) / none.length;
      const gains = eff(r).map((x, i) => ((x - none[i]) / avg) * 100);
      for (const fight of [String(r.fight), 'all']) {
        const k = [fight, r.cls, r.race].join('|');
        if (!acc.has(k)) acc.set(k, { key: k, fight, cls: r.cls, race: r.race, faction: r.faction, v: [] });
        acc.get(k).v.push(...gains);
      }
    }
    const statsOf = (v) => {
      const s = v.slice().sort((a, b) => a - b), q = (p) => { const i = (s.length - 1) * p, lo = Math.floor(i); return s[lo] + (s[Math.ceil(i)] - s[lo]) * (i - lo); };
      const q1 = q(0.25), q3 = q(0.75), inside = s.filter((x) => x >= q1 - 1.5 * (q3 - q1) && x <= q3 + 1.5 * (q3 - q1)), r2 = (x) => Math.round(x * 100) / 100;
      return { q1: r2(q1), median: r2(q(0.5)), q3: r2(q3), lo: r2(inside[0]), hi: r2(inside[inside.length - 1]), min: r2(s[0]), max: r2(s[s.length - 1]), mean: r2(v.reduce((a, b) => a + b, 0) / v.length), n: v.length };
    };
    return [...acc.values()].map(({ v, ...a }) => ({ ...a, ...statsOf(v) }));
  },
});
dash.calc('healRunHps', {
  inputs: ['healRuns'],
  title: 'Healing per second, run by run',
  description: 'Each race’s healing per second over its 40 same-seed runs per healer and fight length (all four lengths pooled for all): quartiles, median, whiskers (runs within 1.5 boxes) and the extremes.',
  fn: (runs) => {
    const acc = new Map();
    for (const r of runs) {
      if (r.race === 'No racials') continue;
      const hps = (typeof r.effRuns === 'string' ? JSON.parse(r.effRuns) : r.effRuns).map((x) => Number(x) / r.fight);
      for (const fight of [String(r.fight), 'all']) {
        const k = [fight, r.cls, r.race].join('|');
        if (!acc.has(k)) acc.set(k, { key: k, fight, cls: r.cls, race: r.race, faction: r.faction, v: [] });
        acc.get(k).v.push(...hps);
      }
    }
    const statsOf = (v) => {
      const s = v.slice().sort((a, b) => a - b), q = (p) => { const i = (s.length - 1) * p, lo = Math.floor(i); return s[lo] + (s[Math.ceil(i)] - s[lo]) * (i - lo); };
      const q1 = q(0.25), q3 = q(0.75), inside = s.filter((x) => x >= q1 - 1.5 * (q3 - q1) && x <= q3 + 1.5 * (q3 - q1)), r2 = (x) => Math.round(x * 100) / 100;
      return { q1: r2(q1), median: r2(q(0.5)), q3: r2(q3), lo: r2(inside[0]), hi: r2(inside[inside.length - 1]), min: r2(s[0]), max: r2(s[s.length - 1]), mean: r2(v.reduce((a, b) => a + b, 0) / v.length), n: v.length };
    };
    return [...acc.values()].map(({ v, ...a }) => ({ ...a, ...statsOf(v) }));
  },
});

dash.calc('healSummary', {
  inputs: ['healByFight'],
  title: 'Each race per healer',
  description: 'The per-fight rows, plus each race’s average over the four fight lengths (fight = all).',
  fn: (byFight) => {
    const acc = new Map();
    for (const r of byFight) {
      const k = [r.scope, 'all', r.cls, r.race].join('|');
      let a = acc.get(k);
      if (!a) acc.set(k, (a = { key: k, scope: r.scope, fight: 'all', length: 'All', cls: r.cls, healer: r.healer, race: r.race, faction: r.faction, n: 0, hps: 0, pct: 0, gain: 0, se2: 0, manaEnd: 0, oom: null, overPct: 0, wins: 0 }));
      a.n++; a.hps += r.hps; a.pct += r.pct; a.gain += r.gain; a.se2 += r.gainSE ** 2; a.manaEnd += r.manaEnd; a.overPct += r.overPct; a.wins += r.status === 'Best' ? 1 : 0;
    }
    const all = [...acc.values()].map((a) => ({ key: a.key, scope: a.scope, fight: a.fight, length: a.length, cls: a.cls, healer: a.healer, race: a.race, faction: a.faction,
      hps: Math.round(a.hps / a.n), pct: Math.round((a.pct / a.n) * 100) / 100, gain: Math.round((a.gain / a.n) * 100) / 100,
      gainSE: Math.round((Math.sqrt(a.se2) / a.n) * 100) / 100, manaEnd: Math.round(a.manaEnd / a.n), oom: null,
      overPct: Math.round((a.overPct / a.n) * 10) / 10, status: '', wins: a.wins }));
    for (const g of new Set(all.map((r) => r.scope + '|' + r.cls))) {
      const rows = all.filter((r) => r.scope + '|' + r.cls === g && r.race !== 'No racials');
      const top = rows.reduce((a, r) => (!a || r.pct > a.pct ? r : a), null);
      if (top) top.status = 'Best';
    }
    return byFight.map((r) => ({ ...r, fight: String(r.fight), wins: r.status === 'Best' ? 1 : 0 })).concat(all);
  },
});

dash.calc('healOverall', {
  inputs: ['healSummary'],
  title: 'Overall race ranking',
  description: 'Each race’s per-healer results averaged over the healers it can play, and the number of healers where it is the best race.',
  fn: (summary) => {
    const top = new Map();
    for (const r of summary) {
      if (r.race === 'No racials') continue;
      const k = [r.scope, r.fight, r.cls].join('|');
      top.set(k, Math.max(top.get(k) ?? -Infinity, r.pct));
    }
    const acc = new Map();
    for (const r of summary) {
      const k = [r.scope, r.fight, r.race].join('|');
      let a = acc.get(k);
      if (!a) acc.set(k, (a = { key: k, scope: r.scope, fight: r.fight, race: r.race, faction: r.faction, healers: 0, pct: 0, gain: 0, manaEnd: 0, healerWins: 0 }));
      a.healers++; a.pct += r.pct; a.gain += r.gain; a.manaEnd += r.manaEnd;
      a.healerWins += r.race !== 'No racials' && top.get([r.scope, r.fight, r.cls].join('|')) === r.pct ? 1 : 0;
    }
    return [...acc.values()].map((a) => ({ ...a, pct: Math.round((a.pct / a.healers) * 100) / 100, gain: Math.round((a.gain / a.healers) * 100) / 100, manaEnd: Math.round(a.manaEnd / a.healers) }));
  },
});

dash.calc('healMatrix', {
  inputs: ['healSummary'],
  title: 'Race by healer table',
  description: 'The per-healer results laid out as one row per race and one column per healer, for each measure.',
  fn: (summary) => {
    const rows = new Map();
    for (const r of summary) {
      for (const metric of ['pct', 'gain', 'manaEnd']) {
        const k = [r.scope, r.fight, metric, r.race].join('|');
        if (!rows.has(k)) rows.set(k, { key: k, scope: r.scope, fight: r.fight, metric, race: r.race, faction: r.faction });
        rows.get(k)[r.healer] = r[metric];
      }
    }
    return [...rows.values()];
  },
});

dash.calc('healBest', {
  inputs: ['healSummary'],
  title: 'Best race per healer',
  description: 'For each healer, the race with the highest share of the best race’s healing, the runner-up, and the lead in percentage points and in the measure itself; a tie between the two Skyborne races counts as one race, Skyborne.',
  fn: (summary) => {
    const groups = new Map();
    for (const r of summary) {
      if (r.race === 'No racials') continue;
      const k = [r.scope, r.fight, r.cls].join('|');
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(r);
    }
    return [...groups.entries()].map(([key, g]) => {
      // An exact tie on % of best goes to the race with the higher HPS.
      const sorted = g.slice().sort((a, b) => b.pct - a.pct || b.hps - a.hps), tied = sorted.filter((r) => r.pct === sorted[0].pct);
      // The two Skyborne races share their racials, so a tie between them reads as one race, Skyborne.
      const sky = tied.length === 2 && tied.every((r) => r.race.endsWith('Skyborne'));
      const first = sorted[0], second = sky ? sorted[2] : sorted[1];
      return { key, scope: first.scope, fight: first.fight, cls: first.cls, healer: first.healer, best: sky ? 'Skyborne' : first.race, faction: sky ? 'Tie' : first.faction,
        second: second ? second.race : '', lead: second ? Math.round((first.pct - second.pct) * 100) / 100 : 0, leadAmt: second ? Math.round(Math.abs(first.hps - second.hps) * 10) / 10 : 0, races: g.length };
    });
  },
});

// ---- Page ----
const $ = (s) => ROOT.querySelector(s);
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const fx = (v, d) => (v == null || Number.isNaN(+v) ? '' : (+v).toFixed(d));
const sign = (v, d) => (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d);
const num = (v) => (v == null ? '' : d3.format(',')(v));
const FIGHT = { all: 'all fight lengths', 120: '2 minute fights', 180: '3 minute fights', 300: '5 minute fights', 420: '7 minute fights' };
const SCOPE = { All: 'all races', Alliance: 'Alliance races', Horde: 'Horde races' };
const HEALERS = ['Holy Priest', 'Restoration Druid', 'Restoration Shaman'];
// WoW class colours; Priest uses the page's text colour so it reads on a light theme too.
const HEALER_COLOR = { 'Holy Paladin': '#F48CBA', 'Restoration Druid': '#FF7C0A', 'Restoration Shaman': '#0070DD' };
const healerColor = (h) => (HEALER_COLOR[h] ? `color-mix(in srgb, ${HEALER_COLOR[h]} 85%, var(--color-fg))` : 'var(--color-fg)');
const healerSpan = (h) => { const e = el('span', null, h); e.style.color = healerColor(h); return e; };
const SHORT = { 'Holy Priest': 'Priest', 'Holy Paladin': 'Paladin', 'Restoration Druid': 'Druid', 'Restoration Shaman': 'Shaman' };
const METRIC = {
  pct: { fmt: (v) => fx(v, 2) + '%', high: true, note: 'Share of the best race’s effective healing for each healer. Bold is the best race in each column.' },
  gain: { fmt: (v) => sign(v, 2) + '%', high: true, note: 'Effective healing gained over the same healer with no racials. Bold is the largest gain in each column.' },
  manaEnd: { fmt: num, high: true, note: 'Mana left when the fight ends, averaged over runs. Mostly 0 in long fights, where every healer runs out. Bold is the most in each column.' },
};
const P = () => {
  const q = dash.params();
  return { faction: q.hFaction ?? 'All', metric: q.hMetric ?? 'pct', lineCls: q.hLineCls ?? 'priest', gainCls: q.hGainCls ?? 'priest', detailCls: q.hDetailCls ?? 'priest',
    bestFight: q.hBestFight ?? 'all', rankFight: q.hRankFight ?? 'all', matrixFight: q.hMatrixFight ?? 'all', specFight: q.hSpecFight ?? 'all', gainFight: q.hGainFight ?? 'all',
    detailFight: q.hDetailFight ?? 'all', detailRace: q.hDetailRace ?? 'all', detailMark: q.hDetailMark ?? 'all', cmpView: q.hCmpView ?? '',
    sitMetric: q.hSitMetric ?? 'hps' };
};
// This page's filters carry an h prefix (hFaction, hLineCls...) so they don't clash with the other tabs'.
const setP = (o) => dash.setParams(Object.fromEntries(Object.entries(o).map(([k, v]) => ['h' + k[0].toUpperCase() + k.slice(1), v])));
const sorts = { overall: { field: 'pct', dir: 'desc' }, matrix: { field: null, dir: 'desc' }, detail: { field: null, dir: 'desc' } };
let hl = null, query = '', zoomState = { key: null, t: d3.zoomIdentity };

const seg = (sel, name) => {
  $(sel).addEventListener('click', (e) => { const b = e.target.closest('button[data-v]'); if (b) setP({ [name]: b.dataset.v }); });
};
seg('.lx-faction', 'faction'); seg('.lx-metric', 'metric'); seg('.lx-sitmetric', 'sitMetric');
// Each box has its own fight length buttons; data-p names the filter it sets.
const FIGHTS = [['all', 'All'], ...Object.keys(FIGHT).filter((k) => k !== 'all').map((k) => [k, k / 60 + ' min'])];
ROOT.querySelectorAll('.lx-fight').forEach((g) => {
  g.replaceChildren(...FIGHTS.map(([v, label]) => { const b = el('button', null, label); b.type = 'button'; b.dataset.v = v; return b; }));
  g.addEventListener('click', (e) => { const b = e.target.closest('button[data-v]'); if (b) setP({ [g.dataset.p]: b.dataset.v }); });
});
const dfight = $('.lx-dfight');
dfight.replaceChildren(...FIGHTS.map(([v, label]) => new Option(v === 'all' ? 'All lengths' : label, v)));
dfight.addEventListener('change', (e) => setP({ detailFight: e.target.value }));
$('.lx-drace').addEventListener('change', (e) => setP({ detailRace: e.target.value }));
$('.lx-dmark').addEventListener('change', (e) => setP({ detailMark: e.target.value }));
// Healer pickers: the healer name in a card's title opens a menu of every healer in its class colour.
let HEALER_LIST = [], menu = null;
const closeMenu = () => { if (menu) { menu.btn.setAttribute('aria-expanded', 'false'); menu.el.remove(); menu = null; } };
function openMenu(btn, param, current) {
  closeMenu();
  const root = ROOT, list = el('div', 'hr-menu');
  list.setAttribute('role', 'menu');
  for (const [cls, name] of HEALER_LIST) {
    const item = el('button', null, name);
    item.type = 'button'; item.setAttribute('role', 'menuitemradio'); item.setAttribute('aria-checked', String(cls === current));
    item.style.color = healerColor(name);
    item.addEventListener('click', () => { closeMenu(); setP({ [param]: cls }); });
    list.append(item);
  }
  root.append(list);
  const rb = root.getBoundingClientRect(), bb = btn.getBoundingClientRect();
  list.style.left = Math.max(0, Math.min(rb.width - list.offsetWidth, bb.left - rb.left)) + 'px';
  list.style.top = bb.bottom - rb.top + 4 + 'px';
  btn.setAttribute('aria-expanded', 'true');
  menu = { el: list, btn };
  (list.querySelector('[aria-checked="true"]') || list.firstChild).focus();
}
const healerPicker = (cls, param) => {
  const name = HEALER_LIST.find(([c]) => c === cls)[1];
  const b = el('button', 'hr-pick', name);
  b.type = 'button'; b.style.color = healerColor(name);
  b.setAttribute('aria-haspopup', 'menu'); b.setAttribute('aria-expanded', 'false'); b.title = 'Choose a healer';
  b.addEventListener('click', (e) => { e.stopPropagation(); if (menu && menu.btn === b) closeMenu(); else openMenu(b, param, cls); });
  return b;
};
document.addEventListener('pointerdown', (e) => { if (menu && !menu.el.contains(e.target) && e.target !== menu.btn) closeMenu(); });
document.addEventListener('keydown', (e) => {
  if (!menu) return;
  if (e.key === 'Escape') { const b = menu.btn; closeMenu(); b.focus(); }
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault();
    const items = [...menu.el.children], i = items.indexOf(document.activeElement);
    items[(i + (e.key === 'ArrowDown' ? 1 : items.length - 1)) % items.length].focus();
  }
});
$('.lx-q').addEventListener('input', (e) => { query = e.target.value.trim().toLowerCase(); draw(); });
$('.lx-cards').addEventListener('click', (e) => {
  const b = e.target.closest('button[data-cls]');
  if (b) pickHealer(b.dataset.cls);
});

function table(tbl, cols, rows, sort, onSort, cell) {
  const tr = el('tr');
  for (const c of cols) {
    const th = el('th', c.num ? '' : 't');
    th.dataset.field = c.field;
    if (sort.field === c.field) th.setAttribute('aria-sort', sort.dir === 'asc' ? 'ascending' : 'descending');
    const b = el('button', null, c.label);
    b.type = 'button';
    if (c.title) b.title = c.title;
    if (c.color) b.style.color = c.color;
    b.addEventListener('click', () => onSort(c));
    th.append(b);
    tr.append(th);
  }
  tbl.tHead.replaceChildren(tr);
  tbl.tBodies[0].replaceChildren(...rows.map((r) => {
    const row = el('tr', r.race === 'No racials' ? 'base' : '');
    row.dataset.key = r.key;
    for (const c of cols) row.append(cell(c, r));
    return row;
  }));
}
const sortRows = (rows, sort, cols) => {
  if (!sort.field) return rows;
  const c = cols.find((x) => x.field === sort.field), m = sort.dir === 'asc' ? 1 : -1;
  return rows.slice().sort((a, b) => {
    const x = a[sort.field], y = b[sort.field];
    if (x == null || x === '') return 1;
    if (y == null || y === '') return -1;
    return (c && c.num ? x - y : String(x).localeCompare(String(y))) * m;
  });
};
const toggle = (key, c, defDir) => {
  const s = sorts[key];
  if (s.field === c.field) s.dir = s.dir === 'asc' ? 'desc' : 'asc';
  else { s.field = c.field; s.dir = defDir(c); }
  draw();
};
const raceCell = (r) => { const td = el('td', 't', r.race); td.dataset.fa = r.faction; return td; };
const specIcon = (spec) => {
  const img = el('img', 'hr-sicon');
  const src = (window.SPEC_ICONS || {})[spec];
  if (src) img.src = src;
  img.alt = ''; img.dataset.specIcon = spec; // race_icons.js fills it in if it loads later
  return img;
};
const raceIcon = (race, faction) => {
  const src = rrIcons()[race], img = el('img', 'hr-ricon');
  if (src) img.src = src;
  img.alt = ''; img.dataset.fa2 = faction; img.dataset.raceIcon = race; // race_icons.js fills it in if it loads later
  return img;
};
const plain = (c, r) => el('td', c.num ? '' : 't', c.fmt ? c.fmt(r[c.field]) : r[c.field]);
const accent = () => dash.colors[0];

// The race picked in the grid's Race column; its results order the columns.
let colRace = null;

function drawMatrix(p, rows, overall) {
  const m = METRIC[p.metric] || METRIC.pct;
  const rank = new Map(overall.filter((r) => r.scope === p.faction && r.fight === p.fight).map((r) => [r.race, r.race === 'No racials' ? -1 : r.pct]));
  const list = rows.filter((r) => r.scope === p.faction && r.fight === p.fight && r.metric === p.metric).sort((a, b) => rank.get(b.race) - rank.get(a.race));
  // A picked race orders the columns by its own results, best first; columns it can't play go last.
  const by = list.find((r) => r.race === colRace), order = by ? [...HEALERS].sort((a, b) => (by[a] == null) - (by[b] == null) || (true ? by[b] - by[a] : by[a] - by[b])) : HEALERS;
  const cols = [{ field: 'race', label: 'Race' }].concat(order.map((h) => ({ field: h, label: SHORT[h], title: h, num: true, fmt: m.fmt, color: healerColor(h) })));
  const best = {}, ext = {};
  for (const h of HEALERS) {
    const v = list.filter((r) => r.race !== 'No racials').map((r) => r[h]).filter((x) => x != null);
    if (!v.length) continue;
    best[h] = Math.max(...v);
    ext[h] = [Math.min(...v), Math.max(...v)];
  }
  table($('.lx-matrix'), cols, sortRows(list, sorts.matrix, cols), sorts.matrix,
    (c) => { colRace = null; toggle('matrix', c, (c) => (c.field === 'race' ? 'asc' : 'desc')); },  // a column sort clears the picked race
    (c, r) => {
      if (c.field === 'race') {
        const td = raceCell(r), icon = raceIcon(r.race, r.faction);
        if (icon.src) { td.classList.add('lx-raceface'); td.prepend(icon); } // the race's portrait, bordered in its faction's colour, for the dot
        td.classList.add('lx-pickrace'); td.classList.toggle('picked', r.race === colRace); td.dataset.race = r.race; td.tabIndex = 0; td.setAttribute('role', 'button');
        td.title = r.race === colRace ? 'Put the healers back in class order' : `Order the healers by ${r.race}’s results, best first`;
        return td;
      }
      const v = r[c.field];
      if (v == null) { const td = el('td', 'na', ''); td.title = `${r.race} can't be a ${c.field}`; return td; }
      const td = el('td', v === best[c.field] && r.race !== 'No racials' ? 'top best' : '', c.fmt(v));
      if (r.race !== 'No racials' && ext[c.field]) {
        const [lo, hi] = ext[c.field];
        const t = hi > lo ? (v - lo) / (hi - lo) : 1;
        td.style.background = `color-mix(in srgb, ${accent()} ${Math.round(6 + t * 34)}%, transparent)`;
      }
      td.title = `${r.race}, ${c.field}`;
      return td;
    });
  $('.lx-metricnote').textContent = m.note + ' Click a healer to sort by it, or a race to order the healers by its results.';
  // Picking a race clears the column sort, so its results alone order the table.
  const pick = (td) => { colRace = colRace === td.dataset.race ? null : td.dataset.race; sorts.matrix = { field: null, dir: 'desc' }; redraw(); };
  const body = $('.lx-matrix').tBodies[0];
  body.onclick = (e) => { const td = e.target.closest('td.lx-pickrace'); if (td) pick(td); };
  body.onkeydown = (e) => { const td = e.target.closest('td.lx-pickrace'); if (td && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); pick(td); } };
}

function drawCards(p, rows, healers) {
  $('.lx-cards').replaceChildren(...healers.map(([cls, name]) => {
    const r = rows.find((x) => x.scope === p.faction && x.fight === p.fight && x.cls === cls);
    const b = el('button', 'hr-spec');
    b.type = 'button'; b.dataset.cls = cls;
    b.setAttribute('aria-pressed', String(cls === p.lineCls && cls === p.gainCls && cls === p.detailCls));
    const sn = el('span', 's', name.replace(/ (Druid|Hunter|Mage|Paladin|Priest|Rogue|Shaman|Warlock|Warrior)$/, '')), pic = el('span', 'pic'); sn.style.color = healerColor(name);
    b.append(pic, sn);
    if (!r) { pic.append(specIcon(name)); b.append(el('span', 'l', 'No race of this faction')); b.disabled = true; return b; }
    const where = 'key=' + encodeURIComponent(r.key);
    pic.append(specIcon(name), raceIcon(r.best === 'Skyborne' ? 'Horde Skyborne' : r.best, r.faction)); // the two Skyborne tied get a plain border
    const best = el('span', 'r', r.best.replace(/^(Alliance|Horde) Skyborne$/, (m, f) => 'Skyborne (' + f[0] + ')')); // short enough for the card
    best.dataset.source = 'healBest'; best.dataset.field = 'best'; best.dataset.where = where;
    // Alliance a light blue; Horde the red of the Racial Bonus box's negative bars
    if (r.faction === 'Alliance') best.style.color = 'color-mix(in srgb, var(--hr-alliance) 70%, #fff)';
    else if (r.faction === 'Horde') best.style.color = 'var(--hr-down)';
    b.append(best);
    return b;
  }));
  fitNames($('.lx-cards'));
}

function drawLines(p, rows) {
  const box = $('.lx-lines'), legend = $('.lx-legend');
  box.replaceChildren(); legend.replaceChildren();
  const list = rows.filter((r) => r.scope === p.faction && r.cls === p.cls && r.race !== 'No racials');
  const overall = list.filter((r) => r.fight === 'all').sort((a, b) => b.pct - a.pct);
  if (!overall.length) return;
  const fights = ['120', '180', '300', '420'];
  const color = new Map(overall.map((r, i) => [r.race, dash.colors[i % 8]]));
  const series = overall.map((o) => ({ race: o.race, pts: fights.map((f) => list.find((r) => r.race === o.race && r.fight === f)).filter(Boolean) }));
  // Races with the same line (the two Skyborne often tie) share it checkered: each takes its turn along the line.
  const same = (a, b) => a.pts.length && a.pts.length === b.pts.length && a.pts.every((d, i) => d.fight === b.pts[i].fight && Math.abs(d.pct - b.pts[i].pct) < 0.005);
  for (const s of series) { s.tie = series.filter((o) => o === s || same(o, s)); s.k = s.tie.length; s.j = s.tie.indexOf(s); }
  const swatch = (sw, s) => {
    sw.style.background = s.k > 1 ? `repeating-linear-gradient(90deg, ${s.tie.map((o, i) => `${color.get(o.race)} ${i * 4}px ${i * 4 + 4}px`).join(', ')})` : color.get(s.race);
  };
  for (const s of series) {
    const b = el('button'); b.type = 'button'; b.dataset.race = s.race;
    const sw = el('span', 'hr-sw'); swatch(sw, s);
    b.append(sw, el('span', null, s.race));
    b.addEventListener('mouseenter', () => { hl = s.race; apply(); });
    b.addEventListener('mouseleave', () => { hl = null; apply(); });
    b.addEventListener('focus', () => { hl = s.race; apply(); });
    b.addEventListener('blur', () => { hl = null; apply(); });
    legend.append(b);
  }
  // As tall as the gain chart's box beside it when the two share a row; from the width when stacked.
  const card = box.closest('section'), gainCard = $('.lx-gains').closest('section');
  box.style.minHeight = '0'; box.style.height = '0px';
  let boxH = Math.round(Math.min(400, Math.max(220, box.clientWidth * 0.38)));
  if (gainCard.parentElement === card.parentElement && getComputedStyle(card.parentElement).flexDirection === 'row' && !gainCard.classList.contains('collapsed'))
    boxH = Math.max(180, gainCard.offsetHeight - card.offsetHeight);
  box.style.height = boxH + 'px';
  const W = Math.max(280, box.clientWidth), H = Math.max(120, Math.floor(box.clientHeight) || 240), top = 8, bottom = H - 24;
  const lo = Math.min(...series.flatMap((s) => s.pts.map((d) => d.pct)));
  const yLo = Math.floor((lo - 0.25) * 2) / 2, yHi = 100 + (100 - yLo) * 0.08;
  const y0 = d3.scaleLinear([yLo, yHi], [bottom, top]);
  const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
  const probe = svg.append('text').text('100.00%');
  const ml = probe.node().getComputedTextLength() + 10; probe.remove();
  // Time on the x axis, from 0 min to the longest fight, so the gaps between fight lengths read true.
  const xi = (f) => +f, minutes = d3.range(0, +fights[fights.length - 1] + 1, 60);
  const x0 = d3.scaleLinear([0, +fights[fights.length - 1]], [ml + 12, W - 16]);
  const clip = 'hr-clip-' + Math.random().toString(36).slice(2);
  svg.append('clipPath').attr('id', clip).append('rect').attr('x', ml).attr('y', top - 4).attr('width', W - ml).attr('height', bottom - top + 8);
  const grid = svg.append('g'), yLabels = svg.append('g'), xLabels = svg.append('g');
  const plot = svg.append('g').attr('clip-path', `url(#${clip})`);
  // Every race starts level, at 100% at 0 min; the dashed lead-in to its first sim is not sim data.
  const leads = plot.append('g').selectAll('path').data(series).join('path').attr('class', 'ln').attr('stroke-dasharray', (s) => (s.k > 1 ? `3 ${6 * s.k - 3}` : '3 4')).attr('stroke-dashoffset', (s) => -6 * s.j).attr('stroke-width', 1.5).attr('stroke', (s) => color.get(s.race));
  const paths = plot.append('g').selectAll('path').data(series).join('path').attr('class', 'ln').attr('stroke', (s) => color.get(s.race)).attr('stroke-dasharray', (s) => (s.k > 1 ? `8 ${8 * (s.k - 1)}` : null)).attr('stroke-dashoffset', (s) => -8 * s.j).attr('stroke-linecap', (s) => (s.k > 1 ? 'butt' : null));
  const dots = plot.append('g').selectAll('g').data(series).join('g').attr('fill', (s) => color.get(s.race));
  const circles = dots.selectAll('circle').data((s) => s.pts).join('circle').attr('r', 3);
  let x = x0, y = y0;
  const render = () => {
    const ticks = y.ticks(5), fmt = d3.format('.' + Math.min(3, d3.precisionFixed(ticks[1] - ticks[0] || 1)) + 'f');
    grid.selectAll('line').data(ticks).join('line').attr('x1', ml).attr('x2', W).attr('y1', y).attr('y2', y).attr('stroke', 'var(--cds-chart-grid)');
    yLabels.selectAll('text').data(ticks).join('text').attr('x', ml - 6).attr('y', (t) => y(t) + 4).attr('text-anchor', 'end').text((t) => fmt(t) + '%');
    xLabels.selectAll('text').data(minutes.filter((f) => x(f) >= ml - 1 && x(f) <= W + 1)).join('text')
      .attr('x', (f) => Math.min(W - 16, Math.max(ml + 12, x(xi(f))))).attr('y', H - 4).attr('text-anchor', 'middle').text((f) => f / 60 + ' min');
    const line = d3.line().x((d) => x(xi(d.fight))).y((d) => y(d.pct));
    paths.attr('d', (s) => line(s.pts));
    leads.attr('d', (s) => (s.pts.length ? d3.line()([[x(0), y(100)], [x(xi(s.pts[0].fight)), y(s.pts[0].pct)]]) : null));
    circles.attr('cx', (d) => x(xi(d.fight))).attr('cy', (d) => y(d.pct));
  };
  const key = [p.faction, p.cls, W, H].join('|');
  if (zoomState.key !== key) zoomState = { key, t: d3.zoomIdentity };
  const reset = $('.lx-zoomreset');
  const zoom = d3.zoom().scaleExtent([1, 40]).extent([[ml, top], [W, bottom]]).translateExtent([[ml, top], [W, bottom]])
    .on('zoom', (ev) => {
      zoomState.t = ev.transform;
      x = ev.transform.rescaleX(x0); y = ev.transform.rescaleY(y0);
      reset.hidden = ev.transform.k === 1;
      tip.hidden = true; guide.attr('opacity', 0);
      render();
    });
  // The wheel always zooms the chart, never scrolls the page, even when fully zoomed out.
  svg.node().addEventListener('wheel', (e) => e.preventDefault(), { passive: false });
  svg.call(zoom).on('dblclick.zoom', null).on('dblclick', () => svg.transition().duration(250).call(zoom.transform, d3.zoomIdentity));
  reset.onclick = () => svg.transition().duration(250).call(zoom.transform, d3.zoomIdentity);
  const apply = () => { paths.classed('fade', (s) => hl && s.race !== hl); leads.classed('fade', (s) => hl && s.race !== hl); dots.classed('fade', (s) => hl && s.race !== hl); legend.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.race === hl))); };
  const tip = el('div', 'hr-tip'); tip.hidden = true; box.append(tip);
  const guide = svg.append('line').attr('y1', 8).attr('y2', H - 24).attr('stroke', 'var(--cds-chart-reference)').attr('opacity', 0);
  svg.append('rect').attr('x', ml).attr('width', W - ml).attr('height', H).attr('fill', 'transparent')
    .on('mousemove', (ev) => {
      const [mx] = d3.pointer(ev);
      const f = fights.reduce((a, b) => (Math.abs(x(xi(b)) - mx) < Math.abs(x(xi(a)) - mx) ? b : a));
      if (x(xi(f)) < ml || x(xi(f)) > W) { tip.hidden = true; guide.attr('opacity', 0); return; }
      guide.attr('x1', x(xi(f))).attr('x2', x(xi(f))).attr('opacity', 1);
      const at = series.map((s) => ({ race: s.race, d: s.pts.find((d) => d.fight === f) })).filter((s) => s.d).sort((a, b) => b.d.pct - a.d.pct);
      tip.replaceChildren(el('div', 'h', f / 60 + ' minute fights'), ...at.map((s) => {
        const row = el('div', 'row'), sw = el('span', 'hr-sw'); swatch(sw, s);
        row.append(sw, el('span', null, s.race), el('b', null, fx(s.d.pct, 2) + '%'));
        return row;
      }));
      tip.hidden = false;
      const px = (x(xi(f)) / W) * box.clientWidth, tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(box.clientWidth - tw, px + 12 + tw > box.clientWidth ? px - tw - 12 : px + 12)) + 'px';
      tip.style.top = '8px';
    })
    .on('mouseleave', () => { tip.hidden = true; guide.attr('opacity', 0); });
  svg.call(zoom.transform, zoomState.t);
  apply();
}

// Box plots: each row's box is the middle half of its runs, the line inside it the median, the whiskers the rest of
// the runs within 1.5 boxes of it, and dots the extremes beyond them. Rows are [{label, color, icon, ring, ...stats}].
function drawBoxes(box, rows, H0, { fmt, zero, value, tip, onPick, labelColor, zoomKey = '' }) {
  const W = Math.max(280, box.clientWidth), gap = 8, bh = Math.max(14, (H0 - 22) / rows.length - gap), H = rows.length * (bh + gap) + 22;
  const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
  const probe = svg.append('text').attr('class', 'lab'), textW = (t) => { probe.text(t); return probe.node().getComputedTextLength(); };
  const iz = Math.min(30, bh), ix = iz + 8, ml = ix + Math.max(...rows.map((r) => textW(r.label))) + 14, mr = Math.max(...rows.map((r) => textW(value(r)))) + 14;
  probe.remove();
  const lo = Math.min(...rows.map((r) => r.min), zero ? 0 : Infinity), hi = Math.max(...rows.map((r) => r.max), zero ? 0 : -Infinity);
  const x0 = d3.scaleLinear([lo, hi], [ml, W - mr]).nice();
  const grid = svg.append('g'), ticks = svg.append('g');
  const g = svg.append('g').selectAll('g').data(rows).join('g').attr('transform', (r, i) => `translate(0,${i * (bh + gap) + 2})`);
  g.append('image').attr('href', (r) => r.icon || null).attr('x', 0).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz);
  g.filter((r) => r.ring).append('rect').attr('x', 0).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz).attr('rx', 3).attr('fill', 'none').attr('stroke-width', 1.5).attr('stroke', (r) => r.ring);
  g.append('text').attr('class', 'lab').attr('x', ix).attr('y', bh / 2 + 4).style('fill', (r) => (labelColor ? r.color : null)).text((r) => r.label);
  // The boxes, the 0% line (no racials, behind the boxes so a race at exactly 0% still shows its colour) and the grid
  // zoom (xzoom.js); the names and portraits don't.
  const plot = svg.append('g').attr('clip-path', xZoomClip(svg, ml - 4, W, H - 18));
  const zl = zero ? plot.append('line').attr('y1', 0).attr('y2', H - 18).attr('stroke', 'var(--color-fg)').attr('stroke-opacity', 0.75).attr('stroke-width', 2) : null;
  const pg = plot.selectAll('g.row').data(rows).join('g').attr('class', 'row').attr('transform', (r, i) => `translate(0,${i * (bh + gap) + 2})`);
  const mid = bh / 2;
  const whisk = pg.append('line').attr('y1', mid).attr('y2', mid).attr('stroke', (r) => r.color).attr('stroke-width', 1.5);
  const ends = ['lo', 'hi'].map((end) => pg.append('line').attr('y1', mid - bh * 0.22).attr('y2', mid + bh * 0.22).attr('stroke', (r) => r.color).attr('stroke-width', 1.5).datum((r) => ({ r, end })));
  const boxes = pg.append('rect').attr('y', bh * 0.12).attr('height', bh * 0.76).attr('rx', 3).style('fill', (r) => r.color).attr('fill-opacity', 0.55).style('stroke', (r) => r.color);
  const meds = pg.append('line').attr('y1', bh * 0.12).attr('y2', bh * 0.88).attr('stroke', 'var(--color-fg)').attr('stroke-width', 2);
  const dots = ['min', 'max'].map((end) => pg.filter((r) => (end === 'min' ? r.min < r.lo : r.max > r.hi)).append('circle').attr('cy', mid).attr('r', 2.5).style('fill', (r) => r.color).datum((r) => ({ r, end })));
  const vals = pg.append('text').attr('y', mid + 4).text(value);
  const render = (x) => {
    grid.selectAll('line').data(x.ticks(6)).join('line').attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', H - 18).attr('stroke', 'var(--cds-chart-grid)');
    ticks.selectAll('text').data(x.ticks(6)).join('text').attr('x', x).attr('y', H - 4).attr('text-anchor', 'middle').text((t) => fmt(t));
    if (zl) zl.attr('x1', x(0)).attr('x2', x(0));
    whisk.attr('x1', (r) => x(r.lo)).attr('x2', (r) => x(r.hi));
    for (const e of ends) e.attr('x1', (d) => x(d.r[d.end])).attr('x2', (d) => x(d.r[d.end]));
    boxes.attr('x', (r) => x(r.q1)).attr('width', (r) => Math.max(2, x(r.q3) - x(r.q1)));
    meds.attr('x1', (r) => x(r.median)).attr('x2', (r) => x(r.median));
    for (const d of dots) d.attr('cx', (o) => x(o.r[o.end]));
    vals.attr('x', (r) => x(r.max) + 8);
  };
  render(x0);
  const t = el('div', 'hr-tip'); t.hidden = true; box.append(t);
  g.append('rect').attr('x', 0).attr('y', -gap / 2).attr('width', W).attr('height', bh + gap).attr('fill', 'transparent').style('cursor', onPick ? 'pointer' : null)
    .on('mousemove', (ev, r) => {
      t.replaceChildren(...tip(r)); t.hidden = false;
      const [mx, my] = d3.pointer(ev, box), tw = t.offsetWidth;
      t.style.left = Math.max(0, Math.min(box.clientWidth - tw, mx + 14)) + 'px'; t.style.top = my + 14 + 'px';
    })
    .on('mouseleave', () => { t.hidden = true; })
    .on('click', (ev, r) => onPick && onPick(r));
  if (!boxZoom.has(box)) boxZoom.set(box, {});
  xZoom(svg, { x0, left: ml, right: W, top: 0, bottom: H, store: boxZoom.get(box), key: zoomKey + '|' + W, onZoom: (x) => { t.hidden = true; render(x); } });
}
const boxZoom = new WeakMap(); // each chart's zoom
const tipLine = (k, v) => { const row = el('div', 'row'); row.append(el('span', null, k), el('b', null, v)); return row; };

function drawGains(p, rows, runRows) {
  const box = $('.lx-gains');
  box.replaceChildren();
  const list = runRows.filter((r) => r.cls === p.cls && r.fight === String(p.fight) && (p.faction === 'All' || r.faction === p.faction)).sort((a, b) => b.median - a.median);
  // Explain races whose median run is below no racials; hidden when none are. This sim gives every race the same base
  // stats, so a race only differs through its traits, and a box that crosses zero is run-to-run noise.
  const below = list.filter((r) => r.median < 0), note = $('.lx-gainnote');
  note.hidden = !below.length;
  const names = below.map((r) => r.race), many = names.length > 1;
  note.replaceChildren(...(below.length ? [el('b', null, 'Below zero: '),
    `${names.length > 2 ? names.slice(0, -1).join(', ') + ' and ' + names.at(-1) : names.join(' and ')} ${many ? 'have their' : 'has its'} median run slightly below no racials, with ${many ? 'boxes' : 'its box'} across zero. This sim gives every race the same base stats, so that’s run-to-run noise, not a real loss.`] : []));
  // A fixed height, room for the 10 races the most a spec can have, so the box keeps its size from spec to spec;
  // a note below the boxes takes its room from them.
  const noteH = note.hidden ? 0 : note.getBoundingClientRect().height + (parseFloat(getComputedStyle(box.parentElement).rowGap) || 0);
  const boxH = 10 * (26 + 8) + 20 - noteH;
  box.style.height = boxH + 'px';
  if (!list.length) return;
  const summary = (race) => rows.find((r) => r.scope === p.faction && r.cls === p.cls && r.fight === p.fight && r.race === race);
  const fa = (r) => (r.faction === 'Horde' ? 'var(--hr-horde)' : 'var(--hr-alliance)');
  // Boxes: the top race gold, other gains blue, losses red, no change grey (by the median run); portraits keep their faction ring.
  const tone = (r) => (r === list[0] && r.median > 0 ? 'var(--hr-gold)' : r.median > 0 ? 'var(--hr-up)' : r.median < 0 ? 'var(--hr-down)' : 'var(--color-fg-muted)');
  drawBoxes(box, list.map((r) => ({ ...r, label: r.race, color: tone(r), ring: fa(r), icon: rrIcons()[r.race] })), boxH, {
    zoomKey: [p.faction, p.cls, p.fight].join('|'),
    zero: true, fmt: (v) => sign(v, 1) + '%', value: (r) => sign(r.median, 2) + '%',
    tip: (r) => { const s = summary(r.race); return [el('div', 'h', r.race), tipLine('Median run', sign(r.median, 2) + '%'), tipLine('Middle half of runs', `${sign(r.q1, 2)}% to ${sign(r.q3, 2)}%`),
      tipLine('All runs', `${sign(r.min, 2)}% to ${sign(r.max, 2)}%`), ...(s ? [tipLine('Healing per second', num(s.hps)), tipLine('Mana left at end', num(s.manaEnd))] : []), tipLine('Runs', String(r.n))]; },
  });
}

// Each healer's best race, with its weakest race.
const healerItems = (p, rows) => [...new Set(rows.map((r) => r.cls))].map((cls) => {
  const g = rows.filter((r) => r.cls === cls && r.scope === p.faction && r.fight === p.fight && r.race !== 'No racials');
  if (!g.length) return null;
  const best = g.reduce((a, r) => (r.hps > a.hps ? r : a)), worst = g.reduce((a, r) => (r.hps < a.hps ? r : a));
  return { key: cls, name: best.healer, icon: best.healer, color: healerColor(best.healer), top: best.hps, best: best.race, faction: best.faction, worst: worst.hps, worstRace: worst.race };
}).filter(Boolean);
const HEALER_NAME = { priest: 'Holy Priest', paladin: 'Holy Paladin', druid: 'Restoration Druid', shaman: 'Restoration Shaman' };
// Picking a healer opens its two charts if they were folded.
const unfold = (sel) => $(sel).querySelectorAll('.collapsed > .hr-cardhead .hr-fold').forEach((f) => f.click());
const pickHealer = (c) => { unfold('#h-healer'); setP({ lineCls: c, gainCls: c, detailCls: c }); $('#h-healer').scrollIntoView({ behavior: 'smooth', block: 'start' }); dash.setLink('h-healer'); };

// Spec comparison: every healer at its best race, ranked. The bar is solid up to the healer's weakest race and
// lighter beyond it, so the lighter end shows how much race choice matters next to the gaps between healers.
function drawSpecCompare(p, items, up, unit, onPick) {
  const box = $('.lx-speccmp');
  box.replaceChildren();
  $('.lx-specnote').textContent = items.length > 1 ? (up
    ? `Each healer with its best race${items.some((d) => d.builds > 1) ? ' on its best build' : ''}. The solid bar is the weakest race; the lighter end is what the best race adds. Hover for the numbers, click to open the healer below.`
    : `Each healer with its best race${items.some((d) => d.builds > 1) ? ' on its best build' : ''}; lower is better. The solid bar is the best race; the lighter end is the extra the weakest race takes. Hover for the numbers, click to open the healer below.`) : '';
  if (!items.length) return;
  items.sort((a, b) => (up ? b.top - a.top : a.top - b.top));
  const fmt = (v) => fx(v, unit === 'TMI' ? 2 : unit === 'HPS' ? 0 : 1);
  const bh = 20, gap = 6, iz = 18, W = Math.max(280, box.clientWidth), H = items.length * (bh + gap) + 22;
  const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
  const probe = svg.append('text').attr('class', 'lab');
  const textW = (t) => { probe.text(t); return probe.node().getComputedTextLength(); };
  for (const d of items) { d.vw = textW(fmt(d.top)); d.rw = textW(d.best); }
  const ml = iz + 8 + Math.max(...items.map((d) => textW(d.name))) + 12;
  const mr = 8 + Math.max(...items.map((d) => d.vw + 6 + iz + 6 + d.rw)) + 4;
  probe.remove();
  const lo = (d) => Math.min(d.top, d.worst), hi = (d) => Math.max(d.top, d.worst);
  const x = d3.scaleLinear([0, Math.max(...items.map(hi))], [ml, W - mr]);
  svg.append('g').selectAll('line').data(x.ticks(5)).join('line').attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', H - 18).attr('stroke', 'var(--cds-chart-grid)');
  svg.append('g').selectAll('text').data(x.ticks(5)).join('text').attr('x', x).attr('y', H - 4).attr('text-anchor', 'middle').text((t) => d3.format(',')(t));
  const g = svg.append('g').selectAll('g').data(items).join('g').attr('transform', (d, i) => `translate(0,${i * (bh + gap) + 2})`);
  g.append('image').attr('href', (d) => (window.SPEC_ICONS || {})[d.icon] || null).attr('x', 0).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz);
  g.append('text').attr('class', 'lab').attr('x', iz + 8).attr('y', bh / 2 + 4).style('fill', (d) => d.color).text((d) => d.name);
  g.append('rect').attr('x', x(0)).attr('height', bh).attr('rx', 3).attr('width', (d) => Math.max(1, x(hi(d)) - x(0))).style('fill', (d) => d.color).attr('fill-opacity', 0.35);
  g.append('rect').attr('x', x(0)).attr('height', bh).attr('rx', 3).attr('width', (d) => Math.max(1, x(lo(d)) - x(0))).style('fill', (d) => d.color).attr('fill-opacity', 0.85);
  const ex = (d) => x(hi(d)) + 8;
  g.append('text').attr('class', 'lab').attr('x', ex).attr('y', bh / 2 + 4).text((d) => fmt(d.top));
  g.append('image').attr('href', (d) => rrIcons()[d.best] || null).attr('x', (d) => ex(d) + d.vw + 6).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz);
  g.append('rect').attr('x', (d) => ex(d) + d.vw + 6).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz).attr('rx', 3).attr('fill', 'none').attr('stroke-width', 1.5)
    .attr('stroke', (d) => (d.faction === 'Horde' ? 'var(--hr-horde)' : 'var(--hr-alliance)'));
  g.append('text').attr('x', (d) => ex(d) + d.vw + 6 + iz + 6).attr('y', bh / 2 + 4).text((d) => d.best);
  // Hover a row for its numbers; click it to show that healer in the boxes below.
  const tip = el('div', 'hr-tip');
  tip.hidden = true; box.append(tip);
  const line = (k, v) => { const row = el('div', 'row'); row.append(el('span', null, k), el('b', null, v)); return row; };
  g.append('rect').attr('x', 0).attr('y', -gap / 2).attr('width', W).attr('height', bh + gap).attr('fill', 'transparent').style('cursor', 'pointer')
    .on('mousemove', (ev, d) => {
      const spread = (Math.abs(d.top - d.worst) / (up ? d.worst : d.top)) * 100;
      const head = el('div', 'h', d.name); head.style.color = d.color;  // the healer in its class colour
      tip.replaceChildren(head, line('Best race', `${d.best}, ${fmt(d.top)} ${unit}`), line('Weakest race', `${d.worstRace}, ${fmt(d.worst)} ${unit}`),
        line(up ? 'Best race adds' : 'Weakest race takes', `${fx(spread, 2)}%${up ? '' : ' more'}`), ...(d.build ? [line('Build', d.builds > 1 ? `${d.build} (best of ${d.builds})` : d.build)] : []));
      tip.hidden = false;
      const [mx, my] = d3.pointer(ev, box), tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(box.clientWidth - tw, mx + 14)) + 'px';
      tip.style.top = my + 14 + 'px';
    })
    .on('mouseleave', () => { tip.hidden = true; })
    .on('click', (ev, d) => onPick(d.key));
}

function drawDetail(p, rows) {
  const forCls = rows.filter((r) => r.scope === p.faction && r.cls === p.cls && r.fight !== 'all');
  const races = [...new Set(forCls.map((r) => r.race))].sort();
  const rsel = $('.lx-drace');
  rsel.replaceChildren(new Option('All races', 'all'), ...races.map((r) => new Option(r, r)));
  rsel.value = races.includes(p.detailRace) ? p.detailRace : 'all';
  $('.lx-dfight').value = p.fight;
  $('.lx-dmark').value = p.detailMark;
  let list = forCls.filter((r) => (p.fight === 'all' || r.fight === p.fight) && (rsel.value === 'all' || r.race === rsel.value)
    && (p.detailMark === 'all' || r.status === 'Best' || (p.detailMark === 'ties' && r.status === 'Tie')));
  if (query) list = list.filter((r) => r.race.toLowerCase().includes(query));
  list = list.slice().sort((a, b) => a.fight - b.fight || b.pct - a.pct);
  const cols = [
    { field: 'length', label: 'Fight' },
    { field: 'race', label: 'Race' },
    { field: 'hps', label: 'Healing per sec', num: true, fmt: num },
    { field: 'pct', label: '% of best', num: true, fmt: (v) => fx(v, 2) + '%' },
    { field: 'gain', label: 'Gain over no racials', num: true, fmt: (v) => sign(v, 2) + '%' },
    { field: 'gainSE', label: '± SE', num: true, fmt: (v) => fx(v, 2) },
    { field: 'manaEnd', label: 'Mana left', num: true, fmt: num },
    { field: 'oom', label: 'Time to OOM (sec)', num: true, fmt: num },
    { field: 'overPct', label: 'Overheal %', num: true, fmt: (v) => fx(v, 1) },
    { field: 'status', label: 'Mark' },
  ];
  const sortCols = cols.map((c) => (c.field === 'length' ? Object.assign({}, c, { field: 'fight', num: true }) : c));
  const s = sorts.detail.field === 'length' ? { field: 'fight', dir: sorts.detail.dir } : sorts.detail;
  const sorted = s.field === 'fight' ? sortRows(list.map((r) => ({ ...r, fightN: +r.fight })), { field: 'fightN', dir: s.dir }, [{ field: 'fightN', num: true }]) : sortRows(list, s, sortCols);
  table($('.lx-detail'), cols, sorted, sorts.detail,
    (c) => toggle('detail', c, (c) => (c.num && c.field !== 'gainSE' && c.field !== 'overPct' ? 'desc' : 'asc')),
    (c, r) => {
      if (c.field === 'race') return raceCell(r);
      if (c.field === 'status') { const td = el('td', 't', r.status); if (r.status === 'Best') td.classList.add('top'); return td; }
      return plain(c, r);
    });
  // A line between fight lengths, so each fight's Best reads against its own rows.
  if (!sorts.detail.field) {
    const trs = $('.lx-detail').tBodies[0].rows;
    sorted.forEach((r, i) => { if (i && r.fight !== sorted[i - 1].fight) trs[i].classList.add('group'); });
  }
}

// The sim's damage presets, lightest on the raid first. The rest of the page uses tank-raid.
const SITUATIONS = [
  { id: 'tank', label: 'Tank damage only', about: 'Both tanks are hit steadily; nobody else takes damage.' },
  { id: 'rot', label: 'Raid-wide rot', about: 'Light damage on one tank; everyone else loses health slowly and steadily.' },
  { id: 'pulses', label: 'Raid hits', about: 'Light damage on one tank; every 20 sec the whole raid takes a big hit.' },
  { id: 'tank-raid', label: 'Tank, rot and raid hits', about: 'The sim’s default: both tanks hit steadily and the whole raid hit every 20 sec.' },
  { id: 'heavy', label: 'Heavy raid hits', about: 'Steady tank damage, slow rot, and the whole raid hit hard every 15 sec; more than five healers can keep up with.' },
];
const SIT_METRIC = {
  hps: { fmt: (v) => num(Math.round(v)), note: 'effective healing per second (the light end of each bar is the middle half of the runs)' },
  share: { fmt: (v) => fx(v, 1) + '%', note: 'the healer’s share of the whole raid’s effective healing (five healers; both Shamans together for Shaman)' },
  overPct: { fmt: (v) => fx(v, 1) + '%', note: 'the share of healing that was overhealing' },
  idle: { fmt: (v) => fx(v, 1) + '%', note: 'the share of the fight spent not casting' },
  manaEnd: { fmt: num, note: 'mana left when the fight ends' },
};

// Each situation is a group of bars, one per healer (no racials).
function drawSituations(p, rows, healers) {
  const box = $('.lx-sits'), key = SIT_METRIC[p.sitMetric] ? p.sitMetric : 'hps', m = SIT_METRIC[key];
  box.replaceChildren();
  const groups = SITUATIONS.map((st) => ({ ...st, items: healers.map(([cls, name]) => {
    const r = rows.find((x) => x.preset === st.id && x.cls === cls);
    // Shaman's share counts both Shamans: the sim's raid has two, and its numbers are their average.
    return r && { ...r, name, color: healerColor(name), value: key === 'share' && cls === 'shaman' ? r.share * 2 : r[key] };
  }).filter(Boolean) })).filter((g) => g.items.length);
  const first = groups[0] && groups[0].items[0];
  $('.lx-sitnote').textContent = groups.length
    ? `Each healer with no racials in each of the sim’s damage presets, at its normal health and damage, 3 minute fights. Bars show ${m.note}. In the sim’s raid the two Shamans heal the tanks and the Priest, Paladin and Druid heal the raid, so a fight that hits only the tanks leaves the raid healers little to do. Hover a bar for the numbers.`
    : '';
  if (!first) return;
  const bh = 16, gap = 4, ggap = 14, iz = 16, W = Math.max(280, box.clientWidth);
  const H = groups.reduce((a, g) => a + g.items.length * (bh + gap) + ggap, 0) + 18;
  const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
  const probe = svg.append('text').attr('class', 'lab');
  const textW = (t) => { probe.text(t); return probe.node().getComputedTextLength(); };
  const items = groups.flatMap((g) => g.items), hi = (d) => (key === 'hps' ? Math.max(d.value, d.q3) : d.value);
  const mr = Math.max(...items.map((d) => textW(m.fmt(d.value)))) + 14;
  probe.style('font-weight', 600);
  const ml = Math.max(...groups.map((g) => textW(g.label))) + 16;
  probe.remove();
  const x = d3.scaleLinear([0, Math.max(1, ...items.map(hi))], [ml + iz + 6, W - mr]).nice();
  svg.append('g').selectAll('line').data(x.ticks(5)).join('line').attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', H - 16).attr('stroke', 'var(--cds-chart-grid)');
  svg.append('g').selectAll('text').data(x.ticks(5)).join('text').attr('x', x).attr('y', H - 2).attr('text-anchor', 'middle').text((t) => m.fmt(t));
  let y = 2;
  const flat = [];
  for (const g of groups) {
    const gh = g.items.length * (bh + gap) - gap;
    svg.append('text').attr('class', 'lab').attr('x', 0).attr('y', y + gh / 2 + 4).style('font-weight', 600).text(g.label);
    if (y > 2) svg.append('line').attr('x1', 0).attr('x2', W).attr('y1', y - ggap / 2 - gap / 2).attr('y2', y - ggap / 2 - gap / 2).attr('stroke', 'var(--color-border-line)');
    g.items.forEach((d, i) => flat.push({ ...d, sit: g, y: y + i * (bh + gap) }));
    y += gh + gap + ggap;
  }
  const row = svg.append('g').selectAll('g').data(flat).join('g').attr('transform', (d) => `translate(0,${d.y})`);
  row.append('image').attr('href', (d) => (window.SPEC_ICONS || {})[d.name] || null).attr('x', ml).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz);
  if (key === 'hps') row.append('rect').attr('x', (d) => x(d.q1)).attr('height', bh).attr('rx', 3).attr('width', (d) => Math.max(1, x(d.q3) - x(d.q1))).style('fill', (d) => d.color).attr('fill-opacity', 0.3);
  row.append('rect').attr('x', x(0)).attr('height', bh).attr('rx', 3).attr('width', (d) => Math.max(1, x(d.value) - x(0))).style('fill', (d) => d.color).attr('fill-opacity', 0.85);
  row.append('text').attr('class', 'lab').attr('x', (d) => x(hi(d)) + 6).attr('y', bh / 2 + 4).text((d) => m.fmt(d.value));
  const tip = el('div', 'hr-tip'); tip.hidden = true; box.append(tip);
  row.append('rect').attr('x', 0).attr('y', -gap / 2).attr('width', W).attr('height', bh + gap).attr('fill', 'transparent').style('cursor', 'pointer')
    .on('mousemove', (ev, d) => {
      tip.replaceChildren(el('div', 'h', `${d.name}: ${d.sit.label}`), el('div', 'about', d.sit.about),
        tipLine('Healing per second', `${num(d.hps)} (middle half ${num(d.q1)}–${num(d.q3)})`), tipLine('Share of raid healing', fx(d.cls === 'shaman' ? d.share * 2 : d.share, 1) + '%' + (d.cls === 'shaman' ? ' (both Shamans)' : '')),
        tipLine('Overhealing', fx(d.overPct, 1) + '%'), tipLine('Time idle', fx(d.idle, 1) + '%'), tipLine('Mana left at end', num(d.manaEnd)),
        tipLine('Raid damage taken', num(d.raidDps) + ' per sec'), tipLine('Raid deaths', fx(d.deaths, 1) + ' per fight'));
      tip.hidden = false;
      const [mx, my] = d3.pointer(ev, box), tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(box.clientWidth - tw, mx + 14)) + 'px'; tip.style.top = my + 14 + 'px';
    })
    .on('mouseleave', () => { tip.hidden = true; })
    .on('click', (ev, d) => pickHealer(d.cls));
}

// Spell breakdown: clicking a healer in the ranking turns the box into where that healer's healing comes from.
// Rows come from the `spells` dataset: each race's average per spell over its 40 runs at each fight length.
// Bars: the direct part solid, the heal-over-time part striped, absorbs outlined, and overhealing a faint tail.
const HEAL_SCHOOL = { priest: ['Holy', '#ffe680'], druid: ['Nature', '#5fd35f'], shaman: ['Nature', '#5fd35f'], paladin: ['Holy', '#ffe680'] };
let healUserH = 0;
function drawHealBreakdown(p, view, data, fitH) {
  const box = $('.lx-speccmp'), [school, c] = HEAL_SCHOOL[view.cls] || ['Holy', '#ffe680'];
  box.replaceChildren();
  const bar = el('div', 'hr-bdbar'), back = el('button', 'hr-reset', '← All healers'), open = el('button', 'hr-reset', 'Open in the boxes below');
  back.type = open.type = 'button';
  back.addEventListener('click', () => setP({ cmpView: '' }));
  open.addEventListener('click', () => pickHealer(view.cls));
  // The healer's name opens the healer menu, to switch to another healer's breakdown.
  const title = el('span', 'hr-bdtitle');
  title.append(healerPicker(view.cls, 'cmpView'));
  bar.append(back, title, open);
  const legend = el('div', 'hr-bdlegend');
  box.append(bar, legend);
  const rows = data.filter((r) => r.cls === view.cls && r.race === view.race && (p.specFight === 'all' || String(r.fight) === String(p.specFight)));
  if (!rows.length) { $('.lx-specnote').textContent = `No spell breakdown for ${view.label} (${view.race}) here.`; return; }
  // Average each spell over the fight lengths shown (one row per length); values are per second.
  const acc = new Map();
  for (const r of rows) {
    // The spell list can arrive as JSON text rather than a list.
    for (const [name, icon, hps, over, casts, crits, hits, hot, type] of typeof r.spells === 'string' ? JSON.parse(r.spells) : r.spells) {
      if (!acc.has(name)) acc.set(name, { name, icon, type, hps: 0, over: 0, casts: 0, crits: 0, hits: 0, hot: 0 });
      const a = acc.get(name), k = 1 / rows.length;
      a.hps += hps * k; a.over += over * k; a.casts += casts * k; a.crits += crits * k; a.hits += hits * k; a.hot += hot * k;
    }
  }
  const list = [...acc.values()].filter((a) => a.hps + a.over > 0.05).sort((a, b) => b.hps - a.hps);
  const total = list.reduce((s2, a) => s2 + a.hps, 0), totalOver = list.reduce((s2, a) => s2 + a.over, 0);
  const fightText = p.specFight === 'all' ? 'averaged over 2, 3, 5 and 7 minute fights' : `${p.specFight / 60} minute fights`;
  $('.lx-specnote').textContent = '';
  const sw = (kind) => { const e = el('span', 'hr-bdsw'); e.dataset.kind = kind; e.style.setProperty('--c', c); return e; };
  const key2 = (e, text) => { const k = el('span', 'hr-bdkey'); k.append(e, text); return k; };
  const isAbsorb = (a) => a.type === 'absorb', isChannel = (a) => String(a.type).startsWith('channel');
  legend.replaceChildren(key2(sw('direct'), school), key2(sw('direct'), 'Direct'), ...(list.some((a) => a.hot > 0) ? [key2(sw('hot'), 'Over time (HoT)')] : []),
    ...(list.some(isChannel) ? [key2(sw('channel'), 'Channel')] : []), ...(list.some(isAbsorb) ? [key2(sw('absorb'), 'Absorb')] : []), key2(sw('over'), 'Overhealing'));
  // As tall as the ranking it replaces, like the DPS tab's breakdown.
  const W = Math.max(280, box.clientWidth), outer = (e) => e.offsetHeight + parseFloat(getComputedStyle(e).marginBottom || 0), barH = outer(bar) + outer(legend);
  const slot = Math.max(16, (fitH - $('.lx-specnote').offsetHeight - barH - 22) / list.length), bh = Math.min(healUserH ? 56 : 34, slot * 0.78), gap = slot - bh, H = list.length * slot + 22;
  const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
  const probe = svg.append('text').attr('class', 'lab'), textW = (t) => { probe.text(t); return probe.node().getComputedTextLength(); };
  const valText = (a) => `${num(Math.round(a.hps))} HPS · ${fx((a.hps / total) * 100, 1)}%`;
  const iz = Math.min(20, Math.max(14, bh)), ml = iz + 6 + Math.max(...list.map((a) => textW(a.name))) + 14, mr = Math.max(...list.map((a) => textW(valText(a)))) + 12;
  probe.remove();
  const x = d3.scaleLinear([0, Math.max(...list.map((a) => a.hps + a.over))], [ml, W - mr]);
  svg.append('g').selectAll('line').data(x.ticks(5)).join('line').attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', H - 18).attr('stroke', 'var(--cds-chart-grid)');
  svg.append('g').selectAll('text').data(x.ticks(5)).join('text').attr('x', x).attr('y', H - 4).attr('text-anchor', 'middle').text((t) => d3.format(',')(t));
  const pid = 'hr-hot-' + Math.random().toString(36).slice(2), pat = svg.append('defs').append('pattern').attr('id', pid).attr('patternUnits', 'userSpaceOnUse').attr('width', 8).attr('height', 8).attr('patternTransform', 'rotate(45)');
  pat.append('rect').attr('width', 8).attr('height', 8).style('fill', c).attr('fill-opacity', 0.35);
  pat.append('rect').attr('width', 4).attr('height', 8).style('fill', c);
  const chPat = svg.select('defs').append('pattern').attr('id', pid + '-ch').attr('patternUnits', 'userSpaceOnUse').attr('width', 6).attr('height', 8);
  chPat.append('rect').attr('width', 6).attr('height', 8).style('fill', c).attr('fill-opacity', 0.35);
  chPat.append('rect').attr('width', 3).attr('height', 8).style('fill', c);
  const g = svg.append('g').selectAll('g').data(list).join('g').attr('transform', (a, i) => `translate(0,${i * (bh + gap) + 2})`);
  g.append('image').attr('href', (a) => (window.ABILITY_ICONS || {})[a.name] || null).attr('x', 0).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz);
  g.append('text').attr('class', 'lab').attr('x', iz + 6).attr('y', bh / 2 + 4).text((a) => a.name);
  const direct = (a) => Math.max(0, a.hps - a.hot);
  g.append('rect').attr('x', x(0)).attr('height', bh).attr('width', (a) => Math.max(0, x(direct(a)) - x(0))).style('fill', (a) => (isChannel(a) ? `url(#${pid}-ch)` : c)).attr('fill-opacity', (a) => (isAbsorb(a) ? 0.25 : 0.9)).style('stroke', (a) => (isAbsorb(a) ? c : 'none')).attr('stroke-width', 1.5);
  g.append('rect').attr('x', (a) => x(direct(a))).attr('height', bh).attr('width', (a) => Math.max(0, x(a.hps) - x(direct(a)))).style('fill', `url(#${pid})`);
  g.append('rect').attr('x', (a) => x(a.hps)).attr('height', bh).attr('width', (a) => Math.max(0, x(a.hps + a.over) - x(a.hps))).style('fill', c).attr('fill-opacity', 0.18);
  g.append('text').attr('x', (a) => x(a.hps + a.over) + 6).attr('y', bh / 2 + 4).text(valText);
  const tip = el('div', 'hr-tip'); tip.hidden = true; box.append(tip);
  g.append('rect').attr('x', 0).attr('y', -gap / 2).attr('width', W).attr('height', bh + gap).attr('fill', 'transparent')
    .on('mousemove', (ev, a) => {
      const secs = p.specFight === 'all' ? null : +p.specFight;
      tip.replaceChildren(el('div', 'h', a.name), tipLine('Effective healing per second', num(Math.round(a.hps))), tipLine('Share', fx((a.hps / total) * 100, 1) + '%'),
        ...(a.hot > 0 && a.hot < a.hps - 0.5 ? [tipLine('From the heal over time', fx((a.hot / a.hps) * 100, 0) + '%')] : []),
        tipLine('Overhealing', a.hps + a.over > 0 ? fx((a.over / (a.hps + a.over)) * 100, 1) + '%' : '–'),
        ...(a.casts >= 0.05 ? [tipLine('Casts per fight', fx(a.casts, 1))] : []),
        ...(secs && a.casts >= 0.5 ? [tipLine('Effective healing per cast', num(Math.round((a.hps * secs) / a.casts)))] : []),
        ...(a.hits > 0 && !isAbsorb(a) ? [tipLine('Crit rate', fx((a.crits / a.hits) * 100, 1) + '%')] : []));
      tip.hidden = false;
      const [mx, my] = d3.pointer(ev, box), tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(box.clientWidth - tw, mx + 14)) + 'px'; tip.style.top = my + 14 + 'px';
    })
    .on('mouseleave', () => { tip.hidden = true; });
}

function draw() {
  if (ROOT.hidden) return;
  const p = P();
  const d = { byFight: rrData(dash.data('healByFight')), summary: rrData(dash.data('healSummary')), overall: rrData(dash.data('healOverall')), matrix: rrData(dash.data('healMatrix')), best: rrData(dash.data('healBest')) , runGains: rrData(dash.data('healRunGains')), runHps: rrData(dash.data('healRunHps')) };
  ROOT.querySelectorAll('.lx-fight').forEach((g) => g.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === p[g.dataset.p]))));
  for (const [sel, v] of [['.lx-faction', p.faction], ['.lx-metric', p.metric], ['.lx-sitmetric', p.sitMetric]])
    ROOT.querySelectorAll(sel + ' button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.v === v)));
  const ok = Object.values(d).every((x) => x.status === 'ok');
  ROOT.querySelectorAll('.lx-cards, .lx-lines, .lx-gains, .lx-speccmp').forEach((e) => e.classList.toggle('dash-skeleton', !ok));
  if (!ok) {
    for (const t of ['.lx-matrix', '.lx-detail']) { $(t).tHead.replaceChildren(); $(t).tBodies[0].replaceChildren(); }
    for (const c of ['.lx-cards', '.lx-lines', '.lx-gains', '.lx-legend', '.lx-speccmp']) $(c).replaceChildren();
    return;
  }
  const healers = [...new Map(d.summary.data.map((r) => [r.cls, r.healer])).entries()].sort((a, b) => HEALERS.indexOf(a[1]) - HEALERS.indexOf(b[1]));
  HEALER_LIST = healers;
  closeMenu();
  for (const k of ['lineCls', 'gainCls', 'detailCls']) if (!healers.some(([c]) => c === p[k])) p[k] = healers[0][0];
  $('.lx-lenhead').replaceChildren(healerPicker(p.lineCls, 'lineCls'), ' Race Standings over Time');
  $('.lx-gainhead').replaceChildren(healerPicker(p.gainCls, 'gainCls'), ' Racial Bonus');
  $('.lx-dethead').replaceChildren(healerPicker(p.detailCls, 'detailCls'), ' Sim Results by Fight');

  drawCards({ ...p, fight: p.bestFight }, d.best.data, healers);
  drawMatrix({ ...p, fight: p.matrixFight }, d.matrix.data, d.overall.data);
  drawGains({ ...p, cls: p.gainCls, fight: p.gainFight }, d.summary.data, d.runGains.data);
  drawLines({ ...p, cls: p.lineCls }, d.summary.data);
  drawDetail({ ...p, cls: p.detailCls, fight: p.detailFight }, d.summary.data);
  // Raid situations come from their own runs; the rest of the page draws without them.
  const sit = rrData(dash.data('healSitStats'));
  $('.lx-sitcard').hidden = sit.status !== 'ok' || !sit.data.length;
  if (!$('.lx-sitcard').hidden) { drawSituations(p, sit.data, healers); }
  {
    // Healer comparison: each healer's best race (highest average in the faction filter), as a box of its runs' HPS.
    const box = $('.lx-speccmp'), runs = d.runHps.data.filter((r) => r.fight === String(p.specFight) && (p.faction === 'All' || r.faction === p.faction));
    const bestOf = new Map();
    for (const r of runs) if (!bestOf.has(r.cls) || r.mean > bestOf.get(r.cls).mean) bestOf.set(r.cls, r);
    const rows = [...bestOf.values()].sort((a, b) => b.median - a.median).map((r) => ({ ...r, label: HEALER_NAME[r.cls] || r.cls, color: healerColor(HEALER_NAME[r.cls]), icon: (window.SPEC_ICONS || {})[HEALER_NAME[r.cls]] }));
    box.replaceChildren();
    $('.lx-specnote').textContent = rows.length ? 'Hover for spec info, click for ability breakdown.' : '';
    // As tall as the longest spell breakdown needs, or as tall as the box was dragged, so opening one doesn't move the page.
    const SP = rrData(dash.data('healSpells')), spellRows = SP.status === 'ok' ? SP.data : [];
    const most = Math.max(0, ...spellRows.map((r) => (typeof r.spells === 'string' ? JSON.parse(r.spells) : r.spells).length));
    const H0 = Math.max(rows.length * 44, most ? most * 18 + 22 + 56 : 0, healUserH);
    if (rows.length) drawBoxes(box, rows, H0, { zoomKey: [p.faction, p.specFight].join('|'), labelColor: true, fmt: (v) => num(Math.round(v)), value: (r) => `${num(Math.round(r.median))} HPS · ${r.race}`, onPick: (r) => setP({ cmpView: r.cls }),
      tip: (r) => [Object.assign(el('div', 'h', r.label), { style: `color: ${r.color}` }), tipLine('Race', r.race), tipLine('Median run', num(Math.round(r.median)) + ' HPS'), tipLine('Middle half of runs', `${num(Math.round(r.q1))} to ${num(Math.round(r.q3))} HPS`), tipLine('All runs', `${num(Math.round(r.min))} to ${num(Math.round(r.max))} HPS`), tipLine('Runs', String(r.n))] });
    // A healer picked from the boxes shows its spell breakdown over them, at their height, until "All healers" is clicked.
    const view = p.cmpView && rows.find((r) => r.cls === p.cmpView);
    if (view && SP.status === 'ok') drawHealBreakdown(p, view, spellRows, $('.lx-specnote').offsetHeight + box.offsetHeight);
  }
}

// A redraw empties and refills every box, and measuring the charts meanwhile lays out a much shorter page,
// which pulls the scroll position up. Hold the page's height and scroll position while it redraws.
const scrollerOf = (node) => {
  for (let n = node.parentElement; n; n = n.parentElement) {
    const o = getComputedStyle(n).overflowY;
    if ((o === 'auto' || o === 'scroll') && n.scrollHeight > n.clientHeight) return n;
  }
  return document.scrollingElement || document.documentElement;
};
function redraw() {
  const root = ROOT, sc = scrollerOf(root), top = sc.scrollTop;
  root.style.minHeight = root.offsetHeight + 'px';
  try { draw(); } finally { root.style.minHeight = ''; if (sc.scrollTop !== top) sc.scrollTop = top; }
}
dash.onData(redraw);

// Dragging the handle under the healer ranking (or arrow keys on it) sets the box's height; double-click resets it.
{
  const grip = $('.lx-cmpgrip');
  let start = null;
  const boxH = () => ($('.lx-speccmp svg') ? $('.lx-speccmp svg').getBoundingClientRect().height : 0);
  const setH = (h) => { healUserH = h > 0 ? Math.round(Math.max(120, Math.min(2400, h))) : 0; queueDraw(); };
  grip.addEventListener('pointerdown', (e) => { start = { y: e.clientY, h: boxH() }; grip.setPointerCapture(e.pointerId); grip.classList.add('drag'); e.preventDefault(); });
  grip.addEventListener('pointermove', (e) => { if (start) setH(start.h + e.clientY - start.y); });
  const end = () => { start = null; grip.classList.remove('drag'); };
  grip.addEventListener('pointerup', end); grip.addEventListener('pointercancel', end);
  grip.addEventListener('dblclick', () => setH(0));
  grip.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault(); setH((healUserH || boxH()) + (e.key === 'ArrowDown' ? 40 : -40));
  });
}

// Collapsible cards: the arrow before each title folds the card down to its header.
let drawQueued = false;
const queueDraw = () => { if (!drawQueued) { drawQueued = true; requestAnimationFrame(() => { drawQueued = false; redraw(); }); } };
for (const card of ROOT.querySelectorAll('.hr-card')) {
  const h2 = card.querySelector('h2'), label = h2 ? h2.textContent : card.dataset.label, title = el('div', 'hr-title'), fold = el('button', 'hr-fold');
  fold.type = 'button';
  fold.setAttribute('aria-expanded', 'true');
  fold.setAttribute('aria-label', 'Collapse ' + label);
  fold.addEventListener('click', () => {
    const open = card.classList.toggle('collapsed') === false;
    fold.setAttribute('aria-expanded', String(open));
    fold.setAttribute('aria-label', (open ? 'Collapse ' : 'Expand ') + label);
    if (open) queueDraw();
  });
  // A card with no title (the race grid) still gets the arrow, first in its header.
  if (h2) { h2.replaceWith(title); title.append(fold, h2); } else { title.append(fold); card.querySelector('.hr-cardhead').prepend(title); }
  // Cards marked data-collapsed start folded (the fights table and the notes).
  if (card.hasAttribute('data-collapsed')) { card.classList.add('collapsed'); fold.setAttribute('aria-expanded', 'false'); fold.setAttribute('aria-label', 'Expand ' + label); }
}
// The two spec charts share a row: drag the border between them to give one more width (arrow keys work too;
// double-click to even them out). Both charts redraw to fit, so a wider chart is also a taller, easier to read one.
{
  const row = ROOT.querySelector('.hr-grid2'), left = row.children[0], split = el('div', 'hr-split');
  split.setAttribute('role', 'separator'); split.setAttribute('aria-orientation', 'vertical'); split.setAttribute('aria-label', 'Resize the two charts'); split.tabIndex = 0;
  row.insertBefore(split, row.children[1]);
  const setW = (w) => {
    const max = row.clientWidth - split.offsetWidth - 280;
    left.style.flex = `0 0 ${Math.round(Math.min(max, Math.max(280, w)))}px`;
    queueDraw();
  };
  split.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    try { split.setPointerCapture(e.pointerId); } catch (err) { /* no active pointer to capture: the drag still works while over the border */ }
    const w0 = left.getBoundingClientRect().width, sx = e.clientX;
    split.classList.add('drag');
    const move = (ev) => setW(w0 + ev.clientX - sx);
    const up = () => { split.classList.remove('drag'); split.removeEventListener('pointermove', move); split.removeEventListener('pointerup', up); split.removeEventListener('pointercancel', up); };
    split.addEventListener('pointermove', move); split.addEventListener('pointerup', up); split.addEventListener('pointercancel', up);
  });
  split.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();
    setW(left.getBoundingClientRect().width + (e.key === 'ArrowRight' ? 32 : -32));
  });
  split.addEventListener('dblclick', () => { left.style.flex = ''; queueDraw(); });
  let lastW = 0;
  new ResizeObserver(() => { if (row.clientWidth !== lastW) { lastW = row.clientWidth; left.style.flex = ''; queueDraw(); } }).observe(row);
}
const named = document.getElementById(location.hash.slice(1));
if (named) setTimeout(() => named.scrollIntoView(), 0);
