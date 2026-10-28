// The race-by-spec tables' size: each table opens as big as its box's width allows without a sideways scrollbar
// (1.5 times at most, so the narrow Tanks and Healing tables don't open huge). Dragging its handle down makes the text
// and cells bigger, up to that no-scrollbar size (2.5 times at most); dragging up makes them smaller again (no smaller
// than normal). Double-click goes back to the opening size; arrow keys work too. The size follows the window: it shrinks
// when the box gets narrower. It is a CSS variable (--mz) on the table's box, so it stays through the table's redraws.
document.querySelectorAll('.lx-mxgrip').forEach((grip) => {
  const card = grip.closest('section'), table = card.querySelector('.lx-matrix'), wrap = table.parentElement;
  const scale = () => parseFloat(card.style.getPropertyValue('--mz')) || 1;
  // The table's width grows with the size, so the biggest size that fits is the box's width over the table's own width
  // at size 1 (measured at its natural width: it is otherwise stretched to fill the box). Null while the tab is hidden.
  const fit = () => {
    if (!wrap.clientWidth) return null;
    const prev = table.style.width;
    table.style.width = 'max-content';
    const w = table.offsetWidth / scale();
    table.style.width = prev;
    return w ? Math.floor(((wrap.clientWidth - 2) / w) * 100) / 100 : null;
  };
  let chosen = null; // the size dragged to, or null for the opening size
  const apply = () => {
    const f = fit();
    if (f == null) return;
    const v = Math.max(1, Math.min(2.5, f, chosen == null ? 1.5 : chosen));
    if (Math.abs(v - scale()) > 0.005) card.style.setProperty('--mz', String(v));
  };
  const set = (v) => { chosen = Math.max(1, Math.min(2.5, fit() ?? 2.5, v)); apply(); };
  new ResizeObserver(apply).observe(wrap);
  new ResizeObserver(apply).observe(table);
  let start = null;
  grip.addEventListener('pointerdown', (e) => { start = { y: e.clientY, h: table.getBoundingClientRect().height, s: scale() }; grip.setPointerCapture(e.pointerId); grip.classList.add('drag'); e.preventDefault(); });
  grip.addEventListener('pointermove', (e) => { if (start) set((start.s * (start.h + e.clientY - start.y)) / start.h); });
  const end = () => { start = null; grip.classList.remove('drag'); };
  grip.addEventListener('pointerup', end);
  grip.addEventListener('pointercancel', end);
  grip.addEventListener('dblclick', () => { chosen = null; apply(); });
  grip.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); set(scale() + (e.key === 'ArrowDown' ? 0.1 : -0.1)); }
  });
});
