"""Record what each beta update changed, for the site's Class Changes page.

Run from inside tc/ (needs internet):
    py changelog.py              add the newest beta build's changes, if it isn't recorded yet (what the daily job does)
    py changelog.py --rebuild    rebuild the whole history, one update per beta build
    py changelog.py --dry        just print what it would record (works with --rebuild too)
    --date=YYYY-MM-DD            with --rebuild: the latest build's date (Wowhead only dates the older builds)

Each run also does a "Needs a look" scan (sanity()) for changes that look like data errors rather than balance changes:
a number growing or shrinking 3x or more, every rank suddenly saying the same number, a value becoming 0, formula text
left in a tooltip, a talent's rank count changing, removals, and numbers moving both ways at once. The daily job puts
the list at the top of the pull request (../needs-a-look.md). It only flags; corrections go in changes_fixes.json.

The changes come from Wowhead's WoW Forever change pages (wowhead.com/forever/changes/talents/<class> and
.../spellbook/<class>). Each page compares the latest build with an older one (?vs=<build>) and lists, per talent or
spell and per rank, the tooltip in both builds plus changes the tooltip doesn't show (threat, icon...). From those
pages every build's tooltips can be rebuilt, and each update is one build compared with the one before it.

changes.json holds one entry per update, newest first:
    {"date", "version", "build", "classes": {class: [[kind, name, icon, where, text, was], ...]}}
was (on reworded, reworked and removed entries, else "") is the old text, shown under "Previous version". A spell
with ranks adds [[rank, text, was], ...] for each rank that changed, highest first (for the rank picker). In reworded
text {*...*} marks the words added and, in was, {~...~} the words removed.
kind is "buff", "nerf" or "other". In the text, {+15%} marks a value that got better (shown green) and {-150}
one that got worse (red). Buff / nerf is a best guess from the wording (a higher cost or cooldown is worse, a
bigger "reduces ... by" is better, other numbers going up are better); anything mixed or reworded goes to
"other". The daily job opens a pull request, so the guesses can be fixed in changes.json before merging.
"build" is Wowhead's build number for the data, which can trail the game client's build in version.json.

It also keeps version.json (beta version, build number and the date that build first appeared) up to date from
Blizzard's patch server.
"""
import json, re, sys, time, datetime, difflib
import talent_meta as tm
from textfix import clean_html, tidy_formula

CLASSES = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior']
KINDS = ['talents', 'spellbook']
NUM = re.compile(r'\d+(?:\.\d+)?')
WORSE_BEFORE = re.compile(r'(cost|costs|cooldown|cast time|casting time|threat)', re.I)
WORSE_AFTER = re.compile(r'^\s*%?\s*(mana|rage|energy|sec cooldown|min cooldown|sec cast)', re.I)
LESS = re.compile(r'\b(reduc\w*|decreas\w*|lower\w*|less)\b', re.I)
# changes Wowhead lists that the tooltip doesn't show: only these read as news (the rest is internal spell data)
HIDDEN_KEEP = re.compile(r'^(Threat|New icon)')

def now(path):
    return json.load(open(path, encoding='utf-8'))

class Lin:
    """a + b * var, for working out Wowhead's leftover formulas"""
    def __init__(s, a=0.0, b=0.0, var=None): s.a, s.b, s.var = a, b, var
    @staticmethod
    def of(o): return o if isinstance(o, Lin) else Lin(float(o))
    def __add__(s, o): o = Lin.of(o); return Lin(s.a + o.a, s.b + o.b, s.var or o.var)
    __radd__ = __add__
    def __sub__(s, o): o = Lin.of(o); return Lin(s.a - o.a, s.b - o.b, s.var or o.var)
    def __rsub__(s, o): return Lin.of(o) - s
    def __mul__(s, o):
        o = Lin.of(o)
        if s.b and o.b: raise ValueError
        return Lin(s.a * o.a, s.a * o.b + s.b * o.a, s.var or o.var)
    __rmul__ = __mul__

def formulas(s):
    """Formulas Wowhead leaves in a tooltip, worked out: '[(430 + Spirit) * (1)]' -> '430 (plus your Spirit)',
    '((((60 - 26) * 1.5) + 14 + (0.078 * ((Shadow spell power)))) * (1 * 1 * 1))' -> '65 (plus about 8% of your
    Shadow spell power)'."""
    out, i = [], 0
    while i < len(s):
        if s[i] in '([':
            depth, j = 0, i
            while j < len(s):
                depth += s[j] in '(['; depth -= s[j] in ')]'
                if depth == 0: break
                j += 1
            g = s[i:j + 1]
            names = set(re.findall(r'[A-Za-z][A-Za-z ]*[A-Za-z]|[A-Za-z]', g))
            if j < len(s) and len(names) <= 1 and re.search(r'[*+]', g) and re.fullmatch(r'[\d\s.+\-*/()\[\]A-Za-z]+', g):
                try:
                    name = next(iter(names), None)
                    expr = g.replace('[', '(').replace(']', ')')
                    if name: expr = expr.replace(name, 'X')
                    v = Lin.of(eval(expr, {'__builtins__': {}}, {'X': Lin(0, 1, name)}))
                    txt = f'{v.a:g}'
                    if v.b:
                        pct = v.b * 100
                        txt += (f' (plus your {v.var})' if abs(v.b - 1) < 1e-9 else
                                f" (plus {'about ' if abs(pct - round(pct)) > 0.05 else ''}{round(pct)}% of your {v.var})")
                    out.append(txt); i = j + 1; continue
                except Exception: pass
        out.append(s[i]); i += 1
    return ''.join(out)

def plain(s):
    s = formulas(tidy_formula(clean_html(re.sub(r'<!--.*?-->', '', s or ''))))
    s = re.sub(r'(?<![\d.])(\d{2,})\.\d{3,}', lambda m: str(round(float(m.group(0)))), s)   # level-scaled damage: 104.473 -> 104, as in game
    s = re.sub(r'\s*<br\s*/?>\s*', ' ', s)
    s = re.sub(r'<[^>]+>', '', s).replace('&nbsp;', ' ')
    s = re.sub(r'[ \t]*\n\s*', '\n', s)   # keep line breaks (a finishing move's "1 point: ..." lines), as the tooltip has them
    return re.sub(r'[ \t\r\f\v]+', ' ', s).strip()

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
    """A cost / cast time / cooldown / range line: '100 Mana' -> '150 Mana'."""
    if (old or '') == (new or ''): return None
    if not old: return f'Now has a {label}: {new}.', {'other'}
    if not new: return f'No longer has a {label} (was {old}).', {'other'}
    o, n = NUM.findall(old), NUM.findall(new)
    if len(o) == 1 and len(n) == 1 and NUM.sub('#', old) == NUM.sub('#', new):
        up = float(n[0]) > float(o[0])
        good = not up if label != 'range' else up
        word = 'increased' if up else 'reduced'
        return f"{label.capitalize()} {word} from {old} to {{{'+' if good else '-'}{new}}}.", {'good' if good else 'bad'}
    return f'{label.capitalize()} changed from {old} to {new}.', {'other'}

def join(notes):
    """Notes one after another; after a text that ends in a list (a finishing move's combo point lines) the next note
    starts on its own line."""
    out = ''
    for n in notes: out += ('\n' if '\n' in out else ' ' if out else '') + n
    return out

def kind_of(verdicts):
    if verdicts == {'good'}: return 'buff'
    if verdicts == {'bad'}: return 'nerf'
    return 'other'

# ---- Wowhead's change pages ----

_cache = {}
def page(kind, cls, vs):
    """The data behind wowhead.com/forever/changes/<kind>/<cls>?vs=<build>: the latest build compared with build vs."""
    if (kind, cls, vs) not in _cache:
        h = tm.get(f'https://www.wowhead.com/forever/changes/{kind}/{cls}' + (f'?vs={vs}' if vs else ''))
        i = h.index('new WH.Wow.Spellbook(')
        _cache[kind, cls, vs] = json.JSONDecoder().raw_decode(h[h.index('{', i):])[0]
        time.sleep(0.5)
    return _cache[kind, cls, vs]

def snapshot(d, which):
    """One build's talents or spells from a change page: which='before' is the compared (older) build, 'after' the
    latest. -> {key: {'icon', 'tab', 'ranks': {rank: tooltip}, 'levels': {rank: level}, 'hidden': set of lines}}"""
    tabs = {t['id']: t['name'] for t in d['data']['tabs']}
    out = {}
    for s in d['data']['spells']:
        e = {'icon': s.get('icon'), 'tab': tabs.get(s.get('tab'), ''), 'ranks': {}, 'levels': {}, 'hidden': {}}
        for r in s['ranks']:
            if which == 'before':
                if r['status'] == 'new': continue
                tip, lvl = r['before'] or r['after'], r['beforeLevel'] if r['before'] else r['afterLevel']
                e['hidden'][r['rank']] = {l for l in r['notShown'] if HIDDEN_KEEP.match(l)}
            else:
                if r['status'] == 'removed' or not r['after']: continue
                tip, lvl = r['after'], r['afterLevel']
            e['ranks'][r['rank']] = tip; e['levels'][r['rank']] = lvl
        if e['ranks']: out[s['key']] = e
    return out

def word_diff(old, new):
    """Mark what a rewording added and removed, as Wowhead does: {*added*} in the new text, {~removed~} in the old
    one. None when the two have too little in common for marks to help (a rewrite)."""
    tok = lambda s: re.findall(r'\d+(?:\.\d+)+|\w+|\s+|[^\w\s]', s)   # "3.0" is one word, not "3", "." and "0"
    a, b = tok(old), tok(new)
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if sm.ratio() < 0.5: return None
    def mark(toks, spans, l, r):
        out, pos = [], 0
        for i, j in spans:
            while i < j and toks[i].isspace(): i += 1           # keep spaces outside the mark
            k = j
            while k > i and toks[k - 1].isspace(): k -= 1
            if k == i: continue
            out.append(''.join(toks[pos:i]) + l + ''.join(toks[i:k]) + r); pos = k
        out.append(''.join(toks[pos:]))
        return re.sub(re.escape(r) + r'(\s+)' + re.escape(l), r'\1', ''.join(out))   # one mark per run of words
    ops = sm.get_opcodes()
    return (mark(a, [(i1, i2) for t, i1, i2, j1, j2 in ops if t in ('replace', 'delete')], '{~', '~}'),
            mark(b, [(j1, j2) for t, i1, i2, j1, j2 in ops if t in ('replace', 'insert')], '{*', '*}'))

def rank_change(pt, nt):
    """One rank's tooltip, old -> new: (notes, verdicts, previous text or None, ' · reworded' / ' · reworked' / '')"""
    notes, verdicts, was, tag = [], set(), None, ''
    if pt['name'] != nt['name']: notes.append(f"Renamed from {pt['name']}."); verdicts.add('other')
    po, no = plain(pt['text']), plain(nt['text'])
    if po != no:
        tc = text_change(po, no)
        if tc: notes.append(tc[0]); verdicts |= tc[1]
        else:
            same_numbers = sorted(map(float, NUM.findall(po))) == sorted(map(float, NUM.findall(no)))
            tag = ' · reworded' if same_numbers else ' · reworked'
            was, now_ = word_diff(po, no) or (po, no)
            notes.append(now_); verdicts.add('other')
    for field, label in (('cost', 'cost'), ('cast', 'cast time'), ('cooldown', 'cooldown'), ('range', 'range')):
        rc = row_change(label, pt.get(field), nt.get(field))
        if rc: notes.append(rc[0]); verdicts |= rc[1]
    return notes, verdicts, was, tag

def diff(kind, prev, nxt, hidden_prev, hidden_next):
    """Entries for one class's talents or spells between two builds' snapshots. hidden_* are the not-in-tooltip
    lines Wowhead lists when comparing the latest build with each of the two builds: the lines that only appear for
    the older one changed in between. A spell with ranks gets a 7th field, [[rank, text, previous text], ...] for every
    rank that changed, highest first; the entry itself shows the highest."""
    talent = kind == 'talents'
    out = []
    for key, n in nxt.items():
        top = max(n['ranks']); nt = n['ranks'][top]
        where = f"{n['tab']} talent" if talent else 'Spell'
        p = prev.get(key)
        if not p:
            out.append(['other', nt['name'], n['icon'], where + ' · new', ('New talent: ' if talent else 'New spell: ') + plain(nt['text'])])
            continue
        extra, xv = [], set()   # notes about the whole talent or spell, shown with every rank
        if len(p['ranks']) != len(n['ranks']):
            extra.append(f"Now has {len(n['ranks'])} ranks (was {len(p['ranks'])})."); xv.add('other')
        pl, nl = p['levels'].get(min(p['ranks'])), n['levels'].get(min(n['ranks']))
        if not talent and pl and nl and pl != nl:
            extra.append(f"Now learned at level {{{'+' if nl < pl else '-'}{nl}}} (was {pl})."); xv.add('good' if nl < pl else 'bad')
        for line in sorted(hidden_prev.get(key, set()) - hidden_next.get(key, set())):
            extra.append(line.rstrip('.') + '.'); xv.add('other')
        if talent and len(p['ranks']) != len(n['ranks']): pairs = [(top, p['ranks'][max(p['ranks'])], nt)]   # top rank to top rank
        else:   # every rank both builds have, highest first (Improved Slam, Oct 1: only rank 1 changed)
            common = sorted(set(p['ranks']) & set(n['ranks']), reverse=True)
            if not common: continue
            pairs = [(r, p['ranks'][r], n['ranks'][r]) for r in common]
        ranks = []
        for r, a, b in pairs:
            notes, v, was, tag = rank_change(a, b)
            if notes: ranks.append((r, notes, v, was, tag, b))
        if not ranks and not extra: continue
        if not ranks: ranks = [(pairs[0][0], [], set(), None, '', pairs[0][2])]   # only a hidden change: show the top rank
        # ranks that got better and ranks that got worse become separate entries (Fireball: higher ranks buffed,
        # low ranks nerfed shows under both Buffs and Nerfs); the whole-spell notes go with each
        groups = {}
        for rk in ranks: groups.setdefault(kind_of(rk[2]), []).append(rk)
        for k, group in groups.items():
            r, notes, v, was, tag, b = group[0]
            entry = [kind_of(v | xv) if len(groups) == 1 else k, b['name'], n['icon'], where + tag, join(notes + extra), was or '']
            if len(n['ranks']) > 1 and not (talent and len(p['ranks']) != len(n['ranks'])):
                entry.append([[rr, join(nn + extra), ww or ''] for rr, nn, vv, ww, tt, bb in group])
            elif not was: entry.pop()
            out.append(entry)
    for key, p in prev.items():
        if key not in nxt:
            pt = p['ranks'][max(p['ranks'])]
            out.append(['other', pt['name'], p['icon'], (f"{p['tab']} talent" if talent else 'Spell') + ' · removed',
                        'Removed from the talent tree.' if talent else 'Removed from the spellbook.', plain(pt['text'])])
    return out

LEFTOVER = re.compile(r'[\[\]*$]|\?(?! )|(?<![\w.])\? ')   # formula or placeholder text Wowhead didn't work out
# a formula in Wowhead's raw text that plain() worked out ("(3 /- 3 * 6)", Vindication, Oct 16): its numbers come from
# Wowhead's export, not the tooltip, so a big jump there is more likely a data error than a balance change
RAW_FORMULA = re.compile(r'\([^()]*\d[^()]*[*/][^()]*\)')
def from_formula(*texts): return any(RAW_FORMULA.search(clean_html(re.sub(r'<!--.*?-->', '', t or ''))) for t in texts)

def nums(s): return [float(x) for x in NUM.findall(s)]

def sanity(kind, prev, nxt):
    """The "Needs a look" scan: changes between two builds that look implausible rather than like balance changes, so a
    person checks them in game before they go live (Thick Hide, Oct 8: "3 armor per level" became 180 at every rank, a
    Wowhead data error). Only flags, never changes anything. -> [(name, reason), ...]"""
    flags = []
    for key, n in nxt.items():
        p = prev.get(key)
        if not p: continue
        name = n['ranks'][max(n['ranks'])]['name']
        common = sorted(set(p['ranks']) & set(n['ranks']))
        if kind == 'talents' and len(p['ranks']) != len(n['ranks']):
            flags.append((name, f"now has {len(n['ranks'])} ranks (was {len(p['ranks'])})"))
        # every rank now says the same number where the ranks used to differ (1 / 2 / 3 -> 180 / 180 / 180)
        if len(common) > 1:
            po = [plain(p['ranks'][r]['text']) for r in common]; no = [plain(n['ranks'][r]['text']) for r in common]
            if len({NUM.sub('#', x) for x in po + no}) == 1:
                pv, nv = [nums(x) for x in po], [nums(x) for x in no]
                for i in range(len(nv[0])):
                    was, now_ = [v[i] for v in pv], [v[i] for v in nv]
                    if len(set(was)) > 1 and len(set(now_)) == 1:
                        f = lambda x: f'{x:g}'
                        flags.append((name, f"every rank now says {f(now_[0])} where the ranks said {' / '.join(map(f, was))}")); break
        for r in common[::-1]:   # the highest rank that changed is enough to show
            a, b = p['ranks'][r], n['ranks'][r]
            ta, tb = plain(a['text']), plain(b['text'])
            reasons = []
            # a number that grew or shrank 3x or more, in the text or in the cost / cast time / cooldown / range
            pairs = list(zip(nums(ta), nums(tb))) if NUM.sub('#', ta) == NUM.sub('#', tb) else []
            for field in ('cost', 'cast', 'cooldown', 'range'):
                fa, fb = a.get(field) or '', b.get(field) or ''
                if NUM.sub('#', fa) == NUM.sub('#', fb): pairs += list(zip(nums(fa), nums(fb)))
            for o, v in pairs:
                if o == v: continue
                if v == 0 and o: reasons.append(f'{o:g} became 0'); break
                if o == 0: reasons.append(f'0 became {v:g}'); break
                if max(o, v) / min(o, v) >= 3: reasons.append(f'{o:g} became {v:g} ({max(o, v) / min(o, v):.0f}x {"bigger" if v > o else "smaller"})'
                                                               + (", worked out from a formula in Wowhead's data (compare Wowhead's tooltip)" if from_formula(a['text'], b['text']) else '')); break
            if LEFTOVER.search(tb) and not LEFTOVER.search(ta): reasons.append('the new text has a formula or placeholder left in it')
            notes, v, was, tag = rank_change(a, b)
            if {'good', 'bad'} <= v: reasons.append('some numbers got better and others worse')
            if reasons:
                flags.append((name, ('' if kind == 'talents' or len(n['ranks']) < 2 else f'rank {r}: ') + '; '.join(reasons))); break
    for key, p in prev.items():
        if key not in nxt:
            flags.append((p['ranks'][max(p['ranks'])]['name'], 'removed' + (' from the talent tree' if kind == 'talents' else ' from the spellbook')))
    return flags

FLAGS = {}   # class -> [(name, reason)] for the update being worked out

def update(prev_vs, next_vs):
    """Every class's changes from build prev_vs to build next_vs (None = the latest build)."""
    classes = {}
    FLAGS.clear()
    for c in CLASSES:
        ch = []
        for kind in KINDS:
            a = page(kind, c, prev_vs)
            b = page(kind, c, next_vs) if next_vs else None
            prev = snapshot(a, 'before')
            nxt = snapshot(b, 'before') if b else snapshot(a, 'after')
            top = lambda e: e['hidden'].get(max(e['ranks']), set())   # the top rank's, so each line shows once
            hp = {k: top(e) for k, e in prev.items()}
            hn = {k: top(e) for k, e in nxt.items()} if b else {}
            ch += diff(kind, prev, nxt, hp, hn)
            for name, why in sanity(kind, prev, nxt):   # one line per talent or spell, its reasons joined
                fl = FLAGS.setdefault(c, []); i = next((j for j, (nm, _) in enumerate(fl) if nm == name), None)
                if i is None: fl.append((name, why))
                elif why not in fl[i][1]: fl[i] = (name, fl[i][1] + '; ' + why)
        talents = {e[1] for e in ch if 'talent' in e[3]}
        ch = [e for e in ch if 'talent' in e[3] or e[1] not in talents]   # a talent's spell (Bloodthirst) shows once
        if ch: classes[c] = ch
    return classes

def builds():
    """(live build label, [older builds oldest first as (build, label, release date)]) from Wowhead."""
    cmp = page('talents', 'warrior', None)['compare']
    old = sorted((b['build'], b['label'], datetime.datetime.fromtimestamp(b['released'], datetime.timezone.utc).strftime('%Y-%m-%d'))
                 for b in cmp['builds'])
    return cmp['live'], old

def beta_build():
    """(version, build) of the WoW Forever beta from Blizzard's patch server, e.g. ('1.60.1', '70338').
    The beta is listed as wow_classic_beta; at launch the live game will likely be a different product."""
    txt = tm.get('http://us.patch.battle.net:1119/wow_classic_beta/versions')
    row = next(l for l in txt.splitlines() if l.startswith('us|')).split('|')
    name = row[5]   # VersionsName, e.g. 1.60.1.70338
    return name.rsplit('.', 1)[0], name.rsplit('.', 1)[1]

def apply_fixes(log):
    """Hand corrections from changes_fixes.json, applied every run so a rebuild keeps them: an entry Wowhead's data got
    wrong (checked in game) is dropped, or its kind / text replaced, or a sentence appended to it and its ranks
    ("append": a cooldown change Wowhead's change page leaves out); "add" is a whole entry Wowhead's change pages
    don't have (Sonic Blast, Oct 15: the patch notes' nerf, missing from the Hunter page). Each fix names the
    update's build, the class and the talent or spell, and says why."""
    try: fixes = now('changes_fixes.json')['fixes']
    except FileNotFoundError: return
    for fx in fixes:
        for u in log['updates']:
            if u['build'] != fx['build']: continue
            if 'add' in fx:
                ch = u['classes'].setdefault(fx['class'], [])
                if not any(e[1] == fx['name'] for e in ch): ch.append(fx['add'])
                continue
            if fx['class'] not in u['classes']: continue
            ch = u['classes'][fx['class']]
            for e in [e for e in ch if e[1] == fx['name']]:
                if fx.get('drop'): ch.remove(e); continue
                if 'kind' in fx: e[0] = fx['kind']
                if 'text' in fx: e[4] = fx['text']
                if 'append' in fx and fx['append'] not in e[4]:
                    e[4] += ' ' + fx['append']
                    for row in (e[6] if len(e) > 6 else []): row[1] += ' ' + fx['append']
            if not ch: del u['classes'][fx['class']]

def needs_a_look(build):
    """The scan's flags for one update, as the top of the pull request report (Markdown); '' when nothing looks off.
    A flag already handled in changes_fixes.json says so."""
    try: fixed = {(f['build'], f['class'], f['name']) for f in now('changes_fixes.json')['fixes']}
    except FileNotFoundError: fixed = set()
    rows = [f"- **{c.capitalize()}: {name}**: {why}" + (' (already corrected in changes_fixes.json)' if (build, c, name) in fixed else '')
            for c, fl in FLAGS.items() for name, why in fl]
    if not rows: return ''
    return ('### Needs a look\n'
            "These changes look unusual for a balance change: check them in game or on Wowhead before merging. If one is "
            "wrong, it can be corrected in tc/changes_fixes.json (and, for a talent's text, TEXT_FIXES in tc/build.py).\n\n"
            + '\n'.join(rows) + '\n')

def show(u):
    print(f"== {u['date']} build {u['build']}")
    for c, ch in u['classes'].items():
        for k, name, icon, where, text, *was in ch: print(f'{c:8} {k:5} {name} [{where}]: {text}')
    print(sum(len(v) for v in u['classes'].values()), 'changes')

def main():
    dry, rebuild = '--dry' in sys.argv, '--rebuild' in sys.argv
    live_date = next((a.split('=', 1)[1] for a in sys.argv if a.startswith('--date=')), None)   # Wowhead doesn't date the latest build
    ver = now('version.json')
    try:
        v, b = beta_build()
        if b != ver.get('build'): ver['date'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')   # first seen today
        ver.update(version=v, build=b)
    except Exception as e:
        print('could not read the beta build from Blizzard:', e)
    if not dry:
        with open('version.json', 'w', encoding='utf-8', newline='\n') as f: json.dump(ver, f, indent=1); f.write('\n')
    log = now('changes.json')
    live, old = builds()
    lv, lb = live.rsplit('.', 1)
    today = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d')
    known = {u['build']: u for u in log['updates']}
    if rebuild:
        # the oldest build Wowhead has is the starting point; every later build is one update
        steps = [(old[i][0], old[i + 1]) for i in range(len(old) - 1)] + [(old[-1][0], None)]
        updates = []
        for prev_vs, nb in steps:
            build, label, date = (nb[0], nb[1], nb[2]) if nb else (int(lb), live, live_date or (known.get(lb) or {}).get('date', today))
            updates.insert(0, {'date': date, 'version': label.rsplit('.', 1)[0], 'build': str(build),
                               'classes': update(prev_vs, nb[0] if nb else None)})
            show(updates[0]); print(needs_a_look(str(build)) or 'Needs a look: nothing')
        log['updates'] = updates
    else:
        if lb in known: print(f'build {lb} is already recorded'); return
        recorded = [int(u['build']) for u in log['updates'] if u['build'].isdigit()]
        avail = [b for b, _, _ in old]
        prev_vs = max([b for b in recorded if b in avail] or [max(avail)])   # the newest build we recorded that Wowhead can still compare with
        u = {'date': today, 'version': lv, 'build': lb, 'classes': update(prev_vs, None)}
        show(u)
        look = needs_a_look(lb); print(look or 'Needs a look: nothing')
        if not dry:   # the workflow puts this at the top of the pull request report
            with open('../needs-a-look.md', 'w', encoding='utf-8', newline='\n') as f: f.write(look)
        if not u['classes']: return
        log['updates'].insert(0, u)
    apply_fixes(log)
    if dry: return
    with open('changes.json', 'w', encoding='utf-8', newline='\n') as f: json.dump(log, f, ensure_ascii=False, indent=1); f.write('\n')

if __name__ == '__main__':
    main()
