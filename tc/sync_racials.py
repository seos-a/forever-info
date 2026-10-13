"""Keep the racials (racials.json, the Racial Abilities page) up to date with Wowhead's WoW Forever data.

Run from inside tc/, after sync_spells.py and changelog.py:  py sync_racials.py      (needs internet)
                                                             py sync_racials.py --dry (report only, write nothing)

Racial traits: each trait's tooltip (TRAIT_IDS below) is compared with the copy saved last time in racials_wh.json.
  - A trait the site shows exactly as Wowhead words it gets its new text (and cast time / cooldown line) automatically.
  - A trait the site words by hand (Eureka! and Expansive Mind merge their per-class versions, Touch of the Grave its
    two proc chances) is never rewritten: the change goes on the
    pull request's "Needs a look" list to be edited in racials.json by hand.
  Each change is summarised in the report (buff / nerf / other, worked out as on the Class Changes page) but not added
  to the Class Changes page: the developers don't plan to change racials after launch. Wowhead's race pages are read
  too, to notice a racial that was added or removed (listed, not applied: where it goes is decided by hand).
Priest racial spells: their text comes from the spellbook data sync_spells.py keeps current (spells_raw.json); the
  Racials page's copy is refreshed from it. Their changes already show under Priest on the Class Changes page.
Prints what changed.
"""
import json, re, sys
import talent_meta as tm
import sync_spells as ss
import spellbook
import changelog as cl

# Wowhead race ids for the race pages (Skyborne has no race page; its traits are only looked up by id)
RACE_PAGES = {'human': 1, 'orc': 2, 'dwarf': 3, 'nightelf': 4, 'undead': 5, 'tauren': 6, 'gnome': 7, 'troll': 8}
# racials.json trait name -> Wowhead spell ids (several when the site merges per-class versions into one line)
TRAIT_IDS = {
    'Perception': [20600], 'Will to Survive': [1259718], 'Sword Specialization': [20597], 'The Human Spirit': [20598],
    'Find Treasure': [2481], 'Stoneform': [20594], 'Big Game Hunter': [1259721], 'Mace Specialization': [1259719],
    "Elune's Light": [1259799], 'Shadowmeld': [20580], 'Quickness': [20582], 'Wisp Spirit': [20585],
    'Escape Artist': [20589], 'Eureka!': [1259813, 1259812, 1259817, 1259823, 1259821],
    'Engineering Specialization': [20593], 'Expansive Mind': [20591, 1259802, 1259803],
    'Read Ley Line': [1259705], 'Skysight': [1259686], 'Walk on Air': [1259416], 'Elemental Insight': [1259707],
    'Wind Blessed': [1259710],
    'Blood Fury': [20572], 'Shatter Curse': [1299026], 'Axe Specialization': [20574], 'Hardiness': [20573],
    'Cannibalize': [20577], 'Will of the Forsaken': [7744], 'Touch of the Grave': [1260201, 1260189],
    'Underwater Breathing': [5227],
    'Cultivation': [20552], 'War Stomp': [20549], 'Endurance': [20550], 'Plainsrunning': [1259918],
    'Berserking': [20554], 'Rapid Regeneration': [1260270], 'Beast Slaying': [20557], 'Regeneration': [20555],
}
# which version each of a merged trait's spells is, for the report ("Eureka! (Warrior)")
VARIANT = {1259813: 'Warrior', 1259812: 'Rogue', 1259817: 'Mage', 1259823: 'Priest', 1259821: 'Warlock',
           20591: 'Mana', 1259802: 'Warrior', 1259803: 'Rogue', 1260201: '10% chance', 1260189: '5% chance'}
SNAP = 'racials_wh.json'

def read(sid):
    """One spell's tooltip -> {"name", "cells": the cast time / cooldown / range / cost cells, "text"}"""
    tip = json.loads(tm.get(f'{tm.BASE}/tooltip/spell/{sid}'))
    html = tip.get('tooltip', '')
    cells = []
    for table in re.findall(r'<table width="100%">(.*?)</table>', html, re.S):
        tr = re.search(r'<tr>(.*?)</tr>', table, re.S)
        if tr: cells += [c for c in (tm.strip(x) for x in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr.group(1), re.S)) if c]
    return {'name': tip.get('name', ''), 'cells': cells, 'text': spellbook.clean(ss.desc_of(html) or '').strip()}

def header(cells):
    """The site's line under a trait's name, from the tooltip cells: "Instant · 3 min cooldown · 5 yd" / "Passive"."""
    order = lambda c: 0 if re.search(r'Instant|cast|Channeled', c) else 1 if 'cooldown' in c else 2 if re.search(r'yd|range', c) else 3
    return ' · '.join(re.sub(r'(\d+) yd range', r'\1 yd', c) for c in sorted(cells, key=order)) or 'Passive'

def fields(s):
    """A snapshot as changelog.rank_change wants it: name, text, cost, cast, cooldown, range."""
    f = {'name': s['name'], 'text': s['text'], 'cost': '', 'cast': '', 'cooldown': '', 'range': ''}
    for c in s['cells']:
        if 'cooldown' in c: f['cooldown'] = c
        elif re.search(r'Instant|cast|Channeled', c): f['cast'] = c
        elif re.search(r'yd|range', c): f['range'] = c
        elif re.search(r'Mana|Rage|Energy|Health', c): f['cost'] = c
    return f

norm = lambda s: re.sub(r'\s+', ' ', spellbook.clean(s or '').replace('&nbsp;', ' ')).strip()

def race_page_ids(rid):
    """The racial trait spell ids Wowhead's race page lists."""
    page = tm.get(f'https://www.wowhead.com/forever/race={rid}')
    i = page.index("id: 'racial-traits'"); j = page.index('data: ', i) + 6
    return {e['id']: e['name'] for e in json.JSONDecoder().raw_decode(page[j:])[0]}

def main():
    dry = '--dry' in sys.argv
    R = json.load(open('racials.json', encoding='utf-8'))
    try: old_all = json.load(open(SNAP, encoding='utf-8'))
    except FileNotFoundError: old_all = {}
    old = {int(k): v for k, v in old_all.items() if k.isdigit()}   # trait tooltips by spell id; "priest:<name>": spellbook text
    first = not old_all
    new, pnew, failed = {}, {}, []
    for ids in TRAIT_IDS.values():
        for sid in ids:
            try: new[sid] = read(sid)
            except Exception: failed.append(sid)
    for sid in failed: new[sid] = old.get(sid)   # couldn't read it this time: keep what we had
    new = {k: v for k, v in new.items() if v}

    applied, flags, entries = [], [], {}
    traits = {t[0]: (r, t) for r in R for t in r['traits']}
    for name, ids in TRAIT_IDS.items():
        if name not in traits: flags.append(f'{name}: listed in sync_racials.py but no longer in racials.json'); continue
        changed = [sid for sid in ids if sid in old and sid in new and old[sid] != new[sid]]
        if not changed: continue
        for r, t in [(r, t) for r in R for t in r['traits'] if t[0] == name]:   # Walk on Air etc. appear for both Skybornes
            plain_trait = len(ids) == 1 and norm(t[3]) == norm(old[ids[0]]['text']) and t[2] == header(old[ids[0]]['cells'])
            for sid in changed:
                notes, v, was, tag = cl.rank_change(fields(old[sid]), fields(new[sid]))
                label = f'{name} ({VARIANT[sid]})' if sid in VARIANT else name
                if notes and not any(e[1] == label for e in entries.get(r['key'], [])):
                    entries.setdefault(r['key'], []).append([cl.kind_of(v), label, t[1], f"{r['name']} racial{tag}", cl.join(notes), was or ''])
            if plain_trait:
                s = new[ids[0]]
                if t[3] != s['text'] or t[2] != header(s['cells']):
                    t[3], t[2] = s['text'], header(s['cells']); applied.append(f"{r['name']} {name}: updated")
            else:
                for sid in changed:
                    flags.append(f"**{r['name']}: {name}**: Wowhead changed it (spell {sid}): \"{old[sid]['text']}\" → "
                                 f"\"{new[sid]['text']}\"; the site words this trait by hand, so edit it in tc/racials.json")
    # a racial Wowhead added or removed
    known = {sid for ids in TRAIT_IDS.values() for sid in ids}
    for key, rid in RACE_PAGES.items():
        try: listed = race_page_ids(rid)
        except Exception: continue
        for sid, nm in listed.items():
            if sid not in known: flags.append(f"**{key.capitalize()}: {nm}**: a racial Wowhead lists (spell {sid}) that the site doesn't have")
        mine = {sid for r in R if r['key'] == key for t in r['traits'] for sid in TRAIT_IDS.get(t[0], [])}
        for sid in mine - set(listed):
            if sid in new: flags.append(f"**{key.capitalize()}: {new[sid]['name']}**: no longer on Wowhead's race page (spell {sid})")

    # Priest racial spells: the Racials page's copy follows the spellbook (kept current by sync_spells.py) when the
    # spellbook's text changes from last time; a copy corrected by hand (Wowhead's "by the attacker by 204" in Touch of
    # Weakness) is flagged instead of overwritten
    pri = {s[0]: s for s in json.load(open('spells_raw.json', encoding='utf-8'))['priest']}
    pold = {k[7:]: v for k, v in old_all.items() if k.startswith('priest:')}
    for r in R:
        for p in r['priest']:
            s = pri.get(p[0])
            if not s: flags.append(f"**{r['name']}: {p[0]}**: Priest racial spell no longer in the spellbook data"); continue
            text, was = norm(s[5]), pold.get(p[0])
            pnew[p[0]] = text
            if was is not None and was != text:
                if norm(p[3]) == was: p[3] = text; applied.append(f"{r['name']} {p[0]} (Priest racial): text")
                else: flags.append(f"**{r['name']}: {p[0]}** (Priest racial): the spellbook text changed to \"{text}\"; "
                                   "the Racials page's copy was corrected by hand, so edit it in tc/racials.json")
            lv = re.sub(r'learned at \d+', f'learned at {min(s[3])}', p[2])
            if lv != p[2]: p[2] = lv; applied.append(f"{r['name']} {p[0]} (Priest racial): learned at {min(s[3])}")

    if first: print(f'first run: saved {len(new)} racial tooltips and {len(pnew)} Priest racial texts to compare with next time')
    print('\n'.join(applied) or 'no racial changes applied')
    for k, ch in entries.items():
        for e in ch: print(f'{k:10} {e[0]:5} {e[1]}: {e[4]}')
    if flags: print('\nTo check by hand:\n' + '\n'.join(f'- {f}' for f in flags))
    if failed: print(f'{len(failed)} tooltips could not be fetched')
    if dry: return
    snap = {**{str(k): v for k, v in sorted(new.items())}, **{f'priest:{k}': v for k, v in sorted(pnew.items())}}
    with open(SNAP, 'w', encoding='utf-8', newline='\n') as f: json.dump(snap, f, ensure_ascii=False, indent=1); f.write('\n')
    if applied:
        with open('racials.json', 'w', encoding='utf-8', newline='\n') as f: f.write(json.dumps(R, ensure_ascii=False))
    if flags:   # at the top of the pull request, with changelog.py's list
        with open('../needs-a-look.md', 'a', encoding='utf-8', newline='\n') as f:
            f.write('### Racials: needs a look\n' + '\n'.join(f'- {x}' for x in flags) + '\n')

if __name__ == '__main__':
    main()
