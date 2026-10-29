"""Changes in WoW Forever's client files (its DB2 tables) between two builds, for the Class Changes page.

Run from inside tc/ (needs internet):
    py client_changes.py                      the client build last compared (version.json's "client") with the latest:
                                              what changelog.py adds next (the daily job's report)
    py client_changes.py --latest             the latest client build compared with the one before it
    py client_changes.py 70532 70658          two given builds (build numbers or full versions)
    py client_changes.py --builds             list the client builds

changelog.py's tooltips (Wowhead) show a spell's wording, its numbers and its cost / range / cast time / cooldown rows;
much of what a spell does is in no tooltip: its diminishing returns group, mechanic, spell power coefficient, internal
cooldown, global cooldown, the spells a talent affects, the values of a triggered effect. Those come from the game's
client tables, which wago.tools serves as CSV for every build of Blizzard's wowf product (WoW Forever's launch client):
    https://wago.tools/api/builds                                        the builds (key "wowf")
    https://wago.tools/db2/<table>/csv?build=1.60.1.70685                one table of one build
Only the spells the site shows are compared: every rank of every talent (<class>.json, matched to the client's Talent
table by tree and position), of every spellbook spell (spells_raw.json: the top rank's id and skill line give the
others), the racial traits (sync_racials.TRAIT_IDS), and the spells each of these triggers (a talent's root effect).

What a tooltip shows is left to Wowhead, so nothing is listed twice:
  - a value the tooltip's text quotes ($s1, $d, $h... in the client's description of any spell the site shows);
  - a cost / range / cast time / cooldown / learned-at level the site already shows with its new value (Wowhead has
    it, in this update or an earlier one, a server hotfix that the client caught up with).
Server hotfixes are not in the client tables at all (they reach the game from the realm, cached in DBCache.bin): a
change the client doesn't have yet is Wowhead's to find (Blood Fury's 2 min cooldown is still 3 min in 70685's table).

entries(old, new) -> {class: [entry, ...]} in changes.json's format ([kind, name, icon, where, text, ""]); every
sentence ends with a "†", which the page explains in a footnote (found in the client files, not in a tooltip).
changelog.py merges them into its update (merge()): a talent or spell Wowhead also lists stays one entry.
"""
import csv, io, json, os, re, sys, tempfile, collections
import talent_meta as tm

WAGO = 'https://wago.tools'
CLASSES = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior']
FAMILY = {'mage': 3, 'warrior': 4, 'warlock': 5, 'priest': 6, 'druid': 7, 'rogue': 8, 'hunter': 9, 'paladin': 10, 'shaman': 11}   # SpellClassSet
CLASS_BIT = {'warrior': 1, 'paladin': 2, 'hunter': 4, 'rogue': 8, 'priest': 16, 'shaman': 64, 'mage': 128, 'warlock': 256, 'druid': 1024}
MARK = '†'   # after every sentence found in the client files (the page's footnote)
TABLES = ['SpellName', 'Spell', 'Talent', 'TalentTab', 'SkillLineAbility', 'SpellLevels', 'SpellMisc', 'SpellCastTimes',
          'SpellDuration', 'SpellRange', 'SpellRadius', 'SpellPower', 'SpellCooldowns', 'SpellCategories', 'SpellAuraOptions',
          'SpellEffect', 'SpellClassOptions', 'SpellTargetRestrictions']
POWER = {0: 'Mana', 1: 'Rage', 2: 'Focus', 3: 'Energy'}
SCHOOLS = [(1, 'Physical'), (2, 'Holy'), (4, 'Fire'), (8, 'Nature'), (16, 'Frost'), (32, 'Shadow'), (64, 'Arcane')]
MECHANICS = {1: 'charm', 2: 'disorient', 3: 'disarm', 4: 'distract', 5: 'fear', 6: 'grip', 7: 'root', 8: 'slowed attack',
             9: 'silence', 10: 'sleep', 11: 'snare', 12: 'stun', 13: 'freeze', 14: 'incapacitate', 15: 'bleed', 16: 'bandage',
             17: 'polymorph', 18: 'banish', 19: 'shield', 20: 'shackle', 21: 'mount', 22: 'infected', 23: 'turn undead',
             24: 'horror', 25: 'invulnerability', 26: 'interrupt', 27: 'daze', 28: 'discovery', 29: 'immune shield', 30: 'sapped'}
DISPELS = {1: 'Magic', 2: 'Curse', 3: 'Disease', 4: 'Poison', 5: 'Stealth', 6: 'Invisibility', 9: 'Enrage'}
# a few effect kinds named, for a value no tooltip quotes (Effect, or EffectAura when Effect is "apply aura")
EFFECT_NAME = {2: 'damage', 10: 'healing', 30: 'mana restored', 35: 'value', 58: 'weapon damage'}
AURA_NAME = {3: 'damage per tick', 8: 'healing per tick', 13: 'spell damage bonus', 22: 'resistance bonus', 29: 'stat bonus',
             31: 'speed bonus', 33: 'slow', 69: 'absorb', 79: 'damage bonus', 85: 'mana regeneration', 99: 'attack power bonus',
             124: 'ranged attack power bonus', 107: 'modifier', 108: 'modifier', 15: 'damage shield', 34: 'health bonus'}
# description variables ($s1, $12494d, ${$m1/4}...): which fields a tooltip quotes, by the variable's letter
REF = re.compile(r'\$(?:\{)?(\d+)?([a-zA-Z])(\d)?')
QUOTES = {'s': ('pts',), 'm': ('pts',), 'w': ('pts',), 'o': ('pts', 'period', 'dur'), 'd': ('dur',), 'h': ('proc',),
          'n': ('charges',), 'u': ('stacks',), 't': ('period',), 'a': ('radius',), 'x': ('chain', 'targets'), 'i': ('targets',)}

# ---- the client tables ----

def builds():
    """The wowf client builds, oldest first, as full versions ('1.60.1.70685')."""
    return sorted({b['version'] for b in json.loads(tm.get(f'{WAGO}/api/builds'))['wowf']}, key=lambda v: int(v.rsplit('.', 1)[1]))

def version(b, known=None):
    """'70658' or '1.60.1.70658' -> '1.60.1.70658'"""
    if '.' in str(b): return str(b)
    return next(v for v in (known or builds()) if v.endswith('.' + str(b)))

CACHE = os.path.join(tempfile.gettempdir(), 'forever-wago')   # a build's tables never change, so they are kept between runs
def table(name, ver):
    path = os.path.join(CACHE, ver, name + '.csv')
    if os.path.exists(path): txt = open(path, encoding='utf-8', newline='').read()
    else:
        txt = tm.get(f'{WAGO}/db2/{name}/csv?build={ver}')
        if not txt.startswith(('ID', '"ID', 'AbilityVerb', '"AbilityVerb')) and ',ID,' not in txt.split('\n', 1)[0]:
            raise RuntimeError(f'wago.tools gave no {name} table for {ver}')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='') as f: f.write(txt)
    return list(csv.DictReader(io.StringIO(txt)))

def num(x):
    try: f = float(x)
    except (TypeError, ValueError): return 0
    return int(f) if f == int(f) else round(f, 4)

class Build:
    """One client build's spell tables, indexed by spell id."""
    def __init__(s, ver):
        s.ver = ver
        t = {n: table(n, ver) for n in TABLES}
        by = lambda rows, key='SpellID': {r[key]: r for r in sorted(rows, key=lambda r: (r.get('DifficultyID', '0') != '0', int(r.get('OrderIndex') or 0)), reverse=True)}
        s.name = {r['ID']: r['Name_lang'] for r in t['SpellName']}
        s.spell = {r['ID']: r for r in t['Spell']}
        s.misc = by(t['SpellMisc'])
        s.levels, s.power, s.cd = by(t['SpellLevels']), by(t['SpellPower']), by(t['SpellCooldowns'])
        s.cat, s.aura, s.cls = by(t['SpellCategories']), by(t['SpellAuraOptions']), by(t['SpellClassOptions'])
        s.targets = by(t['SpellTargetRestrictions'])
        s.cast = {r['ID']: num(r['Base']) for r in t['SpellCastTimes']}
        s.dur = {r['ID']: num(r['Duration']) for r in t['SpellDuration']}
        s.range = {r['ID']: max(num(r['RangeMax_0']), num(r['RangeMax_1'])) for r in t['SpellRange']}
        s.radius = {r['ID']: num(r['Radius']) for r in t['SpellRadius']}
        s.effects = collections.defaultdict(dict)
        for r in t['SpellEffect']:
            if r['DifficultyID'] == '0': s.effects[r['SpellID']][int(r['EffectIndex'])] = r
        s.talents, s.tabs, s.sla = t['Talent'], t['TalentTab'], t['SkillLineAbility']

    def triggers(s, sid):
        return [e['EffectTriggerSpell'] for e in s.effects.get(sid, {}).values() if e['EffectTriggerSpell'] not in ('0', '', sid)]

    def desc(s, sid, seen=None):
        """A spell's description and aura description, with $@spelldesc<id> worked in"""
        seen = seen or set(); seen.add(sid)
        r = s.spell.get(sid, {})
        txt = (r.get('Description_lang') or '') + ' ' + (r.get('AuraDescription_lang') or '')
        for o in re.findall(r'\$@spelldesc<?(\d+)', txt):
            if o not in seen: txt += ' ' + s.desc(o, seen)
        return re.sub(r'\$@spell\w+<?\d+>?', ' ', txt)

    def profile(s, sid):
        """What the site cares about in one spell, worked out: {field: value}, effect fields as '<field><index>'."""
        p = {}
        m = s.misc.get(sid)
        if m:
            p['cast'] = s.cast.get(m['CastingTimeIndex'], 0)
            p['dur'] = s.dur.get(m['DurationIndex'], 0)
            p['range'] = s.range.get(m['RangeIndex'], 0)
            p['school'] = int(m['SchoolMask'] or 0)
            p['speed'] = num(m['Speed'])
        c = s.cd.get(sid, {})
        p['cd'] = max(num(c.get('RecoveryTime')), num(c.get('CategoryRecoveryTime')))
        p['gcd'] = num(c.get('StartRecoveryTime')) if c else 0
        pw = s.power.get(sid)
        if pw:
            pt = int(pw['PowerType'] or 0)
            p['cost'] = (num(pw['PowerCostPct']), '% of base mana') if num(pw['PowerCostPct']) else \
                        (num(pw['ManaCost']) / (10 if pt == 1 else 1), ' ' + POWER.get(pt, 'power'))
        lv = s.levels.get(sid)
        if lv: p['level'] = num(lv['SpellLevel']) or num(lv['BaseLevel'])
        ct = s.cat.get(sid, {})
        p['dr'], p['mech'], p['dispel'] = int(ct.get('DiminishType') or 0), int(ct.get('Mechanic') or 0), int(ct.get('DispelType') or 0)
        p['category'] = int(ct.get('Category') or 0)
        a = s.aura.get(sid)
        if a:   # no row: nothing known (not 0%)
            p['proc'] = min(num(a.get('ProcChance')), 100)
            p['charges'], p['stacks'] = num(a.get('ProcCharges')), num(a.get('CumulativeAura'))
            p['icd'] = num(a.get('ProcCategoryRecovery'))
        p['targets'] = num(s.targets.get(sid, {}).get('MaxTargets'))
        for i, e in s.effects.get(sid, {}).items():
            p[f'pts{i}'] = num(e['EffectBasePointsF'])
            p[f'coef{i}'] = num(e['EffectBonusCoefficient'])
            p[f'apcoef{i}'] = num(e['BonusCoefficientFromAP'])
            p[f'ppl{i}'] = num(e['EffectRealPointsPerLevel'])
            p[f'chain{i}'] = num(e['EffectChainTargets'])
            p[f'radius{i}'] = max(s.radius.get(e['EffectRadiusIndex_0'], 0), s.radius.get(e['EffectRadiusIndex_1'], 0))
            p[f'period{i}'] = num(e['EffectAuraPeriod'])
            p[f'kind{i}'] = (int(e['Effect'] or 0), int(e['EffectAura'] or 0))
            mask = tuple(int(e[f'EffectSpellClassMask_{k}'] or 0) & 0xffffffff for k in range(4))
            if any(mask): p[f'mask{i}'] = mask
        return p

    def family(s, sid):
        """(class set, mask) a talent's EffectSpellClassMask is matched against"""
        r = s.cls.get(sid)
        if not r: return None
        return int(r['SpellClassSet'] or 0), tuple(int(r[f'SpellClassMask_{k}'] or 0) & 0xffffffff for k in range(4))

# ---- which client spells the site shows ----

FEED = []
def talent_feed():
    if not FEED:
        try: FEED.append(tm.talent_feed())
        except Exception as e: print("client files: no Wowhead talent feed, using the client's Talent table:", e); FEED.append(None)
    return FEED[0]

def site_spells(b):
    """{spell id: info} for every rank the site shows and the spells they trigger. info: {'classes', 'name', 'icon',
    'where', 'rank', 'kind' ('talent' / 'spell' / 'racial'), 'via' (the triggered spell's own name, for a trigger)}.
    Also returns the site names it could not find in the client tables (printed, to keep the matching honest)."""
    out, missing = {}, []
    feed = talent_feed()
    talent_names = {}
    tabs = sorted(b.tabs, key=lambda r: int(r['OrderIndex']))
    by_pos = collections.defaultdict(dict)
    for t in b.talents: by_pos[t['TabID']][int(t['TierID']), int(t['ColumnIndex'])] = t
    for c in CLASSES:
        trees = json.load(open(f'{c}.json', encoding='utf-8'))
        mine = [t for t in tabs if int(t['ClassMask']) & CLASS_BIT[c]]
        by_name = {b.name.get(t['SpellRank_0']): t for m in mine for t in by_pos[m['ID']].values()}
        for i, tree in enumerate(trees):
            tab = next((t for t in mine if t['Name_lang'] == tree['n']), mine[i] if i < len(mine) else None)
            feed_tree = {t['name']: t for t in (feed or {}).get('talents', {}).get(str(tree['s']), {}).values()}
            for a in tree['t']:
                row, col, ranks, name, icon = a[:5]
                # Wowhead's talent feed has each rank's spell id; the client's Talent table predates many of Forever's
                # talents, so it is only the fallback (by name, else by place in the tree)
                ids = [str(x) for x in feed_tree[name]['ranks']] if name in feed_tree else []
                if not ids:
                    t = by_name.get(name)
                    if not t and tab:
                        t = by_pos[tab['ID']].get((row, col))
                        if t and b.name.get(t['SpellRank_0']) in {x[3] for tr in trees for x in tr['t']}: t = None
                    ids = [t[f'SpellRank_{k}'] for k in range(9)] if t else []
                ids = [x for x in ids if x not in ('0', '') and x in b.misc][:ranks]
                if not ids: missing.append(f'{c} talent {name}'); continue
                one = len(set(ids)) == 1 and ranks > 1   # Forever's ranked talents can be one spell for every rank
                for r, sid in enumerate(ids, 1):
                    out[sid] = {'classes': [c], 'name': name, 'icon': icon, 'where': f"{tree['n']} talent", 'rank': None if one else r, 'ranks': ranks, 'kind': 'talent'}
                talent_names[name] = c
    spells = json.load(open('spells_raw.json', encoding='utf-8'))
    by_line = collections.defaultdict(list)
    for r in b.sla: by_line[r['SkillLine']].append(r)
    for c in CLASSES:
        for name, icon, line, levels, _, _, top in spells.get(c, []):
            cand = {r['Spell'] for r in by_line[str(line)] if b.name.get(r['Spell']) == name
                    and (not int(r['ClassMask'] or 0) or int(r['ClassMask']) & CLASS_BIT[c])}
            cand.add(str(top))
            cand = [x for x in cand if x in b.misc]
            if not cand: missing.append(f'{c} spell {name}'); continue
            rank_of = lambda x: (int(m.group(1)) if (m := re.match(r'Rank (\d+)', b.spell.get(x, {}).get('NameSubtext_lang') or '')) else 0)
            # the site's ranks (ranks_raw.json: rank number and level; a talent may teach rank 1): the top one is the
            # site's own id, each other the copy learned at its level (a "Rank N" one first, not a racial or NPC copy)
            want = [(r, lv) for r, lv, _ in RANKS.get(c, {}).get(name, {}).get('r', [])] or [(1, levels[-1] if levels else 0)]
            ranks_of, used = {}, {str(top)}
            for r, lv in sorted(want)[:-1]:
                at = [x for x in cand if x not in used and b.profile(x).get('level') == lv]
                x = next((x for x in at if rank_of(x) == r), at[0] if at else None) or                     next((x for x in cand if x not in used and rank_of(x) == r), None)   # learned at another level now
                if x: used.add(x); ranks_of[x] = r
            if str(top) in cand: ranks_of[str(top)] = max(want)[0]
            for sid, r in ranks_of.items():
                info = out.setdefault(sid, {'classes': [], 'name': name, 'icon': icon, 'where': 'Spell', 'rank': r, 'ranks': max(want)[0], 'kind': 'spell'})
                if c not in info['classes']: info['classes'].append(c)
    import sync_racials as sr   # here, not at the top: sync_racials imports changelog, which imports this file
    races = json.load(open('racials.json', encoding='utf-8'))
    variant_class = {v.lower(): v.lower() for v in sr.VARIANT.values() if v.lower() in CLASSES}
    for race in races:
        classes = [x.lower() for x in race['classes']]
        for name, icon, *_ in race['traits']:
            for sid in sr.TRAIT_IDS.get(name, []):
                v = sr.VARIANT.get(sid, '').lower()
                if str(sid) not in b.misc: missing.append(f"{race['name']} racial {name}"); continue
                out.setdefault(str(sid), {'classes': [v] if v in variant_class else classes, 'name': name, 'icon': icon,
                                          'where': f"{race['name']} racial", 'rank': None, 'ranks': 1, 'kind': 'racial'})
    # a talent's effect cast by the server under the talent's name (Entrapment's root): same name, no class set, a mechanic
    for sid, nm in b.name.items():
        c = talent_names.get(nm)
        if c and sid not in out and sid in b.misc and not b.family(sid) and int(b.cat.get(sid, {}).get('Mechanic') or 0):
            info = next(i for i in out.values() if i['name'] == nm and i['kind'] == 'talent')
            out[sid] = dict(info, via=nm, parent=None, rank=None)
    # the spells they trigger (a talent's root, a proc's buff), two steps deep
    for depth in range(2):
        for sid, info in list(out.items()):
            if depth and 'via' not in info: continue
            for t in b.triggers(sid):
                if t not in out and t in b.misc:
                    out[t] = dict(info, via=b.name.get(t, ''), parent=sid, rank=None)
    return out, missing

# ---- reading a change ----

def secs(ms):
    """3600000 -> '1 hr', 180000 -> '3 min', 1500 -> '1.5 sec'"""
    if ms <= 0: return 'none' if ms == 0 else 'until cancelled'
    s = ms / 1000
    if s >= 3600 and s % 3600 == 0: return f'{s / 3600:g} hr'
    if s >= 60 and s % 60 == 0: return f'{s / 60:g} min'
    return f'{s:g} sec'

def school(m): return '/'.join(n for b, n in SCHOOLS if m & b) or 'none'

def site_rows(cls, info):
    """The cost / range / cast time / cooldown cells the site shows for one rank (Wowhead's tooltip), as one string."""
    if info['kind'] == 'spell':
        rt = (RANK_TIPS.get(cls, {}).get(info['name']) or {})
        return ' · '.join((rt.get(str(info['rank'] or 1)) or {}).values())
    if info['kind'] == 'talent':
        r = (TALENT_META.get(cls, {}).get(info['name']) or [])
        rows = r[min(info['rank'] or len(r), len(r)) - 1] if r else []
        return ' · '.join(c for row in rows for c in row)
    races = {t[0]: t[2] for race in RACIALS for t in race['traits']}
    return races.get(info['name'], '')

def shown(cls, info, field, value):
    """Does the site already show this cost / range / cast time / cooldown / level? (Wowhead has it, now or earlier)"""
    cells = site_rows(cls, info)
    if field == 'level':
        lv = next((s[3] for s in SPELLS.get(cls, []) if s[0] == info['name']), [])
        return info['kind'] != 'spell' or (info['rank'] <= len(lv) and lv[info['rank'] - 1] == value)
    if field == 'cd':
        m = re.search(r'(\d+(?:\.\d+)?) (sec|min|hr) cooldown', cells)
        have = float(m.group(1)) * {'sec': 1000, 'min': 60000, 'hr': 3600000}[m.group(2)] if m else 0
        return abs(have - value) < 1
    if field == 'cast':
        if 'Channeled' in cells: return True
        m = re.search(r'(\d+(?:\.\d+)?) sec cast', cells)
        have = float(m.group(1)) * 1000 if m else 0
        return abs(have - value) < 1 or not cells
    if field == 'range':
        m = re.search(r'(\d+(?:\.\d+)?) yd', cells)
        have = float(m.group(1)) if m else (5 if 'Melee' in cells else 0)
        return have == value or (value <= 5 and 'Melee' in cells) or not cells
    if field == 'cost':
        m = re.search(r'(\d+(?:\.\d+)?)%? (?:of base mana|Mana|Rage|Energy|Focus)', cells)
        return (float(m.group(1)) if m else 0) == value[0]
    return False

def fmt(field, v):
    if field in ('cd', 'gcd', 'cast', 'dur', 'icd') or field.startswith('period'): return secs(v)
    if field == 'range' or field.startswith('radius'): return f'{v:g} yd'
    if field == 'cost': return f'{v[0]:g}{v[1]}'
    if field == 'speed': return f'{v:g} yd/sec'
    if field.startswith(('coef', 'apcoef')): return f'{v * 100:.4g}%'
    if field in ('proc',): return f'{v:g}%'
    if field in ('charges', 'stacks', 'targets') and v == 0: return 'no limit'
    return f'{v:g}' if isinstance(v, (int, float)) else str(v)

# field -> (label, True when a higher number is better, None when it's neither); a field not here isn't compared
LABELS = {'cd': ('cooldown', False), 'gcd': ('global cooldown', False), 'cast': ('cast time', False), 'dur': ('duration', None),
          'range': ('range', True), 'cost': ('cost', False), 'level': ('learned at level', False), 'speed': ('travel speed', True),
          'proc': ('chance to trigger', True), 'charges': ('charges', None), 'stacks': ('stacks up to', None),
          'icd': ('internal cooldown', False), 'targets': ('maximum targets', None),
          'coef': ('spell power coefficient', True), 'apcoef': ('attack power coefficient', True),
          'ppl': ('value gained per level', True), 'chain': ('targets hit', True), 'radius': ('radius', True),
          'period': ('time between ticks', None), 'pts': (None, None)}
ROWS = ('cd', 'cast', 'range', 'cost', 'level')   # shown on the site's tooltips (Wowhead's rows)

def label_of(field, p):
    base = re.match(r'[a-z]+', field).group(0)
    lab = LABELS[base][0]
    if base == 'pts':
        i = int(field[3:]); eff, aura = p.get(f'kind{i}', (0, 0))
        lab = AURA_NAME.get(aura) if eff == 6 and aura else EFFECT_NAME.get(eff)
        lab = lab or f'effect {i + 1} value'   # not shown (changes() skips these)
    return lab

def changes(old, new):
    """The client-table changes between two builds, per site spell: {(class, name): {...}} with the readable sentences."""
    A, B = Build(old), Build(new)
    site, missing = site_spells(B)
    site_a, _ = site_spells(A)
    for k, v in site_a.items(): site.setdefault(k, v)
    # the variables any site spell's description quotes, in either build: (spell id, letter, effect index or None)
    quoted = set()
    for b in (A, B):
        for sid in site:
            for ref, letter, idx in REF.findall(b.desc(sid)):
                quoted.add((ref or sid, letter.lower(), int(idx) - 1 if idx else None))
    def is_quoted(sid, field):
        base = re.match(r'[a-z]+', field).group(0); i = int(field[len(base):]) if field[len(base):] else None
        return any((sid, l, j) in quoted for l, fs in QUOTES.items() if base in fs for j in ((i, None) if i is not None else (None, 0, 1, 2)))
    # what the client calls each site spell, to name the spells a talent affects or a diminishing returns group holds
    name_of = lambda b, sid: site[sid]['name'] if sid in site else b.name.get(sid, sid)
    def dr_group(b, sid, dr):
        if not dr: return []
        return sorted({name_of(b, x) for x in site if x != sid and b.cat.get(x, {}).get('DiminishType') == str(dr)
                       and name_of(b, x) != name_of(b, sid)})
    def affects(b, sid, mask):
        fam = b.family(sid)
        if not fam or not mask: return set()
        return {name_of(b, x) for x in site if site[x].get('kind') != 'talent' and 'via' not in site[x]
                and (f := b.family(x)) and f[0] == fam[0] and any(m & n for m, n in zip(mask, f[1]))}
    found = collections.OrderedDict()
    for sid, info in sorted(site.items(), key=lambda kv: (kv[1]['name'], kv[1]['rank'] or 0, int(kv[0]))):
        if sid not in A.misc or sid not in B.misc: continue   # new or removed: Wowhead's change pages have those
        pa, pb = A.profile(sid), B.profile(sid)
        for field in sorted(set(pa) | set(pb)):
            base = re.match(r'[a-z]+', field).group(0)
            if base not in LABELS and base not in ('dr', 'mech', 'dispel', 'school', 'category'): continue
            if base == 'dr': continue   # read with its group below
            o, n = pa.get(field), pb.get(field)
            if o == n or o is None or n is None: continue   # an effect added or removed reads in the wording
            if base in ROWS and 'via' in info and base != 'cd': continue   # a triggered spell's own level, range...
            if base in ROWS and 'via' not in info:
                # the site's tooltip rows are Wowhead's, hotfixes included: one that shows the new value had the change
                # already, one that shows another value has the server's (Blood Fury: 2 min, still 3 min in 70685's
                # table). Only a row the site has none of (a passive talent's cooldown) is the client's to tell.
                if base == 'level' or any(site_rows(c, info) or shown(c, info, base, n) for c in info['classes']): continue
            elif base in QUOTES_FIELDS and is_quoted(sid, field): continue
            # Wowhead works a tooltip's numbers out at the spell's level, so a quoted value's per-level gain shows too
            if base == 'ppl' and is_quoted(sid, 'pts' + field[3:]): continue
            if base == 'pts' and label_of(field, pb).startswith('effect '): continue   # a number nobody can read
            if base == 'dur' and max(o, n) < 1000: continue   # internal timings
            # a tooltip that names a chance ("a $s1% chance to stun") has it in the text: a proc chance moving to 100%
            # there means the chance moved into the effect, which Wowhead reads
            if base == 'proc' and any('chance' in x.desc(sid).lower() for x in (A, B)): continue

            for c in info['classes']:
                key = (c, info['name'])
                e = found.setdefault(key, {'info': info, 'fields': collections.OrderedDict()})
                e['fields'].setdefault((info.get('via', ''), field), []).append((info['rank'], o, n, sid))
        # whole-spell changes worked out from other spells: diminishing returns group, spells affected
        ga, gb = dr_group(A, sid, pa.get('dr')), dr_group(B, sid, pb.get('dr'))
        if pa.get('dr') != pb.get('dr'):   # (a group that only lost or gained others: those others say so)
            for c in info['classes']:
                found.setdefault((c, info['name']), {'info': info, 'fields': collections.OrderedDict()})['fields'] \
                    .setdefault((info.get('via', ''), 'drgroup'), []).append((info['rank'], (pa.get('dr'), ga), (pb.get('dr'), gb), sid))
        for i in sorted({int(f[4:]) for f in list(pa) + list(pb) if f.startswith('mask')}):
            sa, sb = affects(A, sid, pa.get(f'mask{i}')), affects(B, sid, pb.get(f'mask{i}'))
            sa.discard(info['name']); sb.discard(info['name'])
            if sa != sb and f'mask{i}' in pa and f'mask{i}' in pb:
                for c in info['classes']:
                    found.setdefault((c, info['name']), {'info': info, 'fields': collections.OrderedDict()})['fields'] \
                        .setdefault((info.get('via', ''), 'affects'), []).append((info['rank'], sa, sb, sid))
    for e in found.values(): e['lines'] = sentences(e, A, B)
    return {k: e for k, e in found.items() if e['lines']}, missing

QUOTES_FIELDS = {f for fs in QUOTES.values() for f in fs}

def sentences(e, A, B):
    """[(sentence, 'good' / 'bad' / 'other')] for one talent or spell"""
    out = []
    ranks_total = e['info'].get('ranks') or 1
    for (via, field), vals in e['fields'].items():
        vals = sorted({v[0]: v for v in vals}.values(), key=lambda v: v[0] or 0)   # one value per rank
        if any(v[0] is None for v in vals): vals, ranks_total = vals[:1], 1   # a trigger, or one spell for every rank
        who = ''
        if via:
            mech = MECHANICS.get(B.profile(vals[0][3]).get('mech') or A.profile(vals[0][3]).get('mech'))
            who = f"Its {mech} effect" + (f' ({via})' if via != e['info']['name'] else '') if mech else f'Its triggered effect {via}'
        subject = who or 'Its'
        if field == 'drgroup':
            (od, og), (nd, ng) = vals[-1][1], vals[-1][2]
            s = (who + ' ' if who else '') + ('now ' if who else 'Now ')
            if not nd: txt = ('No longer' if not who else who + ' no longer') + ' has diminishing returns' + (f" (it shared them with {', '.join(og)})" if og else '') + '.'
            elif ng: txt = s + f"shares a diminishing returns group with {', '.join(ng)}" + (f" (was {', '.join(og)})" if og and od else ' (it had none)' if not od else ' (a group of its own before)') + '.'
            else: txt = s + 'has a diminishing returns group of its own' + (f" (it shared one with {', '.join(og)})" if og else '') + '.'
            out.append((txt[0].upper() + txt[1:], 'other')); continue
        if field == 'affects':
            sa, sb = vals[-1][1], vals[-1][2]
            parts = []
            if sb - sa: parts.append(f"now also affects {', '.join(sorted(sb - sa))}")
            if sa - sb: parts.append(f"no longer affects {', '.join(sorted(sa - sb))}")
            txt = (who + ' ' if who else '') + ' and '.join(parts) + '.'
            out.append((txt[0].upper() + txt[1:], 'other')); continue
        base = re.match(r'[a-z]+', field).group(0)
        if base in ('mech', 'dispel', 'school', 'category'):
            o, n = vals[-1][1], vals[-1][2]
            if base == 'mech': txt = f"{subject} mechanic changed from {MECHANICS.get(o, 'none')} to {MECHANICS.get(n, 'none')}."
            elif base == 'dispel': txt = f"{subject} dispel type changed from {DISPELS.get(o, 'none')} to {DISPELS.get(n, 'none')}."
            elif base == 'school': txt = f"{subject} school changed from {school(o)} to {school(n)}."
            else:
                ga = sorted({e2 for e2 in (A.name.get(x) for x, r in A.cat.items() if o and r['Category'] == str(o)) if e2} - {e['info']['name']})
                gb = sorted({e2 for e2 in (B.name.get(x) for x, r in B.cat.items() if n and r['Category'] == str(n)) if e2} - {e['info']['name']})
                if ga == gb: continue   # a new category of its own: the cooldown line says what changed
                txt = (f"{subject} cooldown is now shared with {', '.join(gb)}." if gb else f"{subject} cooldown is no longer shared with {', '.join(ga)}.")
            out.append((txt.replace('Its ', 'Its ', 1), 'other')); continue
        lab, up_good = LABELS[base][0], LABELS[base][1]
        p = B.profile(vals[0][3])
        lab = label_of(field, p) if base == 'pts' else lab
        olds, news = [fmt(field, v[1]) for v in vals], [fmt(field, v[2]) for v in vals]
        def verdict(o, n):
            if base == 'cost': o, n = o[0], n[0]
            if up_good is None or o == n: return 'other'
            return 'good' if (n > o) == up_good else 'bad'
        vs = {verdict(v[1], v[2]) for v in vals}
        v = vs.pop() if len(vs) == 1 else 'other'
        mark = lambda t: f"{{{'+' if v == 'good' else '-'}{t}}}" if v in ('good', 'bad') else t
        rank_note = ''
        if len(set(zip(olds, news))) == 1:
            o, n = olds[0], news[0]
            if len(vals) < ranks_total and ranks_total > 1: rank_note = f" (rank{'s' if len(vals) > 1 else ''} {', '.join(str(x[0]) for x in vals)})"
        else:
            o, n = ' / '.join(olds), ' / '.join(news)
            rank_note = f" (rank{'s' if len(vals) > 1 else ''} {', '.join(str(x[0]) for x in vals)})" if len(vals) < ranks_total else ' (by rank)'
        what = (f'{who}: {lab}' if who else lab[0].upper() + lab[1:])
        if base == 'gcd' and vals[-1][2] == 0: txt = f"{who + ': n' if who else 'N'}o longer triggers the global cooldown{rank_note} (was {o})."
        elif base == 'cd' and vals[-1][1] == 0: txt = f"{what}: now {mark(n)}{rank_note} (had none)."
        elif base == 'level': txt = f"Now learned at level {mark(n)}{rank_note} (was {o})."
        elif base == 'charges' and len(vals) == 1 and vals[0][2]: txt = f"{who + ': n' if who else 'N'}ow has {n} charge{'s' if vals[0][2] != 1 else ''}{rank_note} (was {o})."
        else:
            dirn = ''
            if base != 'cost' and all(isinstance(x[1], (int, float)) for x in vals):
                ups = {x[2] > x[1] for x in vals}
                dirn = (' increased' if ups == {True} else ' reduced' if ups == {False} else ' changed')
            else: dirn = ' changed'
            txt = f"{what}{dirn} from {o} to {mark(n)}{rank_note}."
        out.append((txt, v))
    return out

def entries(old, new, quiet=False):
    """{class: [[kind, name, icon, where, text, ""], ...]} for the Class Changes page"""
    global RANK_TIPS, TALENT_META, SPELLS, RACIALS
    found, missing = changes(old, new)
    if missing and not quiet: print('client files: not found for', ', '.join(missing))
    out = {}
    for (c, name), e in found.items():
        info = e['info']
        verdicts = {v for _, v in e['lines']}
        kind = 'buff' if verdicts == {'good'} else 'nerf' if verdicts == {'bad'} else 'other'
        text = ' '.join(t + MARK for t, _ in e['lines'])
        out.setdefault(c, []).append([kind, name, info['icon'], info['where'], text, ''])
    return out

RANK_TIPS = json.load(open('rank_tips.json', encoding='utf-8')) if os.path.exists('rank_tips.json') else {}
TALENT_META = json.load(open('talent_meta.json', encoding='utf-8')) if os.path.exists('talent_meta.json') else {}
RANKS = json.load(open('ranks_raw.json', encoding='utf-8')) if os.path.exists('ranks_raw.json') else {}
SPELLS = json.load(open('spells_raw.json', encoding='utf-8')) if os.path.exists('spells_raw.json') else {}
RACIALS = json.load(open('racials.json', encoding='utf-8')) if os.path.exists('racials.json') else []

# ---- merging with Wowhead's entries ----

KIND_SET = {'buff': {'good'}, 'nerf': {'bad'}, 'other': {'other'}}

def merge(classes, client):
    """Put the client entries into an update's classes (changelog.py's, from Wowhead), in place. A talent or spell Wowhead
    lists too keeps its one entry, with the client's sentences added to it (and to each of its rank rows)."""
    for c, ch in client.items():
        mine = classes.setdefault(c, [])
        for ce in ch:
            e = next((e for e in mine if e[1] == ce[1]), None)
            if e is None: mine.append(list(ce)); continue
            if ce[4] in e[4]: continue
            e[4] += ('\n' if '\n' in e[4] else ' ') + ce[4]
            for row in (e[6] if len(e) > 6 else []): row[1] += ('\n' if '\n' in row[1] else ' ') + ce[4]
            v = KIND_SET[e[0]] | KIND_SET[ce[0]]
            e[0] = 'buff' if v == {'good'} else 'nerf' if v == {'bad'} else 'other'
    for c in [c for c, ch in classes.items() if not ch]: del classes[c]
    return classes

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    known = builds()
    if '--builds' in sys.argv: print('\n'.join(known)); return
    last = json.load(open('version.json', encoding='utf-8')).get('client')
    if len(args) == 2: old, new = version(args[0], known), version(args[1], known)
    elif '--latest' in sys.argv or not last: old, new = known[-2], known[-1]
    else: old, new = last, known[-1]
    if old == new: print(f'client files: {new} is still the latest build, compared already'); return
    print(f'client files {old} -> {new}')
    out = entries(old, new)
    for c, ch in out.items():
        for k, name, icon, where, text, _ in ch: print(f'{c:8} {k:5} {name} [{where}]: {text}')
    print(sum(len(v) for v in out.values()), 'changes')

if __name__ == '__main__':
    main()
