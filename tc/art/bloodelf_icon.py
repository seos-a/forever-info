"""Make images/icons/race_bloodelf_male_tbc.jpg, the Alliance Skyborne portrait on the Racials and Spellbook pages.

It is WoW's race_bloodelf_male icon with the green fel lighting on the hair, face and mouth turned into warm
blond and skin tones, so it looks like the TBC character-creation Blood Elf icon. Then the whole face is made paler and less saturated. The glowing eyes keep their green.
This icon is not on Wowhead, so it is not in assets.json / image-list.txt; the file lives in the repo.
Run from tc/:  py art/bloodelf_icon.py   (downloads the original from Wowhead; needs Pillow)
"""
import colorsys, io, urllib.request
from PIL import Image

SRC = "https://wow.zamimg.com/images/wow/icons/large/race_bloodelf_male.jpg"
OUT = "../images/icons/race_bloodelf_male_tbc.jpg"
im = Image.open(io.BytesIO(urllib.request.urlopen(SRC).read())).convert("RGB"); W, H = im.size; px = im.load()
SAT, LIFT = .68, .82  # overall saturation and brightness lift for the pale TBC look
EYES = [(29, 16.5, 3), (13, 22, 2.6)]   # glowing eyes keep their green (x, y, radius in the 56px icon)
def in_eye(x, y): return any((x-a)**2 + (y-b)**2 <= r*r for a, b, r in EYES)
for y in range(H):
    for x in range(W):
        r, g, b = (c/255 for c in px[x, y]); h, s, v = colorsys.rgb_to_hsv(r, g, b); deg = h*360
        if 60 <= deg <= 175 and s > .12 and not in_eye(x, y):
            w = min(1, (deg-60)/15, (175-deg)/15)          # fade in/out at the edges of the green band
            nh = (deg + (28 - deg)*w) / 360                  # pull the hue to a warm blond / skin tone
            ns = s * (1 - .55*w)                             # and take most of the saturation out
            nv = v * (1 - .08*w)
            px[x, y] = tuple(round(c*255) for c in colorsys.hsv_to_rgb(nh, ns, nv))
for y in range(H):   # second pass: paler, cooler skin and platinum-blond hair like the TBC portrait
    for x in range(W):
        if in_eye(x, y): continue
        r, g, b = (c/255 for c in px[x, y]); h, s, v = colorsys.rgb_to_hsv(r, g, b)
        s *= SAT; v = v ** LIFT
        px[x, y] = tuple(round(c*255) for c in colorsys.hsv_to_rgb(h, s, v))
im.save(OUT, quality=95)
