"""Make images/icons/race_skyborne_male.jpg, the Horde Skyborne portrait on the Racials and Spellbook pages:
WoW's race_skyborne_male icon zoomed in on the face (a 42px square of the 56px icon, scaled back up to 56px),
framed low enough to keep the chin in view. Run from tc/:  py art/skyborne_icon.py   (downloads the original from
Wowhead; needs Pillow). build.py won't overwrite it: fetch_images.py only downloads icons the repo doesn't have."""
import io, urllib.request
from PIL import Image

SRC = "https://wow.zamimg.com/images/wow/icons/large/race_skyborne_male.jpg"
OUT = "../images/icons/race_skyborne_male.jpg"
X, Y, SIDE = 7, 8, 42   # the square kept: 7px from the left, 8px from the top
im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(SRC, headers={"User-Agent": "Mozilla/5.0"})).read())).convert("RGB")
im.resize(im.size, Image.LANCZOS, box=(X, Y, X + SIDE, Y + SIDE)).save(OUT, quality=95)
print(OUT, im.size)
