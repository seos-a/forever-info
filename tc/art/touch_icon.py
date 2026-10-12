"""The site's icons: the green murloc's head from its 300px Wowhead model render, centred on the face, wearing the
favicon's pixel "deal with it" sunglasses (redrawn in sharp blocks, not blown up from the 32px favicon).
Run from tc/art:  py touch_icon.py   Writes, in the repo root:
    apple-touch-icon.png (180)    iPhone / iPad bookmarks and home screen
    favicon-48.png, favicon-96.png  Google search results (they want 48px or more)
    icon-192.png, icon-512.png    Android home screen (site.webmanifest)
    favicon.png (32), favicon.ico (16 + 32)   browser tabs, and Safari's Favourites and search suggestions
The original hand-made pixel favicon stays in tc/art (fav_shades.png); Safari blew it up in Favourites, so the site's
favicons are made from the same art as the big icons."""
from PIL import Image

src = Image.open('../../images/models/441.png').convert('RGBA')
CX, TOP, SIDE = 147, 55, 120             # face centre, crop top and size in the 300px render: framed like the
                                         # favicon, the face filling the icon and the fins running off the top
plain, shades = Image.open('fav.png').convert('RGBA'), Image.open('fav_shades.png').convert('RGBA')
cells = [(x, y, shades.getpixel((x, y))) for y in range(32) for x in range(32)
         if shades.getpixel((x, y)) != plain.getpixel((x, y))]   # the sunglasses' pixels in the favicon
x0, x1, y0 = min(c[0] for c in cells), max(c[0] for c in cells), min(c[1] for c in cells)

def icon(S):
    """The icon at S x S. Big sizes are drawn at 180 and scaled up (the render has no more detail), the glasses
    drawn straight at the final size so their blocks stay sharp."""
    base = min(S, 180)
    head = src.crop((CX - SIDE // 2, TOP, CX + SIDE // 2, TOP + SIDE)).resize((base, base), Image.LANCZOS)
    im = Image.new('RGBA', (base, base), (0, 0, 0, 0)); im.alpha_composite(head)   # transparent behind the murloc (iPhone shows it on dark)
    if S > base: im = im.resize((S, S), Image.LANCZOS)
    B = S / 32                                        # the favicon's pixels, scaled to this size
    left, top = S / 2 - (x1 - x0 + 1) * B / 2, y0 * B     # centred, at the favicon's height (over the eyes)
    g = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    for x, y, c in cells:
        g.paste(c[:3] + (255,), (round(left + (x - x0) * B), round(top + (y - y0) * B),
                                 round(left + (x - x0 + 1) * B), round(top + (y - y0 + 1) * B)))
    im.alpha_composite(g)
    return im

for name, S in (('favicon.png', 32), ('apple-touch-icon.png', 180), ('favicon-48.png', 48), ('favicon-96.png', 96),
                ('icon-192.png', 192), ('icon-512.png', 512)):
    icon(S).save('../../' + name, optimize=True)
    print(name, S)
icon(32).save('../../favicon.ico', sizes=[(16, 16), (32, 32)])
print('favicon.ico 16 + 32')
