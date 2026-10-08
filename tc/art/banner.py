from PIL import Image, ImageDraw, ImageFont
import random, math
random.seed(7)
F='/tmp/claude-0/-home-claude/5aa9955d-ed3a-52fd-aad6-c1027ed5d50d/scratchpad/fonts/'
META=F+'fontsource-metamorphous-5.3.0/package/files/metamorphous-latin-400-normal.woff'
COMIC=F+'fontsource-comic-neue-5.3.0/package/files/comic-neue-latin-700-normal.woff'
W,H=640,112            # drawn at 1x, upscaled 2x nearest-neighbour for chunky pixels
img=Image.new('RGBA',(W,H),(0,0,0,0))
font=ImageFont.truetype(META,50)

def letter(ch,size=50,ang=0):
    f=ImageFont.truetype(META,size)
    pad=14
    bb=f.getbbox(ch); w=bb[2]-bb[0]+pad*2; h=bb[3]-bb[1]+pad*2
    def layer(fill,stroke=0,sfill=None):
        L=Image.new('RGBA',(w,h),(0,0,0,0)); d=ImageDraw.Draw(L); d.fontmode='1'
        d.text((pad-bb[0],pad-bb[1]),ch,font=f,fill=fill,stroke_width=stroke,stroke_fill=sfill)
        return L
    # banded MS-paint gradient fill
    mask=layer((255,255,255,255)).split()[3]
    grad=Image.new('RGBA',(w,h))
    bands=[(255,246,140),(255,214,40),(255,160,20),(232,90,16),(190,40,20)]
    gd=ImageDraw.Draw(grad)
    for y in range(h):
        t=(y-pad)/max(1,(h-2*pad)); i=min(len(bands)-1,max(0,int(t*len(bands))))
        gd.line([(0,y),(w,y)],fill=bands[i]+(255,))
    out=Image.new('RGBA',(w,h),(0,0,0,0))
    shadow=layer((110,20,140,255),3,(110,20,140,255))
    out.alpha_composite(shadow,(0,0)) if False else None
    base=Image.new('RGBA',(w+6,h+6),(0,0,0,0))
    base.alpha_composite(shadow,(5,4))                     # lopsided purple shadow
    base.alpha_composite(layer((0,0,0,255),3,(0,0,0,255)),(0,0))  # fat black outline
    fill=Image.new('RGBA',(w,h),(0,0,0,0)); fill.paste(grad,(0,0),mask)
    base.alpha_composite(fill,(0,0))
    # one crude white "shine" blob
    d=ImageDraw.Draw(base); 
    return base.rotate(ang,resample=Image.NEAREST,expand=True)

x=18; y0=14
text="Forever Info"
for i,ch in enumerate(text):
    if ch==' ': x+=14; continue
    size=random.choice([52,56,58]) if ch not in 'FI' else 68
    ang=random.uniform(-9,9)
    L=letter(ch,size,ang)
    yy=y0+random.randint(-4,4)+(64-size)//2+(0 if ch not in 'FI' else -4)
    img.alpha_composite(L,(int(x),yy))
    x+=L.width-33+random.randint(-2,2)
print('text width',x)
d=ImageDraw.Draw(img); d.fontmode='1'
# crude sparkles
def sparkle(cx,cy,r,col=(255,255,255,255)):
    d.line([(cx-r,cy),(cx+r,cy)],fill=col,width=2); d.line([(cx,cy-r),(cx,cy+r)],fill=col,width=2)
    d.line([(cx-r//2,cy-r//2),(cx+r//2,cy+r//2)],fill=col,width=1); d.line([(cx-r//2,cy+r//2),(cx+r//2,cy-r//2)],fill=col,width=1)
for (cx,cy,r) in [(24,14,7),(205,8,5),(470,4,6),(40,88,4)]: sparkle(cx,cy,r)
title_end=x
# ---- upscale the janky pixel title, then add smooth, readable extras at 2x ----
big=img.resize((W*2,H*2),Image.NEAREST)
D=ImageDraw.Draw(big)
# starburst sticker: smooth edges, still wonky
cx,cy,R,r=(title_end+30)*2,30*2,60,44
pts=[]
for k in range(24):
    a=k*math.pi/12+0.15; rr=(R if k%2==0 else r)+random.randint(-3,3)
    pts.append((cx+rr*math.cos(a),cy+rr*math.sin(a)))
sh=[(px+5,py+6) for px,py in pts]
D.polygon(sh,fill=(110,20,140,255))
D.polygon(pts,fill=(255,226,40,255),outline=(0,0,0,255),width=4)
st=Image.new('RGBA',(140,60),(0,0,0,0)); sd=ImageDraw.Draw(st)
sf=ImageFont.truetype(COMIC,30)
sd.text((70,30),"BETA!",font=sf,fill=(210,0,0,255),anchor='mm')
st=st.rotate(-12,resample=Image.BICUBIC,expand=True)
big.alpha_composite(st,(int(cx-st.width/2),int(cy-st.height/2)))
# tagline: same font/size throughout, each word nudged a little so it isn't machine-perfect
msg="talents ~ racials ~ spellbook ~ like it used to be!!!"
rnd=random.Random(5)
tf=ImageFont.truetype(COMIC,27)
tg=Image.new('RGBA',(1200,70),(0,0,0,0))
xx=6
for word in msg.split(' '):
    ww=int(tf.getlength(word))+16
    g=Image.new('RGBA',(ww+8,50),(0,0,0,0)); gd=ImageDraw.Draw(g)
    gd.text((7,8),word,font=tf,fill=(110,20,140,255),stroke_width=4,stroke_fill=(110,20,140,255))
    gd.text((4,5),word,font=tf,fill=(150,255,60,255),stroke_width=4,stroke_fill=(0,0,0,255))
    g=g.rotate(rnd.uniform(-2.5,2.5),resample=Image.BICUBIC,expand=True)
    tg.alpha_composite(g,(xx,10+rnd.randint(-3,3)))
    xx+=int(tf.getlength(word))+int(tf.getlength(' '))+rnd.randint(0,4)
tg=tg.crop(tg.getbbox())
tg=tg.rotate(1.2,resample=Image.BICUBIC,expand=True)
big.alpha_composite(tg,(max(0,int((title_end*2-tg.width)/2)+30),148))
bb=big.getbbox(); big=big.crop((max(0,bb[0]-4),max(0,bb[1]-4),bb[2]+4,bb[3]+4))
big.save('/home/claude/tc/art/banner.png',optimize=True)
print(big.size)
