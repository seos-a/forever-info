"""Builds the Population Census page (foreverinfo.io/census): who plays which race and class in WoW Forever, from
Raider.IO's census (https://forever.raider.io/population: the characters Raider.IO tracks, levels 10 to 60).

census.html is the page (markup, style, script); census.json the numbers, by region and ruleset; census_history.json
the counts over time, which history() thins into census-history.json, a file the page loads after it shows (the Over Time
graph). It is framed like the
Sims page: experiment.CSS (colours, fonts, the background along the top, the Home and Sims buttons and the corner stamp). Called by
build.py, which adds the analytics snippet and the link-preview tags. To update the numbers, run census_snippet.js in the browser on forever.raider.io/population, then
sync_census.py (it says how at its top), and rebuild."""
import base64, json, os
from datetime import date, timedelta
import experiment

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

DAILY_DAYS = 90   # the page's history: every day for this many days back from the latest, then one point a week


def history():
    """The Over Time graph's points, for census-history.json: {date: {level: {key: counts}}}. census_history.json keeps
    every daily copy and Raider.IO's weekly counts (a date in both is the daily copy's); the page gets every point of the
    last DAILY_DAYS days and, before that, the latest point of each week (Monday to Sunday), as a year of days drawn
    across the graph's width looks the same as its weeks and would make the file about three times bigger."""
    hist = json.load(open('census_history.json', encoding='utf-8'))
    pts = {**hist['weeks'], **hist['days']}
    if not pts:
        return {}
    D = lambda s: date.fromisoformat(s)
    cut = D(max(pts)) - timedelta(days=DAILY_DAYS)
    week = {}   # older points: the latest of each week, by the Sunday it ends
    for d in sorted(pts):
        if D(d) < cut:
            week[D(d) + timedelta(days=6 - D(d).weekday())] = d
    keep = set(week.values()) | {d for d in pts if D(d) >= cut}
    return {d: pts[d] for d in sorted(keep)}


def build(head_extra=''):
    data = json.load(open('census.json', encoding='utf-8'))
    page = open('census.html', encoding='utf-8').read()
    bg = ''
    if os.path.exists('bg.jpg'):
        bg = ('body{background:url("data:image/jpeg;base64,' + base64.b64encode(open('bg.jpg', 'rb').read()).decode()
              + '") top center/auto 540px repeat-x,var(--color-bg)}')
    y, m, d = (int(x) for x in data['date'].split('-'))
    blob = json.dumps({k: data[k] for k in ('date', 'source', 'races', 'classes', 'counts', 'counts60', 'prev', 'levels')}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Population Census – Forever Info</title>
<link rel="canonical" href="https://foreverinfo.io/census">
<link rel="icon" type="image/png" sizes="32x32" href="favicon.png">
<style>{experiment.CSS}{bg}</style>
<script>window.__CENSUS = {blob};</script>
{head_extra}</head>
<body>
<div id="dash-root">
{page}
</div>
<div class="xp-stamp">Raider.IO Census<br>{MONTHS[m - 1]} {d} {y}</div>
<a class="xp-quit xp-up" href="sims">Sims</a>
<a class="xp-quit" href="/">Home</a>
</body>
</html>
"""
