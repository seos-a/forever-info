"""Draws the region flags for the Population Census page's region buttons (images/flags/<region>.svg): the United States
for the Americas region, the European Union, South Korea and Taiwan. Each is square (viewBox 40 x 40), to sit in the
same frame as the faction crests beside them, and simplified to read at button size (the US flag's stars are a grid of
dots). Run from tc/: py art/flags.py"""
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
    cw, ch = 20, h * 7
    dots = ''.join(f'<circle cx="{2.2 + x * 3.1:.2f}" cy="{2.1 + y * 4.3 + (2.15 if x % 2 else 0):.2f}" r=".8" fill="#fff"/>'
                   for x in range(6) for y in range(5 if x % 2 == 0 else 4))
    return svg(f'<rect width="{S}" height="{S}" fill="#fff"/>{stripes}<rect width="{cw}" height="{ch:.3f}" fill="#3c3b6e"/>{dots}')


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
    cw, ch = 24, 22   # a bigger canton on the square flag, as square versions draw it
    cx, cy = cw / 2, ch / 2
    rays = ' '.join(f'{cx + (8.5 if k % 2 == 0 else 4.9) * math.cos(math.radians(k * 15 - 90)):.2f},{cy + (8.5 if k % 2 == 0 else 4.9) * math.sin(math.radians(k * 15 - 90)):.2f}'
                    for k in range(24))
    return svg(f'<rect width="{S}" height="{S}" fill="#fe0000"/><rect width="{cw}" height="{ch}" fill="#000095"/>'
               f'<polygon points="{rays}" fill="#fff"/><circle cx="{cx}" cy="{cy}" r="4.85" fill="#000095"/><circle cx="{cx}" cy="{cy}" r="4.3" fill="#fff"/>')


os.makedirs(OUT, exist_ok=True)
for name, fn in (('us', us), ('eu', eu), ('kr', kr), ('tw', tw)):
    open(f'{OUT}/{name}.svg', 'w', encoding='utf-8', newline='\n').write(fn())
    print(name)
