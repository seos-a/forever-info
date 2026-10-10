"""Bring the spellbook data up to date with Wowhead's WoW Forever data.

Run from inside tc/:  py sync_spells.py          (needs internet; fetches ~1,500 tooltips, a few minutes)
                      py sync_spells.py feed.json (use a talent feed saved earlier for the spell list)

The talent feed lists every trainable spell rank (id + level) per class. This fetches each rank's tooltip, groups
the ranks by spell name, and for every spell already in the spellbook updates:
  spells_raw.json  levels, "Rank N" label, top-rank id and description
  ranks_raw.json   each rank's description (written as full text when it changed)
  rank_tips.json   each rank's cost / range / cast time / cooldown
Spells in the beta that the spellbook doesn't have yet are listed, not added: which tab a new spell belongs on has
to be decided by hand. Prints what changed.
"""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
import talent_meta as tm
import spellbook

CLASS_IDS = {'1': 'warrior', '2': 'paladin', '3': 'hunter', '4': 'rogue', '5': 'priest', '7': 'shaman', '8': 'mage',
             '9': 'warlock', '11': 'druid'}

def desc_of(tip):
    m = re.findall(r'<div class="q">(.*?)</div>', tip, re.S)
    return m[-1].replace('&nbsp;', ' ') if m else None

def header_of(tip):
    """cost / range / cast time / cooldown from the lines under the spell name -> {"c","r","t","cd"}"""
    head = re.sub(r'<!--.*?-->', '', tip.split('<div class="wowhead-tooltip-requirements">')[0])
    head = re.sub(r'<a class="whtt-name".*?</a>', '', head, flags=re.S)
    head = re.sub(r'<b class="q0">.*?</b>', '', head, flags=re.S)                  # "Rank 3" / "Level 60"
    bits = [re.sub(r'<[^>]+>', '', b).replace('&nbsp;', ' ').strip()                 # split at line / cell edges,
            for b in re.split(r'<br\s*/?>|</?(?:td|th|tr|table|div)\b[^>]*>', head)]   # then drop inline tags
    out = {}
    for b in filter(None, bits):
        if 'cooldown' in b: out['cd'] = b
        elif re.search(r'Mana|Rage|Energy|Focus|of base mana|Health', b): out['c'] = re.sub(r' / \d+ to \d+ Combo Points', '', b)
        elif re.search(r'range|Melee Range|yards', b, re.I): out['r'] = b
        elif re.search(r'Instant|cast|Channeled|Next melee', b): out['t'] = 'Channeled' if b.startswith('Channeled') else b
    return out

def same(a, b):
    n = lambda x: re.sub(r'\s+', ' ', spellbook.clean(x).replace('&nbsp;', ' ')).strip()
    return n(a) == n(b)

def load(path):
    s = open(path, encoding='utf-8').read()
    return json.loads(s), (', ', ': ') if '", "' in s[:2000] or '": ' in s[:2000] else (',', ':')

def save(path, data, sep):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(data, separators=sep))

def main():
    feed = json.load(open(sys.argv[1], encoding='utf-8')) if len(sys.argv) > 1 else tm.talent_feed()
    raw, sep_raw = load('spells_raw.json')
    rk, sep_rk = load('ranks_raw.json')
    rt, sep_rt = load('rank_tips.json')
    spellbook.RK, spellbook.RKD = rk, rt
    abil = [(CLASS_IDS[k], a['id'], a['level']) for k, v in feed['abilities'].items() if k in CLASS_IDS for a in v]
    have = {x[1] for x in abil}
    abil += [(c, s[6], None) for c, L in raw.items() for s in L if s[6] and s[6] not in have]   # top ranks the list leaves out
    def fetch(x):
        try: return x, json.loads(tm.get(f'{tm.BASE}/tooltip/spell/{x[1]}'))
        except Exception: return x, None
    with ThreadPoolExecutor(6) as ex:
        tips = list(ex.map(fetch, abil))
    failed = [x for x, t in tips if t is None]
    by_id, groups = {}, {}
    for (cls, sid, lvl), t in tips:
        if not t or not t.get('name'): continue
        d = desc_of(t.get('tooltip', ''))
        if d is None: continue
        e = (lvl, sid, d, header_of(t['tooltip']))
        by_id[sid] = e
        if lvl is not None: groups.setdefault(cls, {}).setdefault(t['name'], []).append(e)

    changes, check = [], []
    for cls, spells in raw.items():
        known = {s[0] for s in spells}
        for s in spells:
            name, icon, skill, levels, label, desc, sid = s
            top = by_id.get(sid)
            if top and not same(desc, top[2]):
                s[5] = top[2]; changes.append(f'{cls} {name}: text')
            g = groups.get(cls, {}).get(name, [])
            beta_levels = sorted({e[0] for e in g})
            if g and beta_levels != sorted(set(levels)):
                check.append(f'{cls} {name}: spellbook levels {levels}, beta lists {beta_levels}')
            # each rank: the beta entry at that level whose wording matches (numbers aside)
            cur = spellbook.ranks(cls, name, s[5]) or []
            if len(cur) < 2: continue
            texts, tipmap, moved = [], {}, False
            for row in cur:
                r, lv, text = row[0], row[1], row[2]
                cand = [e for e in g if e[0] == lv]
                pick = [e for e in cand if spellbook.norm(spellbook.clean(e[2])) == spellbook.norm(text)] or (cand if len(cand) == 1 else [])
                if pick and not same(text, pick[0][2]): texts.append([r, lv, pick[0][2]]); moved = True
                else: texts.append([r, lv, text])
                if pick and 'c' in pick[0][3]: tipmap[str(r)] = pick[0][3]       # castable spell only, not a triggered half
            if moved:
                rk.setdefault(cls, {})[name] = {'r': texts}
                changes.append(f'{cls} {name}: per-rank text')
            old = rt.get(cls, {}).get(name, {})
            new = {r: {**old.get(r, {}), **v} for r, v in {**{r: {} for r in old}, **tipmap}.items()}   # fill in, never drop
            if tipmap and new != old:
                rt.setdefault(cls, {})[name] = new
                changes.append(f'{cls} {name}: per-rank cost / range / cast time / cooldown')
        extra = sorted(set(groups.get(cls, {})) - known - spellbook.DROP)
        if extra: check.append(f'{cls}: in the beta but not in the spellbook (some are pet or passive skills): ' + ', '.join(extra))
    save('spells_raw.json', raw, sep_raw)
    save('ranks_raw.json', rk, sep_rk)
    save('rank_tips.json', rt, sep_rt)
    print('\n'.join(changes) or 'no spell changes')
    if check: print('\nTo check by hand (not changed automatically):\n' + '\n'.join(check))
    if failed: print(f'{len(failed)} tooltips could not be fetched')
    print(f'{len(changes)} spell changes')

if __name__ == '__main__':
    main()
