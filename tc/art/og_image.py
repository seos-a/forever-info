"""Link-preview picture (Discord, iMessage, X, Google chat cards...): the page background with the logo on it.
Writes ../../images/og.jpg (1200x630, the size link previews expect). Run from tc/art:  py og_image.py"""
from PIL import Image, ImageEnhance, ImageFilter
W, H = 1200, 630
bg = Image.open('../bg.jpg').convert('RGB')
s = max(W / bg.width, H / bg.height)
bg = bg.resize((round(bg.width * s), round(bg.height * s)), Image.LANCZOS)
bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
bg = ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(1.5))).enhance(.55)
logo = Image.open('banner_title.png').convert('RGBA')
lw = 1000
logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.NEAREST)
shadow = Image.new('RGBA', logo.size, (0, 0, 0, 0)); shadow.putalpha(logo.getchannel('A').point(lambda a: a * 0.7))
shadow = shadow.filter(ImageFilter.GaussianBlur(10))
x, y = (W - lw) // 2 + 20, (H - logo.height) // 2
bg.paste(shadow, (x + 4, y + 10), shadow); bg.paste(logo, (x, y), logo)
bg.save('../../images/og.jpg', quality=88, optimize=True)
print('images/og.jpg', bg.size)
