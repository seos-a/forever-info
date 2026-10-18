# Raid link previews (Cloudflare Worker)

When someone shares a Raid Composition link, Discord, iMessage and other apps show a picture of that roster instead of
the Forever Info logo, in Wowhead's flat dark style with nothing but the groups:

- 20 players or fewer, in at most 4 groups: each group's members by name (the player's name typed on the page, or
  the spec's name), with spec icons, in class colours.
- Bigger raids: all 8 groups as columns of spec icons ringed in their class colour.

The page's **Copy Link** copies a short link (`https://foreverinfo.io/raid/k3Xa9Q`): the Worker keeps the roster in
Cloudflare KV under a 7-character id made from the roster itself (the same raid always gets the same link) and sends
anyone opening it on to the full `/raid?<code>` address. Without KV (or anywhere but the website) Copy Link copies the
long link, which holds the whole roster.

GitHub Pages can't do this alone: it serves the same `raid.html` for every `/raid?...` address, and chat apps don't run
the page's JavaScript. So a small Cloudflare Worker sits in front of `foreverinfo.io/raid*` only:

- `/raid?<code>`: fetches the page from GitHub Pages and points its preview tags (`og:image`, description) at
  `/raid-preview.png?<code>`.
- `/raid-preview.png?<code>`: draws that picture (`src/roster.js` builds an SVG, resvg turns it into a PNG) and keeps
  it in Cloudflare's cache for a week.
- `POST /raid-share`: stores a roster for Copy Link; `/raid/<id>`: redirects to that roster.
- Every other address on the site never touches the Worker. If the Worker has a problem, it serves the normal page.

## Files

- `src/index.js`: the Worker. `src/roster.js`: reads a raid link and draws the roster. `src/specs.js`: the specs in
  link-code order, with icons and class colours, copied from `tc/template2.html` (change both together).
- `test/render.mjs`: draws sample pictures to `out/` (`npm test`).
- `wrangler.toml`: the Worker's name, its route (`foreverinfo.io/raid*`) and settings.
- The font (Roboto Condensed ExtraBold, SIL Open Font License) isn't committed: `fetch-font.sh` downloads Google
  Fonts' variable Roboto Condensed and cuts the ExtraBold weight out of it (resvg can't pick a weight inside a
  variable font); the workflow runs it before building.
- `.github/workflows/raid-preview.yml`: on every push that changes `worker/`, draws the samples (in the run's
  Artifacts), runs the Worker locally against the live site, and on `main` deploys it once the Cloudflare secrets
  below exist. Until then the deploy step just says it's skipping.

To change the picture's design, edit `src/roster.js` and bump `PREVIEW_VERSION` in `src/index.js` (chat apps cache
pictures by address, so the new version number makes them fetch the new design).

## One-time setup

This moves the domain's DNS from Porkbun to Cloudflare (free plan). The site itself stays on GitHub Pages. The domain
stays registered at Porkbun; only its nameservers change. Allow about an hour, most of it waiting for DNS.

### 1. Note your current DNS records (Porkbun)

1. Log in to porkbun.com → **Account → Domain Management** → `foreverinfo.io` → **DNS**.
2. Screenshot or copy every record. Expect GitHub Pages' four `A` records (`185.199.108.153` to `185.199.111.153`),
   possibly `AAAA` records and a `www` `CNAME` to `seos-a.github.io`, and **`TXT` records such as Google Search
   Console's `google-site-verification=...`**. Losing that TXT record would un-verify Search Console.

### 2. Add the site to Cloudflare

1. Sign up or log in at dash.cloudflare.com → **Add a domain** → `foreverinfo.io` → **Free** plan.
2. Cloudflare scans and imports the DNS records. Compare them with your Porkbun list and add anything missing
   (especially TXT records).
3. Set the GitHub Pages records (`A`, `AAAA`, `www`) to **Proxied** (orange cloud). Leave TXT and any mail records
   as they are.
4. Cloudflare shows two nameservers (like `xxx.ns.cloudflare.com`). Keep this page open.

### 3. Point Porkbun at Cloudflare

1. In Porkbun → `foreverinfo.io` → **Authoritative Nameservers** (the "NS" edit link) → replace Porkbun's four
   nameservers with Cloudflare's two → save.
2. If **DNSSEC** is on at Porkbun, turn it off first (you can turn it on again later from Cloudflare's DNS settings).
3. Wait for Cloudflare's email "foreverinfo.io is now active" (minutes to a few hours).

### 4. Cloudflare settings for GitHub Pages

1. **SSL/TLS → Overview**: set the mode to **Full** (not "Flexible", which causes redirect loops with GitHub Pages).
2. Visit https://foreverinfo.io and a few pages to check the site still loads.
3. GitHub → repo **Settings → Pages**: the custom domain and "Enforce HTTPS" should stay as they are.

### 5. Let GitHub deploy the Worker

1. Cloudflare → **My Profile → API Tokens → Create Token** → template **Edit Cloudflare Workers** → under
   *Account Resources* pick your account and under *Zone Resources* pick `foreverinfo.io` → **Create Token** → copy it.
2. Cloudflare dashboard home → your account → copy the **Account ID** (right-hand side, or in the URL).
3. GitHub → repo **Settings → Secrets and variables → Actions → New repository secret**, twice:
   - `CLOUDFLARE_API_TOKEN` = the token
   - `CLOUDFLARE_ACCOUNT_ID` = the account ID
4. GitHub → **Actions → Raid link previews → Run workflow** (on `main`). The deploy job publishes the Worker and adds
   its route `foreverinfo.io/raid*`.

### 6. Short links (Cloudflare KV)

1. Cloudflare → **Storage & databases → Workers KV → Create instance** (or **Create namespace**) → name it
   `RAID_LINKS` → create.
2. Copy its **ID** (32 letters and digits; not secret) and give it to whoever edits the repo: it goes into
   `worker/wrangler.toml` under `[[kv_namespaces]]` (done: `a8b2ffbe...`). The next deploy connects the store;
   without it Copy Link copies the long link.

### 7. Check it

1. Open `https://foreverinfo.io/raid-preview.png?1pg4jae09k` in a browser: you should see a 10-player roster picture.
2. Paste a raid link into Discord. Discord caches previews per address, so test with a link you haven't shared before.

To turn it off at any time: Cloudflare → **Workers & Pages → foreverinfo-raid-preview → Settings → Domains & Routes**
→ delete the route. The site keeps working as before, with the usual logo preview.
