"""Raid Composition data for the page: raidcomp.json, with each spell's class, icon, text and specs worked out from the
talent trees and the spellbook. build.py calls build(data, sbk) and embeds the result as /*RAIDCOMP*/."""
import json

HYBRID = 51 - 31   # points left for another tree once a spec has its 31-point talent
ORDER = ["druid", "hunter", "mage", "paladin", "priest", "rogue", "shaman", "warlock", "warrior"]

def build(data, sbk):
    R = json.load(open('raidcomp.json', encoding='utf-8'))
    racials = json.load(open('racials.json', encoding='utf-8'))
    race_of = {}   # Priest racial spell -> races
    for r in racials:
        for p in r.get('priest', []):
            race_of.setdefault(p[0], []).append(r['name'])
    talents, book = {}, {}
    for c in ORDER:
        for ti, tr in enumerate(data[c]['trees']):
            for t in tr['t']:
                text = t[9][-1] if len(t) > 9 and t[9] else (t[5].replace('{v}', t[7][-1]) if t[7] else t[5])
                talents[(c, t[3])] = (t[4], text, ti, t[0])
        for s in sbk[c]['spells']:
            book[(c, s[0])] = (s[1], s[5])
    problems, spells, index = [], [], {}

    def ref(name):
        if name in index:
            return index[name]
        c, n = name.split(':', 1) if ':' in name else (None, name)
        x = R['extra'].get(n, {})
        if 'class' in x:
            c = x['class']
        hits = [k for k in ORDER if (k, n) in talents or (k, n) in book] if not c else [c]
        if len(hits) != 1 or ('icon' not in x and (hits[0], n) not in talents and (hits[0], n) not in book):
            problems.append(('raid comp: no single class has', name, hits))
            return None
        c = hits[0]
        e = {'n': n, 'c': c}
        if 'icon' in x:   # a pet ability or a renamed spell
            e['i'], e['d'], e['s'] = x['icon'], x.get('d', ''), [0, 1, 2]
        elif (c, n) in talents:   # a talent (its trainer ranks may be in the spellbook too): that tree's spec only
            icon, text, ti, row = talents[(c, n)]
            e['i'], e['d'], e['s'], e['t'] = icon, x.get('d') or (book.get((c, n)) or (0, text))[1], [ti], 1
            # the other two specs can take it too when it sits low enough in the tree: with 31 points in their own tree
            # they have 20 left, and a talent on row r needs r * 5 points in its tree first (plus its own point)
            if row * 5 + 1 <= HYBRID:
                e['o'], e['need'] = [k for k in (0, 1, 2) if k != ti], row * 5 + 1
        else:
            icon, text = book[(c, n)]
            e['i'], e['d'], e['s'] = icon, x.get('d') or text, [0, 1, 2]
        if 'pet' in x:
            e['p'] = x['pet']
        if c == 'priest' and n in race_of:
            e['r'] = ' / '.join(race_of[n])
        if n in R['party']:
            e['g'] = 1
        index[name] = len(spells)
        spells.append(e)
        return index[name]

    buffs = {n for k in R['categories'] if k['g'] == 'Buffs' for n in k['s']}
    cats = []
    for k in R['categories']:
        cats.append({'g': k['g'], 'n': k['n'], 's': [i for i in map(ref, k['s']) if i is not None],
                     'st': k.get('status', ''), 'note': k.get('note', '')})
    secs = [{'n': s['n'], 's': [i for i in map(ref, s['s']) if i is not None]} for s in R['sections']]
    for p in R['party']:
        if p not in index:
            ref(p)
    for name, i in index.items():   # group-only buffs from the Buffs categories: the icons under each group
        if spells[i].get('g') and name in buffs:
            spells[i]['b'] = 1
    return {'spells': spells, 'cats': cats, 'secs': secs}, problems
