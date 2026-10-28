// The race-by-spec tables' size: each table's text and cells are as big as its box's width allows without a sideways
// scrollbar (1.5 times at most, so the narrow Tanks and Healing tables don't get huge), and follow the window as it
// changes. The size is a CSS variable (--mz) on the table's box, so it stays through the table's redraws.
document.querySelectorAll('.lx-matrix').forEach((table) => {
  const card = table.closest('section'), wrap = table.parentElement;
  const scale = () => parseFloat(card.style.getPropertyValue('--mz')) || 1;
  // The table's width grows with the size, so the biggest size that fits is the box's width over the table's own width
  // at size 1 (measured at its natural width: it is otherwise stretched to fill the box).
  const apply = () => {
    if (!wrap.clientWidth) return; // its tab is hidden
    const prev = table.style.width;
    table.style.width = 'max-content';
    const w = table.offsetWidth / scale();
    table.style.width = prev;
    if (!w) return;
    const v = Math.max(1, Math.min(1.5, Math.floor(((wrap.clientWidth - 2) / w) * 100) / 100));
    if (Math.abs(v - scale()) > 0.005) card.style.setProperty('--mz', String(v));
  };
  new ResizeObserver(apply).observe(wrap);
  new ResizeObserver(apply).observe(table);
});
