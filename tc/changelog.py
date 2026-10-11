"""Record what each beta update changed, for the site's Class Changes page.

Run from inside tc/, after sync_talents.py, sync_spells.py and talent_meta.py and before build.py:
    py changelog.py              compare the data files with the last commit (what the daily job does)
    py changelog.py REV          compare with an older commit instead
    py changelog.py REV --dry    just print what it would record

It compares every talent (each rank's text, rank count, cost / cast time / cooldown) and every spellbook spell
(top-rank text and its cost / cast time / cooldown) per class, and appends one update to changes.json:
    {"date", "version", "build", "classes": {class: [[kind, name, icon, where, text], ...]}}
kind is "buff", "nerf" or "other". In the text, {+15%} marks a value that got better (shown green) and {-150}
one that got worse (red). Buff / nerf is a best guess from the wording (a higher cost or cooldown is worse, a
bigger "reduces ... by" is better, other numbers going up are better); anything mixed or reworded goes to
"other". The daily job opens a pull request, so the guesses can be fixed in changes.json before merging.

It also keeps version.json (beta version, build number and the date that build first appeared) up to date from
Blizzard's patch server.
"""
import json, re, subprocess, sys, datetime
import talent_meta as tm
from textfix import clean_html, tidy_formula

CLASSES = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior']
NUM = re.compile(r'\d+(?:\.\d+)?')
WORSE_BEFORE = re.compile(r'(cost|costs|cooldown|cast time|casting time|threat)', re.I)
WORSE_AFTER = re.compile(r'^\s*%?\s*(mana|rage|energy|sec cooldown|min cooldown|sec cast)', re.I)
LESS = re.compile(r'\b(reduc\w*|decreas\w*|lower\w*|less)\b', re.I)

def at(rev, path):
    r = subprocess.run(['git', 'show', f'{rev}:tc/{path}'], capture_output=True, encoding='utf-8')
    return json.loads(r.stdout) if r.returncode == 0 and r.stdout.strip() else None

def now(path):
    return json.load(open(path, encoding='utf-8'))

def plain(s):
    s = tidy_formula(clean_html(re.sub(r'<!--.*?-->', '', s or '')))
    s = re.sub(r'\s*<br\s*/?>\s*', ' ', s)
    s = re.sub(r'<[^>]+>', '', s).replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', s).strip()

def better(old, new, before, after):
    """Is old -> new an improvement, judging by the words around the number?"""
    up = float(new) > float(old)
    if LESS.search(before[-40:]): return up          # "reduces the cooldown by 2 sec": a bigger reduction is better
    if WORSE_BEFORE.search(before[-30:]) or WORSE_AFTER.search(after): return not up   # "costs 150 mana", "3 min cooldown": higher is worse
    return up

def text_change(old, new):
    """Same wording, different numbers -> (marked text, set of 'good'/'bad'); otherwise None."""
    old, new = plain(old), plain(new)
    if old == new: return None
    if NUM.sub('#', old) != NUM.sub('#', new): return None   # reworded
    o, n = NUM.findall(old), NUM.findall(new)
    out, verdicts, pos = [], set(), 0
    for m, ov in zip(NUM.finditer(new), o):
        nv = m.group(0)
        out.append(new[pos:m.start()])
        if float(ov) == float(nv): out.append(nv)
        else:
            unit = '%' if new[m.end():m.end() + 1] == '%' else ''
            good = better(ov, nv, new[:m.start()], new[m.end():])
            verdicts.add('good' if good else 'bad')
            out.append(f"{{{'+' if good else '-'}{nv}{unit}}} ({'up' if float(nv) > float(ov) else 'down'} from {ov}{unit})")
            if unit: pos = m.end() + 1; continue
        pos = m.end()
    out.append(new[pos:])
    return ''.join(out), verdicts

def row_change(label, old, new):
    """A cost / cast time / cooldown cell: '100 Mana' -> '150 Mana'."""
    if (old or '') == (new or '') or not old or not new: return None   # a value appearing / vanishing is missing data, not news
    o, n = NUM.findall(old), NUM.findall(new)
    if len(o) == 1 and len(n) == 1 and NUM.sub('#', old) == NUM.sub('#', new):
        up = float(n[0]) > float(o[0])
        good = not up if label != 'range' else up
        word = 'increased' if up else 'reduced'
        return f"{label.capitalize()} {word} from {old} to {{{'+' if good else '-'}{new}}}.", {'good' if good else 'bad'}
    return f'{label.capitalize()} changed from {old} to {new}.', {'other'}

def kind_of(verdicts):
    if verdicts == {'good'}: return 'buff'
    if verdicts == {'bad'}: return 'nerf'
    return 'other'

def meta_cells(rows):
    """talent_meta rows for one rank -> {'cost','range','cast time','cooldown'}"""
    out = {}
    for left, right in rows or []:
        for cell in (left, right):
            if not cell: continue
            if 'cooldown' in cell: out['cooldown'] = cell
            elif re.search(r'yd|range', cell, re.I): out['range'] = cell
            elif re.search(r'Instant|cast|Channeled', cell): out['cast time'] = cell
            elif re.search(r'Mana|Rage|Energy|Focus|Health', cell): out['cost'] = cell
    return out

def talents(cls, old, new, old_meta, new_meta):
    out = []
    if old is None: return out
    O = {t[3]: (tr['n'], t) for tr in old for t in tr['t']}
    N = {t[3]: (tr['n'], t) for tr in new for t in tr['t']}
    for name, (tree, t) in N.items():
        where, icon = f'{tree} talent', t[4]
        if name not in O:
            out.append(['other', name, icon, where + ' · new', 'New talent: ' + plain(t[5])]); continue
        o = O[name][1]
        notes, verdicts = [], set()
        if o[2] != t[2]:
            notes.append(f'Now has {t[2]} ranks (was {o[2]}).'); verdicts.add('other')
        ot = (o[8][-1] if len(o) > 8 and o[8] else o[5]); nt = (t[8][-1] if len(t) > 8 and t[8] else t[5])
        if plain(ot) != plain(nt):
            tc = text_change(ot, nt)
            if tc: notes.append(tc[0]); verdicts |= tc[1]
            else: notes.append('Reworked: ' + plain(nt)); verdicts.add('other')
        om, nm = meta_cells((old_meta.get(name) or [[]])[-1]), meta_cells((new_meta.get(name) or [[]])[-1])
        for label in ('cost', 'cast time', 'cooldown', 'range'):
            rc = row_change(label, om.get(label), nm.get(label))
            if rc: notes.append(rc[0]); verdicts |= rc[1]
        if notes: out.append([kind_of(verdicts), name, icon, where + (' · reworked' if 'other' in verdicts and any(n.startswith('Reworked') for n in notes) else ''), ' '.join(notes)])
    for name, (tree, o) in O.items():
        if name not in N: out.append(['other', name, o[4], f'{tree} talent · removed', 'Removed from the talent tree.'])
    return out

def spells(cls, old_raw, new_raw, old_tips, new_tips):
    out = []
    O = {s[0]: s for s in (old_raw or {}).get(cls, [])}
    for s in new_raw.get(cls, []):
        name, icon = s[0], s[1]
        o = O.get(name)
        if not o: continue   # new spellbook entries are added by hand, not news
        notes, verdicts = [], set()
        if plain(o[5]) != plain(s[5]):
            tc = text_change(o[5], s[5])
            if tc: notes.append(tc[0]); verdicts |= tc[1]
            else: notes.append('Reworded: ' + plain(s[5])); verdicts.add('other')
        ot = (old_tips or {}).get(cls, {}).get(name, {}); nt = new_tips.get(cls, {}).get(name, {})
        top = max(nt, key=int) if nt else None
        if top and top in ot:
            for key, label in (('c', 'cost'), ('t', 'cast time'), ('cd', 'cooldown'), ('r', 'range')):
                rc = row_change(label, ot[top].get(key), nt[top].get(key))
                if rc: notes.append(rc[0]); verdicts |= rc[1]
        if notes: out.append([kind_of(verdicts), name, icon, 'Spell · top rank', ' '.join(notes)])
    return out

def beta_build():
    """(version, build) of the WoW Forever beta from Blizzard's patch server, e.g. ('1.60.1', '70338').
    The beta is listed as wow_classic_beta; at launch the live game will likely be a different product."""
    txt = tm.get('http://us.patch.battle.net:1119/wow_classic_beta/versions')
    row = next(l for l in txt.splitlines() if l.startswith('us|')).split('|')
    name = row[5]   # VersionsName, e.g. 1.60.1.70338
    return name.rsplit('.', 1)[0], name.rsplit('.', 1)[1]

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    rev, dry = (args[0] if args else 'HEAD'), '--dry' in sys.argv
    ver = now('version.json')
    try:
        v, b = beta_build()
        if b != ver.get('build'): ver['date'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')   # first seen today
        ver.update(version=v, build=b)
    except Exception as e:
        print('could not read the beta build from Blizzard:', e)
    old_meta, new_meta = at(rev, 'talent_meta.json') or {}, now('talent_meta.json')
    old_raw, new_raw = at(rev, 'spells_raw.json'), now('spells_raw.json')
    old_tips, new_tips = at(rev, 'rank_tips.json'), now('rank_tips.json')
    classes = {}
    for c in CLASSES:
        ch = talents(c, at(rev, f'{c}.json'), now(f'{c}.json'), old_meta.get(c, {}), new_meta.get(c, {}))
        ch += spells(c, old_raw, new_raw, old_tips, new_tips)
        if ch: classes[c] = ch
    for c, ch in classes.items():
        for k, name, icon, where, text in ch: print(f'{c:8} {k:5} {name}: {text}')
    print(f'{sum(len(v) for v in classes.values())} changes')
    if dry: return
    with open('version.json', 'w', encoding='utf-8', newline='\n') as f: json.dump(ver, f, indent=1); f.write('\n')
    if not classes: return
    log = now('changes.json')
    log['updates'].insert(0, {'date': ver.get('date') or datetime.date.today().isoformat(), 'version': ver.get('version'),
                              'build': ver.get('build'), 'classes': classes})
    with open('changes.json', 'w', encoding='utf-8', newline='\n') as f: json.dump(log, f, ensure_ascii=False, indent=1); f.write('\n')

if __name__ == '__main__':
    main()
