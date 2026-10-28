// Horizontal zoom for the Racial Bonus charts, like the Race Standings charts': the wheel zooms where it points (and
// never scrolls the page), dragging moves around, double-click zooms back out. Only the value scale zooms; the race
// rows stay put. onZoom(x) redraws the chart against the zoomed scale x. The zoom is kept in store while key (the
// chart's spec, fight length...) stays the same, so a redraw for something else doesn't throw it away.
window.xZoom = (svg, { x0, left, right, top, bottom, store, key, onZoom }) => {
  if (store.key !== key) { store.key = key; store.t = d3.zoomIdentity; }
  const zoom = d3.zoom().scaleExtent([1, 40]).extent([[left, top], [right, bottom]]).translateExtent([[left, top], [right, bottom]])
    .on('zoom', (ev) => { store.t = ev.transform; onZoom(ev.transform.rescaleX(x0)); });
  svg.node().addEventListener('wheel', (e) => e.preventDefault(), { passive: false });
  svg.call(zoom).on('dblclick.zoom', null).on('dblclick', () => svg.transition().duration(250).call(zoom.transform, d3.zoomIdentity));
  svg.call(zoom.transform, store.t);
};
// A clip path for the plot area, so zoomed bars and boxes don't run over the race names.
window.xZoomClip = (svg, left, right, height) => {
  const id = 'xz-' + Math.random().toString(36).slice(2);
  svg.append('defs').append('clipPath').attr('id', id).append('rect').attr('x', left).attr('y', -4).attr('width', right - left).attr('height', height + 8);
  return `url(#${id})`;
};
