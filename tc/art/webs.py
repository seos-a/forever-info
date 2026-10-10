"""Cobwebs for the Hallow's End title bars: thin light-grey threads, corner webs built like real ones (frame, hub, spokes, rungs; threads only meet end to end).
Drawn at 2x (crisp on high-DPI screens), supersampled 4x for smooth lines. Coordinates are CSS px from the bar's top-left."""
import math, random
from PIL import Image, ImageDraw
M=6; R=2; SS=4; K=R*SS                      # margin round the bar, output scale, supersample
THREAD=(226,226,220,235)
def canvas(w,h): return Image.new('RGBA',((w+2*M)*K,(h+2*M)*K),(0,0,0,0))
def P(x,y): return ((x+M)*K,(y+M)*K)
def quad(p0,c,p1,n=24):
    return [((1-t)**2*p0[0]+2*(1-t)*t*c[0]+t*t*p1[0],(1-t)**2*p0[1]+2*(1-t)*t*c[1]+t*t*p1[1]) for t in (i/n for i in range(n+1))]
def thread(d,pts,w=1.0): d.line([P(*p) for p in pts],fill=THREAD,width=max(1,round(w*K)),joint='curve')
def corner_web(d,cx,cy,sx,sy,rx,ry,seed,rings=(.38,.68,.95),spokes=(4,28,52,76,88)):
    rnd=random.Random(seed)
    ends=[]
    for a in spokes:
        t=math.radians(a); f=1+rnd.uniform(-.04,.04)
        ends.append((cx+sx*rx*f*math.cos(t), cy+sy*ry*f*math.sin(t)))
        thread(d,[(cx,cy),ends[-1]],.8)
    for r in rings:
        for i in range(len(spokes)-1):
            p0=(cx+(ends[i][0]-cx)*r,cy+(ends[i][1]-cy)*r); p1=(cx+(ends[i+1][0]-cx)*r,cy+(ends[i+1][1]-cy)*r)
            mx,my=(p0[0]+p1[0])/2,(p0[1]+p1[1])/2
            c=(cx+(mx-cx)*.78,cy+(my-cy)*.78)                     # sag toward the corner
            thread(d,quad(p0,c,p1),.75)
def spider(d,c,rx,ry,tilt,reach,seed,hang=0):
    rnd=random.Random(seed); cx,cy=c; s=.72                       # spider units -> CSS px
    if hang: thread(d,[(cx,cy-ry*s-hang),(cx,cy-ry*s)],.6)
    def rot(x,y):
        t=math.radians(tilt); return (x*math.cos(t)-y*math.sin(t), x*math.sin(t)+y*math.cos(t))
    for sx in (-1,1):
        for base in (-35,5,40):
            a=math.radians(base+rnd.uniform(-12,12)); L1=(4.5+rnd.uniform(-.8,.8))*reach; L2=(3.2+rnd.uniform(-.8,1))*reach
            hx,hy=rx*.8*math.cos(a),ry*.8*math.sin(a); kx,ky=hx+L1*math.cos(a),hy+L1*math.sin(a)-1
            b=math.radians(55+rnd.uniform(-15,20)); fx,fy=kx+L2*math.cos(a+b),ky+L2*math.sin(a+b)
            pts=[rot(sx*x*s,y*s) for x,y in ((hx,hy),(kx,ky),(fx,fy))]
            d.line([P(cx+x,cy+y) for x,y in pts],fill=(0,0,0,255),width=round(1.3*K),joint='curve')
    d.ellipse([*P(cx-rx*s,cy-ry*s),*P(cx+rx*s,cy+ry*s)],fill=(0,0,0,255))
def save(im,path): im.resize((im.width//SS,im.height//SS),Image.LANCZOS).save(path,optimize=True)

def silk(p0,p1,sag,seed=0,n=48):
    """A strand anchored at p0 and p1 that droops a little under its own weight, with a faint waver."""
    rnd=random.Random(seed); ph=rnd.uniform(0,6.3); dx,dy=p1[0]-p0[0],p1[1]-p0[1]; L=math.hypot(dx,dy) or 1
    nx,ny=-dy/L,dx/L
    out=[]
    for i in range(n+1):
        t=i/n; w=.22*math.sin(t*math.pi*3+ph)*math.sin(t*math.pi)
        out.append((p0[0]+dx*t+nx*w, p0[1]+dy*t+sag*4*t*(1-t)+ny*w))
    return out
def at(pts,f): return pts[round(f*(len(pts)-1))]

def corner_orb(d,corner,sx,sy,side,top,seed,hub=(.32,.36),fr=(.14,.38,.62,.86),rings=9,sag=None):
    """A web in a corner, built the way real ones are: a frame thread draped from the side edge to the top (or bottom) edge,
    a hub inside it, spokes from the hub that end on the frame, the edges or the corner, and rungs between neighbouring
    spokes, closest near the hub. Threads only ever meet end to end; nothing crosses anything.
    corner: the bar corner; sx/sy: +1/-1 pointing into the bar; side: distance down the side edge; top: distance along the top edge."""
    rnd=random.Random(seed); cx,cy=corner
    def xy(u,v): return (cx+sx*u, cy+sy*v)
    F=silk(xy(0,side),xy(top,0),(sag if sag is not None else .1*math.hypot(top,side))*(1 if sy>0 else -1),rnd.randrange(99))
    thread(d,F,.8)
    h=xy(top*hub[0],side*hub[1])
    targets=[xy(0,0),xy(0,side*.55),xy(top*.55,0)]+[at(F,f) for f in fr]
    targets.sort(key=lambda p:math.atan2(p[1]-h[1],p[0]-h[0]))
    spokes=[silk(h,t,.15,rnd.randrange(99)) for t in targets]
    for sp in spokes: thread(d,sp,.65)
    lens=[math.hypot(t[0]-h[0],t[1]-h[1]) for t in targets]
    r=3.0; k=0
    while k<rings:
        for i in range(len(spokes)):
            j=(i+1)%len(spokes)
            a1=math.atan2(targets[i][1]-h[1],targets[i][0]-h[0]); a2=math.atan2(targets[j][1]-h[1],targets[j][0]-h[0])
            if (a2-a1)%(2*math.pi)>2.6 or r>.8*min(lens[i],lens[j]) or rnd.random()<.08: continue   # no rung across a wide gap
            pa=at(spokes[i],r/lens[i]); pb=at(spokes[j],r/lens[j]); m=((pa[0]+pb[0])/2,(pa[1]+pb[1])/2)
            thread(d,quad(pa,(h[0]+(m[0]-h[0])*.88,h[1]+(m[1]-h[1])*.88),pb,10),.5)
        r+=2.2+r*.18+rnd.uniform(-.3,.3); k+=1                       # gaps widen a little outward
    return F,h

def hanging_orb(d,hub,verts,seed,moor=(),rings=10):
    """An orb web hung in open space: an uneven frame of sagging threads round the hub, spokes from the hub to the frame
    corners and to the middle of each frame thread, rungs scalloped in toward the hub, and mooring lines from frame
    corners out to the panel edges. verts: (angle in degrees, distance) of each frame corner, in order round the hub."""
    rnd=random.Random(seed); hx,hy=hub
    V=[(hx+r*math.cos(math.radians(a)),hy+r*math.sin(math.radians(a))) for a,r in verts]
    targets=[]
    for i in range(len(V)):
        e=silk(V[i],V[(i+1)%len(V)],.9,rnd.randrange(99)); thread(d,e,.75)
        targets+= [V[i],at(e,rnd.uniform(.4,.6))]
    for k,end in moor: thread(d,silk(V[k],end,.6,rnd.randrange(99)),.65)
    spokes=[silk(hub,t,.1,rnd.randrange(99)) for t in targets]
    for sp in spokes: thread(d,sp,.6)
    lens=[math.hypot(t[0]-hx,t[1]-hy) for t in targets]
    r=2.6
    for _ in range(rings):
        for i in range(len(spokes)):
            j=(i+1)%len(spokes)
            if r>.86*min(lens[i],lens[j]) or rnd.random()<.07: continue
            pa=at(spokes[i],r/lens[i]); pb=at(spokes[j],r/lens[j]); m=((pa[0]+pb[0])/2,(pa[1]+pb[1])/2)
            thread(d,quad(pa,(hx+(m[0]-hx)*.88,hy+(m[1]-hy)*.88),pb,10),.5)
        r+=1.9+r*.12+rnd.uniform(-.25,.25)

def corner_poly(d,corner,sx,sy,hub,frame,seed,anchors=(),rings=10):
    """A corner web whose outer edge is a chain of short frame threads (a lopsided polygon, not one round sweep): the first
    point sits on the side edge, the last on the top/bottom edge. Spokes run from the hub to every frame corner and to the
    middle of each frame thread, rungs scallop between neighbouring spokes, and anchor lines tie frame corners to the edges.
    Points are (u, v): u along the top/bottom edge away from the corner, v along the side edge."""
    rnd=random.Random(seed); cx,cy=corner
    def xy(q): return (cx+sx*q[0], cy+sy*q[1])
    hx,hy=xy(hub); V=[xy(q) for q in frame]
    targets=[xy((0,0))]
    for i in range(len(V)-1):
        e=silk(V[i],V[i+1],.5*(1 if sy>0 else -1),rnd.randrange(99)); thread(d,e,.75)
        targets+=[V[i],at(e,rnd.uniform(.42,.58))]
    targets.append(V[-1])
    for k,end in anchors: thread(d,silk(V[k],xy(end),.3,rnd.randrange(99)),.6)
    targets.sort(key=lambda p:math.atan2(p[1]-hy,p[0]-hx))
    spokes=[silk((hx,hy),t,.1,rnd.randrange(99)) for t in targets]
    for sp in spokes: thread(d,sp,.6)
    lens=[math.hypot(t[0]-hx,t[1]-hy) for t in targets]
    r=2.6
    for _ in range(rings):
        for i in range(len(spokes)):
            j=(i+1)%len(spokes)
            a1=math.atan2(targets[i][1]-hy,targets[i][0]-hx); a2=math.atan2(targets[j][1]-hy,targets[j][0]-hx)
            if (a2-a1)%(2*math.pi)>2.6 or r>.86*min(lens[i],lens[j]) or rnd.random()<.07: continue
            pa=at(spokes[i],r/lens[i]); pb=at(spokes[j],r/lens[j]); m=((pa[0]+pb[0])/2,(pa[1]+pb[1])/2)
            thread(d,quad(pa,(hx+(m[0]-hx)*.88,hy+(m[1]-hy)*.88),pb,10),.5)
        r+=2.0+r*.14+rnd.uniform(-.25,.25)

def wobbly(p0,p1,sag,seed,amp=.55,n=40):
    """A loose, hand-drawn-looking thread: droops by sag and wanders a little side to side along its length."""
    rnd=random.Random(seed); f1,f2=rnd.uniform(1.2,2.4),rnd.uniform(2.8,4.5); ph1,ph2=rnd.uniform(0,6.3),rnd.uniform(0,6.3)
    dx,dy=p1[0]-p0[0],p1[1]-p0[1]; L=math.hypot(dx,dy) or 1; nx,ny=-dy/L,dx/L; a=amp*min(1,L/30)
    out=[]
    for i in range(n+1):
        t=i/n; w=(a*math.sin(t*math.pi*f1+ph1)+.5*a*math.sin(t*math.pi*f2+ph2))*math.sin(t*math.pi)
        out.append((p0[0]+dx*t+nx*w, p0[1]+dy*t+sag*4*t*(1-t)+ny*w))
    return out
def loose_corner(d,corner,sx,sy,hub,ends,seed,rungs=(2,4)):
    """A simple, loose corner web: a few wobbly spokes from the hub out to the edges or a flowing frame, and only a handful
    of uneven rungs between neighbouring spokes. ends: spoke ends as (u, v) from the corner."""
    rnd=random.Random(seed); cx,cy=corner
    def xy(q): return (cx+sx*q[0], cy+sy*q[1])
    hx,hy=xy(hub); E=[xy(e) for e in ends]
    E.sort(key=lambda p:math.atan2(p[1]-hy,p[0]-hx))
    spokes=[wobbly((hx,hy),e,rnd.uniform(-.6,.9),rnd.randrange(999),.45) for e in E]
    for sp in spokes: thread(d,sp,.65)
    for a,b in zip(spokes,spokes[1:]):
        la,lb=math.hypot(a[-1][0]-hx,a[-1][1]-hy),math.hypot(b[-1][0]-hx,b[-1][1]-hy)
        if abs(math.atan2(b[-1][1]-hy,b[-1][0]-hx)-math.atan2(a[-1][1]-hy,a[-1][0]-hx))>2.4: continue
        fs=sorted(rnd.uniform(.18,.85) for _ in range(rnd.randint(*rungs)))
        for f in fs:
            pa,pb=at(a,f*rnd.uniform(.9,1.1)),at(b,f*rnd.uniform(.9,1.1))
            thread(d,wobbly(pa,pb,rnd.uniform(.6,2.2),rnd.randrange(999),.35),.55)
    return spokes

W,H=223,32
# Classes: a web in the top-left corner, spider on its frame; one long draped thread from the bottom edge up to a
# spider hanging top-right
im=canvas(W,H); d=ImageDraw.Draw(im)
F,h=corner_orb(d,(0,0),1,1,29,56,seed=21)
p=at(F,.62); spider(d,(p[0]+1,p[1]-1),5,4.5,-15,1.0,3)
thread(d,silk((60,32),(206,0),7,24),.8)
spider(d,(206,12),4,4,10,.85,11,hang=8)
save(im,'art/web-classes.png')

# Quick Info: a tall, narrow web down the right edge (running a little past the bar), spider dangling below its hub, one torn
# thread hanging loose from the frame
im=canvas(W,H+10); d=ImageDraw.Draw(im)
F,h=corner_orb(d,(W,0),-1,1,40,34,seed=1,hub=(.36,.32),fr=(.18,.45,.72),rings=8,sag=3)
tear=at(F,.3); thread(d,quad(tear,(tear[0]+2,tear[1]+5),(tear[0]-1,tear[1]+9),12),.55)
spider(d,(h[0]-1,h[1]+14),4,5,0,1.0,5,hang=7)   # dangling below the hub so the web shows
save(im,'art/web-quick.png')

# Search: a wider web across the top-left corner with a long mooring line from its frame out along the top edge;
# spider walking the frame
im=canvas(W,H); d=ImageDraw.Draw(im)
F,h=corner_orb(d,(0,0),1,1,26,92,seed=6,hub=(.26,.38))
thread(d,silk(at(F,.93),(126,0),.4,9),.6)
p=at(F,.55); spider(d,(p[0]+1,p[1]-2),6,5,-25,1.0,8)
save(im,'art/web-search.png')

# Load: a tiny web in the top-right corner; the smallest spider dangling under it
im=canvas(99,31); d=ImageDraw.Draw(im)
F,h=corner_orb(d,(99,0),-1,1,20,32,seed=11,hub=(.33,.38),fr=(.25,.6,.88),rings=5)
p=at(F,.3); spider(d,(p[0],p[1]+7),3.5,3.5,-30,.8,2,hang=4)
save(im,'art/web-load.png')

# Stats panel (a fixed 1202 x 77 on desktop; its inner frame line is ~6px in): simple, loose corner webs in the top-left
# (over the corner beside "Current level") and bottom-right (below Reset All) corners, and in the empty gap between Split and the controls
# a single diagonal strand from the bottom frame line up to the top one with a spider hanging off it, like the Classes bar.
# One image over the whole panel, placed at (-6, -6).
PW,PH,FR=1202,77,6
im=canvas(PW,PH); d=ImageDraw.Draw(im)
sp=loose_corner(d,(FR,FR),1,1,(20,11),[(0,0),(0,33),(46,24),(82,11),(104,0)],seed=71)
p=at(sp[1],.58); spider(d,(p[0],p[1]+1),4,3.5,-20,.9,74)                        # two spiders: one walking a spoke out to the top,
p=at(sp[2],.5); spider(d,(p[0],p[1]+8),3,3,25,.75,75,hang=5)                          # a smaller one dropping from another
thread(d,wobbly((FR+82,FR+11),(FR+138,FR),1.5,72),.6)                     # a stray line out to the top frame
loose_corner(d,(PW-FR,PH-FR),-1,-1,(16,6),[(0,0),(0,17),(36,13),(70,0)],seed=73,rungs=(2,3))
spider(d,(PW-FR-34,PH-FR-12),3.5,3.5,15,.8,63)
thread(d,silk((598,PH-FR),(737,FR),6,64),.8)
spider(d,(728,20),4,4,-10,.9,65,hang=9)
save(im,'art/web-stats.png')
