import os
from PIL import Image, ImageDraw, ImageFont
import random, math
random.seed(7)
F=os.path.dirname(os.path.abspath(__file__))+'/'
META=F+'metamorphous-latin-400-normal.woff'
COMIC=F+'comic-neue-latin-700-normal.woff'
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
sp=text.index(' ')
fn=ImageFont.truetype(META,56); _a,_d=fn.getmetrics()
BASE=y0+(64-56)//2+14+(_a-fn.getbbox('n')[1])   # baseline that a plain 'n' would sit on
for i,ch in enumerate(text):
    if ch==' ': x+=14; continue
    if i<sp:   # "Forever" keeps its original wobble
        size=random.choice([52,56,58]) if ch not in 'FI' else 68
        ang=random.uniform(-9,9)
        L=letter(ch,size,ang)
        yy=y0+random.randint(-4,4)+(64-size)//2+(0 if ch not in 'FI' else -4)
    else:      # "Info": same baseline, only a slight tilt
        size=68 if ch=='I' else 56
        ang=random.uniform(-5,5)
        L=letter(ch,size,ang)
        f2=ImageFont.truetype(META,size); a2,_=f2.getmetrics()
        yy=int(BASE-(a2-f2.getbbox(ch)[1])-14)+random.randint(-3,3)
    img.alpha_composite(L,(int(x),yy))
    x+=L.width-33+random.randint(-2,2)
print('text width',x)
d=ImageDraw.Draw(img); d.fontmode='1'
# crude sparkles
def sparkle(cx,cy,r,col=(255,255,255,255)):
    d.line([(cx-r,cy),(cx+r,cy)],fill=col,width=2); d.line([(cx,cy-r),(cx,cy+r)],fill=col,width=2)
    d.line([(cx-r//2,cy-r//2),(cx+r//2,cy+r//2)],fill=col,width=1); d.line([(cx-r//2,cy+r//2),(cx+r//2,cy-r//2)],fill=col,width=1)
for (cx,cy,r) in [(24,14,7),(205,8,5),(470,4,6),(40,88,4)]: sparkle(cx,cy,r)
sparkle(x-4,96,6)
title_end=x
# ---- upscale the janky pixel title, then add smooth, readable extras at 2x ----
big=img.resize((W*2,H*2),Image.NEAREST)
D=ImageDraw.Draw(big)
# starburst sticker: smooth edges, still wonky
cx,cy=(title_end+30)*2,30*2
# classic grocery-store sale burst, drawn 4x and scaled down so the edges are smooth
SS=4; Rb,rb,NP=60,47,18
bw=(Rb+16)*2
burst=Image.new('RGBA',(bw*SS,bw*SS),(0,0,0,0)); bd=ImageDraw.Draw(burst)
def star(dx,dy,grow,col):
    pts=[]
    for k in range(NP*2):
        a=k*math.pi/NP-math.pi/2; rr=(Rb if k%2==0 else rb)+grow
        pts.append(((bw/2+dx+rr*math.cos(a))*SS,(bw/2+dy+rr*math.sin(a))*SS))
    bd.polygon(pts,fill=col)
star(5,6,3,(110,20,140,255))
star(0,0,3.5,(0,0,0,255))
star(0,0,0,(255,226,40,255))
burst=burst.resize((bw,bw),Image.LANCZOS).rotate(-8,resample=Image.BICUBIC)
if not os.environ.get('NOSTICK'): big.alpha_composite(burst,(int(cx-bw/2),int(cy-bw/2)))
st=Image.new('RGBA',(140,60),(0,0,0,0)); sd=ImageDraw.Draw(st)
sf=ImageFont.truetype(os.environ.get('BFONT',F+'comic-relief-latin-700-normal.woff'),int(os.environ.get('BSIZE','29')))
sd.text((70,30),"BETA!",font=sf,fill=(210,0,0,255),anchor='mm')
st=st.rotate(-12,resample=Image.BICUBIC,expand=True)
if not os.environ.get('NOSTICK'): big.alpha_composite(st,(int(cx-st.width/2),int(cy-st.height/2)))
import os
STYLE=os.environ.get("STYLE","A")
msg=os.environ.get("MSG","talents ~ racials ~ spellbook ~ like it used to be!!!")
rnd=random.Random(5)
def place(tg):
    big.alpha_composite(tg,(max(0,int((title_end*2-tg.width)/2)+30),int(os.environ.get('TY','148'))))
def wordy(font,fill,stroke,sfill,shadow,jit=2.5,grad=None):
    tg=Image.new('RGBA',(1300,80),(0,0,0,0)); xx=6
    for word in msg.split(' '):
        ww=int(font.getlength(word))+20
        g=Image.new('RGBA',(ww+10,60),(0,0,0,0)); gd=ImageDraw.Draw(g)
        if shadow: gd.text((7,9),word,font=font,fill=shadow,stroke_width=stroke,stroke_fill=shadow)
        if grad:
            gd.text((4,6),word,font=font,fill=(0,0,0,255),stroke_width=stroke,stroke_fill=sfill)
            m=Image.new('L',g.size,0); ImageDraw.Draw(m).text((4,6),word,font=font,fill=255)
            gi=Image.new('RGBA',g.size)
            for x in range(g.width):
                t=(xx+x)/900; c=grad(t); ImageDraw.Draw(gi).line([(x,0),(x,g.height)],fill=c)
            g.paste(gi,(0,0),m)
        else:
            gd.text((4,6),word,font=font,fill=fill,stroke_width=stroke,stroke_fill=sfill)
        g=g.rotate(rnd.uniform(-jit,jit),resample=Image.BICUBIC,expand=True)
        tg.alpha_composite(g,(xx,10+rnd.randint(-int(os.environ.get('BOB','2')),int(os.environ.get('BOB','2')))))
        xx+=int(font.getlength(word))+int(font.getlength(' '))+rnd.randint(0,3)
    tg=tg.crop(tg.getbbox()); return tg.rotate(1.0,resample=Image.BICUBIC,expand=True)
if STYLE=="F":
    place(wordy(ImageFont.truetype(os.environ["FONT"],int(os.environ["SIZE"])),(150,255,60,255),4,(0,0,0,255),(110,20,140,255),jit=float(os.environ.get("JIT","2.5"))))
elif STYLE=="P":  # aliased pixel font drawn at 1x then doubled, matching the title
    f=ImageFont.truetype(os.environ["FONT"],int(os.environ["SIZE"]))
    t=Image.new('RGBA',(700,40),(0,0,0,0)); d2=ImageDraw.Draw(t); d2.fontmode='1'
    xx=3
    for word in msg.split(' '):
        yy=6+rnd.randint(-1,1)
        d2.text((xx+2,yy+2),word,font=f,fill=(110,20,140,255),stroke_width=1,stroke_fill=(110,20,140,255))
        d2.text((xx,yy),word,font=f,fill=(150,255,60,255),stroke_width=1,stroke_fill=(0,0,0,255))
        xx+=int(f.getlength(word+' '))+rnd.randint(0,1)
    t=t.crop(t.getbbox()); t=t.resize((t.width*2,t.height*2),Image.NEAREST); place(t)
elif STYLE=="L":  # 1997 hyperlink
    f=ImageFont.truetype(os.environ["FONT"],int(os.environ["SIZE"]))
    t=Image.new('RGBA',(1100,50),(0,0,0,0)); d2=ImageDraw.Draw(t)
    w=int(f.getlength(msg))
    d2.text((6,4),msg,font=f,fill=(0,0,0,255),stroke_width=3,stroke_fill=(0,0,0,255))
    d2.text((4,2),msg,font=f,fill=(70,110,255,255),stroke_width=0)
    asc=f.getbbox(msg)[3]
    d2.line([(4,asc+5),(4+w,asc+5)],fill=(0,0,0,255),width=5); d2.line([(4,asc+4),(4+w,asc+4)],fill=(70,110,255,255),width=2)
    t=t.crop(t.getbbox()); place(t)
elif STYLE=="A":   # current lime
    place(wordy(ImageFont.truetype(COMIC,27),(150,255,60,255),4,(0,0,0,255),(110,20,140,255)))
elif STYLE=="B": # chunky pixel, matches title
    f=ImageFont.truetype(META,15)
    t=Image.new('RGBA',(600,40),(0,0,0,0)); d2=ImageDraw.Draw(t); d2.fontmode='1'
    d2.text((4,5),msg,font=f,fill=(110,20,140,255),stroke_width=2,stroke_fill=(110,20,140,255))
    d2.text((2,3),msg,font=f,fill=(255,236,170,255),stroke_width=2,stroke_fill=(0,0,0,255))
    t=t.crop(t.getbbox()); t=t.resize((t.width*2,t.height*2),Image.NEAREST); place(t)
elif STYLE=="C": # 2004 fan-site parchment serif italic
    f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf',24)
    place(wordy(f,(245,225,170,255),3,(40,20,5,255),(0,0,0,200),jit=1.2))
elif STYLE=="D": # white comic, black outline
    place(wordy(ImageFont.truetype(COMIC,27),(255,255,255,255),4,(0,0,0,255),(110,20,140,255)))
elif STYLE=="E": # rainbow WordArt
    import colorsys
    gr=lambda t:tuple(int(v*255) for v in colorsys.hsv_to_rgb((0.55+t*0.9)%1,0.75,1))+(255,)
    place(wordy(ImageFont.truetype(COMIC,27),None,4,(0,0,0,255),(40,10,60,255),grad=gr))
bb=big.getbbox(); box=(max(0,bb[0]-4),max(0,bb[1]-4),bb[2]+4,bb[3]+4)
if os.environ.get('CROP'): box=tuple(int(v) for v in os.environ['CROP'].split(','))
print('BOX',','.join(map(str,box)))
big=big.crop(box)
big.save(os.environ.get('OUT',F+'banner.png'),optimize=True)
print(big.size)
