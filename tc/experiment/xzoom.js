// Horizontal zoom for the Heals tab's box plots, like the Race Standings charts': the wheel zooms where it points (and
// never scrolls the page), dragging moves around, double-click zooms back out. On a touch screen one finger dragged
// sideways moves along, up or down scrolls the page, and two fingers zoom. Only the value scale zooms; the race
// rows stay put. onZoom(x) redraws the chart against the zoomed scale x. The zoom is kept in store while key (the
// chart's spec, fight length...) stays the same, so a redraw for something else doesn't throw it away.
window.xZoom = (svg, { x0, left, right, top, bottom, store, key, onZoom }) => {
  if (store.key !== key) { store.key = key; store.t = d3.zoomIdentity; }
  const zoom = d3.zoom().scaleExtent([1, 40]).extent([[left, top], [right, bottom]]).translateExtent([[left, top], [right, bottom]])
    .filter((ev) => (!ev.ctrlKey || ev.type === 'wheel') && !ev.button && (!ev.touches || ev.touches.length > 1))
    .on('zoom', (ev) => { store.t = ev.transform; onZoom(ev.transform.rescaleX(x0)); });
  svg.node().addEventListener('wheel', (e) => e.preventDefault(), { passive: false });
  svg.style('touch-action', 'pan-y').call(zoom).on('dblclick.zoom', null).on('dblclick', () => svg.transition().duration(250).call(zoom.transform, d3.zoomIdentity));
  touchPanX(svg, zoom);
  svg.call(zoom.transform, store.t);
};
// Touch: one finger dragged sideways moves a d3-zoomed chart along (d3's own touch handling is left to two fingers);
// dragged up or down it still scrolls the page. The svg keeps touch-action: pan-y, so sideways moves reach us.
window.touchPanX = (svg, zoom) => {
  const node = svg.node(); let s = null;
  node.addEventListener('touchstart', (e) => { s = e.touches.length === 1 ? { x: e.touches[0].clientX, y: e.touches[0].clientY, side: null } : null; }, { passive: true });
  node.addEventListener('touchmove', (e) => {
    if (!s || e.touches.length !== 1) return;
    const t = e.touches[0], dx = t.clientX - s.x, dy = t.clientY - s.y;
    if (s.side === null) { if (Math.hypot(dx, dy) < 6) return; s.side = Math.abs(dx) > Math.abs(dy); }
    if (!s.side) return;
    if (e.cancelable) e.preventDefault();
    zoom.translateBy(svg, dx / d3.zoomTransform(node).k, 0);
    s.x = t.clientX; s.y = t.clientY;
  }, { passive: false });
};
// Touch: two fingers pinch to zoom (and move along) a scrolling timeline that redraws itself, so the listeners go on
// the touched elements, which keep getting the fingers' events after a redraw takes them out of the page.
// begin(clientX) when the second finger lands, move(scale since then, clientX) as they move; clientX is their midpoint.
window.pinchZoom = (node, { begin, move }) => {
  let d0 = 0, raf = 0, last = null, on = [];
  const dist = (t) => Math.hypot(t[0].clientX - t[1].clientX, t[0].clientY - t[1].clientY) || 1, mid = (t) => (t[0].clientX + t[1].clientX) / 2;
  const onMove = (e) => {
    if (!d0 || e.touches.length !== 2) return;
    if (e.cancelable) e.preventDefault();
    last = [dist(e.touches) / d0, mid(e.touches)];
    if (!raf) raf = requestAnimationFrame(() => { raf = 0; if (d0) move(...last); });
  };
  const stop = (e) => {
    if (e && e.touches.length >= 2) return;
    d0 = 0;
    for (const t of on) { t.removeEventListener('touchmove', onMove); t.removeEventListener('touchend', stop); t.removeEventListener('touchcancel', stop); }
    on = [];
  };
  node.addEventListener('touchstart', (e) => {
    if (e.touches.length !== 2) return;
    stop(); d0 = dist(e.touches); begin(mid(e.touches));
    on = [...new Set([...e.touches].map((t) => t.target))];
    for (const t of on) { t.addEventListener('touchmove', onMove, { passive: false }); t.addEventListener('touchend', stop); t.addEventListener('touchcancel', stop); }
  }, { passive: true });
};
// A clip path for the plot area, so zoomed bars and boxes don't run over the race names.
window.xZoomClip = (svg, left, right, height) => {
  const id = 'xz-' + Math.random().toString(36).slice(2);
  svg.append('defs').append('clipPath').attr('id', id).append('rect').attr('x', left).attr('y', -4).attr('width', right - left).attr('height', height + 8);
  return `url(#${id})`;
};
// On a narrow screen (a phone), charts shorten spec names so their bars keep room: "Prot Warrior", "Resto Druid".
window.shortSpec = (n) => n.replace(/^Protection /, 'Prot ').replace(/^Restoration /, 'Resto ').replace(/^Beast Mastery /, 'BM ')
  .replace(/^Marksmanship /, 'MM ').replace(/^Enhancement /, 'Enh ').replace(/^Assassination /, 'Assassin ').replace(/^Demonology /, 'Demo ')
  .replace(/^Destruction /, 'Destro ').replace(/^Affliction /, 'Affli ').replace(/^Elemental /, 'Ele ').replace(/^Retribution /, 'Ret ').replace(/^Subtlety /, 'Sub ');
window.narrowChart = (W) => W < 560;
