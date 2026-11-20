"""Builds the Population Census page (foreverinfo.io/census): who plays which race and class in WoW Forever, from
Raider.IO's census (https://forever.raider.io/population: the characters Raider.IO tracks, levels 10 to 60).

census.html is the page (markup, style, script); census.json the numbers, by region and ruleset. It is framed like the
Sims page: experiment.CSS (colours, fonts, the background along the top, the Home and Sims buttons and the corner stamp). Called by
build.py, which adds the analytics snippet and the link-preview tags. To update the numbers, run census_snippet.js in the browser on forever.raider.io/population, then
sync_census.py (it says how at its top), and rebuild."""
import base64, json, os
import experiment

MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def build(head_extra=''):
    data = json.load(open('census.json', encoding='utf-8'))
    page = open('census.html', encoding='utf-8').read()
    bg = ''
    if os.path.exists('bg.jpg'):
        bg = ('body{background:url("data:image/jpeg;base64,' + base64.b64encode(open('bg.jpg', 'rb').read()).decode()
              + '") top center/auto 540px repeat-x,var(--color-bg)}')
    y, m, d = (int(x) for x in data['date'].split('-'))
    blob = json.dumps({k: data[k] for k in ('date', 'source', 'races', 'classes', 'counts', 'levels')}, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/')
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
