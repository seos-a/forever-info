// Actions per Minute by Spec, shown in each tab's ranking box when its DPS / APM switch is on APM (it uses the box's
// fight length buttons). DPS and Tanks read the `apm` dataset (WoWSims runs counting every press, each build's best race
// at 1 target); Healing works its APM out from the healing sim's spell casts.
const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const CLASS_OF = { Druid: 'druid', Hunter: 'hunter', Mage: 'mage', Paladin: 'paladin', Rogue: 'rogue', Shaman: 'shaman', Warlock: 'warlock', Warrior: 'warrior', Bear: 'druid' };
const CLASS_COLOR = { druid: '#FF7C0A', hunter: '#AAD372', mage: '#3FC7EB', paladin: '#F48CBA', rogue: '#FFF468', shaman: '#0070DD', warlock: '#8788EE', warrior: '#C69B6D' };
const specColor = (s) => { const c = CLASS_COLOR[CLASS_OF[s.split(' ').pop()]]; return c ? `color-mix(in srgb, ${c} 85%, var(--color-fg))` : 'var(--color-fg)'; };
const RACE_NAME = { 'High Order Skyborne': 'Alliance Skyborne', 'Windshaper Skyborne': 'Horde Skyborne' };
const HEALER = { priest: 'Holy Priest', druid: 'Restoration Druid', shaman: 'Restoration Shaman' };
const list = (v) => (typeof v === 'string' ? JSON.parse(v) : v || []);

dash.calc('healApm', {
  title: 'Healer APM',
  description: 'Each healer\'s spell casts per minute with no racials, from the healing runs.',
  inputs: ['healSpells'],
  fn: (healSpells) => healSpells.filter((r) => r.race === 'No racials').map((r) => {
    const presses = JSON.parse(r.spells).map((s) => [s[0], s[4] / (r.fight / 60)]).filter((s) => s[1] > 0).sort((a, b) => b[1] - a[1]);
    return { cls: r.cls, fight: r.fight, apm: presses.reduce((t, s) => t + s[1], 0), presses: JSON.stringify(presses) };
  }),
});

// One ranking box per tab: its dataset, its fight lengths, how it picks each spec's build, and the filters it reads
// (each tab's own: the Healing and Tanks tabs prefix theirs with h and t).
const BOXES = [
  { tab: 'dps', id: 'speccmp', mode: 'cmpMode', fight: 'specFight', source: 'apm', role: 'dps', by: 'dps' },
  { tab: 'tanks', id: 't-speccmp', mode: 'tCmpMode', fight: 'tSpecFight', source: 'apm', role: 'tank', by: 'tps' },
  { tab: 'healing', id: 'h-speccmp', mode: 'hCmpMode', fight: 'hSpecFight', source: 'healApm' },
];

// Each spec at the chosen fight length (All: averaged over the four), on the build that does most damage (tanks: threat).
function specItems(b, rows, fight) {
  const pick = rows.filter((r) => fight === 'all' || String(r.fight) === fight);
  const acc = new Map();
  for (const r of pick) {
    const spec = b.source === 'healApm' ? HEALER[r.cls] : r.spec;
    if (!spec) continue;
    const k = spec + '|' + (r.build || '');
    if (!acc.has(k)) acc.set(k, { spec, build: r.build, race: r.race, n: 0, apm: 0, val: 0, presses: new Map() });
    const a = acc.get(k);
    a.n++; a.apm += +r.apm; a.val += b.by ? +r[b.by] : 0;
    for (const [name, v] of list(r.presses)) a.presses.set(name, (a.presses.get(name) || 0) + v);
  }
  const specs = new Map();
  for (const a of acc.values()) {
    const cur = specs.get(a.spec);
    a.builds = (cur ? cur.builds : 0) + 1;
    if (!cur || a.val / a.n > cur.val / cur.n) specs.set(a.spec, a); else cur.builds = a.builds;
  }
  return [...specs.values()].map((a) => ({ ...a, apm: a.apm / a.n, presses: [...a.presses].map(([k, v]) => [k.replace(/�/g, '–'), v / a.n]).sort((x, y) => y[1] - x[1]) }))
    .sort((x, y) => y.apm - x.apm);
}

function setup(b) {
  const panel = document.querySelector(`[data-tab-panel="${b.tab}"]`), card = panel && panel.querySelector('#' + b.id);
  if (!card) return;
  const seg = card.querySelector('.lx-cmpmode'), box = card.querySelector('.lx-apm'), h2 = card.querySelector('h2'), title = h2.textContent;
  seg.addEventListener('click', (e) => { const t = e.target.closest('button[data-v]'); if (t) dash.setParams({ [b.mode]: t.dataset.v }); });
  dash.onData(() => {
    const on = dash.params()[b.mode] === 'apm', fight = String(dash.params()[b.fight] || 'all');
    seg.querySelectorAll('button').forEach((e) => e.setAttribute('aria-pressed', String(e.dataset.v === (on ? 'apm' : 'rank'))));
    card.classList.toggle('apm-on', on);
    h2.textContent = on ? 'Actions per Minute by Spec' : title;
    box.replaceChildren();
    if (!on) return;
    const res = dash.data(b.source);
    if (res.status !== 'ok') { box.textContent = '—'; return; }
    const items = specItems(b, b.role ? res.data.filter((r) => r.role === b.role) : res.data, fight);
    if (!items.length) { box.textContent = '—'; return; }
    draw(b, box, items);
  });
}

function draw(b, box, items) {
  const bh = 20, gap = 6, iz = 18, W = Math.max(280, box.clientWidth), H = items.length * (bh + gap) + 22;
  const svg = d3.select(box).append('svg').attr('width', '100%').attr('viewBox', `0 0 ${W} ${H}`);
  const probe = svg.append('text').attr('class', 'lab');
  const textW = (t) => { probe.text(t); return probe.node().getComputedTextLength(); };
  const label = (d) => d.apm.toFixed(1);
  const side = (d) => (b.role ? `${d.build} · ${RACE_NAME[d.race] || d.race}` : '');
  const ml = iz + 8 + Math.max(...items.map((d) => textW(d.spec))) + 12;
  const mr = 8 + Math.max(...items.map((d) => textW(label(d)) + 8 + textW(side(d)))) + 4;
  probe.remove();
  const x = d3.scaleLinear([0, d3.max(items, (d) => d.apm)], [ml, W - mr]).nice();
  svg.append('g').selectAll('line').data(x.ticks(5)).join('line').attr('x1', x).attr('x2', x).attr('y1', 0).attr('y2', H - 18).attr('stroke', 'var(--cds-chart-grid)');
  svg.append('g').selectAll('text').data(x.ticks(5)).join('text').attr('x', x).attr('y', H - 4).attr('text-anchor', 'middle').text((t) => t);
  const g = svg.append('g').selectAll('g').data(items).join('g').attr('transform', (d, i) => `translate(0,${i * (bh + gap) + 2})`);
  g.append('image').attr('href', (d) => (window.SPEC_ICONS || {})[d.spec] || null).attr('y', (bh - iz) / 2).attr('width', iz).attr('height', iz);
  g.append('text').attr('class', 'lab').attr('x', iz + 8).attr('y', bh / 2 + 4).style('fill', (d) => specColor(d.spec)).text((d) => d.spec);
  g.append('rect').attr('x', x(0)).attr('height', bh).attr('rx', 3).attr('width', (d) => Math.max(1, x(d.apm) - x(0))).style('fill', (d) => specColor(d.spec)).attr('fill-opacity', 0.85);
  g.append('text').attr('class', 'lab').attr('x', (d) => x(d.apm) + 8).attr('y', bh / 2 + 4).text(label);
  g.append('text').attr('x', (d) => x(d.apm) + 8 + textW2(svg, label(d)) + 8).attr('y', bh / 2 + 4).text(side);
  // Hover a spec for what it presses, most first.
  const tip = el('div', 'rr-tip'); tip.hidden = true; box.append(tip);
  const line = (k, v) => { const row = el('div', 'row'); row.append(el('span', null, k), el('b', null, v)); return row; };
  g.append('rect').attr('x', 0).attr('y', -gap / 2).attr('width', W).attr('height', bh + gap).attr('fill', 'transparent')
    .on('mousemove', (ev, d) => {
      const top = d.presses.slice(0, 12), rest = d.presses.slice(12).reduce((t, p) => t + p[1], 0);
      tip.replaceChildren(el('div', 'h', `${d.spec} · ${d.apm.toFixed(1)} APM`),
        ...(b.role ? [line('Build', d.builds > 1 ? `${d.build} (best of ${d.builds})` : d.build), line('Race', RACE_NAME[d.race] || d.race)] : []),
        el('div', 'h', 'Presses per minute'), ...top.map((p) => line(p[0], p[1].toFixed(p[1] < 1 ? 2 : 1))), ...(rest > 0.005 ? [line('Other', rest.toFixed(rest < 1 ? 2 : 1))] : []));
      tip.hidden = false;
      const [mx, my] = d3.pointer(ev, box), tw = tip.offsetWidth, th = tip.offsetHeight;
      tip.style.left = Math.max(0, Math.min(box.clientWidth - tw, mx + 14)) + 'px';
      tip.style.top = Math.max(0, Math.min(H - th, my + 14)) + 'px';
    })
    .on('mouseleave', () => { tip.hidden = true; });
}
const textW2 = (svg, t) => { const p = svg.append('text').attr('class', 'lab').text(t), w = p.node().getComputedTextLength(); p.remove(); return w; };

BOXES.forEach(setup);
