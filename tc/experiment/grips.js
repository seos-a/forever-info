// The race-by-spec tables' drag handles: dragging one down makes its table's text and cells bigger, up to the size
// where the table fills its box's width (2.5 times at most), or 1.5 times for a table already about as wide as its box
// (it then scrolls sideways, its Race column staying in view); dragging up makes them smaller
// again (no smaller than normal); double-click resets, arrow keys work too. The size is a CSS variable (--mz) on the
// table's box, so it stays through the table's redraws.
document.querySelectorAll('.lx-mxgrip').forEach((grip) => {
  const card = grip.closest('section'), table = card.querySelector('.lx-matrix');
  const scale = () => parseFloat(card.style.getPropertyValue('--mz')) || 1;
  // The table's width grows with the size, so the widest size that still fits is the box's width over the table's own
  // width at size 1 (measured at its natural width: it is otherwise stretched to fill the box).
  const fit = () => {
    const prev = table.style.width;
    table.style.width = 'max-content';
    const w = table.offsetWidth / scale();
    table.style.width = prev;
    return w ? table.parentElement.clientWidth / w : 1;
  };
  const set = (v) => card.style.setProperty('--mz', String(Math.max(1, Math.min(Math.min(2.5, Math.max(1.5, fit())), v))));
  let start = null;
  grip.addEventListener('pointerdown', (e) => { start = { y: e.clientY, h: table.getBoundingClientRect().height, s: scale() }; grip.setPointerCapture(e.pointerId); grip.classList.add('drag'); e.preventDefault(); });
  grip.addEventListener('pointermove', (e) => { if (start) set((start.s * (start.h + e.clientY - start.y)) / start.h); });
  const end = () => { start = null; grip.classList.remove('drag'); };
  grip.addEventListener('pointerup', end);
  grip.addEventListener('pointercancel', end);
  grip.addEventListener('dblclick', () => set(1));
  grip.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); set(scale() + (e.key === 'ArrowDown' ? 0.1 : -0.1)); }
  });
});
