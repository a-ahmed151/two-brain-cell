import os, json, math
from PIL import Image

PAL = {
 'K':'#2b1a24',
 'A':'#7f8c52','H':'#5f6a3f','h':'#464e30',            # hood
 'n':'#7a4b37','u':'#553326',                          # hair
 'S':'#e7b48c','s':'#c98f6a','r':'#d58a78',            # skin
 'V':'#7a6c45','v':'#5a4e33','d':'#3d3530','D':'#524840',  # tunic, trousers
 'w':'#4e3226','W':'#7a4a30','L':'#a0663f','l':'#c08350', # leather / wood
 'T':'#c9ae7a','t':'#9e8458','P':'#e3cfa0',            # tan sack
 'B':'#4f86a8','C':'#8ec0d8','b':'#3a6584','N':'#c6d6dc', # blue flask / glass
 'Y':'#d8b25e','o':'#c8743a','F':'#f0cf6a','X':'#efe4cc',
}
RGBA = {k: tuple(int(v[i:i+2],16) for i in (1,3,5))+(255,) for k,v in PAL.items()}
FW=FH=24; OX,OY=4,6

def canvas(w=FW,h=FH): return [['.']*w for _ in range(h)]
def rows(rs):
    for r in rs: assert len(r)==len(rs[0]),(r,len(r))
    return [list(r) for r in rs]
def put(c,x,y,ch):
    if 0<=y<len(c) and 0<=x<len(c[0]): c[y][x]=ch
def paste(c,p,ox,oy):
    for y,r in enumerate(p):
        for x,ch in enumerate(r):
            if ch!='.': put(c,x+ox,y+oy,ch)
def outline(c):
    h,w=len(c),len(c[0]); o=[r[:] for r in c]
    for y in range(h):
        for x in range(w):
            if c[y][x]=='.' and any(0<=x+dx<w and 0<=y+dy<h and c[y+dy][x+dx]!='.' for dx,dy in((1,0),(-1,0),(0,1),(0,-1))):
                o[y][x]='K'
    return o
def sprite(w,h,draw):
    c=canvas(w+2,h+2); draw(lambda x,y,ch: put(c,x+1,y+1,ch)); return outline(c)
def flip(c): return [r[::-1] for r in c]
def to_img(c):
    im=Image.new('RGBA',(len(c[0]),len(c)),(0,0,0,0)); px=im.load()
    for y,r in enumerate(c):
        for x,ch in enumerate(r):
            if ch!='.': px[x,y]=RGBA[ch]
    return im

# ---------------- body parts (16 wide) ----------------
HOOD_TOP=["......KKKKKK....","....KKHHHHHHK...","...KHAHHHHHhhK..","..KHAHHHHHHHhK..",".KHHHHHHHHHHhhK."]
HEAD_F=rows([r.ljust(16,'.')[:16] for r in HOOD_TOP]+[
".KHhnnnnnnnnhHK.",
".KHKnSSSSSSnKhK.",
".KHKnSKSSKSnKhK.",
".KhKSSrSSrSSKhK.",
"..KhKsSSSSsKhK.."])
HEAD_B=rows([r.ljust(16,'.')[:16] for r in HOOD_TOP]+[
".KHHHHHHHHHHhhK.",
".KHHHHHHHHHHhhK.",
".KhHHHHHHHHhhhK.",
"..KhhHHHHHhhK...",
"...KhhhhhhhK...."])
HEAD_S=rows([
"......KKKKK.....",
".....KHHHHHK....",
"....KHAHHHHhK...",
"...KHAHHHHHHhK..",
"..KHHHHHHHHHHhK.",
"..KHHHHHHnnnnhK.",
"..KhHHHKnSSSSK..",
"..KhHHHKnSSKSK..",
"...KhHHKSSrSSK..",
"....KhhKsSSSK..."])
TORSO_F=rows(["....KhHHHHhK....","....KVVwVVvK....","....KwwYwwwK....","....KvVVVVvK...."])
TORSO_B=rows(["....KhHHHHhK....","....KVwVVwvK....","....KwwwwwwK....","....KvVVVVvK...."])
TORSO_S=rows([".....KhHHK......",".....KVVwVK.....",".....KwwYwK.....",".....KvVVvK....."])
LEGS_F={'stand':rows(["....KddKKddK....","....KwwKKwwK....","....KKKKKKKK...."]),
        'liftL':rows(["....KwwKKddK....","....KKKKKwwK....","........KKKK...."]),
        'liftR':rows(["....KddKKwwK....","....KwwKKKKK....","....KKKK........"]),
        'wide': rows(["...KddK..KddK...","...KwwK..KwwK...","...KKKK..KKKK..."])}
def blink(head,row,cols):
    h=[r[:] for r in head]
    for x in cols: h[row][x]='s'
    return h

# ---------------- gear on his back ----------------
def sack(w=9,h=7):
    def d(p):
        cx,cy=(w-1)/2,(h-1)/2
        for y in range(h):
            for x in range(w):
                if ((x-cx)/(w/2))**2+((y-cy)/(h/2))**2<=1.0:
                    lx=(x-cx)/(w/2)+(y-cy)/(h/2)
                    p(x,y,'P' if lx<-0.9 else ('T' if lx<0.5 else 't'))
        for y in range(h):
            if ((w//2-cx)/(w/2))**2+((y-cy)/(h/2))**2<=1.0: p(w//2,y,'t')
        p(w//2,0,'w'); p(w//2,h-1,'w')
    return sprite(w,h,d)
def leather_bag(w,h):
    def d(p):
        for y in range(h):
            for x in range(w):
                if (x,y) in ((0,0),(w-1,0),(0,h-1),(w-1,h-1)): continue
                ch='W'
                if x==0: ch='L'
                if x==w-1 or y==h-1: ch='w'
                p(x,y,ch)
        fl=max(2,h//3)
        for y in range(fl):
            for x in range(1,w-1): p(x,y,'L' if y else 'l')
        for x in range(1,w-1): p(x,fl,'w')
        p(w//2,fl,'Y'); p(w//2,fl+1,'Y')
    return sprite(w,h,d)
def stick(length=9):
    def d(p):
        for i in range(length): p(i//3,i,'L' if i%2 else 'W')
        p(0,0,'o'); p(0,1,'o')
    return sprite(3,length,d)
def flask(sz=5):
    def d(p):
        p(2,0,'w'); p(2,1,'N')
        for y in range(2,2+sz-1):
            for x in range(sz):
                if (x-2)**2+(y-2-(sz-2)/2)**2<=((sz)/2)**2-0.2:
                    p(x,y,'C' if x+y<5 else ('B' if x+y<8 else 'b'))
        p(1,3,'N')
    return sprite(5,sz+1,d)


def pickaxe_s():
    def d(p):
        for x,y,ch in ((0,2,'N'),(1,1,'N'),(2,0,'N'),(3,0,'N'),(4,0,'N'),(5,1,'N'),(6,2,'N')): p(x,y,ch)
        for y in range(1,8): p(3,y,'W' if y%2 else 'L')
    return sprite(7,8,d)
def rope_s():
    g=[".TT.","Tt.T","T.tT",".TT."]
    return sprite(4,4,lambda p:[p(x,y,ch) for y,r in enumerate(g) for x,ch in enumerate(r) if ch!='.'])
def pot_s():
    g=["N..N","dddd","dDdd",".dd."]
    return sprite(4,4,lambda p:[p(x,y,ch) for y,r in enumerate(g) for x,ch in enumerate(r) if ch!='.'])
def red_potion():
    g=[".w.","rrP","rPr",".r."]
    return sprite(3,4,lambda p:[p(x,y,{'r':'o','P':'X'}.get(ch,ch) if False else ch) for y,r in enumerate(g) for x,ch in enumerate(r) if ch!='.'])
SIZE='medium'
def gear_back(c,view,dy):
    """everything carried on the back, drawn behind the body in down view, over it in up view"""
    if view=='down':
        if SIZE=='small': paste(c,leather_bag(12,6),6,12+dy)
        elif SIZE=='medium': paste(c,stick(),19,0+dy); paste(c,SACK,11,1+dy); paste(c,leather_bag(16,7),3,12+dy)
        else:
            paste(c,stick(),20,0+dy); paste(c,pickaxe_s(),0,1+dy); paste(c,sack(9,6),3,2+dy); paste(c,sack(11,8),10,0+dy)
            paste(c,leather_bag(20,8),2,11+dy)
    elif view=='up':
        if SIZE=='small': paste(c,leather_bag(10,7),7,12+dy)
        elif SIZE=='medium': paste(c,stick(),17,1+dy); paste(c,SACK,3,3+dy); paste(c,leather_bag(12,9),5,11+dy)
        else:
            paste(c,stick(),19,0+dy); paste(c,pickaxe_s(),12,0+dy); paste(c,sack(11,8),1,1+dy); paste(c,sack(8,6),11,4+dy)
            paste(c,leather_bag(16,11),4,9+dy)
    else:
        if SIZE=='small': paste(c,leather_bag(5,6),3,12+dy)
        elif SIZE=='medium': paste(c,leather_bag(7,8),1,11+dy); paste(c,stick(),3,0+dy); paste(c,SACK_S,1,4+dy)
        else:
            paste(c,leather_bag(9,10),0,10+dy); paste(c,stick(),5,0+dy); paste(c,pickaxe_s(),-2,0+dy); paste(c,sack(10,7),0,3+dy)
def gear_hang(c,view,dy,sway):
    if view=='down':
        paste(c,flask(),5+sway,15+dy)
        if SIZE=='large': paste(c,red_potion(),16-sway,16+dy); paste(c,rope_s(),18+sway,13+dy); paste(c,pot_s(),-1,14+dy)
    elif view=='up':
        paste(c,flask(),17+sway,15+dy)
        if SIZE=='large': paste(c,pot_s(),0+sway,15+dy); paste(c,rope_s(),18-sway,10+dy)
    else:
        paste(c,flask(),11+sway,15+dy)
        if SIZE=='large': paste(c,pot_s(),-1+sway,19+dy); paste(c,rope_s(),2-sway,18+dy)

# ---------------- character assembly ----------------
def arms_front(c,dy,hl,hr,raised=False):
    if raised:
        for ax in (2,13):
            for y in range(6,11): put(c,OX+ax,OY+y+dy,'V' if y>6 else 'v')
            put(c,OX+ax,OY+5+dy,'S'); put(c,OX+ax,OY+4+dy,'S')
        return
    for ax,hy in ((3,hl),(12,hr)):
        put(c,OX+ax,OY+10+dy,'V'); put(c,OX+ax,OY+11+dy+min(0,hy),'v'); put(c,OX+ax,OY+12+dy+hy,'S')
def body_front(c,dy,legs,hl=0,hr=0,closed=False,raised=False,head_dy=0):
    paste(c,LEGS_F[legs],OX,OY+14)
    paste(c,TORSO_F,OX,OY+10+dy)
    if not raised: arms_front(c,dy,hl,hr)
    paste(c,blink(HEAD_F,7,(6,9)) if closed else HEAD_F,OX,OY+dy+head_dy)
    if raised: arms_front(c,dy,hl,hr,True)
def body_back(c,dy,legs,hl=0,hr=0):
    paste(c,LEGS_F[legs],OX,OY+14); paste(c,TORSO_B,OX,OY+10+dy); arms_front(c,dy,hl,hr); paste(c,HEAD_B,OX,OY+dy)
def legs_side(c,nd,fd,nl,fl):
    for hip,dx,lift,col in ((6,fd,fl,'d'),(8,nd,nl,'D')):
        x=OX+hip; put(c,x,OY+14,col); put(c,x+1,OY+14,col)
        fx=x+dx//2; put(c,fx,OY+15-lift,col); put(c,fx+1,OY+15-lift,col)
        bx=x+dx; put(c,bx,OY+16-lift,'w'); put(c,bx+1,OY+16-lift,'w'); put(c,bx+2,OY+16-lift,'W' if col=='D' else 'w')
def torso_side(c,dy,hand,reach=0):
    paste(c,TORSO_S,OX,OY+10+dy)
    if reach:
        for i in range(reach+1): put(c,OX+8+i,OY+11+dy,'V')
        put(c,OX+9+reach,OY+11+dy,'S'); put(c,OX+9+reach,OY+10+dy,'S')
        return
    hx,hy=hand; put(c,OX+7,OY+10+dy,'v'); put(c,OX+7+(hx>0),OY+11+dy,'v'); put(c,OX+7+hx,OY+12+dy+hy,'S')
def head_side(c,dy,closed=False,lean=0):
    paste(c,blink(HEAD_S,7,(11,)) if closed else HEAD_S,OX+lean,OY+dy)

SACK=sack(); SACK_S=sack(9,6)
def frame(view,dy=0,legs='stand',hl=0,hr=0,closed=False,sway=0,side=None,extra=None):
    c=canvas()
    if view=='down':
        gear_back(c,'down',dy)
        body_front(c,dy,legs,hl,hr,closed)
        gear_hang(c,'down',dy,sway)
    elif view=='up':
        body_back(c,dy,legs,hl,hr)
        gear_back(c,'up',dy)
        gear_hang(c,'up',dy,sway)
    else:  # side, facing right
        nd,fd,nl,fl,hand,lean,reach=side
        legs_side(c,nd,fd,nl,fl); torso_side(c,dy,hand,reach)
        gear_back(c,'side',dy)
        head_side(c,dy,closed,lean)
        if reach==0: gear_hang(c,'side',dy,sway)
    c=outline(c)
    if extra: extra(c)
    return c

def sparkle(c,pts):
    for x,y,ch in pts: put(c,x,y,ch)

def build(size):
    global SIZE
    SIZE=size
    # ---------------- animations ----------------
    A={}
    IDLE=[0,0,1,1]
    A['idle_down']=[frame('down',d,closed=(i==3)) for i,d in enumerate(IDLE)]
    A['idle_up']=[frame('up',d) for d in IDLE]
    A['idle_right']=[frame('side',d,closed=(i==3),side=(1,-1,0,0,(0,0),0,0)) for i,d in enumerate(IDLE)]
    WALK_F=[('liftL',0,1,-1),('liftL',1,1,-1),('stand',0,0,0),('liftR',0,-1,1),('liftR',1,-1,1),('stand',0,0,0)]
    SW=[0,1,0,-1,0,1]
    A['walk_down']=[frame('down',dy,l,hl,hr,sway=SW[i]) for i,(l,dy,hl,hr) in enumerate(WALK_F)]
    A['walk_up']=[frame('up',dy,{'liftL':'liftR','liftR':'liftL'}.get(l,l),hr,hl,sway=SW[i]) for i,(l,dy,hl,hr) in enumerate(WALK_F)]
    WALK_S=[(2,-2,0,0,0,(2,0)),(1,-1,0,1,1,(1,0)),(0,0,0,1,0,(0,0)),(-2,2,0,0,0,(-2,-1)),(-1,1,1,0,1,(-1,0)),(0,0,1,0,0,(0,0))]
    A['walk_right']=[frame('side',dy,sway=SW[i],side=(nd,fd,nl,fl,hand,0,0)) for i,(nd,fd,nl,fl,dy,hand) in enumerate(WALK_S)]
    RUN_F=[('liftL',-1,2,-2),('liftL',0,2,-2),('stand',1,0,0),('liftR',-1,-2,2),('liftR',0,-2,2),('stand',1,0,0)]
    A['run_down']=[frame('down',dy,l,hl,hr,sway=SW[i]) for i,(l,dy,hl,hr) in enumerate(RUN_F)]
    A['run_up']=[frame('up',dy,{'liftL':'liftR','liftR':'liftL'}.get(l,l),hr,hl,sway=SW[i]) for i,(l,dy,hl,hr) in enumerate(RUN_F)]
    RUN_S=[(3,-3,0,0,0,(2,-1)),(2,-2,0,2,-1,(1,-1)),(0,0,0,2,0,(0,0)),(-3,3,0,0,0,(-2,-1)),(-2,2,2,0,-1,(-1,-1)),(0,0,2,0,0,(0,0))]
    A['run_right']=[frame('side',dy,sway=SW[i],side=(nd,fd,nl,fl,hand,1,0)) for i,(nd,fd,nl,fl,dy,hand) in enumerate(RUN_S)]

    def dig_frame(stage):
        c=canvas(); dy=1 if stage in (1,2) else 0
        if SIZE=='medium': paste(c,stick(),19,0+dy); paste(c,SACK,11,1+dy)
        if SIZE=='large': paste(c,stick(),20,0+dy); paste(c,pickaxe_s(),0,1+dy); paste(c,sack(9,6),3,2+dy); paste(c,sack(11,8),10,0+dy)
        paste(c,LEGS_F['wide'],OX,OY+14); paste(c,TORSO_F,OX,OY+10+dy)
        paste(c,HEAD_F if stage!=2 else blink(HEAD_F,7,(6,9)),OX,OY+dy+(1 if stage==2 else 0))
        bw={'small':10,'medium':14,'large':18}[SIZE]; paste(c,leather_bag(bw,7),12-bw//2-1,15)
        if stage==0: put(c,12-bw//2,15,'S'); put(c,12+bw//2-1,15,'S')
        c=outline(c)
        if stage==2: sparkle(c,[(2,6,'N'),(3,4,'Y'),(20,10,'N'),(21,8,'Y'),(1,9,'F')])
        if stage==3: sparkle(c,[(11,16,'F'),(12,15,'X'),(13,16,'F'),(12,17,'Y')]); put(c,9,16,'S'); put(c,14,16,'S')
        return c
    A['dig']=[dig_frame(s) for s in range(4)]
    def hold(dy):
        c=canvas(); gear_back(c,'down',dy)
        body_front(c,dy,'stand',raised=True); gear_hang(c,'down',dy,0)
        return outline(c)
    A['hold_up']=[hold(0),hold(1)]
    A['give_right']=[frame('side',0,side=(1,-1,0,0,(1,0),0,0)),frame('side',0,side=(1,-1,0,0,(0,0),0,1)),frame('side',0,side=(2,-1,0,0,(0,0),1,3))]
    def hurt_frame(flash):
        c=canvas(); gear_back(c,'down',1)
        body_front(c,0,'wide',-2,-2,closed=True,head_dy=0)
        c=[r[:-1]+['.'] if False else r for r in c]
        c=outline(c)
        if flash: c=[[('X' if ch not in '.K' else ch) for ch in r] for r in c]
        return c
    A['hurt']=[hurt_frame(False),hurt_frame(True)]
    def death_frames():
        base=frame('down',0,closed=True)
        sink=canvas();
        for y in range(FH):
            for x in range(FW):
                if y+2<FH and base[y][x]!='.': sink[y+2][x]=base[y][x]
        # lying on his back: rotate the standing frame and drop it to the floor
        rot=[list(r) for r in zip(*base)][::-1]
        ys=[y for y,r in enumerate(rot) if any(ch!='.' for ch in r)]
        lie=canvas(); paste(lie,rot,0,23-ys[-1])
        lie2=[r[:] for r in lie]; sparkle(lie2,[(5,9,'F'),(9,7,'Y'),(13,9,'F')])
        return [base,sink,lie,lie2]
    A['death']=death_frames()
    for k in ('idle','walk','run'): A[f'{k}_left']=[flip(f) for f in A[f'{k}_right']]
    A['give_left']=[flip(f) for f in A['give_right']]

    ORDER=['idle_down','idle_up','idle_left','idle_right','walk_down','walk_up','walk_left','walk_right',
           'run_down','run_up','run_left','run_right','dig','hold_up','give_left','give_right','hurt','death']
    FPS={'idle':4,'walk':9,'run':13,'dig':6,'hold':4,'give':8,'hurt':10,'death':6}
    LOOP={'dig':False,'give':False,'hurt':False,'death':False}
    OUT=f'helper_bags3/{SIZE}'; os.makedirs(OUT+'/frames',exist_ok=True)
    cols=max(len(A[k]) for k in ORDER)
    sheet=Image.new('RGBA',(FW*cols,FH*len(ORDER)),(0,0,0,0))
    meta={'image':f'helper_{SIZE}.png','frameWidth':FW,'frameHeight':FH,'anchor':'feet at bottom-centre (x=12, y=23)','animations':{}}
    for r,k in enumerate(ORDER):
        for i,f in enumerate(A[k]):
            im=to_img(f); sheet.paste(im,(i*FW,r*FH)); im.save(f'{OUT}/frames/{k}_{i}.png')
        base=k.split('_')[0]
        meta['animations'][k]={'row':r,'frames':len(A[k]),'fps':FPS[base],'loop':LOOP.get(base,True)}
    meta['notes']={'hold_up':'hands raised and empty: draw the gear icon above his head',
                   'give_left/right':'last frame has the hand out: draw the gear at the hand',
                   'dig':'rummages in the pack; ends on a glint, then play hold_up'}
    sheet.save(f'{OUT}/helper_{SIZE}.png'); json.dump(meta,open(f'{OUT}/helper_{SIZE}.json','w'),indent=1)
    # end


    return sheet, A, ORDER

results={}
for size in ('small','medium','large'):
    results[size]=build(size)
sheets=[results[s][0] for s in ('small','medium','large')]
pv=Image.new('RGBA',(sum(x.width for x in sheets)+40,sheets[0].height),(61,37,59,255)); x=0
for sh in sheets: pv.alpha_composite(sh,(x,0)); x+=sh.width+20
pv.resize((pv.width*3,pv.height*3),Image.NEAREST).save('helper_bags3/preview_3x_not_for_game.png')
show=['idle_down','walk_down','walk_left','walk_up','walk_right','dig','hold_up']
gif=[]
for t in range(24):
    im=Image.new('RGB',(FW*len(show),FH*3),(61,37,59))
    for si,size in enumerate(('small','medium','large')):
        A=results[size][1]
        for j,k in enumerate(show):
            seq=A[k]; idx=(t//2 if k.startswith('idle') or k in ('dig','hold_up') else t)%len(seq)
            fr=to_img(seq[idx]); im.paste(fr,(j*FW,si*FH),fr)
    gif.append(im.resize((im.width*4,im.height*4),Image.NEAREST))
gif[0].save('helper_bags3/animated_preview_not_for_game.gif',save_all=True,append_images=gif[1:],duration=110,loop=0)
print('built', [s.size for s in sheets])
