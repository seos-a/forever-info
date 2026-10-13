"""Link-preview picture (Discord, iMessage, X, Google chat cards...): the logo on flat black, with the site's murloc
(the icon's murloc, sunglasses and all) peeking up from the bottom edge, fins to grin.
Writes ../../images/og.png (1200x630, the size link previews expect). Run from tc/art:  py og_image.py
The logo is pixel art drawn at 2x (each "pixel" is a 2x2 block), so it is pasted at its own size, never resized:
any other scale makes the blocks uneven and the edges look smeared. PNG keeps those edges sharp, where JPEG blurs them."""
from PIL import Image
from touch_icon import src, CX, TOP, SIDE, cells, x0, x1, y0, GLASS_TOP

W, H = 1200, 630
LOGO_Y = 70                 # the logo's top, raised to leave the murloc room
FACE, SHOW = 220, .95       # face scale (the icon's face at 220px) and how much of it rises above the bottom edge

def murloc(S):
    """The murloc's head with the sunglasses: cropped from the render's top so the fins show whole, twice as wide as
    the icon's crop so its own outline shows at the sides (no hard edges)."""
    T = src.getbbox()[1]
    L, R = max(0, CX - SIDE), min(src.width, CX + SIDE)
    k = S / SIDE
    h = src.crop((L, T, R, TOP + SIDE * 2))
    h = h.resize((round(h.width * k), round(h.height * k)), Image.LANCZOS)
    B, cx = S / 32, (CX - L) * k
    left, top = cx - (x1 - x0 + 1) * B / 2, (TOP - T) * k + GLASS_TOP * B
    g = Image.new('RGBA', h.size, (0, 0, 0, 0))
    for x, y, c in cells:
        g.paste(c[:3] + (255,), (round(left + (x - x0) * B), round(top + (y - y0) * B),
                                 round(left + (x - x0 + 1) * B), round(top + (y - y0 + 1) * B)))
    h.alpha_composite(g)
    return h, cx, (TOP - T) * k

logo = Image.open('banner_title.png').convert('RGBA')
logo = logo.crop(logo.getbbox())
img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
img.alpha_composite(logo, ((W - logo.width) // 2, LOGO_Y))
head, cx, fins = murloc(FACE)
img.alpha_composite(head, (round(W / 2 - cx), H - int(FACE * SHOW + fins)))
img.convert('RGB').save('../../images/og.png', optimize=True)
print('images/og.png', img.size, 'logo', logo.size)
