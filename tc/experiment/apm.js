// Actions per Minute by Spec, shown in each tab's ranking box when its DPS / APM switch is on APM (it uses the box's
// fight length buttons). DPS and Tanks read the `apm` dataset (WoWSims runs counting every press, each build's best race
// at 1 target); Healing works its APM out from the healing sim's spell casts. Clicking a spec shows what it presses,
// damage-meter style: each ability's school colour (from the ability breakdowns), striped when it works over time.
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const CLASS_OF = { Druid: 'druid', Hunter: 'hunter', Mage: 'mage', Paladin: 'paladin', Priest: 'priest', Rogue: 'rogue', Shaman: 'shaman', Warlock: 'warlock', Warrior: 'warrior', Bear: 'druid' };
// Grouped by class, then spec, as the DPS view's spec menu lists them.
const byClass = (a, b) => (CLASS_OF[a.split(' ').pop()] || '').localeCompare(CLASS_OF[b.split(' ').pop()] || '') || a.localeCompare(b);
// Item procs the sim counts as casts though nobody presses them (older runs; the harness's shape_apm.py now leaves them out).
const PROC = new Set(["Alcor's Sunrazor"]);
const CLASS_COLOR = { druid: '#FF7C0A', hunter: '#AAD372', mage: '#3FC7EB', paladin: '#F48CBA', rogue: '#FFF468', shaman: '#0070DD', warlock: '#8788EE', warrior: '#C69B6D' };
const specColor = (s) => { const c = CLASS_COLOR[CLASS_OF[s.split(' ').pop()]]; return c ? `color-mix(in srgb, ${c} 85%, var(--color-fg))` : 'var(--color-fg)'; };
// WoW's combat-log school colours, as the damage breakdowns use them.
const SCHOOL_COLOR = { Physical: '#f0d24a', Holy: '#ffe680', Fire: '#ff8a1f', Nature: '#5fd35f', Frost: '#7fdcff', Shadow: '#9d8cff', Arcane: '#ff8cf2' };
const RACE_NAME = { 'High Order Skyborne': 'Alliance Skyborne', 'Windshaper Skyborne': 'Horde Skyborne' };
const raceName = (r) => RACE_NAME[r] || r;
const HEALER = { priest: 'Holy Priest', druid: 'Restoration Druid', shaman: 'Restoration Shaman' };
const list = (v) => (typeof v === 'string' ? JSON.parse(v) : v || []);
const fightText = (f, lens) => (f === 'all' ? `averaged over ${lens}` : `${f / 60} minute fights`);

dash.calc('healApm', {
  title: 'Healer APM',
  description: 'Each healer\'s spell casts per minute with no racials, from the healing runs, with each spell\'s heal type.',
  inputs: ['healSpells'],
  fn: (healSpells) => healSpells.filter((r) => r.race === 'No racials').map((r) => {
    const presses = JSON.parse(r.spells).map((s) => [s[0], s[4] / (r.fight / 60), s[8]]).filter((s) => s[1] > 0).sort((a, b) => b[1] - a[1]);
    return { cls: r.cls, fight: r.fight, apm: presses.reduce((t, s) => t + s[1], 0), presses: JSON.stringify(presses) };
  }),
});

// One ranking box per tab (spec: the param of the spec whose breakdown the ranking view has open): its dataset, how it picks each spec's build, the ability breakdowns that give each press
// its school and kind, and the filters it reads (each tab's own: the Healing and Tanks tabs prefix theirs with h and t).
const TANK_TITLE = { tps: 'Threat Per Second', dtps: 'Damage Taken Per Second', tmi: 'Spikes (TMI)', dps: 'Damage Per Second' };
// pin / race / specTab: the DPS view's build and race picked (from its breadcrumb or the builds table) and its view switch.
const BOXES = [
  { tab: 'dps', id: 'speccmp', mode: 'cmpMode', fight: 'specFight', view: 'apmView', spec: 'specView', pin: 'specBuild', race: 'specRace', specTab: 'specTab', source: 'apm', role: 'dps', by: 'dps', title: () => 'Damage Per Second', bd: 'breakdown', lens: '1, 2, 3 and 5 minute fights' },
  { tab: 'tanks', id: 't-speccmp', mode: 'tCmpMode', fight: 'tSpecFight', view: 'tApmView', spec: 'tSpecView', pin: 'tSpecBuild', race: 'tSpecRace', specTab: 'tSpecTab', source: 'apm', role: 'tank', by: 'tps', title: (q) => TANK_TITLE[q.tMeasure] || TANK_TITLE.tps, bd: 'tankBreakdown', lens: '1, 2, 3 and 5 minute fights' },
  { tab: 'healing', id: 'h-speccmp', mode: 'hCmpMode', fight: 'hSpecFight', view: 'hApmView', source: 'healApm', title: () => 'Healing Per Second', lens: '2, 3, 5 and 7 minute fights' },
];

// Each spec at the chosen fight length (All: averaged over the four), on the build that does most damage (tanks: threat),
// or the build picked in the DPS view (pin: "spec|build"). Each keeps its spec's builds, best first, for the build menu.
function specItems(b, rows, fight, pin) {
  const pick = rows.filter((r) => fight === 'all' || String(r.fight) === fight);
  const acc = new Map();
  for (const r of pick) {
    const spec = b.source === 'healApm' ? HEALER[r.cls] : r.spec;
    if (!spec) continue;
    const k = spec + '|' + (r.build || '');
    if (!acc.has(k)) acc.set(k, { spec, build: r.build, race: r.race, n: 0, apm: 0, val: 0, presses: new Map(), type: new Map() });
    const a = acc.get(k);
    a.n++; a.val += b.by ? +r[b.by] : 0;
    for (const [name, v, type] of list(r.presses)) {
      if (PROC.has(name)) continue;
      a.apm += v; a.presses.set(name, (a.presses.get(name) || 0) + v); if (type) a.type.set(name, type);
    }
  }
  const specs = new Map(), all = new Map();
  for (const a of acc.values()) {
    if (!all.has(a.spec)) all.set(a.spec, []);
    all.get(a.spec).push(a);
  }
  for (const [spec, g] of all) {
    g.sort((x, y) => y.val / y.n - x.val / x.n);
    const picked = pin && pin.startsWith(spec + '|') && g.find((a) => spec + '|' + a.build === pin);
    specs.set(spec, Object.assign(picked || g[0], { builds: g.length, buildList: g.map((a) => a.build), best: g[0].build }));
  }
  return [...specs.values()].map((a) => ({ ...a, apm: a.apm / a.n,
    presses: [...a.presses].map(([k, v]) => ({ name: k.replace(/�/g, '–'), raw: k, v: v / a.n, type: a.type.get(k) })).sort((x, y) => y.v - x.v) }))
    .sort((x, y) => y.apm - x.apm);
}

function setup(b) {
  const panel = document.querySelector(`[data-tab-panel="${b.tab}"]`), card = panel && panel.querySelector('#' + b.id);
  if (!card) return;
  const title = b.titleEl = card.querySelector('.lx-cmptitle');
  const seg = card.querySelector('.lx-cmpmode'), box = card.querySelector('.lx-apm'), note = card.querySelector('.lx-apmnote'), noteText = note.textContent;
  // Show the chosen chart before the page redraws, so the ranking is measured (and drawn) at its real width.
  card.classList.toggle('apm-on', dash.params()[b.mode] === 'apm');
  seg.addEventListener('click', (e) => {
    const t = e.target.closest('button[data-v]');
    if (!t) return;
    card.classList.toggle('apm-on', t.dataset.v === 'apm');
    // A spec open in one view stays open in the other (DPS and Tanks: its ability breakdown and what it presses).
    const q = dash.params(), apm = t.dataset.v === 'apm';
    dash.setParams({ [b.mode]: t.dataset.v, ...(b.spec && (apm ? { [b.view]: q[b.spec] || '' } : { [b.spec]: q[b.view] || '' })) });
  });
  // The APM view's own drag handle: the chart's height (0: its natural height), kept per box.
  const grip = card.querySelector('.lx-apmgrip');
  b.userH = 0;
  const render = () => {
    const q = dash.params(), on = q[b.mode] === 'apm', fight = String(q[b.fight] || 'all');
    seg.querySelectorAll('button').forEach((e) => e.setAttribute('aria-pressed', String(e.dataset.v === (on ? 'apm' : 'rank'))));
    card.classList.toggle('apm-on', on);
    // The box's title names what it shows (the Tanks tab: its chosen measure). While a spec's breakdown is open the
    // dashboard shows it as a breadcrumb ("Damage Per Second › Combat Rogue"), whose first part is this name.
    title.dataset.base = b.title(q);
    const crumb = !on && title.querySelector('.rr-crumb');
    if (crumb) crumb.textContent = title.dataset.base; else title.textContent = on ? 'Actions Per Minute' : title.dataset.base;
    box.replaceChildren();
    note.textContent = noteText;
    if (!on) return;
    const res = dash.data(b.source);
    if (res.status !== 'ok') { box.textContent = '—'; return; }
    const items = specItems(b, b.role ? res.data.filter((r) => r.role === b.role) : res.data, fight, q[b.view] && b.pin && q[b.pin]);  // the ranking shows each spec's best build
    if (!items.length) { box.textContent = '—'; return; }
    const view = q[b.view] && items.find((d) => d.spec === q[b.view]);
    if (view) drawBreakdown(b, box, note, view, fight, items.map((d) => d.spec), q);
    else draw(b, box, items);
  };
  dash.onData(render);
  let start = null;
  const svgH = () => { const v = box.querySelector('svg'); return v ? v.getBoundingClientRect().height : 0; };
  grip.addEventListener('pointerdown', (e) => { start = { y: e.clientY, h: svgH() }; grip.setPointerCapture(e.pointerId); grip.classList.add('drag'); e.preventDefault(); });
  grip.addEventListener('pointermove', (e) => { if (!start) return; b.userH = Math.max(120, start.h + e.clientY - start.y); render(); });
  const end = () => { start = null; grip.classList.remove('drag'); };
  grip.addEventListener('pointerup', end);
  grip.addEventListener('pointercancel', end);
  grip.addEventListener('dblclick', () => { b.userH = 0; render(); });
  grip.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    e.preventDefault(); b.userH = Math.max(120, (b.userH || svgH()) + (e.key === 'ArrowDown' ? 40 : -40)); render();
  });
}

function draw(b, box, items) {
  // Rows are 20 px bars with 6 px gaps, spread out (bars up to 64 px) when the box has been dragged taller.
  let bh = 20, gap = 6;
  if (b.userH) { const slot = Math.max(12, (b.userH - 22) / items.length); bh = Math.min(64, slot * 0.75); gap = slot - bh; }
  const iz = Math.min(28, Math.max(14, bh)), W = Math.max(280, box.clientWidth), H = items.length * (bh + gap) + 22;
  const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
  const probe = svg.append('text').attr('class', 'lab');
  const textW = (t) => { probe.text(t); return probe.node().getComputedTextLength(); };
  const label = (d) => d.apm.toFixed(1);
  // A phone: short spec names, no build and race after the bar (the hover has them), so the bars keep room.
  const narrow = narrowChart(W), nm = (d) => (narrow ? shortSpec(d.spec) : d.spec);
  const side = (d) => (b.role && !narrow ? `${d.build} · ${RACE_NAME[d.race] || d.race}` : '');
  for (const d of items) d.lw = textW(label(d));
  const ml = iz + 8 + Math.max(...items.map((d) => textW(nm(d)))) + 12;
  const mr = 8 + Math.max(...items.map((d) => d.lw + 8 + textW(side(d)))) + 4;
  probe.remove();
  const x = d3.scaleLinear([0, d3.max(items, (d) => d.apm)], [ml, W - mr]).nice();
  svg.append('g').selectAll('line').data(x.ticks(5)).join('line').attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', H - 18).attr('stroke', 'var(--cds-chart-grid)');
  svg.append('g').selectAll('text').data(x.ticks(5)).join('text').attr('x', x).attr('y', H - 4).attr('text-anchor', 'middle').text((t) => t);
  const g = svg.append('g').selectAll('g').data(items).join('g').attr('transform', (d, i) => `translate(0,${i * (bh + gap) + 2})`);
  g.append('image').attr('href', (d) => (window.SPEC_ICONS || {})[d.spec] || null).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz);
  g.append('text').attr('class', 'lab').attr('x', iz + 8).attr('y', bh / 2 + 4).style('fill', (d) => specColor(d.spec)).text(nm);
  g.append('rect').attr('x', x(0)).attr('height', bh).attr('rx', 3).attr('width', (d) => Math.max(1, x(d.apm) - x(0))).style('fill', (d) => specColor(d.spec)).attr('fill-opacity', 0.85);
  g.append('text').attr('class', 'lab').attr('x', (d) => x(d.apm) + 8).attr('y', bh / 2 + 4).text(label);
  g.append('text').attr('x', (d) => x(d.apm) + 8 + d.lw + 8).attr('y', bh / 2 + 4).text(side);
  // Hover a spec for its numbers; click it for what it presses.
  const tip = el('div', 'rr-tip'); tip.hidden = true; box.append(tip);
  const line = (k, v) => { const row = el('div', 'row'); row.append(el('span', null, k), el('b', null, v)); return row; };
  g.append('rect').attr('x', 0).attr('y', -gap / 2).attr('width', W).attr('height', bh + gap).attr('fill', 'transparent').style('cursor', 'pointer')
    .on('mousemove', (ev, d) => {
      const head = el('div', 'h', d.spec); head.style.color = specColor(d.spec);
      tip.replaceChildren(head, line('Actions per minute', d.apm.toFixed(1)),
        ...(b.role ? [line('Build', d.builds > 1 ? `${d.build} (best of ${d.builds})` : d.build), line('Race', RACE_NAME[d.race] || d.race)] : []),
        line('Most pressed', d.presses[0] ? d.presses[0].name : '–'));
      tip.hidden = false;
      const [mx, my] = d3.pointer(ev, box), tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(box.clientWidth - tw, mx + 14)) + 'px';
      tip.style.top = my + 14 + 'px';
    })
    .on('mouseleave', () => { tip.hidden = true; })
    .on('click', (ev, d) => dash.setParams({ [b.view]: d.spec }));
}

// Each press's school and kind, from the spec's ability breakdowns; a press that does no damage (a buff, a stance, a
// cooldown, a potion) is Utility.
function kinds(b, spec) {
  const out = new Map();
  if (!b.bd) return out;
  const res = dash.data(b.bd);
  if (res.status !== 'ok') return out;
  for (const r of res.data) {
    if (r.spec !== spec) continue;
    for (const [name, pet, , , , , school, kind] of list(r.abilities)) if (!pet && !out.has(name)) out.set(name, { school: school || 'Physical', kind: kind === 'resource' ? 'utility' : kind || 'direct' });
  }
  return out;
}

const KIND_LABEL = { direct: 'Direct', dot: 'Over time', channel: 'Channel', utility: 'Utility (no damage)', heal: 'Heal', hot: 'Heal over time', absorb: 'Absorb' };
// The spec's name opens a menu of the other specs, to switch breakdowns as the DPS view does.
let apmMenu = null;
const closeApmMenu = () => { if (apmMenu) { apmMenu.btn.setAttribute('aria-expanded', 'false'); apmMenu.el.remove(); apmMenu = null; } };
document.addEventListener('pointerdown', (e) => { if (apmMenu && !apmMenu.el.contains(e.target) && e.target !== apmMenu.btn) closeApmMenu(); });
document.addEventListener('keydown', (e) => { if (apmMenu && e.key === 'Escape') { const btn = apmMenu.btn; closeApmMenu(); btn.focus(); } });
// opts (the build menu): { items, pick(s), label(s), title } in place of the specs, with spec the current choice.
function apmPicker(b, spec, specs, opts) {
  const btn = el('button', opts ? 'rr-pick rr-pick2' : 'rr-pick', opts && opts.label ? opts.label(spec) : spec);
  btn.type = 'button'; if (!opts) btn.style.color = specColor(spec); btn.title = opts ? opts.title : 'Choose a spec';
  btn.setAttribute('aria-haspopup', 'menu'); btn.setAttribute('aria-expanded', 'false');
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    if (apmMenu && apmMenu.btn === btn) { closeApmMenu(); return; }
    closeApmMenu();
    const root = btn.closest('[data-tab-panel]'), list = el('div', 'rr-menu');
    list.setAttribute('role', 'menu');
    for (const s of opts ? opts.items : [...specs].sort(byClass)) {
      const it = el('button', null, opts && opts.label ? opts.label(s) : s);
      it.type = 'button'; it.setAttribute('role', 'menuitemradio'); it.setAttribute('aria-checked', String(s === spec)); it.style.color = opts ? 'var(--color-fg)' : specColor(s);
      it.addEventListener('click', () => { closeApmMenu(); if (opts) opts.pick(s); else dash.setParams({ [b.view]: s }); });
      list.append(it);
    }
    root.append(list);
    // Opened around the spec name, like a dropdown: the current spec sits over the name with the others above and
    // below it (a long list scrolled to put it mid-way), kept on screen. Placed against whatever box the menu is
    // positioned in, as the tab itself isn't one.
    const cur = list.querySelector('[aria-checked="true"]') || list.firstChild, pad = (e) => parseFloat(getComputedStyle(e).paddingLeft) || 0;
    // The current spec is drawn just as the name it covers (font, size and highlight), so the name seems to stay put.
    const bs = getComputedStyle(btn);
    Object.assign(cur.style, { fontFamily: bs.fontFamily, fontSize: bs.fontSize, fontWeight: bs.fontWeight, letterSpacing: bs.letterSpacing, lineHeight: bs.lineHeight, background: 'color-mix(in srgb, var(--color-fg) 10%, transparent)' });
    list.scrollTop = Math.max(0, cur.offsetTop - (list.clientHeight - cur.offsetHeight) / 2);
    const bb = btn.getBoundingClientRect(), lb = list.getBoundingClientRect(), cb = cur.getBoundingClientRect(), ob = list.offsetParent.getBoundingClientRect();
    const x = Math.max(8, Math.min(innerWidth - lb.width - 8, bb.left + pad(btn) - (cb.left - lb.left + pad(cur))));
    // Where the list starts for the current spec to sit over the name. A list that would run off the screen is cut
    // short there rather than moved (and scrolled on to keep the current spec in place), so the name never shifts. With
    // no room above for more than a couple of specs (the name near the top of the window, the current spec near the
    // list's end), it opens as a plain dropdown below the name instead, scrolled to the current spec.
    let y = bb.top + (bb.height - cb.height) / 2 - (cb.top - lb.top), h = lb.height;
    const below = 8 - y > cb.height * 2;
    list.style.boxSizing = 'border-box'; // a cut height counts the menu's padding and border
    if (below) {
      for (const k of ['fontFamily', 'fontSize', 'fontWeight', 'letterSpacing', 'lineHeight', 'background']) cur.style[k] = '';
      y = bb.bottom + 4;
      list.style.maxHeight = Math.min(lb.height, innerHeight - 8 - y) + 'px';
      list.scrollTop = Math.max(0, cur.offsetTop - (list.clientHeight - cur.offsetHeight) / 2);
    } else {
      if (y < 8) { h -= 8 - y; list.style.maxHeight = h + 'px'; list.scrollTop += 8 - y; y = 8; }
      if (y + h > innerHeight - 8) list.style.maxHeight = (h = innerHeight - 8 - y) + 'px';
    }
    list.style.left = x - ob.left + 'px'; list.style.top = y - ob.top + 'px';
    // The other specs unfold above and below it (a dropdown below the name unfolds downwards).
    const ll = list.getBoundingClientRect(), cl = cur.getBoundingClientRect();
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches)
      list.animate([{ clipPath: below ? 'inset(0 0 100% 0)' : `inset(${cl.top - ll.top}px 0 ${ll.bottom - cl.bottom}px 0)` }, { clipPath: 'inset(0 0 0 0)' }], { duration: 160, easing: 'cubic-bezier(.2, .8, .2, 1)' });
    btn.setAttribute('aria-expanded', 'true');
    apmMenu = { el: list, btn };
    (list.querySelector('[aria-checked="true"]') || list.firstChild).focus({ preventScroll: true });
  });
  return btn;
}
function drawBreakdown(b, box, note, item, fight, specs, q) {
  const healer = !b.role, cls = healer ? specColor(item.spec) : null, K = kinds(b, item.spec);
  const rows = item.presses.map((p) => {
    if (healer) {
      const t = String(p.type || '');
      return { ...p, school: null, kind: t.includes('hot') ? 'hot' : t.startsWith('channel') ? 'channel' : t === 'absorb' ? 'absorb' : 'heal' };
    }
    const k = K.get(p.raw) || { school: null, kind: 'utility' };
    return { ...p, school: k.school, kind: k.kind === 'auto' || k.kind === 'proc' ? 'direct' : k.kind };
  });
  const total = rows.reduce((t, a) => t + a.v, 0);
  // What was simmed and the total: the build, the race and the fight length, then every press per minute added up.
  const pinRace = b.race && q[b.race] && b.pin && q[b.pin] === item.spec + '|' + item.build ? q[b.race] : '';
  note.replaceChildren(`${b.role ? `${item.build} · ${raceName(item.race)} · ` : ''}${fight === 'all' ? `averaged over ${b.lens}` : `${fight / 60} minute fight${b.role ? '' : 's'}`} · `,
    el('b', null, `${total.toFixed(1)} actions per minute`),
    ...(pinRace && pinRace !== item.race ? [` · Presses were counted only with each build's best race, so this is ${raceName(item.race)}'s, not ${raceName(pinRace)}'s.`] : []));
  // The box's title becomes a breadcrumb, as in the damage breakdown: its name goes back to all specs, then the spec
  // and (DPS and Tanks) the build, each a menu of the others; picking a build here picks it in the DPS view too.
  const back = el('button', 'rr-crumb', 'Actions Per Minute');
  back.type = 'button'; back.title = 'Back to all specs';
  back.addEventListener('click', () => dash.setParams({ [b.view]: '' }));
  const sep = () => el('span', 'rr-crumbsep', '›');
  b.titleEl.replaceChildren(back, sep(), apmPicker(b, item.spec, specs),
    ...(b.role ? [sep(), apmPicker(b, item.build, null, { items: item.buildList, title: 'Choose a build', pick: (bd) => dash.setParams({ [b.pin]: item.spec + '|' + bd, [b.race]: '' }) })] : []));
  const col = (a) => (healer ? cls : SCHOOL_COLOR[a.school] || 'var(--color-fg-muted)');
  // Legend swatches reuse the damage breakdown's styles: over time as its stripes, utility as its grey, absorbs outlined.
  const sw = (c, kind) => { const e = el('span', 'rr-bdsw'); e.dataset.kind = kind === 'hot' ? 'dot' : kind === 'utility' ? 'resource' : kind === 'absorb' ? 'proc' : kind; e.style.setProperty('--c', c); return e; };
  const key = (s, t) => { const k = el('span', 'rr-bdkey'); k.append(s, t); return k; };
  const schools = healer ? [] : [...new Set(rows.filter((a) => a.school && a.kind !== 'utility').map((a) => a.school))];
  const present = new Set(rows.map((a) => a.kind)), c0 = healer ? cls : SCHOOL_COLOR[schools[0]] || SCHOOL_COLOR.Physical;
  const legend = el('div', 'rr-bdlegend');
  legend.append(...schools.map((sc) => key(sw(SCHOOL_COLOR[sc], 'direct'), sc)), ...(schools.length ? [el('span', 'rr-bdsep')] : []),
    ...Object.keys(KIND_LABEL).filter((k) => present.has(k)).map((k) => key(sw(c0, k), KIND_LABEL[k])));
  // DPS and Tanks: Setup opens the build's gear, talents and consumables in the damage view.
  if (b.role) {
    const bar = el('div', 'rr-bdbar'), seg = el('div', 'rr-seg'), su = el('button', null, 'Setup');
    su.type = 'button'; su.title = 'The gear, talents, consumables and buffs this build was simmed with';
    su.addEventListener('click', () => {
      b.titleEl.closest('section').classList.remove('apm-on');
      dash.setParams({ [b.mode]: 'rank', [b.spec]: item.spec, [b.specTab]: 'setup', ...(q[b.pin] === item.spec + '|' + item.build ? {} : { [b.pin]: item.spec + '|' + item.build, [b.race]: item.race }) });
    });
    seg.append(su); bar.append(legend, seg); box.append(bar);
  } else box.append(legend);
  const slot = b.userH ? Math.max(16, (b.userH - 22) / rows.length) : 26, bh = Math.min(64, slot * 0.78), gap = slot - bh;
  const W = Math.max(280, box.clientWidth), H = rows.length * slot + 22, iz = Math.min(28, Math.max(14, bh));
  const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
  const probe = svg.append('text').attr('class', 'lab');
  const textW = (t) => { probe.text(t); return probe.node().getComputedTextLength(); };
  const valText = (a) => (narrowChart(W) ? `${a.v.toFixed(a.v < 1 ? 2 : 1)}` : `${a.v.toFixed(a.v < 1 ? 2 : 1)} / min · ${((a.v / total) * 100).toFixed(1)}%`);
  for (const a of rows) a.vw = textW(valText(a));
  const ml = iz + 6 + Math.max(...rows.map((a) => textW(a.name))) + 14, mr = Math.max(...rows.map((a) => a.vw)) + 12;
  probe.remove();
  const x = d3.scaleLinear([0, rows[0].v], [ml, W - mr]);
  svg.append('g').selectAll('line').data(x.ticks(5)).join('line').attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', H - 18).attr('stroke', 'var(--cds-chart-grid)');
  svg.append('g').selectAll('text').data(x.ticks(5)).join('text').attr('x', x).attr('y', H - 4).attr('text-anchor', 'middle').text((t) => t);
  // Stripes for damage and heals over time (diagonal) and channels (upright), one pattern per colour shown.
  const defs = svg.append('defs'), uid = Math.random().toString(36).slice(2), colors = [...new Set(rows.map(col))];
  const pid = (c, kind) => `apm-${uid}-${colors.indexOf(c)}-${kind}`;
  for (const c of colors) {
    const d = defs.append('pattern').attr('id', pid(c, 'dot')).attr('patternUnits', 'userSpaceOnUse').attr('width', 8).attr('height', 8).attr('patternTransform', 'rotate(45)');
    d.append('rect').attr('width', 8).attr('height', 8).style('fill', c).attr('fill-opacity', 0.35);
    d.append('rect').attr('width', 4).attr('height', 8).style('fill', c);
    const ch = defs.append('pattern').attr('id', pid(c, 'ch')).attr('patternUnits', 'userSpaceOnUse').attr('width', 6).attr('height', 8);
    ch.append('rect').attr('width', 6).attr('height', 8).style('fill', c).attr('fill-opacity', 0.35);
    ch.append('rect').attr('width', 3).attr('height', 8).style('fill', c);
  }
  const fill = (a) => (a.kind === 'utility' ? 'var(--color-fg-muted)' : a.kind === 'dot' || a.kind === 'hot' ? `url(#${pid(col(a), 'dot')})` : a.kind === 'channel' ? `url(#${pid(col(a), 'ch')})` : col(a));
  const g = svg.append('g').selectAll('g').data(rows).join('g').attr('transform', (a, i) => `translate(0,${i * slot + 2})`);
  const abIcons = g.append('image').attr('href', (a) => (window.ABILITY_ICONS || {})[a.raw] || (window.ABILITY_ICONS || {})[a.name] || null).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz);
  g.append('text').attr('class', 'lab').attr('x', iz + 6).attr('y', bh / 2 + 4).text((a) => a.name);
  window.abilityLinks(box, abIcons.nodes(), (a) => [a.raw, a.name]);
  g.append('rect').attr('x', x(0)).attr('height', bh).attr('rx', 3).attr('width', (a) => Math.max(1, x(a.v) - x(0)))
    .style('fill', fill).attr('fill-opacity', (a) => (a.kind === 'utility' ? 0.5 : a.kind === 'absorb' ? 0.25 : 0.9))
    .style('stroke', (a) => (a.kind === 'absorb' ? col(a) : 'none')).attr('stroke-width', 1.5);
  g.append('text').attr('x', (a) => x(a.v) + 6).attr('y', bh / 2 + 4).text(valText);
  const tip = el('div', 'rr-tip'); tip.hidden = true; box.append(tip);
  const line = (k, v) => { const row = el('div', 'row'); row.append(el('span', null, k), el('b', null, v)); return row; };
  // Hovering the bar (or its value) shows its numbers; the icon has Wowhead's tooltip of its own.
  g.append('rect').attr('x', x(0)).attr('y', -gap / 2).attr('width', (a) => Math.max(1, x(a.v) - x(0)) + 6 + a.vw).attr('height', slot).attr('fill', 'transparent')
    .on('mousemove', (ev, a) => {
      const secs = fight === 'all' ? null : +fight;
      tip.replaceChildren(el('div', 'h', a.name), line('Presses per minute', a.v.toFixed(2)), line('Share of presses', ((a.v / total) * 100).toFixed(1) + '%'),
        ...(secs ? [line('Per fight', ((a.v * secs) / 60).toFixed(1))] : []), ...(a.school && a.kind !== 'utility' ? [line('School', a.school)] : []), line('Kind', KIND_LABEL[a.kind]));
      tip.hidden = false;
      const [mx, my] = d3.pointer(ev, box), tw = tip.offsetWidth;
      tip.style.left = Math.max(0, Math.min(box.clientWidth - tw, mx + 14)) + 'px'; tip.style.top = my + 14 + 'px';
    })
    .on('mouseleave', () => { tip.hidden = true; });
}

BOXES.forEach(setup);
