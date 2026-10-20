import math, json, os, zipfile
from PIL import Image, ImageDraw, ImageFont

PAL = {
 'K':'#1a1220','1':'#241a2a','2':'#4a3448',
 'w':'#4a2c1c','W':'#7a4a2a',
 'y':'#b07a1a','Y':'#e8b13a','Z':'#ffe27a',
 'm':'#4d5566','M':'#8a94a8','N':'#c8d0e0','O':'#f2f0e6',
 'r':'#6e1c2a','R':'#b8333a','P':'#e85a5a',
 'C':'#6ab0f0','X':'#d8ccb0','F':'#ffd84a',
}
RGBA = {k: tuple(int(v[i:i+2],16) for i in (1,3,5))+(255,) for k,v in PAL.items()}
S = 32

def new(w=S,h=S): return [['.']*w for _ in range(h)]
def rows(rs):
    for r in rs: assert len(r)==len(rs[0]),(r,len(r))
    return [list(r) for r in rs]
def size(c): return len(c[0]),len(c)
def put(c,x,y,ch):
    w,h=size(c)
    if 0<=x<w and 0<=y<h: c[y][x]=ch
def get(c,x,y):
    w,h=size(c); return c[y][x] if 0<=x<w and 0<=y<h else '.'
def rect(c,x,y,w,h,ch):
    for yy in range(y,y+h):
        for xx in range(x,x+w): put(c,xx,yy,ch)
def paste(d,s,ox,oy):
    for y,row in enumerate(s):
        for x,ch in enumerate(row):
            if ch!='.': put(d,x+ox,y+oy,ch)
def outline(c,ch='K'):
    w,h=size(c); o=[r[:] for r in c]
    for y in range(h):
        for x in range(w):
            if c[y][x]=='.' and any(get(c,x+dx,y+dy)!='.' for dx,dy in((1,0),(-1,0),(0,1),(0,-1))):
                o[y][x]=ch
    return o
def flip(c): return [r[::-1] for r in c]
def vflip(c): return [r[:] for r in c[::-1]]
def rot_ccw(c): return [list(r) for r in zip(*c)][::-1]
def recolor(c,m): return [[m.get(ch,ch) for ch in r] for r in c]
def to_img(c):
    w,h=size(c); im=Image.new('RGBA',(w,h),(0,0,0,0)); px=im.load()
    for y in range(h):
        for x in range(w):
            if c[y][x]!='.': px[x,y]=RGBA[c[y][x]]
    return im
def line(c,a,b,c1,c2=None):
    (x0,y0),(x1,y1)=a,b; n=max(abs(x1-x0),abs(y1-y0),1)
    for i in range(n+1):
        x=round(x0+(x1-x0)*i/n); y=round(y0+(y1-y0)*i/n)
        put(c,x,y,c1)
        if c2: put(c,x,y+1,c2)

# ---------------- parts ----------------
HELMET=rows([
".......KKKKKK.......",
".....KKNNNNMMKK.....",
"....KNNOONNNMMmK....",
"...KNNOONNNNMMMmK...",
"..KNNONNNNNNMMMmmK..",
"..KNNNNNNNNNMMMmmK..",
".KNNNNNNNNNNMMMMmmK.",
".KMMMMMMMMMMMMMMmmK.",
".KNKKKKKKKKKKKKKKmK.",
".KM1OOO1111111111mK.",
".KM1OOO111111OO11mK.",
".KM1OOK111111KO11mK.",
".KM111111OO111111mK.",
".KMMMMMMMPPMMMMMmmK.",
"..KKKKKKKPPKKKKKKK..",
".........KK........."])
HELMET[5][7]='m'; HELMET[4][8]='M'   # dent
def helmet(eyes='derp',tongue=True):
    h=[r[:] for r in HELMET]
    def clear():
        for y in (9,10,11):
            for x in (4,5,6,13,14): h[y][x]='1'
        h[11][6]='1'
    if eyes=='blink':
        clear(); rect(h,4,11,3,1,'O'); rect(h,13,11,2,1,'O')
    elif eyes=='wide':
        clear(); rect(h,4,9,3,3,'O'); put(h,5,10,'K'); rect(h,13,10,2,2,'O'); put(h,14,10,'K')
    elif eyes=='dead':
        clear()
        for (x,y) in ((4,9),(6,9),(5,10),(4,11),(6,11),(13,10),(14,11)): put(h,x,y,'O')
    elif eyes=='happy':
        clear()
        for (x,y) in ((4,10),(5,9),(6,10),(13,11),(14,10)): put(h,x,y,'O')
        put(h,4,11,'O'); put(h,6,11,'O')
    elif eyes=='up':
        clear(); rect(h,4,9,3,3,'O'); put(h,4,9,'K'); rect(h,13,10,2,2,'O'); put(h,14,10,'K')
    elif eyes in ('left','right'):
        clear(); rect(h,4,9,3,3,'O'); rect(h,13,10,2,2,'O')
        if eyes=='left': put(h,4,10,'K'); put(h,13,10,'K')
        else: put(h,6,10,'K'); put(h,14,10,'K')
    if not tongue:
        h[13][9]='M'; h[13][10]='M'; h[14][9]='K'; h[14][10]='K'; h[15][9]='.'; h[15][10]='.'
    return h
PLUMES=[rows(p) for p in (
["..RPPR","..rP..",".Rr...","..r..."],
["...RPP",".RPr..",".Rr...","..r..."],
["RPR...","..PR..","..Rr..","..r..."])]
TORSO=rows([
"..KKKKKKKK..",
".KNNMMMMMmK.",
"KNMMKMMKMMmK",
"KNMMMKKMMMmK",
"KRRRRYYRRRrK",
"KmMMMMMMMmmK",
".KmMMMMMmmK.",
".KKKKKKKKKK."])
SHIELD=rows([
"KKKKKKKKK",
"KNNNNNMmK",
"KNMMMMMmK",
"KNMKMKMmK",
"KNMMMMMmK",
"KNKMMMKmK",
"KNMKKKMmK",
".KNMMMmK.",
".KNMMMmK.",
"..KNMmK..",
"...KmK...",
"....K...."])
SHIELD_UPSIDE=vflip(SHIELD)
QMARK=rows([".OOO.","O...O","...O.","..O..",".....","..O.."])
EXCL=rows(["O","O","O",".","O"])
STAR=rows([".F.","FZF",".F."])
DROP=rows([".C","CC","CC"])
PUFF=rows([".X.","XXX"])
def fx(c,spr,x,y,ol=True):
    if not ol: paste(c,spr,x,y); return
    pad=[['.']*(len(spr[0])+2) for _ in range(len(spr)+2)]
    paste(pad,spr,1,1); paste(c,outline(pad),x-1,y-1)

DEF=dict(bx=0,by=0,hx=0,hy=0,eyes='derp',tongue=True,plume=0,legs='stand',cape=0,
         hand=(8,22),sword=90,swlen=7,shield='side',fx=[])
def P(**kw):
    d=dict(DEF); d.update(kw); return d

def draw(p):
    c=new(); bx,by=p['bx'],p['by']
    # cape (behind)
    s=p['cape']
    for y in range(19+by,29+min(0,by)):
        t=(y-19-by)/9
        l=round(10+bx-t*2+s*t); r=round(21+bx+t*2+s*t)
        rect(c,l,y,r-l+1,1,'R'); put(c,l,y,'P'); put(c,r,y,'r'); put(c,r-1,y,'r')
    rect(c,round(10+bx-2+s),28+min(0,by),14,1,"r")
    # legs
    lt=26+by
    lx,rx=12+bx,18+bx
    lb,rb=29,29
    if p['legs']=='lstep': lb=28
    if p['legs']=='rstep': rb=28
    if p['legs']=='wide': lx-=1; rx+=1
    if p['legs']=='air': lb,rb=27+by//2,27+by//2
    for x,b,toe in ((lx,lb,-1),(rx,rb,0)):
        rect(c,x,lt,3,max(1,b-lt),'M'); rect(c,x+2,lt,1,max(1,b-lt),'m'); put(c,x,lt,'N')
        rect(c,x+toe,b,4,1,'m'); put(c,x+toe+(0 if toe else 3),b,'K')
    paste(c,TORSO,10+bx,18+by)
    # sword arm + sword
    sh=(11+bx,20+by); hand=(p['hand'][0]+bx,p['hand'][1]+by)
    line(c,sh,hand,'M','m')
    if p['sword'] is not None:
        a=math.radians(p['sword']); dx,dy=math.cos(a),math.sin(a)
        put(c,round(hand[0]-dx*2),round(hand[1]-dy*2),'Y')
        gx,gy=hand[0]+dx*1.5,hand[1]+dy*1.5
        for t in (-1,0,1): put(c,round(gx-dy*t),round(gy+dx*t),'y' if t else 'Y')
        for i in range(3,p['swlen']+3):
            put(c,round(hand[0]+dx*i),round(hand[1]+dy*i),'O' if i==p['swlen']+2 else ('N' if i%2 else 'O'))
    rect(c,hand[0]-1,hand[1]-1,3,3,'M'); put(c,hand[0]+1,hand[1]+1,'m'); put(c,hand[0]-1,hand[1]-1,'N')
    # shield beside the body
    if p['shield']=='side': paste(c,SHIELD_UPSIDE,21+bx+p.get('shx',0),18+by+p.get('shy',0))
    # head
    hx,hy=6+bx+p['hx'],3+by+p['hy']
    paste(c,PLUMES[p['plume']],hx+8,hy-3)
    paste(c,helmet(p['eyes'],p['tongue']),hx,hy)
    if p['shield']=='raised': paste(c,SHIELD_UPSIDE,13+bx,8+by)
    if p['shield']=='raised_ok': paste(c,SHIELD,13+bx,8+by)
    if p['shield']=='peek': paste(c,SHIELD_UPSIDE,12+bx+p.get('shx',0),14+by)
    c=outline(c)
    for kind,x,y in p['fx']:
        if kind=='slash':
            for a in range(-80,41,4):
                for r,ch in ((12,'N'),(13,'O')):
                    put(c,round(16+r*math.cos(math.radians(a))),round(17+r*math.sin(math.radians(a))),ch)
        else:
            fx(c,{'?':QMARK,'!':EXCL,'star':STAR,'drop':DROP,'puff':PUFF}[kind],x,y)
    return c

def lie(c):
    r=rot_ccw(c)
    ys=[y for y,row in enumerate(r) if any(ch!='.' for ch in row)]
    xs=[x for x in range(S) if any(r[y][x]!='.' for y in range(S))]
    o=new(); paste(o,r,(S-(xs[-1]-xs[0]+1))//2-xs[0],30-ys[-1]); return o
def flash(c): return recolor(c,{k:'O' for k in PAL if k!='K'})

def sword_at(c,hand,ang,length):
    if ang is None: return
    a=math.radians(ang); dx,dy=math.cos(a),math.sin(a)
    put(c,round(hand[0]-dx*2),round(hand[1]-dy*2),'Y')
    gx,gy=hand[0]+dx*1.5,hand[1]+dy*1.5
    for t in (-1,0,1): put(c,round(gx-dy*t),round(gy+dx*t),'y' if t else 'Y')
    for i in range(3,length+3):
        put(c,round(hand[0]+dx*i),round(hand[1]+dy*i),'O' if i==length+2 else ('N' if i%2 else 'O'))
def fx_all(c,lst,cx=16,cy=17):
    for kind,x,y in lst:
        if kind=='slash':
            for a in range(-80,41,4):
                for r,ch in ((12,'N'),(13,'O')):
                    put(c,round(cx+r*math.cos(math.radians(a))),round(cy+r*math.sin(math.radians(a))),ch)
        else: fx(c,{'?':QMARK,'!':EXCL,'star':STAR,'drop':DROP,'puff':PUFF}[kind],x,y)

# ---------------- side (profile, facing right) ----------------
HELM_SIDE=rows([
".....KKKKKK......",
"...KKNNNNMMKK....",
"..KNNOONNNNMmK...",
".KNNOONNNNNNMmK..",
".KNONNNNNNNNMMmK.",
"KNNNNNNNNNNNMMmK.",
"KNNNNNNNNNNNMMMmK",
"KMMMMMMMMMMMMMMmK",
"KNMMMMMMKKKKKKKK.",
"KNMMMMMMK1OOO11K.",
"KNMMMMMMK1OOK11K.",
"KNMMMMMMK1111OOK.",
"KNMMMMMMMMMMMMPPK",
".KmmmmmmmmmmmKPPK",
"..KKKKKKKKKKK.KK."])
HELM_SIDE[4][6]='m'
def helm_side(eyes='derp',tongue=True):
    h=[r[:] for r in HELM_SIDE]
    for x in (10,11,12):
        for y in (9,10): h[y][x]='1'
    full=lambda:[put(h,x,y,'O') for x in (10,11,12) for y in (9,10)]
    pup={'derp':(12,10),'fwd':(12,9),'back':(10,9),'wide':(11,10),'down':(11,10)}
    if eyes in pup: full(); put(h,*pup[eyes],'K')
    elif eyes=='blink': rect(h,10,10,3,1,'O')
    elif eyes=='happy': [put(h,x,y,'O') for x,y in ((10,10),(11,9),(12,10))]
    elif eyes=='dead': [put(h,x,y,'O') for x,y in ((10,9),(12,9),(11,10))]
    if not tongue:
        h[12][14]='M'; h[12][15]='M'; h[13][14]='K'; h[13][15]='K'; h[13][16]='.'; h[14][14]='.'; h[14][15]='.'
    return h
TORSO_SIDE=rows([
".KKKKKKK.",
"KNNMMMMmK",
"KNMMMMMmK",
"KNMMMMMmK",
"KRRRRYRrK",
"KmMMMMmmK",
".KmMMMmK.",
".KKKKKKK."])
SHIELD_SMALL=rows([
"...K...",
"..KmK..",
".KmMNK.",
"KmMMMNK",
"KmKKKNK",
"KmKMKNK",
"KmMMMNK",
"KmKMKNK",
"KKKKKKK"])
SDEF=dict(bx=0,by=0,hx=0,hy=0,eyes='derp',tongue=True,plume=0,cape=0.3,
          legs=((-1,0),(1,0)),ground=True,hand=(18,23),sword=100,swlen=6,shx=0,shy=0,fx=[])
def SP(**kw):
    d=dict(SDEF); d.update(kw); d['_v']='side'; return d
def line3(c,a,b,c1,c2):
    (x0,y0),(x1,y1)=a,b; n=max(abs(x1-x0),abs(y1-y0),1)
    for i in range(n+1):
        x=round(x0+(x1-x0)*i/n); y=round(y0+(y1-y0)*i/n)
        put(c,x,y,c1); put(c,x+1,y,c1); put(c,x+2,y,c2)
def draw_side(p):
    c=new(); bx,by=p['bx'],p['by']; hip=25+by
    # cape trailing behind
    bottom=29 if p['ground'] else min(29,hip+3)
    for y in range(18+by,bottom):
        t=y-(18+by); right=12+bx; left=right-1-round(t*p['cape'])
        rect(c,left,y,right-left+1,1,'R'); put(c,left,y,'r'); put(c,left+1,y,'r') if t%3==0 else None
    # far arm + sword
    sh=(17+bx,19+by); hand=(p['hand'][0]+bx,p['hand'][1]+by)
    line(c,sh,hand,'m','m'); sword_at(c,hand,p['sword'],p['swlen'])
    rect(c,hand[0]-1,hand[1]-1,3,3,'m')
    # legs
    for i,((dx,lift),(c1,c2),boot) in enumerate(zip(p['legs'],(('m','1'),('M','m')),('m','M'))):
        hx_=13+bx+i*2; fx_=hx_+dx
        fy=(29-lift) if p['ground'] else (hip+4-lift)
        fy=max(min(fy,29),hip+1)
        line3(c,(hx_,hip),(fx_,fy-1),c1,c2)
        rect(c,fx_,fy,4,1,boot); put(c,fx_+3,fy,'m' if boot=='M' else '1')
    paste(c,TORSO_SIDE,11+bx,17+by)
    hx,hy=8+bx+p['hx'],3+by+p['hy']
    paste(c,flip(PLUMES[p['plume']]),hx+4,hy-3)
    paste(c,helm_side(p['eyes'],p['tongue']),hx,hy)
    # near arm holding the (upside-down) shield
    paste(c,SHIELD_SMALL,17+bx+p['shx'],17+by+p['shy'])
    c=outline(c); fx_all(c,p['fx'],cx=14,cy=17)
    return c

# ---------------- back view ----------------
HELM_BACK=[r[:] for r in HELMET]
for y in range(9,13): HELM_BACK[y]=list(".KNNNNNNNNNNMMMMmmK.")
HELM_BACK[8]=list(".KmmmmmmmmmmmmmmmmK.")
HELM_BACK[13]=list(".KMMMMMMMMMMMMMMmmK."); HELM_BACK[14]=list("..KKKKKKKKKKKKKKKK.."); HELM_BACK[15]=list('.'*20)
SHIELD_BACK=recolor(SHIELD,{'N':'m','M':'m'})
for y in (3,7):
    for x in range(1,8):
        if SHIELD_BACK[y][x]!='K': SHIELD_BACK[y][x]='W'
SHIELD_BACK=vflip(SHIELD_BACK)
BDEF=dict(bx=0,by=0,legs='stand',plume=0,cape=0,hand=(24,22),sword=90,swlen=6,shx=0,shy=0,fx=[])
def BP(**kw):
    d=dict(BDEF); d.update(kw); d['_v']='back'; return d
def draw_back(p):
    c=new(); bx,by=p['bx'],p['by']
    lt=26+by; lx,rx=12+bx,17+bx; lb,rb=29,29
    if p['legs']=='lstep': lb=28
    if p['legs']=='rstep': rb=28
    if p['legs']=='wide': lx-=1; rx+=1
    for x,b in ((lx,lb),(rx,rb)):
        rect(c,x,lt,3,max(1,b-lt),'M'); rect(c,x+2,lt,1,max(1,b-lt),'m')
        rect(c,x,b,3,1,'m')
    # sword (screen right)
    hand=(p['hand'][0]+bx,p['hand'][1]+by)
    line(c,(20+bx,20+by),hand,'M','m'); sword_at(c,hand,p['sword'],p['swlen'])
    rect(c,hand[0]-1,hand[1]-1,3,3,'M')
    # cape covering the back
    s=p['cape']
    for y in range(17+by,28):
        t=(y-17-by)/10
        l=round(10+bx-t*2+s*t); r=round(21+bx+t*2+s*t)
        rect(c,l,y,r-l+1,1,'R'); put(c,l,y,'P'); put(c,r,y,'r')
        for fxx in (13,18): put(c,round(fxx+bx+s*t),y,'r') if t>0.2 else None
    rect(c,round(8+bx+s),27,16,1,'r')
    paste(c,SHIELD_BACK,2+bx+p['shx'],18+by+p['shy'])
    paste(c,PLUMES[p['plume']],14+bx,0+by)
    paste(c,HELM_BACK,6+bx,3+by)
    c=outline(c); fx_all(c,p['fx'])
    return c

A={}
A['idle']=[P(),P(plume=1),P(by=1,cape=0),P(by=1,plume=1,eyes='blink')]
A['walk_down']=[P(legs='lstep',cape=-1,hand=(7,23),shy=-1,plume=1),P(by=1,hand=(8,22)),
           P(legs='rstep',cape=1,hand=(9,21),shy=1,plume=1),P(by=1,hand=(8,22),plume=0)]
A['run_down']=[P(legs='lstep',by=-1,cape=-2,hand=(6,21),shy=-2,plume=2,eyes='wide'),P(legs='wide',hand=(8,23),cape=-1,eyes='wide'),
          P(legs='rstep',by=-1,cape=2,hand=(10,21),shy=1,plume=2,eyes='wide',fx=[('drop',4,4)]),P(legs='wide',hand=(8,23),cape=1,eyes='wide')]
A['attack']=[
 P(by=1,eyes='up',hand=(9,12),sword=-95,swlen=8,plume=1,tongue=False),
 P(bx=-1,eyes='blink',hand=(7,10),sword=-130,swlen=8,plume=2,cape=-1,tongue=False),
 P(bx=1,eyes='wide',hand=(23,17),sword=10,swlen=7,cape=1,plume=2,fx=[('slash',0,0)]),
 P(bx=1,by=2,eyes='wide',legs='wide',hand=(22,23),sword=75,swlen=7,cape=1,fx=[('puff',24,28)]),
 P(bx=1,by=2,eyes='derp',legs='wide',hand=(22,23),sword=75,swlen=7,fx=[('drop',4,3),('!',28,0)])]
A['block']=[P(shield='raised',hand=(7,21),eyes='blink',legs='wide'),
            P(shield='raised',hand=(7,21),eyes='blink',legs='wide',fx=[('?',26,0)]),
            P(shield='raised_ok',hand=(7,21),eyes='happy',legs='wide')]
hurt=P(bx=-2,hx=-1,eyes='blink',cape=-2,plume=2,hand=(5,19),sword=-60,fx=[('drop',27,3)])
A['hurt']=[draw(hurt),flash(draw(hurt))]
flat=P(eyes='dead',sword=None,plume=2,hand=(9,24))
dead=lie(draw(flat)); dead2=[r[:] for r in dead]; fx(dead2,STAR,4,15); fx(dead2,STAR,10,12)
A['death']=[draw(P(bx=-1,eyes='dead',plume=2,cape=-1)),
            draw(P(by=3,legs='wide',eyes='dead',plume=0,sword=95,swlen=6)),dead,dead2]
A['dizzy']=[]
pos=[(6,0),(24,1),(15,0),(10,1)]
for i in range(4):
    sw=(-1,0,1,0)[i]
    A['dizzy'].append(P(bx=sw,hx=sw,cape=-sw,eyes=('dead','derp','dead','wide')[i],plume=i%2,
                        fx=[('star',*pos[i]),('star',*pos[(i+2)%4])]))
A['scratch']=[P(hand=(5,12),sword=-100,swlen=7,eyes='up'),P(hand=(5,11),sword=-95,swlen=7,eyes='up',plume=1),
              P(hand=(5,12),sword=-100,swlen=7,fx=[('?',26,0)]),P(hand=(5,11),sword=-95,swlen=7,plume=1,eyes='wide',fx=[('?',26,0)])]
A['victory']=[P(hand=(8,12),sword=-90,swlen=8,eyes='happy'),
              P(by=-3,legs='air',hand=(8,10),sword=-90,swlen=8,eyes='happy',plume=2,cape=1),
              P(by=-3,legs='air',hand=(8,10),sword=-85,swlen=8,eyes='happy',plume=2,cape=-1,fx=[('star',2,6),('star',27,4)]),
              P(by=1,hand=(8,13),sword=-90,swlen=8,eyes='derp')]


# ---- side view ----
A['idle_side']=[SP(),SP(plume=1),SP(by=1,hand=(20,24)),SP(by=1,plume=1,eyes='blink',hand=(20,24))]
def gait(n,stride,lift,**kw):
    out=[]
    for i in range(n):
        ph=2*math.pi*i/n; cs,sn=math.cos(ph),math.sin(ph)
        far=(round(-stride*cs)-1, lift if sn<-0.3 else 0)
        near=(round(stride*cs), lift if sn>0.3 else 0)
        out.append((far,near,cs,sn,i))
    return out
A['walk_side']=[SP(legs=(f,nr),by=0 if abs(sn)>0.5 else 1,hand=(20+round(-cs*2),23),shx=round(cs*1.5),
                   plume=i%2,cape=0.4) for f,nr,cs,sn,i in gait(6,3,1)]
A['run_side']=[SP(legs=(f,nr),bx=1,hx=1,by=-1 if abs(sn)>0.5 else 0,hand=(21+round(-cs*3),22),sword=60,
                  shx=round(cs*2),plume=2 if i%2 else 1,cape=0.8,eyes='fwd',tongue=True,
                  fx=[('drop',5,3)] if i in (2,3) else []) for f,nr,cs,sn,i in gait(6,4,2)]
A['jump_side']=[
 SP(by=3,legs=((-4,0),(3,0)),hand=(19,26),sword=85,eyes='blink',cape=0.5),
 SP(by=-4,ground=False,legs=((-3,0),(1,1)),hand=(21,14),sword=-60,eyes='up' if False else 'fwd',cape=0.1,plume=1),
 SP(by=-6,ground=False,legs=((-2,2),(2,1)),hand=(22,13),sword=-50,eyes='wide',cape=0.1,plume=2),
 SP(by=-5,ground=False,legs=((-1,0),(1,0)),hand=(23,15),sword=-30,eyes='wide',cape=0.0,plume=2,fx=[('drop',5,1)]),
 SP(by=-2,ground=False,legs=((-2,0),(2,0)),hand=(22,16),sword=-20,eyes='down',cape=-0.1,plume=2),
 SP(by=3,legs=((-4,0),(3,0)),hand=(21,26),sword=70,eyes='blink',cape=0.6,fx=[('puff',6,28),('puff',22,28)]),
 SP(by=1,eyes='derp',plume=1)]
A['sneak_side']=[]
for i,(f,nr,cs,sn,_) in enumerate(gait(6,3,1)):
    A['sneak_side'].append(SP(by=3,hx=2,legs=((f[0]-1,f[1]),(nr[0]+1,nr[1])),hand=(16,25),sword=160,swlen=6,
        shx=2,shy=-3,cape=0.2,tongue=False,eyes=('back','back','fwd','fwd','back','fwd')[i],plume=0,
        fx=[('drop',4,4)] if i==3 else []))
A['attack_side']=[
 SP(bx=-1,eyes='up',hand=(15,9),sword=-110,swlen=7,plume=1,tongue=False,legs=((-2,0),(2,0))),
 SP(bx=-2,eyes='blink',hand=(12,9),sword=-150,swlen=7,plume=2,tongue=False,cape=0.5,legs=((-3,0),(1,0))),
 SP(bx=1,hx=1,eyes='fwd',hand=(24,17),sword=0,swlen=6,plume=2,legs=((-3,0),(4,0)),fx=[('slash',0,0)]),
 SP(bx=1,by=2,eyes='wide',hand=(23,23),sword=75,swlen=6,legs=((-3,0),(4,0)),fx=[('puff',25,28)]),
 SP(bx=1,by=2,eyes='derp',hand=(23,23),sword=75,swlen=6,legs=((-3,0),(4,0)),fx=[('drop',5,3),('!',28,0)])]
# ---- back view (walking away) ----
A['idle_up']=[BP(),BP(plume=1),BP(by=1),BP(by=1,plume=1)]
A['walk_up']=[BP(legs='lstep',cape=1,hand=(25,23),shy=1,plume=1),BP(by=1),
              BP(legs='rstep',cape=-1,hand=(23,21),shy=-1,plume=1),BP(by=1)]
# ---- front extras ----
A['jump_down']=[P(by=3,legs='wide',hand=(8,24),eyes='blink'),
                P(by=-5,legs='air',hand=(6,15),sword=-110,swlen=7,eyes='up',plume=1),
                P(by=-6,legs='air',hand=(5,14),sword=-120,swlen=7,eyes='wide',plume=2,shy=-3),
                P(by=-3,legs='air',hand=(6,17),sword=-100,swlen=7,eyes='wide',plume=2),
                P(by=3,legs='wide',hand=(8,24),eyes='blink',fx=[('puff',5,28),('puff',24,28)]),
                P(by=1)]
A['sneak_down']=[P(by=3,legs='wide',shield='peek',hand=(7,24),eyes='left',cape=0),
                 P(by=3,legs='lstep',shield='peek',shx=-1,hand=(6,24),eyes='left',cape=-1),
                 P(by=3,legs='wide',shield='peek',hand=(7,24),eyes='right',cape=0),
                 P(by=3,legs='rstep',shield='peek',shx=1,hand=(8,24),eyes='right',cape=1,fx=[('drop',4,5)])]
def render(p):
    v=p.get('_v')
    return draw_side(p) if v=='side' else draw_back(p) if v=='back' else draw(p)

ORDER=['idle','idle_side','idle_up','walk_down','walk_side','walk_up','run_down','run_side','jump_side','jump_down','sneak_side','sneak_down','attack','attack_side','block','hurt','death','dizzy','scratch','victory']
F={k:[render(f) if isinstance(f,dict) else f for f in A[k]] for k in ORDER}
fps={'idle':5,'idle_side':5,'idle_up':5,'walk_down':8,'walk_side':10,'walk_up':8,'run_down':12,'run_side':12,'jump_side':10,'jump_down':10,'sneak_side':6,'sneak_down':5,'attack_side':12,'attack':12,'block':6,'hurt':8,'death':6,'dizzy':6,'scratch':5,'victory':8}
loop={'jump_side':False,'jump_down':False,'attack_side':False,'attack':False,'block':False,'hurt':False,'death':False}

OUT='chibi_knight'; os.makedirs(OUT+'/frames',exist_ok=True)
maxn=max(len(F[k]) for k in ORDER)
sheet=Image.new('RGBA',(S*maxn*2,S*len(ORDER)),(0,0,0,0))
meta={"frameWidth":S,"frameHeight":S,"image":"chibi_knight.png","background":"transparent",
      "layout":f"one row per animation; columns 0-{maxn-1} face right, columns {maxn}-{2*maxn-1} face left","animations":{}}
for r,k in enumerate(ORDER):
    for i,f in enumerate(F[k]):
        im=to_img(f); sheet.paste(im,(i*S,r*S)); sheet.paste(to_img(flip(f)),((maxn+i)*S,r*S))
        im.save(f"{OUT}/frames/{k}_{i}.png")
    meta["animations"][k]={"row":r,"frames":len(F[k]),"fps":fps[k],"loop":loop.get(k,True)}
sheet.save(f'{OUT}/chibi_knight.png')
sheet.resize((sheet.width*4,sheet.height*4),Image.NEAREST).save(f'{OUT}/chibi_knight_4x.png')
json.dump(meta,open(f'{OUT}/chibi_knight.json','w'),indent=1)

# labelled preview on a checkerboard (shows the transparency)
SC=4; LW=110
prev=Image.new('RGBA',(LW+S*SC*maxn,S*SC*len(ORDER)),(36,30,44,255)); d=ImageDraw.Draw(prev)
for y in range(0,prev.height,16):
    for x in range(LW,prev.width,16):
        d.rectangle((x,y,x+15,y+15),fill=(70,70,78,255) if (x//16+y//16)%2 else (88,88,96,255))
try: font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',18)
except: font=ImageFont.load_default()
for r,k in enumerate(ORDER):
    d.text((10,r*S*SC+S*SC//2-10),k,fill=(232,177,58,255),font=font)
    for i,f in enumerate(F[k]):
        prev.alpha_composite(to_img(f).resize((S*SC,S*SC),Image.NEAREST),(LW+i*S*SC,r*S*SC))
prev.save(f'{OUT}/chibi_knight_preview.png')

# transparent animated gif
keys=list(PAL); palimg=Image.new('P',(1,1))
flatpal=[255,0,255]+[v for k in keys for v in RGBA[k][:3]]+[0]*(768-3-3*len(keys))
palimg.putpalette(flatpal)
cols=5; cell=S*4; rws=math.ceil(len(ORDER)/cols)
frames=[]
for t in range(60):
    im=Image.new('RGB',(cols*cell,rws*cell),(255,0,255))
    for n,k in enumerate(ORDER):
        fl=F[k]; ticks=max(1,round(12/fps[k])); idx=(t//ticks)%len(fl)
        fr=to_img(fl[idx]).resize((cell,cell),Image.NEAREST)
        im.paste(fr,((n%cols)*cell,(n//cols)*cell),fr)
    frames.append(im.quantize(palette=palimg,dither=Image.Dither.NONE))
frames[0].save(f'{OUT}/chibi_knight_animated.gif',save_all=True,append_images=frames[1:],duration=83,loop=0,transparency=0,disposal=2)

with zipfile.ZipFile('chibi_knight.zip','w',zipfile.ZIP_DEFLATED) as z:
    for root,_,files in os.walk(OUT):
        for f in sorted(files):
            p=os.path.join(root,f); z.write(p,os.path.relpath(p,OUT))
    z.write('chibi_knight.py','chibi_knight.py')
print(sheet.size, sheet.getpixel((0,0)))
