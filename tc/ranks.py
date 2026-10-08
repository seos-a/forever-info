import re
NUM = re.compile(r'(?<![\w.])(\d+(?:\.\d+)?)(?=(%| sec| min| yd| yards| Rage| Energy| Mana| \d|\b))')
def fmt(v, like):
    dec = len(like.split('.')[1]) if '.' in like else 0
    if dec: return f'{v:.{dec}f}'
    return str(int(round(v))) if abs(v-round(v))<1e-9 else f'{v:.2f}'.rstrip('0').rstrip('.')
def per_rank(desc, ranks, mx):
    """Return (template, [value strings per rank]) or None if the scaling number can't be found."""
    if not ranks or mx < 2 or len(ranks) < mx: return None
    rs = [abs(x) for x in ranks[:mx]]
    for idx in (-1, 0):
      top = rs[idx]
      if top == 0: continue
      for scale in (1, 0.001, 0.1, 1/60000):
        target = top*scale
        for m in NUM.finditer(desc):
            if abs(float(m.group(1)) - target) < 1e-6:
                tok = m.group(1)
                vals = [fmt(r*scale, tok) for r in rs]
                if len(set(vals)) < 2: continue
                return desc[:m.start()] + '{v}' + desc[m.end():], vals
    return None
