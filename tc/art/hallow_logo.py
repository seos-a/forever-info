"""Make art/banner_hallow.png, the Hallow's End version of the site logo, from art/banner_title.png.

The letters go from pumpkin orange at the top to a dark purple base, the purple drop shadow turns slime green,
the BETA! starburst turns orange with purple lettering, and a few bats fly round the title.
Run from tc/:  py art/hallow_logo.py   (needs Pillow), then paste the PNG as a base64 data URI into the logo
<img data-hw="..."> in template2.html.
"""
import colorsys
from PIL import Image, ImageDraw

SRC, OUT = "art/banner_title.png", "art/banner_hallow.png"
LETTERS = {   # banded letter fill of the original title -> Hallow's End bands
    (255, 246, 140): (255, 206, 120), (255, 214, 40): (255, 158, 28), (255, 160, 20): (236, 108, 12),
    (232, 90, 16): (168, 52, 40), (190, 40, 20): (96, 30, 110)}
SHADOW = (110, 20, 140)
SLIME = (120, 210, 40)

im = Image.open(SRC).convert("RGBA"); px = im.load(); W, H = im.size
for y in range(H):
    for x in range(W):
        r, g, b, a = px[x, y]
        if a == 0: continue
        if (r, g, b) in LETTERS: px[x, y] = LETTERS[(r, g, b)] + (a,); continue
        if (r, g, b) == SHADOW: px[x, y] = SLIME + (a,); continue
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        if s > .35 and .1 < h < .2:            # yellow starburst (antialiased) -> pumpkin orange
            nr, ng, nb = colorsys.hsv_to_rgb(.075, s, v); px[x, y] = (round(nr*255), round(ng*255), round(nb*255), a)
        elif s > .35 and (h < .05 or h > .95):  # red BETA! lettering -> dark purple
            nr, ng, nb = colorsys.hsv_to_rgb(.78, s*.9, v*.55); px[x, y] = (round(nr*255), round(ng*255), round(nb*255), a)
        elif s > .35 and .7 < h < .85:          # the starburst's purple shadow -> slime too
            nr, ng, nb = colorsys.hsv_to_rgb(.25, .8, v*1.5 if v < .6 else v); px[x, y] = (round(nr*255), round(ng*255), round(nb*255), a)

# a few bats, drawn 4x and scaled down for smooth edges
def bat(cx, cy, w, ang=0):
    S = 4; L = Image.new("RGBA", (w*S, w*S//2), (0, 0, 0, 0)); d = ImageDraw.Draw(L)
    u = w*S/20   # wing shape on a 20 x 10 grid
    pts = [(10, 3.2), (11, 2.2), (11.6, 3.4), (13.5, 2), (16, 1.2), (20, 3), (17.2, 4.2), (16.2, 6.4), (14.6, 5.2),
           (12.8, 7), (11.2, 6), (10, 8), (8.8, 6), (7.2, 7), (5.4, 5.2), (3.8, 6.4), (2.8, 4.2), (0, 3), (4, 1.2),
           (6.5, 2), (8.4, 3.4), (9, 2.2)]
    d.polygon([(px_*u, py*u) for px_, py in pts], fill=(18, 6, 24, 255), outline=(0, 0, 0, 255))
    d.ellipse((8.9*u, 3.9*u, 9.5*u, 4.5*u), fill=(255, 150, 30, 255)); d.ellipse((10.5*u, 3.9*u, 11.1*u, 4.5*u), fill=(255, 150, 30, 255))
    L = L.resize((w, w//2), Image.LANCZOS).rotate(ang, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(L, (int(cx - L.width/2), int(cy - L.height/2)))
for cx, cy, w, ang in [(34, 22, 46, -12), (420, 12, 34, 8), (1046, 150, 36, -6), (22, 170, 30, 10)]:
    bat(cx, cy, w, ang)
im.save(OUT, optimize=True)
print(OUT, im.size)
