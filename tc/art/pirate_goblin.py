"""Make images/models/greenskin_pirate.png for the Hallow's End theme: Captain Greenskin (Wowhead model
thumbnail, display 7113) with his skull-and-crossbones pirate hat drawn back on (the thumbnail leaves it out).
Run from tc/:  py art/pirate_goblin.py   (downloads the thumbnail; needs Pillow)
"""
import io, urllib.request
from PIL import Image, ImageDraw

SRC = "https://wow.zamimg.com/modelviewer/classic/webthumbs/npc/201/7113.png"
OUT = "../images/models/greenskin_pirate.png"
TOP = 34                      # extra room above the head for the hat
gob = Image.open(io.BytesIO(urllib.request.urlopen(SRC).read())).convert("RGBA")
im = Image.new("RGBA", (gob.width, gob.height + TOP), (0, 0, 0, 0)); im.alpha_composite(gob, (0, TOP))

S = 4; HW, HH = 120, 62       # hat size before scaling down
hat = Image.new("RGBA", (HW*S, HH*S), (0, 0, 0, 0)); d = ImageDraw.Draw(hat)
def P(pts): return [(x*S, y*S) for x, y in pts]
crown = [(16, 40), (22, 18), (38, 7), (60, 3), (82, 7), (98, 18), (104, 40)]
brim = [(2, 30), (10, 44), (30, 52), (60, 55), (90, 52), (110, 44), (118, 30), (106, 40), (84, 45), (60, 47), (36, 45), (14, 40)]
d.polygon(P(crown + [(104, 44), (16, 44)]), fill=(26, 28, 52, 255), outline=(0, 0, 0, 255), width=S*2)
d.polygon(P(brim), fill=(20, 22, 42, 255), outline=(0, 0, 0, 255), width=S*2)
d.line(P([(4, 32), (12, 43), (30, 50), (60, 53), (90, 50), (108, 43), (116, 32)]), fill=(222, 214, 190, 255), width=S*2)   # pale trim on the brim
d.line(P([(18, 38), (24, 19), (39, 9), (60, 5), (81, 9), (96, 19), (102, 38)]), fill=(60, 64, 104, 255), width=S)          # light catching the crown
# skull and crossbones
W_ = (238, 234, 220, 255)
for a, b in (((47, 34), (73, 20)), ((47, 20), (73, 34))):
    d.line(P([a, b]), fill=W_, width=S*3)
    for cx, cy in (a, b): d.ellipse(P([(cx-2.4, cy-2.4), (cx+2.4, cy+2.4)]), fill=W_)
d.ellipse(P([(52, 12), (68, 28)]), fill=W_, outline=(0, 0, 0, 255), width=S)
d.rectangle(P([(55, 24), (65, 31)]), fill=W_)
d.ellipse(P([(54.5, 17), (59, 21.5)]), fill=(20, 22, 42, 255)); d.ellipse(P([(61, 17), (65.5, 21.5)]), fill=(20, 22, 42, 255))
d.polygon(P([(60, 22), (58.6, 25), (61.4, 25)]), fill=(20, 22, 42, 255))
hat = hat.resize((HW, HH), Image.LANCZOS).rotate(4, resample=Image.BICUBIC, expand=True)
im.alpha_composite(hat, (152 - hat.width//2, TOP + 26 - hat.height + 19))
im.save(OUT, optimize=True)
print(OUT, im.size)
