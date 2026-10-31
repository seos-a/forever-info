"""Bring the spellbook data up to date with Wowhead's WoW Forever data.

Run from inside tc/:  py sync_spells.py          (needs internet; fetches ~1,500 tooltips, a few minutes)
                      py sync_spells.py feed.json (use a talent feed saved earlier for the spell list)

The talent feed lists every trainable spell rank (id + level) per class. This fetches each rank's tooltip, groups
the ranks by spell name, and for every spell already in the spellbook updates:
  spells_raw.json  levels, "Rank N" label, top-rank id and description
  ranks_raw.json   each rank's description (written as full text when it changed)
  rank_tips.json   each rank's cost / range / cast time / cooldown (a single-rank spell's as rank 1)
A spell the beta's trainers teach that the spellbook doesn't have yet is added when Wowhead's spellbook page says which
tab it's on (a Classic spell); a brand-new Forever spell comes without a tab there, so it's listed for placing by hand.
Rank counts and levels of spells already in the spellbook are listed too, not changed. Prints what changed.
"""
import json, re, sys
from concurrent.futures import ThreadPoolExecutor
import talent_meta as tm
import spellbook

CLASS_IDS = {'1': 'warrior', '2': 'paladin', '3': 'hunter', '4': 'rogue', '5': 'priest', '7': 'shaman', '8': 'mage',
             '9': 'warlock', '11': 'druid'}

# Already reviewed, so not listed under "To check by hand" again.
# Names in the beta's list that rightly aren't spellbook spells (talents that were changed, merged or removed):
KNOWN_EXTRA = {'warrior': {'Improved Cleave', 'Improved Overpower', 'Toughness'},
               'mage': {'Improved Blink', 'Magic Attunement'}}
# Spells whose first rank comes from a talent, so the beta's trainer list starts later. These are the levels the
# beta listed when reviewed; if it lists different ones later, the spell is flagged again.
KNOWN_LEVELS = {('paladin', 'Flash of Light'): [20, 26, 34, 42, 50, 58], ('paladin', 'Righteous Fury'): [16],  # the beta's trainer still says 16; learned at 10 since the Oct 23 hotfix
                ('rogue', 'Mutilate'): [40, 50, 60], ('priest', 'Shadow Word: Death'): [32, 40, 48, 56],
                ('priest', 'Penance'): [40, 50, 60], ('priest', 'Prayer of Mending'): [50, 60],
                ('shaman', 'Lava Burst'): [50, 60], ('druid', 'Lacerate'): [42, 50, 58],
                ('druid', 'Swipe'): [16, 24, 34, 44, 54], ('druid', "Tiger's Fury"): [24]}

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

_wh = {}
def wowhead_spells(cls):
    """Wowhead's spellbook for a class ({"tabs": [{id, name}], "spells": [{name, tab, icon, ...}]}), from its change page"""
    if cls not in _wh:
        import changelog
        _wh[cls] = changelog.page('spellbook', cls, None)['data']
    return _wh[cls]

def same(a, b):
    n = lambda x: re.sub(r'\s+', ' ', spellbook.clean(x).replace('&nbsp;', ' ')).strip()
    return n(a) == n(b)

def worse(old, new):
    """Wowhead sometimes serves a tooltip with its formula variables left in ($apm for Attack Power): keep the worded
    text rather than flip back and forth between the two from run to run."""
    return bool(re.search(r'\$[a-zA-Z]', new)) and not re.search(r'\$[a-zA-Z]', old)

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
            if top and not same(desc, top[2]) and not worse(desc, top[2]):
                s[5] = top[2]; changes.append(f'{cls} {name}: text')
            g = groups.get(cls, {}).get(name, [])
            beta_levels = sorted({e[0] for e in g})
            if g and beta_levels != sorted(set(levels)) and KNOWN_LEVELS.get((cls, name)) != beta_levels:
                check.append(f'{cls} {name}: spellbook levels {levels}, beta lists {beta_levels}')
            # each rank: the beta entry at that level whose wording matches (numbers aside)
            cur = spellbook.ranks(cls, name, s[5]) or []
            single = len(cur) < 2
            texts, tipmap, moved = [], {}, False
            if single and top and top[3]: tipmap['1'] = top[3]   # one rank: the top rank's header, stored as rank 1
            for row in [] if single else cur:
                r, lv, text = row[0], row[1], row[2]
                cand = [e for e in g if e[0] == lv]
                pick = [e for e in cand if spellbook.norm(spellbook.clean(e[2])) == spellbook.norm(text)] or (cand if len(cand) == 1 else [])
                # Two beta entries at one level that read alike (an old rank and its replacement): the one the spellbook
                # already shows wins, so the pick doesn't flip between them from run to run.
                pick = [e for e in pick if same(text, e[2])] or pick
                if pick and not same(text, pick[0][2]) and not worse(text, pick[0][2]): texts.append([r, lv, pick[0][2]]); moved = True
                else: texts.append([r, lv, text])
                if pick and 'c' in pick[0][3]: tipmap[str(r)] = pick[0][3]       # castable spell only, not a triggered half
            if moved:
                rk.setdefault(cls, {})[name] = {'r': texts}
                changes.append(f'{cls} {name}: per-rank text')
            old = rt.get(cls, {}).get(name, {})
            new = tipmap if single else {r: {**old.get(r, {}), **v} for r, v in {**{r: {} for r in old}, **tipmap}.items()}   # fill in, never drop
            if tipmap and new != old:
                rt.setdefault(cls, {})[name] = new
                changes.append(f'{cls} {name}: per-rank cost / range / cast time / cooldown')
        extra = sorted(set(groups.get(cls, {})) - known - spellbook.DROP - KNOWN_EXTRA.get(cls, set()))
        # a spell the trainer now teaches that the spellbook doesn't have: added when Wowhead's spellbook page says which
        # tab it's on (a Classic spell); a brand-new Forever spell comes without a tab there, so it's listed to place by hand
        unplaced = []
        for name in extra:
            wh = next((s for s in wowhead_spells(cls)['spells'] if s['name'] == name), None)
            tab = wh and wh.get('tab')
            if tab not in spellbook.SKILL[cls]: unplaced.append(name); continue
            by_lv = {}
            for e in sorted(groups[cls][name], key=lambda e: (e[0], 'c' not in e[3])):   # one entry per level, the castable one
                by_lv.setdefault(e[0], e)
            rows = [by_lv[lv] for lv in sorted(by_lv)]
            top = rows[-1]
            spells.append([name, wh['icon'], tab, [r[0] for r in rows], f'Rank {len(rows)}' if len(rows) > 1 else '', top[2], top[1]])
            if len(rows) > 1:
                rk.setdefault(cls, {})[name] = {'r': [[i + 1, r[0], r[2]] for i, r in enumerate(rows)]}
                tips = {str(i + 1): r[3] for i, r in enumerate(rows) if 'c' in r[3]}
                if tips: rt.setdefault(cls, {})[name] = tips
            tab_name = next((t['name'] for t in wowhead_spells(cls)['tabs'] if t['id'] == tab), tab)
            changes.append(f'{cls} {name}: new spell, added to the {tab_name} tab (learned at {", ".join(str(r[0]) for r in rows)})')
        if unplaced: check.append(f'{cls}: in the beta but not in the spellbook, and Wowhead doesn\'t say which tab (a new Forever '
                                  'spell, or a pet or passive skill): ' + ', '.join(unplaced))
    save('spells_raw.json', raw, sep_raw)
    save('ranks_raw.json', rk, sep_rk)
    save('rank_tips.json', rt, sep_rt)
    print('\n'.join(changes) or 'no spell changes')
    if check: print('\nTo check by hand (not changed automatically):\n' + '\n'.join(check))
    if failed: print(f'{len(failed)} tooltips could not be fetched')
    print(f'{len(changes)} spell changes')

if __name__ == '__main__':
    main()
