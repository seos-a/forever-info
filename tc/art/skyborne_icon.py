"""Make images/icons/race_skyborne_female.jpg, the Horde Skyborne portrait on the Racials and Spellbook pages and the
Experiment page (tc/experiment/race_icons.js, "Windshaper Skyborne"): WoW's race_skyborne_female icon as it is (it is
already framed close on the face; the male one, used before Oct 29, needed zooming in). Run from tc/:
py art/skyborne_icon.py   (downloads the original from Wowhead; needs Pillow). build.py won't overwrite it:
fetch_images.py only downloads icons the repo doesn't have."""
import base64, io, re, urllib.request
from PIL import Image

SRC = "https://wow.zamimg.com/images/wow/icons/large/race_skyborne_female.jpg"
OUT = "../images/icons/race_skyborne_female.jpg"
EXPERIMENT = "experiment/race_icons.js"
im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(SRC, headers={"User-Agent": "Mozilla/5.0"})).read())).convert("RGB")
im.save(OUT, quality=95)
uri = "data:image/jpeg;base64," + base64.b64encode(open(OUT, "rb").read()).decode()
js = open(EXPERIMENT, encoding="utf-8").read()
js = re.sub(r'("Windshaper Skyborne": )"data:[^"]*"', lambda m: m.group(1) + '"' + uri + '"', js)
open(EXPERIMENT, "w", encoding="utf-8", newline="\n").write(js)
print(OUT, im.size, "and", EXPERIMENT)
