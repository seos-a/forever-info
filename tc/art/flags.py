"""Draws the region flags for the Population Census page's region buttons (images/flags/<region>.svg): the United States
for the Americas region, the European Union, South Korea and Taiwan. Each is square (viewBox 40 x 40), to sit in the
same frame as the faction crests beside them, and simplified to read at button size (the US flag has 14 larger stars on a
shorter canton). Run from tc/: py art/flags.py"""
import math, os

OUT = '../images/flags'
S = 40


def star(cx, cy, r, rot=-90):
    """A five-pointed star's points, its first point at angle rot."""
    pts = []
    for k in range(10):
        a = math.radians(rot + k * 36)
        rr = r if k % 2 == 0 else r * 0.382
        pts.append(f'{cx + rr * math.cos(a):.2f},{cy + rr * math.sin(a):.2f}')
    return ' '.join(pts)


def svg(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {S} {S}">{body}</svg>\n'


def us():
    h = S / 13
    stripes = ''.join(f'<rect y="{i * h:.3f}" width="{S}" height="{h:.3f}" fill="#b22234"/>' for i in range(0, 13, 2))
    # The canton is 5 stripes deep (the real flag's 7 look too tall on a square flag), ending on a red stripe as the real
    # one does, with 14 stars in staggered rows of 4 and 3, big enough to read at button size.
    cw, ch = 18, h * 5
    rows = [(4, 2.25), (3, 4.5), (4, 2.25), (3, 4.5)]
    stars = ''.join(f'<polygon points="{star(x0 + k * 4.5, 2.35 + r * 3.55, 1.45)}" fill="#fff"/>'
                    for r, (n, x0) in enumerate(rows) for k in range(n))
    return svg(f'<rect width="{S}" height="{S}" fill="#fff"/>{stripes}<rect width="{cw}" height="{ch:.3f}" fill="#3c3b6e"/>{stars}')


def eu():
    stars = ''.join(f'<polygon points="{star(20 + 12 * math.cos(math.radians(k * 30)), 20 + 12 * math.sin(math.radians(k * 30)), 2.4)}" fill="#ffcc00"/>' for k in range(12))
    return svg(f'<rect width="{S}" height="{S}" fill="#003399"/>{stars}')


def kr():
    a = 45   # on a square flag the trigrams sit on the diagonals
    taeguk = (f'<g transform="translate(20 20) rotate({a - 11.3:.2f})">'   # the taegeuk keeps the real flag's tilt (33.7 degrees)
              '<path d="M-9 0A9 9 0 0 1 9 0Z" fill="#cd2e3a"/><path d="M-9 0A9 9 0 0 0 9 0Z" fill="#0047a0"/>'
              '<circle cx="-4.5" r="4.5" fill="#cd2e3a"/><circle cx="4.5" r="4.5" fill="#0047a0"/></g>')

    def trigram(angle, bars):
        """Three bars (True solid, False broken) across the line from the centre at angle, the first nearest the centre."""
        g = ''
        for n, solid in enumerate(bars):
            x = 12.5 + n * 2.5
            if solid:
                g += f'<rect x="{x:.2f}" y="-5" width="1.6" height="10" fill="#000"/>'
            else:
                g += f'<rect x="{x:.2f}" y="-5" width="1.6" height="4.4" fill="#000"/><rect x="{x:.2f}" y=".6" width="1.6" height="4.4" fill="#000"/>'
        return f'<g transform="translate(20 20) rotate({angle})">{g}</g>'
    tri = (trigram(180 + a, [True, True, True])       # top left: heaven
           + trigram(-a, [False, True, False])        # top right: water
           + trigram(180 - a, [True, False, True])    # bottom left: fire
           + trigram(a, [False, False, False]))       # bottom right: earth
    return svg(f'<rect width="{S}" height="{S}" fill="#fff"/>{taeguk}{tri}')


def tw():
    cw = ch = S / 2   # the real flag's canton: half its width and half its height, the sun in its middle
    cx, cy = cw / 2, ch / 2
    rays = ' '.join(f'{cx + (7.2 if k % 2 == 0 else 4.15) * math.cos(math.radians(k * 15 - 90)):.2f},{cy + (7.2 if k % 2 == 0 else 4.15) * math.sin(math.radians(k * 15 - 90)):.2f}'
                    for k in range(24))
    return svg(f'<rect width="{S}" height="{S}" fill="#fe0000"/><rect width="{cw}" height="{ch}" fill="#000095"/>'
               f'<polygon points="{rays}" fill="#fff"/><circle cx="{cx}" cy="{cy}" r="4.1" fill="#000095"/><circle cx="{cx}" cy="{cy}" r="3.6" fill="#fff"/>')


os.makedirs(OUT, exist_ok=True)
for name, fn in (('us', us), ('eu', eu), ('kr', kr), ('tw', tw)):
    open(f'{OUT}/{name}.svg', 'w', encoding='utf-8', newline='\n').write(fn())
    print(name)
