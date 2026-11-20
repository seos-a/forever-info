// Population Census refresh, step 1 of 2 (step 2: py sync_census.py). Paste into the browser console (F12 > Console)
// on https://forever.raider.io/population. It asks the page's own data address for each region and ruleset, about a
// second apart, and downloads census-raiderio.json. See sync_census.py.
(async () => {
  const out = {};
  for (const region of ['all', 'us', 'eu', 'kr', 'tw']) {
    for (const ruleset of ['all', 'normal', 'pvp', 'rp', 'pvp-rp']) {
      const r = await fetch(`/api/population?region=${region}&ruleset=${ruleset}&level=all&faction=all`);
      if (!r.ok) { console.error(`${region} ${ruleset}: HTTP ${r.status}, stopped`); return; }
      const j = await r.json(), s = j.stats || j;
      out[`${region}|${ruleset}`] = { generatedAt: s.generatedAt, factionBalance: s.factionBalance, classLevels: s.classLevels };
      console.log(`${region} ${ruleset}: done`);
      await new Promise((ok) => setTimeout(ok, 1000));
    }
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out)], { type: 'application/json' }));
  a.download = 'census-raiderio.json';
  a.click();
  console.log('Saved census-raiderio.json. Next, in tc/: py sync_census.py');
})();
