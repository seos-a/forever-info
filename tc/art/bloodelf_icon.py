"""Make images/icons/race_bloodelf_female_skyborne.jpg, the Alliance Skyborne portrait on the Racials and Spellbook
pages and the Experiment page (tc/experiment/race_icons.js, "High Order Skyborne").

It is WoW's race_bloodelf_female icon recoloured to look like the Skyborne icons (race_skyborne_female): the skin and
hair turned periwinkle blue, the lightest parts a little more lavender, and the fel-green glowing eyes turned
Skyborne's gold. (Before Oct 29 it was race_bloodelf_male made into a TBC-style blond, race_bloodelf_male_tbc.jpg.)
This icon is not on Wowhead, so it is not in assets.json / image-list.txt; the file lives in the repo.
Run from tc/:  py art/bloodelf_icon.py   (downloads the original from Wowhead; needs Pillow)
"""
import base64, colorsys, io, re, urllib.request
from PIL import Image

SRC = "https://wow.zamimg.com/images/wow/icons/large/race_bloodelf_female.jpg"
OUT = "../images/icons/race_bloodelf_female_skyborne.jpg"
EXPERIMENT = "experiment/race_icons.js"
EYES = [(14.6, 21.2, 3.2), (33.2, 23.8, 3.4)]   # the glowing eyes (x, y, radius in the 56px icon)
im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(SRC, headers={"User-Agent": "Mozilla/5.0"})).read())).convert("RGB")
src = im.copy(); px = im.load(); W, H = im.size
def blue(s, v):   # Skyborne blue: hue, saturation and brightness for a pixel of the original's saturation s and brightness v
    return (229 - 6*v) / 360, min(1, .32 + .45*s) * (1 - .4 * max(0, v - .75) / .25), v ** .97
for y in range(H):
    for x in range(W):
        h, s, v = colorsys.rgb_to_hsv(*(c/255 for c in src.getpixel((x, y)))); deg = h*360
        eye = max(max(0, 1 - ((x-a)**2 + (y-b)**2) ** .5 / r) for a, b, r in EYES)
        green = max(0, min(1, (s - .25) / .3)) * (55 <= deg <= 120)
        b = colorsys.hsv_to_rgb(*blue(s, v))
        if eye and green:   # the fel-green glow becomes gold, brightest at the centre
            w = min(1, eye*2) * green
            g = colorsys.hsv_to_rgb(42/360, .78, min(1, v*1.15 + .1))
            px[x, y] = tuple(round(255 * (w*gc + (1-w)*bc)) for gc, bc in zip(g, b))
        else:
            px[x, y] = tuple(round(255*c) for c in b)
im.save(OUT, quality=95)
uri = "data:image/jpeg;base64," + base64.b64encode(open(OUT, "rb").read()).decode()
js = open(EXPERIMENT, encoding="utf-8").read()
js = re.sub(r'("High Order Skyborne": )"data:[^"]*"', lambda m: m.group(1) + '"' + uri + '"', js)
open(EXPERIMENT, "w", encoding="utf-8", newline="\n").write(js)
print(OUT, im.size, "and", EXPERIMENT)
