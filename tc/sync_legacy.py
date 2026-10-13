"""Bring the Legacy trees (legacy_raw.json) up to date with Wowhead's WoW Forever Legacy Calculator.

Run from inside tc/:  py sync_legacy.py        (needs internet)
                      py sync_legacy.py --dry  (report only, write nothing)

The calculator's data feed has every tree's nodes: name, icon, grid position, rank count, the points needed in the tree
first, whether it is a locked "Unknown" placeholder, each rank's text, a cast time / cooldown, and the arrows between
nodes. legacy_raw.json is rewritten from it, keeping the site's own tree icons, and what changed is printed. A node
added or removed is applied too, and listed so the new layout can be checked on the page.
"""
import json, re, sys
import talent_meta as tm

STEP, X0, Y0 = 750, 2400, 1050   # Wowhead's grid: 750 units a slot, the first column / row at 2400 / 1050
PX = 92                          # the site's slot size; legacy_raw.json positions are 14 + slot * 92

def feed():
    # the data URL carries a version parameter, so read it off the calculator page
    page = tm.get('https://www.wowhead.com/forever/legacy-calculator')
    url = re.search(r'https://nether\.wowhead\.com/forever/data/legacy-calculator\?[^"\']+', page).group(0)
    js = tm.get(url.replace('&amp;', '&'))
    return json.JSONDecoder().raw_decode(js[js.index(',{') + 1:])[0]

def span(ms, unit):
    """25000 -> "25 sec", 82800000 -> "23 hr" (the largest whole unit)"""
    s = ms / 1000
    for size, name in ((3600, 'hr'), (60, 'min'), (1, 'sec')):
        if s >= size and (s / size).is_integer(): return f'{int(s // size)} {name}'
    return f'{s:g} sec'

def texts(n):
    """Each rank's text, with a cast time / cooldown line first when the node has one (Dedicated Study)."""
    head = ', '.join(x for x in (n['castMs'] and span(n['castMs'], 'cast') + ' cast', n['cdMs'] and span(n['cdMs'], 'cd') + ' cooldown') if x)
    return [f'{head}\n{t}' if head else t for t in n['ranks']]

def build(d, old):
    icons = {t['name']: t['icon'] for t in old.get('trees', [])}
    nodes = {n['id']: n for t in d['trees'] for n in t['nodes']}
    trees, need = [], {}
    for t in d['trees']:
        trees.append({'name': t['name'], 'blurb': t['blurb'], 'icon': icons.get(t['name'], 'inv_misc_questionmark'),
                      'nodes': [[str(n['id']), n['name'], 14 + (n['x'] - X0) // STEP * PX, 14 + (n['y'] - Y0) // STEP * PX,
                                 n['icon'], n['maxRanks'], n['requiredSpent'], n['locked'], texts(n)] for n in t['nodes']]})
        # an arrow: the node it points to needs points in the one it starts from. The feed doesn't say how many, so a
        # link the site already has keeps its number (checked by hand: 1, Reagent Economy 2); a new one gets 1
        for e in t['edges']:
            a, b = nodes.get(e['from']), nodes.get(e['to'])
            if not (a and b) or a['locked'] or b['locked']: continue   # between "Unknown" placeholders
            was = old.get('need', {}).get(str(b['id']))
            need[str(b['id'])] = [str(a['id']), was[1] if was and was[0] == str(a['id']) else 1]
    return {'need': need, 'trees': trees}

def report(old, new):
    o = {n[0]: n for t in old.get('trees', []) for n in t['nodes']}
    w = {n[0]: n for t in new['trees'] for n in t['nodes']}
    out = []
    for i, n in w.items():
        p = o.get(i)
        if not p: out.append(f'new node: {n[1]} (rank {n[5]}, needs {n[6]} points)'); continue
        for k, label in ((1, 'name'), (4, 'icon'), (5, 'ranks'), (6, 'points needed'), (7, 'locked')):
            if p[k] != n[k]: out.append(f'{n[1]}: {label} {p[k]} -> {n[k]}')
        if (p[2], p[3]) != (n[2], n[3]): out.append(f'{n[1]}: moved')
        if p[8] != n[8]: out.append(f'{n[1]}: text')
    out += [f'removed node: {p[1]}' for i, p in o.items() if i not in w]
    names = {**{i: p[1] for i, p in o.items()}, **{i: n[1] for i, n in w.items()}}
    for b, (a, k) in new['need'].items():
        if old.get('need', {}).get(b, [None])[0] != a:
            out.append(f'new prerequisite: {names[b]} needs {names[a]} (set to 1 point; check how many in game or on Wowhead)')
    for b, (a, k) in old.get('need', {}).items():
        if new['need'].get(b, [None])[0] != a: out.append(f'prerequisite removed: {names.get(b, b)} no longer needs {names.get(a, a)}')
    ot = [(t['name'], t['blurb']) for t in old.get('trees', [])]; nt = [(t['name'], t['blurb']) for t in new['trees']]
    if ot != nt: out.append(f'trees: {ot} -> {nt}')
    return out

def main():
    dry = '--dry' in sys.argv
    old = json.load(open('legacy_raw.json', encoding='utf-8'))
    d = feed()
    new = build(d, old)
    changes = report(old, new)
    print(f"Legacy Calculator data: build {d['build']}, {d['cap']} points")
    print('\n'.join(changes) or 'no Legacy changes')
    if d['cap'] != 16: print(f"To check by hand: the Legacy point cap is now {d['cap']} (the site uses 16, in build.py)")
    if changes and not dry:
        with open('legacy_raw.json', 'w', encoding='utf-8', newline='\n') as f: f.write(dump(new, old))

def dump(new, old):
    """legacy_raw.json's layout, one node per line (so a change shows as a small diff); links in their old order"""
    j = lambda x: json.dumps(x, ensure_ascii=False, separators=(',', ':'))
    order = [k for k in old.get('need', {}) if k in new['need']] + [k for k in new['need'] if k not in old.get('need', {})]
    trees = [j({k: v for k, v in t.items() if k != 'nodes'})[:-1] + ',"nodes":[\n' + ',\n'.join(j(n) for n in t['nodes']) + ']}'
             for t in new['trees']]
    return '{"need":' + j({k: new['need'][k] for k in order}) + ',\n"trees":[\n' + ',\n'.join(trees) + '\n]}\n'

if __name__ == '__main__':
    main()
