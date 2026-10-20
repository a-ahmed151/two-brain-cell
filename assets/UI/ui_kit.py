import json, os, base64, io, zipfile
from PIL import Image, ImageDraw

PALHEX = {
 'K':'#1a1220','1':'#2b1d2e','2':'#4a3448','3':'#6b4e63','4':'#8a6a7d',
 'w':'#4a2c1c','W':'#7a4a2a','L':'#a86a3a',
 'y':'#b07a1a','Y':'#e8b13a','Z':'#ffe27a',
 'm':'#4d5566','M':'#8a94a8','N':'#c8d0e0','O':'#f2f0e6',
 'r':'#6e1c2a','R':'#b8333a','P':'#e85a5a',
 'e':'#1f5a2e','E':'#3a9a4a','G':'#7ad86a',
 'x':'#a09078','X':'#d8ccb0',
}
C = {k: tuple(int(v[i:i+2],16) for i in (1,3,5))+(255,) for k,v in PALHEX.items()}

def img(w,h): return Image.new('RGBA',(w,h),(0,0,0,0))
def R(im,x,y,w,h,ch):
    if w>0 and h>0: ImageDraw.Draw(im).rectangle((x,y,x+w-1,y+h-1),fill=C[ch])
def Px(im,x,y,ch):
    if 0<=x<im.width and 0<=y<im.height: im.putpixel((x,y),C[ch])
def clear(im,x,y):
    if 0<=x<im.width and 0<=y<im.height: im.putpixel((x,y),(0,0,0,0))
def outline(im,ch='K'):
    w,h=im.size; a=im.load(); o=im.copy(); b=o.load()
    for y in range(h):
        for x in range(w):
            if a[x,y][3]==0:
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    xx,yy=x+dx,y+dy
                    if 0<=xx<w and 0<=yy<h and a[xx,yy][3]>0: b[x,y]=C[ch]; break
    return o
def pad(im,n=1):
    o=img(im.width+2*n,im.height+2*n); o.alpha_composite(im,(n,n)); return o
def silhouette(im,ch):
    o=img(*im.size); a=im.load(); b=o.load()
    for y in range(im.height):
        for x in range(im.width):
            if a[x,y][3]>0: b[x,y]=C[ch]
    return o
def from_rows(rs,ch='Y',m=None):
    im=img(len(rs[0]),len(rs))
    for y,r in enumerate(rs):
        for x,c in enumerate(r):
            if c=='#': Px(im,x,y,ch)
            elif m and c in m: Px(im,x,y,m[c])
    return im

# ---------------- 5x7 pixel font ----------------
G = {
'A':[".###.","#...#","#...#","#####","#...#","#...#","#...#"],
'B':["####.","#...#","#...#","####.","#...#","#...#","####."],
'C':[".###.","#...#","#....","#....","#....","#...#",".###."],
'D':["####.","#...#","#...#","#...#","#...#","#...#","####."],
'E':["#####","#....","#....","####.","#....","#....","#####"],
'F':["#####","#....","#....","####.","#....","#....","#...."],
'G':[".###.","#...#","#....","#.###","#...#","#...#",".####"],
'H':["#...#","#...#","#...#","#####","#...#","#...#","#...#"],
'I':[".###.","..#..","..#..","..#..","..#..","..#..",".###."],
'J':["..###","...#.","...#.","...#.","...#.","#..#.",".##.."],
'K':["#...#","#..#.","#.#..","##...","#.#..","#..#.","#...#"],
'L':["#....","#....","#....","#....","#....","#....","#####"],
'M':["#...#","##.##","#.#.#","#.#.#","#...#","#...#","#...#"],
'N':["#...#","#...#","##..#","#.#.#","#..##","#...#","#...#"],
'O':[".###.","#...#","#...#","#...#","#...#","#...#",".###."],
'P':["####.","#...#","#...#","####.","#....","#....","#...."],
'Q':[".###.","#...#","#...#","#...#","#.#.#","#..#.",".##.#"],
'R':["####.","#...#","#...#","####.","#.#..","#..#.","#...#"],
'S':[".####","#....","#....",".###.","....#","....#","####."],
'T':["#####","..#..","..#..","..#..","..#..","..#..","..#.."],
'U':["#...#","#...#","#...#","#...#","#...#","#...#",".###."],
'V':["#...#","#...#","#...#","#...#","#...#",".#.#.","..#.."],
'W':["#...#","#...#","#...#","#.#.#","#.#.#","#.#.#",".#.#."],
'X':["#...#","#...#",".#.#.","..#..",".#.#.","#...#","#...#"],
'Y':["#...#","#...#",".#.#.","..#..","..#..","..#..","..#.."],
'Z':["#####","....#","...#.","..#..",".#...","#....","#####"],
'0':[".###.","#...#","#..##","#.#.#","##..#","#...#",".###."],
'1':["..#..",".##..","..#..","..#..","..#..","..#..",".###."],
'2':[".###.","#...#","....#","...#.","..#..",".#...","#####"],
'3':["####.","....#","....#",".###.","....#","....#","####."],
'4':["...#.","..##.",".#.#.","#..#.","#####","...#.","...#."],
'5':["#####","#....","####.","....#","....#","#...#",".###."],
'6':["..##.",".#...","#....","####.","#...#","#...#",".###."],
'7':["#####","....#","...#.","..#..",".#...",".#...",".#..."],
'8':[".###.","#...#","#...#",".###.","#...#","#...#",".###."],
'9':[".###.","#...#","#...#",".####","....#","...#.",".##.."],
' ':["....."]*7,
':':[".....","..#..","..#..",".....","..#..","..#..","....."],
'%':["##...","##..#","...#.","..#..",".#...","#..##","...##"],
'!':["..#..","..#..","..#..","..#..","..#..",".....","..#.."],
'?':[".###.","#...#","....#","...#.","..#..",".....","..#.."],
'-':[".....",".....",".....",".###.",".....",".....","....."],
'/':["....#","....#","...#.","..#..",".#...","#....","#...."],
'.':[".....",".....",".....",".....",".....",".##..",".##.."],
"'":["..#..","..#..",".....",".....",".....",".....","....."],
',':[".....",".....",".....",".....",".##..","..#..",".#..."],
'<':["...#.","..#..",".#...","#....",".#...","..#..","...#."],
'>':[".#...","..#..","...#.","....#","...#.","..#..",".#..."],
'X2':[".....","#...#",".#.#.","..#..",".#.#.","#...#","....."],
}
GOLD_GRAD=['Z','Z','Y','Y','Y','y','y']
def text(s,col='X',scale=1,shadow='K',grad=None,outline_=None,sh_off=1):
    s=s.upper(); w=max(1,len(s)*6*scale-scale); h=7*scale
    g=img(w,h)
    for i,ch in enumerate(s):
        for y,row in enumerate(G.get(ch,G['?'])):
            for x,c in enumerate(row):
                if c=='#':
                    colr=grad[y] if grad else col
                    R(g,i*6*scale+x*scale,y*scale,scale,scale,colr)
    if outline_: g=outline(pad(g),outline_)
    if shadow:
        o=img(g.width+sh_off,g.height+sh_off)
        o.alpha_composite(silhouette(g,shadow),(sh_off,sh_off)); o.alpha_composite(g,(0,0)); return o
    return g
def tw(s,scale=1): return len(s)*6*scale-scale

# ---------------- panels ----------------
def panel(w,h,inner='1'):
    im=img(w,h)
    R(im,0,0,w,h,'K'); R(im,1,1,w-2,h-2,'3')
    R(im,1,1,w-2,1,'4'); R(im,1,1,1,h-2,'4'); R(im,1,h-2,w-2,1,'2'); R(im,w-2,1,1,h-2,'2')
    for x in range(10,w-6,12):
        Px(im,x,1,'2'); Px(im,x,2,'2'); Px(im,x,3,'2'); Px(im,x,h-2,'1'); Px(im,x,h-3,'2'); Px(im,x,h-4,'2')
    for y in range(10,h-6,12):
        for x in (1,2,3,w-2,w-3,w-4): Px(im,x,y,'2')
    R(im,4,4,w-8,h-8,'K'); R(im,5,5,w-10,h-10,inner)
    R(im,5,5,w-10,1,'K')
    for y in range(6,h-5):
        for x in range(5,w-5):
            if (x*7+y*13)%37==0: Px(im,x,y,'2' if inner=='1' else '3')
    for cx,cy in ((1,1),(w-4,1),(1,h-4),(w-4,h-4)):
        R(im,cx,cy,3,3,'Y'); Px(im,cx,cy,'Z'); Px(im,cx+2,cy+2,'y'); Px(im,cx+1,cy+1,'Z')
    return im
def ribbon(w,h=20):
    im=img(w,h)
    # tails
    for side in (0,1):
        x0=0 if side==0 else w-14
        R(im,x0,4,14,h-4,'r')
        for i in range(5):
            y=4+(h-4)//2-2+i
            if side==0: R(im,x0,y,5-abs(i-2)*2 if i!=2 else 4,1,'.' if False else 'r')
    R(im,0,4,14,h-4,'r'); R(im,w-14,4,14,h-4,'r')
    for i in range(h-4):  # notches
        d=max(0,4-abs(i-(h-4)//2))
        for x in range(d): clear(im,x,4+i); clear(im,w-1-x,4+i)
    R(im,8,0,w-16,h-4,'R'); R(im,8,0,w-16,2,'P'); R(im,8,h-6,w-16,1,'r')
    R(im,8,h-4,6,1,'K'); R(im,w-14,h-4,6,1,'K')
    for x in range(10,w-10,2): Px(im,x,3,'Y')
    for x in range(10,w-10,2): Px(im,x,h-8,'Y')
    return outline(pad(im))

# ---------------- buttons ----------------
BTN={'stone':{'n':('2','3','1','y','X'),'h':('3','4','2','Y','Z'),'p':('1','2','K','y','x')},
     'red':  {'n':('R','P','r','Y','O'),'h':('P','O','R','Z','O'),'p':('r','R','K','y','X')},
     'gold': {'n':('y','Y','w','Z','O'),'h':('Y','Z','y','Z','O'),'p':('w','y','K','Y','X')}}
def button(w,h,state='n',variant='stone',label=None,icon=None):
    fill,hi,sh,rim,tc=BTN[variant][state]
    im=img(w,h); top=2 if state=='p' else 0
    R(im,0,top,w,h-top,'K')
    if state=='p':
        R(im,1,top+1,w-2,h-top-2,rim); R(im,2,top+2,w-4,h-top-4,fill); R(im,2,top+2,w-4,1,hi)
    else:
        R(im,1,1,w-2,h-4,rim); R(im,2,2,w-4,h-6,fill); R(im,2,2,w-4,1,hi)
        R(im,1,h-3,w-2,2,sh)
    for (x,y) in ((0,top),(w-1,top),(0,h-1),(w-1,h-1)): clear(im,x,y)
    face_h=(h-top-2) if state=='p' else h-4
    cy=top+1+face_h//2
    if label:
        shc='K' if variant=='stone' else ('r' if variant=='red' else 'w')
        t=text(label,tc,1,shc)
        if icon is not None:
            ic=icon(tc,shc); tot=ic.width+5+tw(label); x0=(w-tot)//2
            im.alpha_composite(ic,(x0,cy-ic.height//2)); im.alpha_composite(t,(x0+ic.width+5,cy-4))
            return im
        im.alpha_composite(t,((w-tw(label))//2,cy-4))
    if icon is not None:
        ic=icon(tc,'K' if variant=='stone' else 'r')
        im.alpha_composite(ic,((w-ic.width)//2+0,cy-ic.height//2))
    return im

ICONS={
'back':["...#.....","..##.....",".#######.","########.",".#######.","..##.....","...#....."],
'left':["...##","..##.",".##..","##...",".##..","..##.","...##"],
'right':["##...",".##..","..##.","...##","..##.",".##..","##..."],
'gear':["....#....",".#.###.#.","..#####..",".##...##.","###...###",".##...##.","..#####..",".#.###.#.","....#...."],
'close':["##...##","###.###",".#####.","..###..",".#####.","###.###","##...##"],
'home':["....#....","...###...","..#####..",".#######.","#########",".##...##.",".##.#.##.",".##.#.##."],
'music':["..#####","..#####","..#...#","..#...#",".##..##","###.###","###.###",".#...#."],
'sound':["...#.....","..##..#..","####...#.","####.#.#.","####...#.","..##..#..","...#....."],
'play':["#....","##...","###..","####.","###..","##...","#...."],
'door':["..###..",".#...#.","#.....#","#.....#","#...#.#","#.....#","#######"],
'exit':["####...","#......","#...#..","#.#####","#...#..","#......","####..."],
'fullscreen':["##...##","#.....#",".......",".......",".......","#.....#","##...##"],
'shake':["#.#####.#","#.#...#.#","..#...#..","#.#...#.#","..#...#..","#.#...#.#","#.#####.#"],
'globe':["..###..",".#.#.#.","#######","#..#..#","#######",".#.#.#.","..###.."],
'pause':["##.##","##.##","##.##","##.##","##.##","##.##","##.##"],
}
def icon_fn(name):
    def f(tc,sh):
        g=from_rows(ICONS[name],tc)
        o=img(g.width+1,g.height+1); o.alpha_composite(silhouette(g,sh),(1,1)); o.alpha_composite(g,(0,0)); return o
    return f

# ---------------- level tiles ----------------
PADLOCK=["..###..",".#...#.",".#...#.","#######","###.###","###.###","#######"]
def level_tile(state,num=None,hover=False):
    im=img(28,28); R(im,0,0,28,28,'K')
    frame=('Y','Z','y') if (state=='current' or hover) else ('3','4','2')
    if hover and state!='current': frame=('4','X','3')
    R(im,1,1,26,26,frame[0]); R(im,1,1,26,1,frame[1]); R(im,1,1,1,26,frame[1]); R(im,1,26,26,1,frame[2]); R(im,26,1,1,26,frame[2])
    inner={'locked':'1','open':'2','done':'2','current':'3'}[state]
    R(im,3,3,22,22,'K'); R(im,4,4,20,20,inner); R(im,4,4,20,1,'K' if inner=='1' else '1')
    for c in ((0,0),(27,0),(0,27),(27,27)): clear(im,*c)
    if state=='locked':
        lk=from_rows(PADLOCK,'Y',None)
        for y in range(3):
            for x in range(7):
                if PADLOCK[y][x]=='#': lk.putpixel((x,y),C['M'])
        lk.putpixel((3,4),C['K']); lk.putpixel((3,5),C['K']); lk.putpixel((0,3),C['Z'])
        lk=outline(pad(lk)); im.alpha_composite(lk,(10,9))
    elif num is not None:
        s=str(num); col={'open':'X','done':'Z','current':'O'}[state]
        t=text(s,col,2,'K',sh_off=1); im.alpha_composite(t,((28-tw(s,2))//2,7))
    return im
import math
def door_tile(state,hover=False):
    im=img(28,28); gold=(state=='current' or hover)
    fr=('Y','Z','y') if gold else ('3','4','2')
    def inside(x,y,r,cy=14.0):
        dx=x+0.5-14
        return abs(dx)<=r if y+0.5>=cy else dx*dx+(y+0.5-cy)**2<=r*r
    for y in range(3,27):
        for x in range(28):
            if inside(x,y,11.5) and not inside(x,y,8.5):
                seg=int((math.atan2(y+0.5-14,x+0.5-14)+math.pi)/(math.pi/6)) if y<14 else y//4
                ch=fr[0] if seg%2==0 else fr[2]
                if not inside(x,y,10.5): ch=fr[1] if y<20 else fr[0]
                Px(im,x,y,ch)
            elif inside(x,y,8.5):
                if state=='done':
                    Px(im,x,y,'K' if y<20 else ('1' if y<24 else '2'))
                else:
                    px=(x-6)%4; wood=('w','W','W','w') if state=='locked' else ('w','L','W','W')
                    Px(im,x,y,wood[px])
    if state=='done':
        for (x,y) in ((12,22),(15,23),(13,24),(16,21)): Px(im,x,y,'y')
        Px(im,14,22,'Y'); Px(im,10,24,'3')
    else:
        for by in (13,21):
            for x in range(28):
                if inside(x,by,8.5): Px(im,x,by,'m'); Px(im,x,by-1,'M')
        if state=='locked':
            for i in range(-8,9):
                for (cx,sg) in ((14,1),(14,-1)):
                    x=cx+i; y=17+sg*round(i*0.9)
                    if inside(x,y,8.5): Px(im,x,y,'M' if i%2 else 'm')
            lk=from_rows(PADLOCK,'Y')
            for yy in range(3):
                for xx in range(7):
                    if PADLOCK[yy][xx]=='#': lk.putpixel((xx,yy),C['M'])
            lk.putpixel((3,4),C['K']); lk.putpixel((3,5),C['K'])
            im.alpha_composite(outline(pad(lk)),(10,15))
        else:
            R(im,17,17,2,2,'Y'); Px(im,17,17,'Z')
            if state=='current':
                Px(im,10,18,'Z'); R(im,10,19,1,2,'K')
    R(im,2,26,24,1,'K')
    im=outline(im)
    # number plaque
    pc=('M','N','m') if state=='locked' else ('Y','Z','y')
    R(im,6,0,16,10,'K'); R(im,7,1,14,8,pc[0]); R(im,7,1,14,1,pc[1]); R(im,7,8,14,1,pc[2])
    return im
STAR=["...#...","..###..","#######",".#####.","..###..",".##.##.","##...##"]
def star(filled):
    g=from_rows(STAR,'Y' if filled else '2')
    if filled:
        for x in range(7):
            if STAR[2][x]=='#': g.putpixel((x,2),C['Z'])
        g.putpixel((3,0),C['Z']); g.putpixel((3,1),C['Z'])
    return outline(pad(g))

# ---------------- slider / toggle / cursor ----------------
def slider_track(w):
    im=img(w,8); R(im,0,0,w,8,'K'); R(im,1,1,w-2,6,'1'); R(im,1,1,w-2,1,'K')
    for x in range(4,w-2,8): Px(im,x,6,'2')
    clear(im,0,0); clear(im,w-1,0); clear(im,0,7); clear(im,w-1,7)
    return im
def slider_fill(w):
    im=img(max(1,w),5); R(im,0,0,w,5,'Y'); R(im,0,0,w,1,'Z'); R(im,0,4,w,1,'y'); return im
KNOB=["...#...","..#M#..",".#MMN#.","#MMMMN#","#M###N#","#M#M#N#","#MMMMN#","#M#M#N#","#######"]
def knob():
    im=img(7,9)
    for y,r in enumerate(KNOB):
        for x,c in enumerate(r):
            if c=='#': Px(im,x,y,'K')
            elif c=='M': Px(im,x,y,'M')
            elif c=='N': Px(im,x,y,'N')
    for x in range(1,6):
        if KNOB[0][x]=='.' : pass
    return pad(im)
def toggle(on,hover=False):
    im=img(26,12); R(im,0,0,26,12,'K')
    R(im,1,1,24,10,'E' if on else '1'); R(im,1,1,24,1,'G' if on else 'K')
    for c in ((0,0),(25,0),(0,11),(25,11)): clear(im,*c)
    kx=14 if on else 1
    R(im,kx,1,11,10,'K'); R(im,kx+1,2,9,8,'N' if hover else 'M'); R(im,kx+1,2,9,1,'O' if hover else 'N'); R(im,kx+1,9,9,1,'m')
    R(im,kx+4,4,1,4,'m'); R(im,kx+6,4,1,4,'m')
    return im
def cursor():
    g=from_rows(["..y.........","wwYNNNNNNNNO","..y........."],'Y',{'y':'y','w':'w','Y':'Y','N':'N','O':'O'})
    return outline(pad(g))

# ---------------- load game assets ----------------
DT=Image.open('dungeon_pack/dungeon_tileset.png'); DJ=json.load(open('dungeon_pack/dungeon_tileset.json'))
def T(n):
    f=DJ['frames'][n]; return DT.crop((f['x'],f['y'],f['x']+f['w'],f['y']+f['h']))
def KN(n): return Image.open(f'chibi_knight/frames/{n}.png').convert('RGBA')

SW,SH=320,180
def background(dark=0.35, seed=1):
    import random; rnd=random.Random(seed)
    bg=Image.new('RGBA',(SW,SH),C['K'])
    walls=['wall_plain_1','wall_plain_2','wall_plain_3','wall_plain_1','wall_cracked','wall_mossy']
    for ty in range(0,9):
        for tx in range(0,20):
            n=rnd.choice(walls) if rnd.random()<0.85 else 'wall_plain_1'
            bg.alpha_composite(T(n),(tx*16,ty*16))
    floors=['floor_1','floor_2','floor_3','floor_1','floor_cracked_1','floor_pebbles','floor_moss']
    for ty in range(9,12):
        for tx in range(20):
            n=rnd.choice(floors)
            if ty==9: n=n.replace('floor','floor_shadow')
            bg.alpha_composite(T(n),(tx*16,ty*16))
    for x in range(20): bg.alpha_composite(T('wall_top_04'),(x*16,-12))
    shade=Image.new('RGBA',(SW,SH),(20,12,26,int(255*dark)))
    bg.alpha_composite(shade)
    # vignette
    v=img(SW,SH); vp=v.load()
    for y in range(SH):
        for x in range(SW):
            dx=(x-SW/2)/(SW/2); dy=(y-SH/2)/(SH/2); d=max(0,(dx*dx+dy*dy)**0.5-0.55)
            vp[x,y]=(10,6,14,min(200,int(d*260)))
    bg.alpha_composite(v)
    return bg

# ================= sprites atlas =================
S={}
for st in 'nhp':
    S[f'button9_stone_{st}']=button(24,20,st,'stone')
    S[f'button9_red_{st}']=button(24,20,st,'red')
S['panel9']=panel(48,48); S['panel9_light']=panel(48,48,'2')
for nm in ICONS:
    for st in 'nhp': S[f'icon_{nm}_{st}']=button(18,18,st,'stone',icon=icon_fn(nm))
for stt in ('locked','open','done','current'):
    S[f'level_{stt}']=door_tile(stt); S[f'level_{stt}_hover']=door_tile(stt,hover=True)
S['star_full']=star(True); S['star_empty']=star(False)
S['slider_knob']=knob(); S['toggle_on']=toggle(True); S['toggle_off']=toggle(False)
S['toggle_on_hover']=toggle(True,True); S['toggle_off_hover']=toggle(False,True)
S['cursor_sword']=cursor()
S['coin']=T('coin_0')
FONT_CHARS=[c for c in G if len(c)==1]
for c in FONT_CHARS:
    code=ord(c)
    S[f'font_cream_{code}']=text(c,'X',1,'K'); S[f'font_gold_{code}']=text(c,'Z',1,'y'); S[f'font_dark_{code}']=text(c,'K',1,None)

# ================= screens / layout =================
LAYOUT={}
def place_buttons(ids_labels,x,y,w,h,gap,variants):
    out=[]
    for i,(bid,lab) in enumerate(ids_labels):
        out.append(dict(type='button',id=bid,x=x,y=y+i*(h+gap),w=w,h=h,label=lab,variant=variants.get(bid,'stone')))
    return out
TITLE='DUNGEON DUMMY'
def title_img(s,scale=2):
    return text(s,'Y',scale,'1',grad=[c for c in GOLD_GRAD],outline_='K',sh_off=2)

# ---- main menu ----
main_static=background(0.42,1)
for x in (40,264): pass
rib=ribbon(196,22); main_static.alpha_composite(rib,((SW-rib.width)//2,8))
S['title_main']=title_img(TITLE)
sub='A NOT-SO-BRAVE ADVENTURE'; st_=text(sub,'X',1,'K'); main_static.alpha_composite(st_,((SW-st_.width)//2,36))
pn=panel(120,102); main_static.alpha_composite(pn,(100,50))
ver=text('V 0.1','3',1,'K'); main_static.alpha_composite(ver,(SW-ver.width-4,SH-11))
for nm,x,y in (('chest_closed',258,134),('barrel',282,134),('barrel',292,128),('crate',10,134),('pot',28,138)):
    main_static.alpha_composite(T(nm),(x,y))
main_static.alpha_composite(T('banner_red'),(64,44)); main_static.alpha_composite(T('banner_blue'),(240,44))
LAYOUT['main']=dict(
  widgets=place_buttons([('play','PLAY'),('levels','LEVELS'),('settings','SETTINGS'),('quit','QUIT')],112,60,96,20,3,{'play':'red'}),
  title=dict(name='title_main',y=10), torches=[[40,40],[264,40]], knight=dict(mode='walk',y=118,xmin=40,xmax=232))

# ---- level select ----
lv_static=background(0.5,2)
rib=ribbon(176,22); lv_static.alpha_composite(rib,((SW-rib.width)//2,4))
S['title_levels']=title_img('SELECT LEVEL')
pn=panel(256,118); lv_static.alpha_composite(pn,(32,32))
LEVELS=[("THE CELLAR DOOR",3),("RAT PROBLEMS",2),("BARREL ROLL",3),("SPIKY SITUATION",0)]+[("???",0)]*6
STATES=['done','done','done','current']+['locked']*6
tiles=[]
for i in range(10):
    col,row=i%5,i//5
    x=32+(256-(5*28+4*16))//2+col*44; y=50+row*48
    tiles.append(dict(type='level',id=f'lv{i+1}',x=x,y=y,w=28,h=28,level=i+1,state=STATES[i],stars=LEVELS[i][1],name=LEVELS[i][0]))
LAYOUT['levels']=dict(widgets=[dict(type='icon',id='back',icon='back',x=6,y=6,w=18,h=18),
    dict(type='icon',id='prev',icon='left',x=8,y=82,w=18,h=18),dict(type='icon',id='next',icon='right',x=294,y=82,w=18,h=18)]+tiles,
    worlds=["WORLD 1 - THE CELLAR","WORLD 2 - THE CRYPT"], torches=[[8,100],[296,100]], title=dict(name='title_levels',y=6), knight=dict(mode='idle',x=4,y=134),
    info=dict(x=160,y=160), coins=dict(x=262,y=9,value=125))

# ---- settings ----
se_static=background(0.5,3)
rib=ribbon(140,22); se_static.alpha_composite(rib,((SW-rib.width)//2,4))
S['title_settings']=title_img('SETTINGS')
pn=panel(232,124); se_static.alpha_composite(pn,(44,30))
rows_y=[42,62,82,102,122]
for lab,ic,y in zip(['MUSIC','SOUND','FULLSCREEN','SCREEN SHAKE','LANGUAGE'],['music','sound','fullscreen','shake','globe'],rows_y):
    icm=icon_fn(ic)('Y','K'); se_static.alpha_composite(icm,(56+(10-icm.width)//2,y+5-icm.height//2))
    se_static.alpha_composite(text(lab,'X',1,'K'),(70,y+2))
for y in rows_y[:-1]:
    for x in range(56,264,2): Px(se_static,x,y+15,'2')
ic=icon_fn('music')('3','K'); se_static.alpha_composite(ic,(148-ic.width,0)) if False else None
for y in rows_y[:2]: se_static.alpha_composite(slider_track(80),(144,y+1))
LAYOUT['settings']=dict(widgets=[
    dict(type='icon',id='back',icon='back',x=6,y=6,w=18,h=18),
    dict(type='slider',id='music',x=144,y=rows_y[0]+1,w=80,h=8,value=70,icon='music'),
    dict(type='slider',id='sound',x=144,y=rows_y[1]+1,w=80,h=8,value=50,icon='sound'),
    dict(type='toggle',id='fullscreen',x=238,y=rows_y[2]-1,w=26,h=12,value=True),
    dict(type='toggle',id='shake',x=238,y=rows_y[3]-1,w=26,h=12,value=True),
    dict(type='icon',id='lang_prev',icon='left',x=144,y=rows_y[4]-4,w=18,h=18),
    dict(type='icon',id='lang_next',icon='right',x=246,y=rows_y[4]-4,w=18,h=18),
    dict(type='button',id='defaults',x=72,y=158,w=84,h=18,label='DEFAULTS',variant='stone'),
    dict(type='button',id='save',x=164,y=158,w=84,h=18,label='SAVE',variant='red')],
    languages=['ENGLISH','FRANCAIS','ESPANOL','DEUTSCH','ITALIANO'], lang_y=rows_y[4]+2,
    torches=[[14,70],[290,70]], title=dict(name='title_settings',y=6), rows=rows_y, knight=dict(mode='scratch',x=284,y=134))

# baked labelled buttons (for engines that prefer ready-made images)
for scr in LAYOUT.values():
    for wd in scr['widgets']:
        if wd['type']=='button':
            ic={'play':'play','levels':'door','settings':'gear','quit':'exit'}.get(wd['id'])
            for st in 'nhp': S[f"btn_{wd['id']}_{st}"]=button(wd['w'],wd['h'],st,wd['variant'],label=wd['label'],icon=icon_fn(ic) if ic else None)
# torches and knight frames for the demo
for i in range(4): S[f'torch_{i}']=T(f'wall_torch_{i}')
for nm in ['idle_0','idle_1','idle_2','idle_3']+[f'walk_side_{i}' for i in range(6)]+[f'scratch_{i}' for i in range(4)]+[f'victory_{i}' for i in range(4)]:
    S['knight_'+nm]=KN(nm)

# ================= mockup renderer =================
def render(screen,static,hover=None,pressed=None,extra=None):
    im=static.copy(); L=LAYOUT[screen]
    t=S[L['title']['name']]; im.alpha_composite(t,((SW-t.width)//2,L['title']['y']))
    for x,y in L.get('torches',[]): im.alpha_composite(S['torch_1'],(x,y))
    k=L['knight']
    if k['mode']=='walk': im.alpha_composite(S['knight_walk_side_1'],(60,k['y']))
    elif k['mode']=='idle': im.alpha_composite(S['knight_idle_0'],(k['x'],k['y']))
    else: im.alpha_composite(S['knight_scratch_2'],(k['x'],k['y']))
    for wd in L['widgets']:
        st='p' if wd['id']==pressed else ('h' if wd['id']==hover else 'n')
        t=wd['type']
        if t=='button':
            im.alpha_composite(S[f"btn_{wd['id']}_{st}"],(wd['x'],wd['y']))
            if st=='h': im.alpha_composite(S['cursor_sword'],(wd['x']-16,wd['y']+6))
        elif t=='icon': im.alpha_composite(S[f"icon_{wd['icon']}_{st}"],(wd['x'],wd['y']))
        elif t=='level':
            nm=f"level_{wd['state']}"+('_hover' if wd['id']==hover else '')
            tile=door_tile(wd['state'],hover=wd['id']==hover)
            im.alpha_composite(tile,(wd['x'],wd['y']))
            if wd['state']!='locked':
                n=str(wd['level']); im.alpha_composite(text(n,'K',1,None),(wd['x']+14-tw(n)//2,wd['y']+2))
            if wd['state']!='locked':
                for s in range(3):
                    im.alpha_composite(S['star_full' if s<wd['stars'] else 'star_empty'],(wd['x']-1+s*10,wd['y']+29))
        elif t=='slider':
            fw=round((wd['w']-2)*wd['value']/100)
            im.alpha_composite(slider_fill(fw),(wd['x']+1,wd['y']+2))
            im.alpha_composite(S['slider_knob'],(wd['x']+1+fw-4,wd['y']-2))
            v=text(f"{wd['value']}%",'X',1,'K'); im.alpha_composite(v,(wd['x']+wd['w']+8,wd['y']))
        elif t=='toggle':
            im.alpha_composite(S['toggle_on' if wd['value'] else 'toggle_off'],(wd['x'],wd['y']))
            lab=text('ON' if wd['value'] else 'OFF','G' if wd['value'] else '3',1,'K'); im.alpha_composite(lab,(wd['x']-lab.width-6,wd['y']+3))
    if screen=='levels':
        w=text(L['worlds'][0],'Z',1,'y'); im.alpha_composite(w,((SW-w.width)//2,38))
        c=L['coins']; im.alpha_composite(S['coin'],(c['x']-4,c['y']-5)); im.alpha_composite(text(f"X {c['value']}",'Z',1,'K'),(c['x']+12,c['y']))
        info=text('LEVEL 4: SPIKY SITUATION','X',1,'K'); im.alpha_composite(info,((SW-info.width)//2,158))
        pr=text('CLICK A DOOR TO START','3',1,'K'); im.alpha_composite(pr,((SW-pr.width)//2,169))
    if screen=='settings':
        lang=text('< ENGLISH >'[2:-2],'Z',1,'y'); im.alpha_composite(lang,(204-lang.width//2,L['lang_y']))
    return im

OUT='ui_kit'; os.makedirs(OUT+'/sprites',exist_ok=True); os.makedirs(OUT+'/screens',exist_ok=True)
mocks={'main_menu':render('main',main_static,hover='play'),
       'level_select':render('levels',lv_static,hover='lv3'),
       'settings':render('settings',se_static,hover='save')}
for n,m in mocks.items():
    m.save(f'{OUT}/screens/{n}.png'); m.resize((SW*4,SH*4),Image.NEAREST).save(f'{OUT}/screens/{n}_4x.png')
for n,st in (('main_bg',main_static),('levels_bg',lv_static),('settings_bg',se_static)):
    st.save(f'{OUT}/screens/{n}.png')

# atlas
names=[n for n in S if not n.startswith('knight_') and not n.startswith('torch_')]
x=y=rowh=0; W=320; frames={}
for n in names:
    im=S[n]
    if x+im.width>W: x=0; y+=rowh+1; rowh=0
    frames[n]=dict(x=x,y=y,w=im.width,h=im.height); x+=im.width+1; rowh=max(rowh,im.height)
atlas=img(W,y+rowh)
for n in names: atlas.alpha_composite(S[n],(frames[n]['x'],frames[n]['y']))
atlas.save(f'{OUT}/ui_atlas.png')
atlas.resize((atlas.width*3,atlas.height*3),Image.NEAREST).save(f'{OUT}/ui_atlas_3x.png')
json.dump(dict(image='ui_atlas.png',frames=frames,
    nine_slice={'panel9':16,'panel9_light':16,'button9_stone_*':8,'button9_red_*':8},
    notes={'states':'_n normal, _h hover, _p pressed','font':'font_<color>_<charcode>, 6px advance'}),
    open(f'{OUT}/ui_atlas.json','w'),indent=1)
for n in names: S[n].save(f'{OUT}/sprites/{n}.png')
json.dump(LAYOUT,open(f'{OUT}/ui_layout.json','w'),indent=1)

# data for the html demo
def b64(im):
    b=io.BytesIO(); im.save(b,'PNG'); return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
demo={'sprites':{n:b64(im) for n,im in S.items()},
      'bg':{'main':b64(main_static),'levels':b64(lv_static),'settings':b64(se_static)},
      'layout':LAYOUT}
json.dump(demo,open('ui_demo_data.json','w'))
print('atlas',atlas.size,len(names))
