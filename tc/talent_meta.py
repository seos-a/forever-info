"""Fetch cast time / cooldown / cost / range for every talent from Wowhead (WoW Forever)
and write talent_meta.json, which build.py merges into the talent tooltips.

Run from inside tc/:  py talent_meta.py
Output: {class: {talent name: [rows for rank 1, rows for rank 2, ...]}}
where rows are [left, right] pairs, e.g. [["Instant", "5 min cooldown"]].
Passive talents get no entry.
"""
import json, re, time, urllib.request

BASE = 'https://nether.wowhead.com/forever'
CLASSES = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior']

def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    for attempt in range(4):
        try:
            return urllib.request.urlopen(req, timeout=30).read().decode('utf-8')
        except Exception:
            if attempt == 3: raise
            time.sleep(2 * (attempt + 1))

def talent_feed():
    # the data URL carries version parameters, so read it off the talent calculator page
    page = get('https://www.wowhead.com/forever/talent-calc/rogue')
    url = re.search(r'https://nether\.wowhead\.com/forever/data/talents-classic\?[^"\']+', page).group(0)
    js = get(url.replace('&amp;', '&'))
    return json.JSONDecoder().raw_decode(js[js.index(',{') + 1:])[0]

def strip(html):
    html = re.sub(r'<!--.*?-->', '', html)
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html)).strip()

def rows(spell_id):
    """The left/right header rows of a spell tooltip (cost/range, cast time/cooldown)."""
    tip = json.loads(get(f'{BASE}/tooltip/spell/{spell_id}'))['tooltip']
    out = []
    for table in re.findall(r'<table width="100%">(.*?)</table>', tip, re.S):
        if 'whtt-name' in table: continue  # name / level header, not a spell row
        tr = re.search(r'<tr>(.*?)</tr>', table, re.S)
        if not tr: continue
        tr = tr.group(1)
        cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, re.S)
        cells = [strip(c) for c in cells] + ['', '']
        if cells[0] or cells[1]: out.append(cells[:2])
    return out

def main():
    feed = talent_feed()
    tree_class = {}
    for tid, tr in feed['trees'].items():
        cls = next((c for c in CLASSES if tr['description'].lower().startswith(c)), None)
        if cls: tree_class[tid] = cls
    meta = {c: {} for c in CLASSES}
    n = 0
    for tid, talents in feed['talents'].items():
        cls = tree_class.get(tid)
        if not cls: continue
        for t in talents.values():
            ranks = t['ranks']
            first = rows(ranks[0]); n += 1
            if not first: continue  # passive
            per_rank, cache = [], {ranks[0]: first}
            for sid in ranks:
                if sid not in cache: cache[sid] = rows(sid); n += 1
                per_rank.append(cache[sid])
            meta[cls][t['name']] = per_rank
            print(cls, t['name'], per_rank[-1])
    json.dump(meta, open('talent_meta.json', 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1, sort_keys=True)
    print('tooltips fetched:', n, 'active talents:', sum(len(v) for v in meta.values()))

if __name__ == '__main__':
    main()
