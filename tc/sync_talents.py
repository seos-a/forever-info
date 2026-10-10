"""Bring the class talent files (<class>.json) up to date with Wowhead's WoW Forever talent feed.

Run from inside tc/:  py sync_talents.py          (needs internet)
                      py sync_talents.py feed.json (use a feed saved earlier)

For every talent it takes the beta's grid position, rank count, icon, prerequisite and the full description of
every rank. The per-rank texts are stored as a 9th field, and build.py shows them as they are, so talents where
several numbers change per rank read correctly at every rank. Talents are matched by name, or by grid position
when the beta renamed one. Prints what changed.
"""
import json, re, sys
from talent_meta import talent_feed

CLASSES = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior']
NUM = re.compile(r'\d+(?:\.\d+)?')

def num(s):
    v = float(s)
    return int(v) if v.is_integer() else v

def varying(texts):
    """The first number that changes from rank to rank, per rank (the old single-value field), or None."""
    nums = [NUM.findall(t) for t in texts]
    if len(texts) < 2 or len({len(n) for n in nums}) > 1: return None
    for i in range(len(nums[0])):
        col = [n[i] for n in nums]
        if len(set(col)) > 1: return [num(v) for v in col]
    return None

def main():
    feed = json.load(open(sys.argv[1], encoding='utf-8')) if len(sys.argv) > 1 else talent_feed()
    every = {t['id']: t for tree in feed['talents'].values() for t in tree.values()}
    changes = []
    for key in CLASSES:
        path = f'{key}.json'
        trees = json.load(open(path, encoding='utf-8'))
        for tr in trees:
            live = list(feed['talents'].get(str(tr['s']), {}).values())
            by_name = {t['name']: t for t in live}
            by_cell = {(t['row'], t['col']): t for t in live}
            out, used = [], set()
            for old in tr['t']:
                l = by_name.get(old[3]) or by_cell.get((old[0], old[1]))
                if not l:
                    changes.append(f'{key} {tr["n"]}: {old[3]} removed'); continue
                used.add(l['id'])
                texts = [l['descriptions'][k] for k in sorted(l['descriptions'], key=int)]
                req = l['requires'][0] if l['requires'] else None
                pre = [every[req['id']]['name'], req['qty']] if req and req['id'] in every else None
                new = [l['row'], l['col'], len(l['ranks']), l['name'], l['icon'], texts[-1], varying(texts), pre, texts]
                if old[3] != l['name']: changes.append(f'{key} {tr["n"]}: {old[3]} renamed {l["name"]}')
                elif (old[0], old[1], old[2], old[4], old[7]) != tuple(new[i] for i in (0, 1, 2, 4, 7)):
                    changes.append(f'{key} {tr["n"]}: {l["name"]} layout / ranks / icon / prerequisite')
                if old[5] != texts[-1] or (old[8] if len(old) > 8 else None) != texts:
                    changes.append(f'{key} {tr["n"]}: {l["name"]} text')
                out.append(new)
            for l in live:
                if l['id'] in used: continue
                texts = [l['descriptions'][k] for k in sorted(l['descriptions'], key=int)]
                req = l['requires'][0] if l['requires'] else None
                pre = [every[req['id']]['name'], req['qty']] if req and req['id'] in every else None
                out.append([l['row'], l['col'], len(l['ranks']), l['name'], l['icon'], texts[-1], varying(texts), pre, texts])
                changes.append(f'{key} {tr["n"]}: {l["name"]} added')
            tr['t'] = sorted(out, key=lambda t: (t[0], t[1]))
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(json.dumps(trees, separators=(',', ':')))
    print('\n'.join(changes) or 'no changes')
    print(f'{len(changes)} changes')

if __name__ == '__main__':
    main()
