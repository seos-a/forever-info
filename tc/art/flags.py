"""Draws the region flags for the Population Census page's region buttons (images/flags/<region>.svg): the United States
for the Americas region, the European Union, South Korea and Taiwan. Each is 3:2 (viewBox 60 x 40), simplified to read at
button size (the US flag's stars are a grid of dots). Run from tc/: py art/flags.py"""
import math, os

OUT = '../images/flags'


def star(cx, cy, r, rot=-90):
    """A five-pointed star's points, its first point at angle rot."""
    pts = []
    for k in range(10):
        a = math.radians(rot + k * 36)
        rr = r if k % 2 == 0 else r * 0.382
        pts.append(f'{cx + rr * math.cos(a):.2f},{cy + rr * math.sin(a):.2f}')
    return ' '.join(pts)


def svg(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 40">{body}</svg>\n'


def us():
    h = 40 / 13
    stripes = ''.join(f'<rect y="{i * h:.3f}" width="60" height="{h:.3f}" fill="#b22234"/>' for i in range(0, 13, 2))
    cw, ch = 25, h * 7
    dots = ''.join(f'<circle cx="{2.5 + x * 4:.2f}" cy="{2.1 + y * 3.65 + (1.8 if x % 2 else 0):.2f}" r=".85" fill="#fff"/>'
                   for x in range(6) for y in range(5 if x % 2 == 0 else 4))
    return svg(f'<rect width="60" height="40" fill="#fff"/>{stripes}<rect width="{cw}" height="{ch:.3f}" fill="#3c3b6e"/>{dots}')


def eu():
    stars = ''.join(f'<polygon points="{star(30 + 12 * math.cos(math.radians(k * 30)), 20 + 12 * math.sin(math.radians(k * 30)), 2.3)}" fill="#ffcc00"/>' for k in range(12))
    return svg(f'<rect width="60" height="40" fill="#003399"/>{stars}')


def kr():
    a = math.degrees(math.atan2(40, 60))   # the diagonal, about 33.7 degrees
    # the taegeuk: red above, blue below, along the diagonal, with the two half-size circles making the S
    taeguk = (f'<g transform="translate(30 20) rotate({a:.2f})">'
              '<path d="M-10 0A10 10 0 0 1 10 0Z" fill="#cd2e3a"/><path d="M-10 0A10 10 0 0 0 10 0Z" fill="#0047a0"/>'
              '<circle cx="-5" r="5" fill="#cd2e3a"/><circle cx="5" r="5" fill="#0047a0"/></g>')

    def trigram(angle, bars):
        """Three bars (True solid, False broken) across the line from the centre at angle, the first nearest the centre."""
        g = ''
        for n, solid in enumerate(bars):
            x = 15 + n * 2.7
            if solid:
                g += f'<rect x="{x:.2f}" y="-6" width="1.8" height="12" fill="#000"/>'
            else:
                g += f'<rect x="{x:.2f}" y="-6" width="1.8" height="5.4" fill="#000"/><rect x="{x:.2f}" y=".6" width="1.8" height="5.4" fill="#000"/>'
        return f'<g transform="translate(30 20) rotate({angle:.2f})">{g}</g>'
    tri = (trigram(180 + a, [True, True, True])       # top left: heaven
           + trigram(-a, [False, True, False])        # top right: water
           + trigram(180 - a, [True, False, True])    # bottom left: fire
           + trigram(a, [False, False, False]))       # bottom right: earth
    return svg(f'<rect width="60" height="40" fill="#fff"/>{taeguk}{tri}')


def tw():
    cx, cy = 15, 10
    rays = ' '.join(f'{cx + (7.5 if k % 2 == 0 else 4.3) * math.cos(math.radians(k * 15 - 90)):.2f},{cy + (7.5 if k % 2 == 0 else 4.3) * math.sin(math.radians(k * 15 - 90)):.2f}'
                    for k in range(24))
    return svg(f'<rect width="60" height="40" fill="#fe0000"/><rect width="30" height="20" fill="#000095"/>'
               f'<polygon points="{rays}" fill="#fff"/><circle cx="{cx}" cy="{cy}" r="4.25" fill="#000095"/><circle cx="{cx}" cy="{cy}" r="3.75" fill="#fff"/>')


os.makedirs(OUT, exist_ok=True)
for name, fn in (('us', us), ('eu', eu), ('kr', kr), ('tw', tw)):
    open(f'{OUT}/{name}.svg', 'w', encoding='utf-8', newline='\n').write(fn())
    print(name)
