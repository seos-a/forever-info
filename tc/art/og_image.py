"""Link-preview picture (Discord, iMessage, X, Google chat cards...): the logo on flat black.
Writes ../../images/og.png (1200x630, the size link previews expect). Run from tc/art:  py og_image.py
The logo is pixel art drawn at 2x (each "pixel" is a 2x2 block), so it is pasted at its own size, never resized:
any other scale makes the blocks uneven and the edges look smeared. PNG keeps those edges sharp, where JPEG blurs them."""
from PIL import Image
W, H = 1200, 630
logo = Image.open('banner_title.png').convert('RGBA')
logo = logo.crop(logo.getbbox())
img = Image.new('RGBA', (W, H), (0, 0, 0, 255))
img.alpha_composite(logo, ((W - logo.width) // 2, (H - logo.height) // 2))
img.convert('RGB').save('../../images/og.png', optimize=True)
print('images/og.png', img.size, 'logo', logo.size)
