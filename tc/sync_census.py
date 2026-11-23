"""Refresh the Population Census page's numbers (census.json) from Raider.IO's WoW Forever census, by hand.

Step 1, in your browser: open https://forever.raider.io/population, open the console (F12 > Console), paste
census_snippet.js and press Enter. It asks the page's own data address for each region and ruleset, about a second
apart, at all levels and at level 60, each also for Alliance and Horde alone, and downloads census-raiderio.json.
Step 2, from inside tc/:  py sync_census.py              (reads Downloads/census-raiderio.json)
                          py sync_census.py <file>       (another place)
                          py sync_census.py --dry        (report only, write nothing)
then rebuild (py build.py, cp ../web/*.html ..).

Nothing here goes on the internet: Raider.IO's site refuses scripts (HTTP 403), so the fetching is done by you, in the
browser, as their own page does it. Nothing runs on a schedule.

census.json gets each region|ruleset's race x class counts (`factionBalance`), `counts60` the same at level 60, `prev` the class and race counts at the end of the week before last (Raider.IO's weekly history, at least 7 days old, for the page's
rising / falling arrows: per level (all, 60) and key, {week, classes, races, alliance, horde}; the last two are the
classes within each faction), `levels` from `classLevels` (per key
[characters, at level 60, median level: the level by which half are counted]) and the snapshot's date (Raider.IO's
`generatedAt`, US Eastern). A key with no characters (Korea and Taiwan have no Roleplay realms) is left out.
"""
import json, os, sys
from datetime import datetime, timedelta, timezone

REGIONS = ['all', 'us', 'eu', 'kr', 'tw']
RULESETS = {'all': None, 'normal': 'Normal', 'pvp': 'PvP', 'rp': 'Roleplay', 'pvp-rp': 'Roleplay PvP'}
# Raider.IO's ids, in census.json's race and class order
RACE_IDS = {'Human': 1, 'Dwarf': 3, 'Night Elf': 4, 'Gnome': 7, 'High Order Skyborne': 95,
            'Orc': 2, 'Undead': 5, 'Tauren': 6, 'Troll': 8, 'Windshaper Skyborne': 96}
CLASS_IDS = {'Warrior': 1, 'Paladin': 2, 'Hunter': 3, 'Rogue': 4, 'Priest': 5, 'Shaman': 7, 'Mage': 8, 'Warlock': 9, 'Druid': 11}


def shape(stats, races, classes, check=True):
    """the race x class counts and [characters, at level 60, median level] for one region and ruleset"""
    ri = {RACE_IDS[r]: i for i, r in enumerate(races)}
    ci = {CLASS_IDS[c]: j for j, c in enumerate(classes)}
    counts = [[0] * len(races) for _ in classes]
    for x in stats['factionBalance']:
        if x['raceId'] not in ri or x['classId'] not in ci:
            sys.exit(f"Unknown race or class id {x['raceId']} / {x['classId']}: add it to RACE_IDS / CLASS_IDS.")
        counts[ci[x['classId']]][ri[x['raceId']]] += x['characters']
    per_level = [0] * 60
    for c in stats['classLevels']:
        for k, n in enumerate(c['levels'][:60]):
            per_level[k] += n
    total = sum(per_level)
    median, seen = 0, 0
    for k, n in enumerate(per_level):
        seen += n
        if total and seen * 2 >= total:
            median = k + 1
            break
    if check and total != sum(map(sum, counts)):
        sys.exit(f'Counts ({sum(map(sum, counts))}) and levels ({total}) disagree: has the data changed shape?')
    return counts, [total, per_level[59], median]


def last_week(weeks, key, ids):
    """the counts, in census.json's order, from the week before last in a classWeeks / raceWeeks list.
    Each entry is dated by the day its week starts but holds the running total at the end of that week, and the last
    entry is the live total: weeks[-2] closed as recently as yesterday (on the first day of a week the arrows would
    compare against a day ago), weeks[-3] 7 to 13 days ago, so the arrows always cover at least a full week. With only
    two weeks of history, weeks[-2]."""
    if len(weeks or []) < 2:
        return None
    w = weeks[-3] if len(weeks) >= 3 else weeks[-2]
    n = {x[key]: x['characters'] for x in w['classes' if key == 'classId' else 'races']}
    return w['week'], [n.get(i, 0) for i in ids]


def write(d, path='census.json'):
    """census.json as it was laid out by hand: one line per key"""
    J = lambda v: json.dumps(v, ensure_ascii=False, separators=(', ', ': '))
    lines = ['{', f' "_about": {J(d["_about"])},', f' "date": {J(d["date"])},', ' "levels": {']
    lines += [f'  {J(k)}: {J(v)},' for k, v in d['levels'].items()]
    lines[-1] = lines[-1][:-1]
    lines += [' },', f' "source": {J(d["source"])},', f' "races": {J(d["races"])},', f' "classes": {J(d["classes"])},', ' "counts": {']
    lines += [f'  {J(k)}: {J(v)},' for k, v in d['counts'].items()]
    lines[-1] = lines[-1][:-1]
    lines += [' },', ' "counts60": {']
    lines += [f'  {J(k)}: {J(v)},' for k, v in d['counts60'].items()]
    lines[-1] = lines[-1][:-1]
    lines += [' },', ' "prev": {']
    for lvl, block in d['prev'].items():
        lines += [f'  {J(lvl)}: {{']
        lines += [f'   {J(k)}: {J(v)},' for k, v in block.items()]
        lines[-1] = lines[-1][:-1]
        lines += ['  },']
    lines[-1] = lines[-1][:-1]
    lines += [' }', '}']
    open(path, 'w', encoding='utf-8', newline='\n').write('\n'.join(lines) + '\n')


def main():
    dry = '--dry' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    path = args[0] if args else os.path.join(os.path.expanduser('~'), 'Downloads', 'census-raiderio.json')
    if not os.path.exists(path):
        sys.exit(f'{path} not found: run census_snippet.js on forever.raider.io/population first (see the top of this file).')
    raw = json.load(open(path, encoding='utf-8'))
    # Raider.IO publishes hourly (at :15), but each address is cached on its own (some for over an hour), so one run
    # often mixes two snapshots: fine when they are close (an hour moves shares by hundredths of a point)
    when_all = sorted({v.get('generatedAt') for v in raw.values()})
    t = [datetime.fromisoformat(w.replace('Z', '+00:00')) for w in when_all]
    if t[-1] - t[0] > timedelta(hours=2):
        sys.exit(f'Raider.IO snapshots more than 2 hours apart ({when_all[0]} .. {when_all[-1]}): run the snippet again.')
    d = json.load(open('census.json', encoding='utf-8'))
    counts, counts60, levels, stamps = {}, {}, {}, set()
    prev = {'all': {}, '60': {}}
    cls_ids, race_ids = [CLASS_IDS[c] for c in d['classes']], [RACE_IDS[r] for r in d['races']]
    for region in REGIONS:
        for slug, name in RULESETS.items():
            stats, s60 = raw.get(f'{region}|{slug}|all'), raw.get(f'{region}|{slug}|60')
            if not stats or not s60:
                sys.exit(f'{path} has no {region} {slug} (all levels and level 60): run the latest census_snippet.js again.')
            stamps.update((stats.get('generatedAt'), s60.get('generatedAt')))
            c, lv = shape(stats, d['races'], d['classes'])
            if lv[0]:
                key = region if name is None else f'{region}|{name}'
                counts[key], levels[key] = c, lv
                # at level 60 Raider.IO still sends every level's curve: check the counts against that answer's own
                # level-60 slice
                counts60[key], lv60 = shape(s60, d['races'], d['classes'], check=False)
                if sum(map(sum, counts60[key])) != lv60[1]:
                    sys.exit(f'{key}: level 60 counts ({sum(map(sum, counts60[key]))}) and level 60 total ({lv60[1]}) disagree: has the data changed shape?')
                # last week, for the rising / falling arrows
                for lvl, st in (('all', stats), ('60', s60)):
                    c_ = last_week(st.get('classWeeks'), 'classId', cls_ids)
                    r_ = last_week(st.get('raceWeeks'), 'raceId', race_ids)
                    fa = [last_week((raw.get(f'{region}|{slug}|{lvl}|{f}') or {}).get('classWeeks'), 'classId', cls_ids) for f in ('alliance', 'horde')]
                    if c_ and r_ and all(fa):
                        prev[lvl][key] = {'week': c_[0], 'classes': c_[1], 'races': r_[1], 'alliance': fa[0][1], 'horde': fa[1][1]}
    stamp = max(stamps)   # the newest snapshot in the run
    # their snapshot time, as a US Eastern date (the site's other dates are; -5 h, close enough either side of DST)
    when = datetime.fromisoformat(stamp.replace('Z', '+00:00')).astimezone(timezone(timedelta(hours=-5)))
    old_total = d['levels'].get('all', [0])[0]
    print(f"Raider.IO snapshot {stamp}: {levels['all'][0]:,} characters, {sum(map(sum, counts60['all'])):,} at level 60 (was {old_total:,} on {d['date']}), {len(counts)} region/ruleset keys")
    for k in d['counts']:
        if k not in counts:
            print(f'  {k}: no longer has characters, dropped')
    for k in counts:
        if k not in d['counts']:
            print(f'  {k}: new')
    if dry:
        print('--dry: census.json not written')
        return
    d.update(date=when.strftime('%Y-%m-%d'), counts=counts, counts60=counts60, prev=prev, levels=levels)
    write(d)
    print('census.json written. Rebuild: py build.py, then copy /Y ..\\web\\*.html ..  (Git Bash: cp ../web/*.html ..)')


if __name__ == '__main__':
    main()
