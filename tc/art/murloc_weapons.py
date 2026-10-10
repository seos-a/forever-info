"""Give the two Hallow's End murlocs a weapon each (Wowhead's model thumbnails come without): a spear held across both
claws for the left one (images/models/540.png -> murloc_spear.png) and a foreshortened scimitar for the right
one (images/models/1005.png, shown mirrored -> murloc_scimitar.png). The weapons are drawn here in front of the body, then
the claws are laid back over the grip so they close round it. Run from the repo root:  py tc/art/murloc_weapons.py"""
import math
from PIL import Image, ImageDraw
SS=4
HANDS=[(105,243),(178,268)]                     # where the two claws close, in the 300 x 300 thumbnail
def P(x,y): return (x*SS,y*SS)
def qb(p0,c,p1,t): return ((1-t)**2*p0[0]+2*(1-t)*t*c[0]+t*t*p1[0],(1-t)**2*p0[1]+2*(1-t)*t*c[1]+t*t*p1[1])
def layer(): return Image.new('RGBA',(300*SS,300*SS),(0,0,0,0))
def finish(weap,src,out,grips):
    weap=weap.resize((300,300),Image.LANCZOS); m=Image.open(src).convert('RGBA')
    im=m.copy(); im.alpha_composite(weap)
    claws=Image.new('L',m.size,0); d=ImageDraw.Draw(claws)
    for x,y,r in grips: d.ellipse((x-r,y-r,x+r,y+r),fill=255)
    claws=Image.composite(m.getchannel('A'),Image.new('L',m.size,0),claws)
    im.paste(m,(0,0),claws)                       # claws back on top of the grip
    im.save(out,optimize=True)

# left murloc: a spear held diagonally in both claws, head up and out past one hand, butt down past the other
L=layer(); d=ImageDraw.Draw(L)
(x1,y1),(x2,y2)=HANDS; ux,uy=x1-x2,y1-y2; l=math.hypot(ux,uy); ux,uy=ux/l,uy/l; nx,ny=-uy,ux
base=(x1+ux*52,y1+uy*52); butt=(x2-ux*58,y2-uy*58)
d.line([P(*butt),P(*base)],fill=(40,42,48,255),width=8*SS)
d.line([P(*butt),P(*base)],fill=(150,152,160,255),width=6*SS)
d.line([P(butt[0]+nx*1.4,butt[1]+ny*1.4),P(base[0]+nx*1.4,base[1]+ny*1.4)],fill=(214,216,224,255),width=SS)
def h(t,w): return (base[0]+ux*t+nx*w, base[1]+uy*t+ny*w)
d.polygon([P(*q) for q in [h(0,-5),h(13,-9),h(44,0),h(13,9),h(0,5)]],fill=(200,204,214,255),outline=(50,54,62,255))
d.line([P(*h(1,0)),P(*h(40,0))],fill=(246,248,252,255),width=SS)
d.line([P(*h(-4,-6)),P(*h(-4,6))],fill=(60,62,70,255),width=5*SS)
d.polygon([P(*q) for q in [butt,(butt[0]-ux*12-nx*3.5,butt[1]-uy*12-ny*3.5),(butt[0]-ux*12+nx*3.5,butt[1]-uy*12+ny*3.5)]],
          fill=(150,152,160,255),outline=(40,42,48,255))
finish(L,'images/models/540.png','images/models/murloc_spear.png',[(x1,y1,11),(x2,y2,12)])

# right murloc (shown mirrored): a scimitar in its lower claw, angled down and toward the viewer, so the blade is
# foreshortened: short, narrow at the guard and widening toward the near end before curling up to the point
L=layer(); d=ImageDraw.Draw(L)
gx,gy=HANDS[1]; p0,c,p1=(gx-6,gy+5),(gx-52,gy+30),(gx-92,gy+12)
N=60; spine=[qb(p0,c,p1,i/N) for i in range(N+1)]
def width(t): return (5+15*min(t/.78,1)**1.2) if t<.84 else 20*(1-t)/.16         # wider as it comes closer
edge=[]
for i,(x,y) in enumerate(spine):
    t=i/N; a=spine[min(i+1,N)]; b=spine[max(i-1,0)]; dx,dy=a[0]-b[0],a[1]-b[1]; l=math.hypot(dx,dy) or 1
    nx,ny=-dy/l,dx/l; w=width(t); edge.append((x+nx*w,y+ny*w) if ny<0 else (x-nx*w,y-ny*w))   # cutting edge on top
d.polygon([P(*q) for q in spine+edge[::-1]],fill=(216,220,228,255),outline=(70,74,84,255))
mid=[(s_[0]*.4+e[0]*.6,s_[1]*.4+e[1]*.6) for s_,e in zip(spine,edge)]
d.line([P(*q) for q in mid[3:-7]],fill=(250,251,255,255),width=2*SS)                  # bright bevel
d.line([P(*q) for q in spine[:-3]],fill=(128,134,146,255),width=SS)
cx,cy=p0; ax,ay=(p0[0]-c[0]),(p0[1]-c[1]); l=math.hypot(ax,ay); ax,ay=ax/l,ay/l       # back along the blade, into the claw
gnx,gny=-ay,ax
d.line([P(cx+gnx*8,cy+gny*8),P(cx-gnx*8,cy-gny*8)],fill=(40,30,18,255),width=6*SS)    # crossguard
d.line([P(cx+gnx*8,cy+gny*8),P(cx-gnx*8,cy-gny*8)],fill=(196,160,72,255),width=4*SS)
d.line([P(cx+ax*2,cy+ay*2),P(cx+ax*14,cy+ay*14)],fill=(30,20,14,255),width=6*SS)      # grip, running away from us
d.line([P(cx+ax*2,cy+ay*2),P(cx+ax*14,cy+ay*14)],fill=(82,56,36,255),width=4*SS)
px_,py_=cx+ax*16,cy+ay*16; d.ellipse([P(px_-3,py_-3),P(px_+3,py_+3)],fill=(196,160,72,255),outline=(40,30,18,255),width=SS)  # small far pommel
finish(L,'images/models/1005.png','images/models/murloc_scimitar.png',[(gx,gy,11)])
print('ok')
