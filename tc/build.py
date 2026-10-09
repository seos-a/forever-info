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

def clean_html(desc):
    """Wowhead occasionally leaves HTML in a description (Weaponmaster): a double <br /> starts a new line,
    a single one is just a line wrap, and tags such as <span> are dropped."""
    desc = re.sub(r'\s*(<br\s*/?>\s*){2,}', '\n', desc)
    desc = re.sub(r'\s*<br\s*/?>\s*', ' ', desc)
    desc = re.sub(r'<[^>]+>', '', desc)
    return re.sub(r'[ \t]{2,}', ' ', desc)

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
        for r, c, mx, tname, icon, desc, ranks, pre in tr['t']:
            desc = fix_desc(clean_html(desc), ranks).strip()
            # values Wowhead doesn't list yet: show "?" instead of a misleading 0
            desc = re.sub(r'(?<![\d.])0 (sec|Mana)', r'? \1', desc)
            desc = desc.replace('(0 /- 3 * - 204)', '?')
            if pre and pre[0] not in names:
                problems.append((key, tr['n'], tname, pre))
                pre = None
            pr = OVERRIDES.get((key, tname)) or per_rank(desc, ranks, mx)
            talents.append([r, c, mx, tname, icon, pr[0] if pr else desc, pre, pr[1] if pr else None])
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
blob = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
for src, dst in (('template.html', '../Forever-Talents.html'), ('template2.html', '../Forever-Talents-Classic-Style.html')):
    html = open(src, encoding='utf-8').read().replace('/*DATA*/', blob).replace('/*BG*/', BG).replace('/*RACIALS*/', open('racials.json', encoding='utf-8').read()).replace('/*SPELLBOOK*/', json.dumps(SBK, ensure_ascii=False, separators=(',',':')))
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
web=web.replace('</head>',GC+'</head>',1)
assert 'zamimg' not in web, _re.findall(r'.{40}zamimg.{40}',web)[:3]
_os.makedirs('../web',exist_ok=True)
open('../web/index.html', 'w', encoding='utf-8', newline='\n').write(web)
A=_json.load(open('assets.json', encoding='utf-8'))
models=sorted(set(_re.findall(r'images/models/(\d+)\.png',web)))
lines=[f"https://wow.zamimg.com/images/wow/icons/large/{i}.jpg|images/icons/{i}.jpg" for i in A['icons']]
lines+=[f"https://wow.zamimg.com/images/wow/talents/backgrounds/classicplus/{s}.jpg|images/backgrounds/{s}.jpg" for s in A['specs']]
lines+=[f"https://wow.zamimg.com/modelviewer/classic/webthumbs/npc/{int(m)&255}/{m}.png|images/models/{m}.png" for m in models]
open('../web/image-list.txt', 'w', encoding='utf-8', newline='\n').write("\n".join(lines)+"\n")
print('web', len(lines))
