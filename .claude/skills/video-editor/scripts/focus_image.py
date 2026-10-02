#!/usr/bin/env python3
"""Turn a still image into an attention-guiding clip (never show a plain,
static image: it's boring and confusing). Combines:
  - slow push-in (movement on a still)
  - darken and/or blur everything outside the focus area (fades in)
  - optional glow on the focus area
  - optional hue tint: red = negative, green/yellow = positive
  - optional accent box or underline around the focus area
Usage:
  focus_image.py img.png out.mp4 --focus 0.55,0.30,0.35,0.25 [--dur 4]
     [--size 1920x1080] [--mode darken|blur|both] [--tint red|green|yellow]
     [--glow] [--mark box|underline] [--push 1.08] [--reveal 0.6]
--focus is x,y,w,h as fractions of the frame (after cover-scaling to --size).
Output has no audio; add a shutter/pop/highlight SFX when it appears."""
import argparse, subprocess

TINTS={"red":"colorchannelmixer=rr=1:gg=0.5:bb=0.5",
       "green":"colorchannelmixer=rr=0.65:gg=1:bb=0.65",
       "yellow":"colorchannelmixer=rr=1:gg=0.95:bb=0.5"}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("img"); ap.add_argument("out")
    ap.add_argument("--focus",required=True); ap.add_argument("--dur",type=float,default=4)
    ap.add_argument("--size",default="1920x1080"); ap.add_argument("--mode",default="both")
    ap.add_argument("--tint"); ap.add_argument("--glow",action="store_true")
    ap.add_argument("--mark",choices=["box","underline"]); ap.add_argument("--push",type=float,default=1.08)
    ap.add_argument("--reveal",type=float,default=0.6,help="seconds before focus effect starts")
    ap.add_argument("--accent",default="0x3CC8FF"); ap.add_argument("--fps",type=int,default=30)
    a=ap.parse_args()
    W,H=map(int,a.size.split("x")); fx,fy,fw,fh=map(float,a.focus.split(","))
    X,Y,FW,FH=int(fx*W),int(fy*H),int(fw*W)//2*2,int(fh*H)//2*2
    surround=[]
    if a.mode in("darken","both"): surround.append("eq=brightness=-0.22:saturation=0.7")
    if a.mode in("blur","both"): surround.append("boxblur=12:2")
    fc=[f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
        f"fps={a.fps},trim=duration={a.dur}"+(","+TINTS[a.tint] if a.tint else "")+",format=yuva420p,split=3[plain][d][f]",
        f"[d]{','.join(surround) or 'null'},fade=t=in:st={a.reveal}:d=0.4:alpha=1[dark]",
        f"[plain][dark]overlay[bg]"]
    fg=f"[f]crop={FW}:{FH}:{X}:{Y}"
    if a.glow:
        fc.append(fg+",format=gbrap,split[f1][f2]"); fc.append("[f2]boxblur=8:1[g]")
        fc.append("[f1][g]blend=all_mode=screen:all_opacity=0.3,format=yuva420p[fgc]")
    else:
        fc.append(fg+"[fgc]")
    fc.append(f"[fgc]fade=t=in:st={a.reveal}:d=0.01:alpha=1[fgf]")
    chain=f"[bg][fgf]overlay={X}:{Y}"
    if a.mark=="box":
        chain+=f",drawbox=x={X-4}:y={Y-4}:w={FW+8}:h={FH+8}:color={a.accent}:t=5:enable='gte(t,{a.reveal+0.15})'"
    elif a.mark=="underline":
        chain+=f",drawbox=x={X}:y={Y+FH+6}:w={FW}:h=6:color={a.accent}:t=fill:enable='gte(t,{a.reveal+0.15})'"
    # slow push-in toward the focus center
    cx,cy=X+FW/2,Y+FH/2; k=(a.push-1)/a.dur
    chain+=(f",scale=w='trunc({W}*(1+{k}*t)/2)*2':h=-2:eval=frame,"
            f"crop={W}:{H}:x='min(max(0,{cx}*(iw/{W})-{W}/2),iw-{W})':y='min(max(0,{cy}*(ih/{H})-{H}/2),ih-{H})',"
            f"format=yuv420p[v]")
    fc.append(chain)
    subprocess.run(["ffmpeg","-v","error","-y","-loop","1","-i",a.img,"-filter_complex",";".join(fc),
        "-map","[v]","-t",str(a.dur),"-c:v","libx264","-crf","18","-preset","fast",a.out],check=True)

if __name__=="__main__": main()
