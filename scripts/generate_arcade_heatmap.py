#!/usr/bin/env python3
"""Generate the looping arcade contribution heatmap GIF."""

import argparse, datetime, random
from PIL import Image, ImageDraw, ImageFont

S=2; W=53; D=7; CELL=10*S; GAP=2*S; PITCH=CELL+GAP
LM=RM=6*S; TM=16*S; LANE=26*S
GW=W*PITCH-GAP; GH=D*PITCH-GAP
CW=LM+GW+RM; CH=TM+GH+LANE

BG=(13,17,23); EMPTY=(22,27,34)
LEVEL=[EMPTY,(14,68,41),(0,109,50),(38,166,65),(57,211,83)]
TEXT=(125,133,144); SHIP=(88,166,255); WHITE=(201,209,217)
BULLET=(255,214,102); EXP=[(255,235,130),(255,160,60),(255,90,60)]
FIRE=1; SPEED=14*S; EXPL=4; ATTACK=85; REBUILD=23; FRAME_MS=110

SHIP_BITMAP=[
    ".....#.....",
    "....###....",
    "...#####...",
    "..#######..",
    ".###...###.",
    "###########",
    "..##...##..",
]

def grid(seed=42):
    r=random.Random(seed); g=[[0]*D for _ in range(W)]
    for w in range(W):
        base=r.random()
        for d in range(D):
            x=r.random()
            if base<.15: v=0 if x<.7 else r.choice([1,2])
            elif base<.6: v=0 if x<.35 else r.choice([1,1,2,3])
            else: v=0 if x<.15 else r.choice([1,2,3,3,4])
            g[w][d]=v
    return g

def labels():
    today=datetime.date.today()
    start=today-datetime.timedelta(weeks=W-1)
    start-=datetime.timedelta(days=(start.weekday()+1)%7)
    out={}; last=None
    for w in range(W):
        dt=start+datetime.timedelta(weeks=w)
        if dt.month!=last: out[w]=dt.strftime("%b"); last=dt.month
    return out

def xy(w,d): return LM+w*PITCH, TM+d*PITCH

def draw_grid(draw,g,font,labs,img):
    layer=Image.new("L",img.size,0); ld=ImageDraw.Draw(layer)
    for w,name in labs.items():
        x,_=xy(w,0); ld.text((x,2*S),name,fill=255,font=font)
    img.paste(Image.new("RGB",img.size,TEXT),(0,0),layer)
    for w in range(W):
        for d in range(D):
            x,y=xy(w,d)
            draw.rounded_rectangle((x,y,x+CELL-1,y+CELL-1),radius=2*S,fill=LEVEL[g[w][d]])

def ship(draw,cx,base):
    scale=3; x0=int(cx-len(SHIP_BITMAP[0])*scale/2); y0=base-len(SHIP_BITMAP)*scale
    for j,row in enumerate(SHIP_BITMAP):
        for i,ch in enumerate(row):
            if ch=="#":
                c=WHITE if j==0 else SHIP
                x=x0+i*scale; y=y0+j*scale
                draw.rectangle((x,y,x+scale-1,y+scale-1),fill=c)

def bullet(draw,x,y):
    bw=2*S; bh=4*S
    draw.rectangle((x-bw//2,y-bh,x+bw//2,y),fill=BULLET)

def explosion(draw,x,y,age):
    c=EXP[min(age,len(EXP)-1)]; r=(1+age)*S; s=S
    for px,py in ((x,y-r),(x,y+r),(x-r,y),(x+r,y),(x,y)):
        draw.rectangle((px-s//2,py-s//2,px+s//2,py+s//2),fill=c)

def frames():
    original=grid(); g=[r[:] for r in original]; labs=labels()
    font=None
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"):
        try: font=ImageFont.truetype(p,9*S); break
        except Exception: pass
    if font is None: font=ImageFont.load_default()

    xmin=LM+CELL; xmax=LM+GW-CELL; ship_y=CH-4*S
    bullets=[]; explosions=[]; destroyed=[]; out=[]

    for f in range(ATTACK+REBUILD):
        img=Image.new("RGB",(CW,CH),BG); draw=ImageDraw.Draw(img)
        if f<ATTACK:
            half=ATTACK/2
            t=f/max(1,half-1) if f<half else (f-half)/max(1,half-1)
            sx=(xmin+t*(xmax-xmin)) if f<half else (xmax-t*(xmax-xmin))
            if f and f%FIRE==0:
                col=min(W-1,max(0,round((sx-LM)/PITCH)))
                bullets.append({"w":col,"x":LM+col*PITCH+CELL/2,"y":ship_y-10*S})
            alive=[]
            for b in bullets:
                b["y"]-=SPEED
                row=int((b["y"]-TM)/PITCH)
                if 0<=row<D and g[b["w"]][row]:
                    g[b["w"]][row]=0; destroyed.append((b["w"],row))
                    x,y=xy(b["w"],row)
                    explosions.append({"x":x+CELL//2,"y":y+CELL//2,"a":0}); continue
                if b["y"]>=TM-8: alive.append(b)
            bullets=alive
        else:
            t=(f-ATTACK)/max(1,REBUILD-1)
            sx=xmin+(xmax-xmin)*(.4*(t/.5 if t<.5 else (1-t)/.5))
            bullets=[]
            n=round(t*len(destroyed))
            for w,d in destroyed[:n]: g[w][d]=original[w][d]
            if f==ATTACK+REBUILD-1: g=[r[:] for r in original]

        ex2=[]
        for e in explosions:
            e["a"]+=1
            if e["a"]<=EXPL: ex2.append(e)
        explosions=ex2

        draw_grid(draw,g,font,labs,img)
        for b in bullets: bullet(draw,int(b["x"]),int(b["y"]))
        for e in explosions: explosion(draw,e["x"],e["y"],e["a"])
        ship(draw,sx,ship_y); out.append(img)
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--out",default="contrib-heatmap-arcade.gif"); a=ap.parse_args()
    fs=frames()
    colors=list(dict.fromkeys([BG,EMPTY]+LEVEL+[TEXT,SHIP,WHITE,BULLET]+EXP))
    pal=Image.new("P",(1,1)); flat=[]
    for c in colors: flat.extend(c)
    flat.extend(colors[-1]*(256-len(colors))); pal.putpalette(flat)
    q=[im.quantize(palette=pal,dither=Image.Dither.NONE) for im in fs]
    q[0].save(a.out,save_all=True,append_images=q[1:],duration=FRAME_MS,loop=0,optimize=True,disposal=2)
    print(f"Wrote {a.out}: {len(fs)} frames, canvas {CW}x{CH}, colors {len(colors)}")

if __name__=="__main__": main()
