import json, re
from ranks import per_rank

CLASSES = [
    ("druid", "Druid", "#FF7C0A"),
    ("hunter", "Hunter", "#AAD372"),
    ("mage", "Mage", "#3FC7EB"),
    ("paladin", "Paladin", "#F48CBA"),
    ("priest", "Priest", "#FFFFFF"),
    ("rogue", "Rogue", "#FFF468"),
    ("shaman", "Shaman", "#0070DD"),
    ("warlock", "Warlock", "#8788EE"),
    ("warrior", "Warrior", "#C69B6D"),
]

def fmt_num(v):
    return str(int(v)) if float(v).is_integer() else str(v)

from textfix import clean_html, tidy_formula

def fix_desc(desc, ranks):
    """Wowhead sometimes leaves a value as 0 when it lives in another rank field.
    Fill those placeholders with the talent's max-rank value."""
    if not ranks:
        return desc
    top = max(ranks, key=abs)
    a = abs(top)
    # "0%" placeholders -> max rank percent (only for plausible percentages)
    if a <= 100:
        desc = re.sub(r'(?<![\d.])0%', f'{fmt_num(a)}%', desc)
    # "0 sec" placeholders -> max rank time when ranks look like milliseconds
    if a >= 100 and all(abs(r) % 100 == 0 or abs(r) % 10 == 0 for r in ranks):
        secs = a / 1000
        s = f'{secs:g}'
        desc = re.sub(r'(?<![\d.])0 sec', f'{s} sec', desc)
    return desc

# Hand corrections confirmed in game: (class, talent) -> (description template, per-rank values)
OVERRIDES = {
    ('rogue', 'Improved Gouge'): ('Increases the duration of your Gouge ability by {v} sec.', ['0.5', '1', '1.5']),
}

# Wowhead tooltip errors in the per-rank texts, checked in game: (class, talent) -> (pattern, the right text for rank k).
# Each applies only while every rank shows the same wrong number, so it stops by itself once Wowhead's data is fixed.
TEXT_FIXES = {
    # Oct 8 (1.60.1.70291): Wowhead shows "180 additional base Armor per level" at every rank (3 x level 60?);
    # in game it is 1 / 2 / 3 per level
    ('druid', 'Thick Hide'): (r'gain (\d+) additional base Armor per level', lambda k: f'gain {k} additional base Armor per level'),
}

import os
TMETA = json.load(open('talent_meta.json', encoding='utf-8')) if os.path.exists('talent_meta.json') else {}

data = {}
problems = []
for key, name, color in CLASSES:
    trees = json.load(open(f'{key}.json', encoding='utf-8'))
    out_trees = []
    for tr in trees:
        names = {t[3] for t in tr['t']}
        talents = []
        for r, c, mx, tname, icon, desc, ranks, pre, *rest in tr['t']:
            # per-rank texts from sync_talents.py: shown as they are, so every changing number is right at every rank
            texts = [tidy_formula(clean_html(x)).strip() for x in rest[0]] if rest and rest[0] else None
            fix = TEXT_FIXES.get((key, tname))
            if fix and texts and len({m.group(1) for x in texts for m in [re.search(fix[0], x)] if m}) == 1 and all(re.search(fix[0], x) for x in texts) and len(texts) > 1:
                texts = [re.sub(fix[0], fix[1](k + 1), x) for k, x in enumerate(texts)]
            desc = fix_desc(tidy_formula(clean_html(desc)), ranks).strip()
            if fix and texts and re.search(fix[0], texts[-1]) and re.search(fix[0], texts[-1]).group(0) == fix[1](mx):
                desc = re.sub(fix[0], fix[1](mx), desc)   # a corrected talent's fallback text too, at the top rank
            # values Wowhead doesn't list yet: show "?" instead of a misleading 0
            desc = re.sub(r'(?<![\d.])0 (sec|Mana)', r'? \1', desc)
            desc = desc.replace('(0 /- 3 * - 204)', '?')
            if pre and pre[0] not in names:
                problems.append((key, tr['n'], tname, pre))
                pre = None
            pr = OVERRIDES.get((key, tname)) or per_rank(desc, ranks, mx)
            talents.append([r, c, mx, tname, icon, pr[0] if pr else desc, pre, pr[1] if pr else None]
                           + ([None, texts] if texts and len(texts) == mx else []))
            cells = [(t[0], t[1]) for t in tr['t']]
        if len(set(cells)) != len(cells):
            problems.append((key, tr['n'], 'duplicate cell'))
        out_trees.append({'n': tr['n'], 's': tr['s'], 'i': tr['i'], 't': talents})
    data[key] = {'name': name, 'color': color, 'trees': out_trees}
    # cost / range / cast time / cooldown rows per rank for active talents (from talent_meta.py)
    if TMETA:
        tnames = {t[3] for tr in out_trees for t in tr['t']}
        tm = TMETA.get(key, {})
        problems += [(key, n, 'no talent for meta') for n in tm if n not in tnames]
        data[key]['tm'] = {n: [rk[:2] for rk in r] for n, r in tm.items() if n in tnames}

# Legacy tree (account-wide): gates are points spent in that tree, 16 points total
L = json.load(open('legacy_raw.json', encoding='utf-8'))
ids = {}
for tr in L['trees']:
    for n in tr['nodes']: ids[n[0]] = n[1]
ltrees = []
for tr in L['trees']:
    t = []
    for nid, name, x, y, icon, mx, gate, nyi, texts in tr['nodes']:
        pre = None
        if nid in L['need']:
            src, k = L['need'][nid]; pre = [ids[src], k]
        t.append([(y - 14) // 92, (x - 14) // 92, mx, name, icon, texts[-1], pre, None, gate, texts, nyi])
    ltrees.append({'n': tr['name'], 's': 0, 'i': tr['icon'], 'd': tr['blurb'], 't': t})
data['legacy'] = {'name': 'Legacy', 'color': '#f2c14e', 'legacy': True, 'max': 16, 'trees': ltrees}
print('problems:', problems)
import os, base64
BG = ''
if os.path.exists('bg.jpg'):
    BG = 'data:image/jpeg;base64,' + base64.b64encode(open('bg.jpg','rb').read()).decode()
from spellbook import build as _sb
SBK=_sb()
# Class Changes history and the beta version stamp (tc/changelog.py keeps both up to date)
CHG=json.load(open('changes.json', encoding='utf-8')) if os.path.exists('changes.json') else {'updates': []}
VER=json.load(open('version.json', encoding='utf-8')) if os.path.exists('version.json') else {}
blob = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
for src, dst in (('template.html', '../Forever-Talents.html'), ('template2.html', '../Forever-Talents-Classic-Style.html')):
    html = open(src, encoding='utf-8').read().replace('/*DATA*/', blob).replace('/*BG*/', BG).replace('/*RACIALS*/', open('racials.json', encoding='utf-8').read()).replace('/*SPELLBOOK*/', json.dumps(SBK, ensure_ascii=False, separators=(',',':'))).replace('/*CHANGES*/', json.dumps(CHG, ensure_ascii=False, separators=(',',':'))).replace('/*VERSION*/', json.dumps(VER))
    open(dst, 'w', encoding='utf-8', newline='\n').write(html)
print('written', len(html))

# ---- web package: images served from local folder ----
import re as _re, os as _os, json as _json
web=open('../Forever-Talents-Classic-Style.html', encoding='utf-8').read()
web=web.replace('https://wow.zamimg.com/images/wow/icons/large/','images/icons/')
web=web.replace('https://wow.zamimg.com/images/wow/talents/backgrounds/classicplus/','images/backgrounds/')
web=_re.sub(r'https://wow\.zamimg\.com/modelviewer/classic/webthumbs/npc/\d+/','images/models/',web)
web=web.replace("Icons and backgrounds load from Wowhead's image server and need an internet connection. ","")
GC="""<script>
window.goatcounter={no_onload:true};
(function(){var last=null;
function send(){var g=window.goatcounter; if(!g||!g.count) return;
  var s=decodeURIComponent(location.hash.slice(1)).split(":")[0]||"home"; if(s===last) return; last=s;
  g.count({path:"/forever-info/"+s,title:s});}
window.gcTrack=send;
var _r=history.replaceState; history.replaceState=function(){var r=_r.apply(this,arguments); setTimeout(send,0); return r;};
window.addEventListener("hashchange",send);
var t=document.createElement("script"); t.async=true; t.src="https://gc.zgo.at/count.js";
t.setAttribute("data-goatcounter","https://seos-a.goatcounter.com/count"); t.onload=send;
document.head.appendChild(t);})();
</script>
"""
# real icon files and link-preview tags: search engines and link cards (Discord, Google chat...) can't use the inline icon
SITE='https://foreverinfo.io/'
ICONV=2   # bump when the icons change: browsers (Safari especially) keep old icons until the address changes
HEAD=f"""<link rel="icon" type="image/png" sizes="32x32" href="favicon.png?v={ICONV}">
<link rel="icon" type="image/png" sizes="48x48" href="favicon-48.png?v={ICONV}">
<link rel="icon" type="image/png" sizes="96x96" href="favicon-96.png?v={ICONV}">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png?v={ICONV}">
<link rel="apple-touch-icon" href="apple-touch-icon.png?v={ICONV}">
<meta name="apple-mobile-web-app-title" content="Forever Info">
<link rel="manifest" href="site.webmanifest?v={ICONV}">
<script type="application/ld+json">{{"@context":"https://schema.org","@type":"WebSite","name":"Forever Info","url":"{SITE}"}}</script>
<link rel="canonical" href="{SITE}">
<meta property="og:site_name" content="Forever Info">
<meta property="og:type" content="website">
<meta property="og:url" content="{SITE}">
<meta property="og:title" content="Forever Info – WoW Forever Talent Calculator &amp; Class Changes">
<meta property="og:description" content="Up-to-date WoW Forever class data: talent calculator, spellbook, patch-by-patch class changes and more... without the bloat.">
<meta property="og:image" content="{SITE}images/og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:image:alt" content="The Forever Info logo">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#1a0d04">
"""
web=web.replace('</head>',HEAD+GC+'</head>',1)
# the template's inline favicon (for the offline pages) would come first; search engines need the real files above
web=_re.sub(r'<link rel="icon" type="image/png" href="data:image/png;base64,[^"]*">\n?','',web,count=1)
assert 'zamimg' not in web, _re.findall(r'.{40}zamimg.{40}',web)[:3]
# ---- 404 page (GitHub Pages shows ../404.html for any address that doesn't exist), styled like the
# Burning Crusade-era WoW site's: a parchment panel with a red title bar. It borrows the page's own textures. ----
_T=open('template2.html',encoding='utf-8').read()
_vars='\n'.join(l for l in _T.split('\n')[:60] if _re.match(r'\s*--(tex-weather|tex-paper|tex-fibre|tex-speck|tex-stain|parch-bg):',l))
P404=open('page404.html',encoding='utf-8').read().replace('/*VARS*/',_vars)
open('../404.html','w',encoding='utf-8',newline='\n').write(P404)
_os.makedirs('../web',exist_ok=True)
open('../web/index.html', 'w', encoding='utf-8', newline='\n').write(web)
A=_json.load(open('assets.json', encoding='utf-8'))
models=sorted(set(_re.findall(r'images/models/(\d+)\.png',web)))
# every icon the data uses (so a new talent, spell or tab from a beta sync gets its icon), plus the hand list in assets.json
used={tr['i'] for c in data.values() for tr in c['trees']} | {t[4] for c in data.values() for tr in c['trees'] for t in tr['t']}
used|={s[1] for k,v in SBK.items() if isinstance(v,dict) and 'spells' in v for s in v['spells']+v['general']+v.get('tabs',[])}
RAC=_json.load(open('racials.json', encoding='utf-8'))
used|={r['icon'] for r in RAC}|{t[1] for r in RAC for t in r['traits']}|{p[1] for r in RAC for p in r.get('priest',[])}
used|={e[2] for u in CHG['updates'] for ch in u['classes'].values() for e in ch}   # Class Changes icons
used|=set(_re.findall(r'images/icons/([a-z0-9_]+)\.jpg',web))   # icons named directly in the page (Quick Info buttons...)
icons=list(A['icons'])+sorted(i for i in used if i and i not in set(A['icons']))
lines=[f"https://wow.zamimg.com/images/wow/icons/large/{i}.jpg|images/icons/{i}.jpg" for i in icons]
lines+=[f"https://wow.zamimg.com/images/wow/talents/backgrounds/classicplus/{s}.jpg|images/backgrounds/{s}.jpg" for s in A['specs']]
lines+=[f"https://wow.zamimg.com/modelviewer/classic/webthumbs/npc/{int(m)&255}/{m}.png|images/models/{m}.png" for m in models]
open('../web/image-list.txt', 'w', encoding='utf-8', newline='\n').write("\n".join(lines)+"\n")
print('web', len(lines))
