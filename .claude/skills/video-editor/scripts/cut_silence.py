#!/usr/bin/env python3
"""Remove EMPTY dead air (pauses with nothing happening) from talking-head
footage. Intentional pauses (beats filled with a visual + SFX, or music
carrying emotion) are good; protect them with --protect A-B. Optionally alternate punch-in
zooms on each jump cut so cuts feel intentional (a standard YouTube technique).
Writes <out>.map.json mapping source time -> output time.
Usage: cut_silence.py in.mp4 out.mp4 [--noise -35dB] [--min-silence 0.4]
       [--pad 0.12] [--min-keep 0.6] [--punch 1.12] [--protect A-B] [--dry-run]"""
import argparse, re, subprocess, json

def duration(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0",p],capture_output=True,text=True).stdout)

def dims(p):
    o=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
        "stream=width,height","-of","csv=p=0",p],capture_output=True,text=True).stdout
    w,h=o.strip().split(","); return int(w),int(h)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--noise",default="auto",
        help="RMS pause threshold, e.g. -40dB, or 'auto' = this file's noise floor + 6 dB "
             "(fixed thresholds fail on quiet or noisy recordings)")
    ap.add_argument("--min-silence",type=float,default=0.4)
    ap.add_argument("--pad",type=float,default=0.12,help="breath kept on each side")
    ap.add_argument("--min-keep",type=float,default=0.6,help="drop/merge shorter segments")
    ap.add_argument("--punch",type=float,default=1.0,help="zoom on alternate segments, e.g. 1.12")
    ap.add_argument("--punch-y",type=float,default=0.5,
        help="vertical anchor of the punch-in: 0=top (keep a head near the top of frame), 0.5=center")
    ap.add_argument("--punch-x",type=float,default=0.5,help="horizontal anchor (0=left, 1=right)")
    ap.add_argument("--protect",action="append",default=[],
        help="A-B range (input seconds) whose pauses are intentional; never cut")
    ap.add_argument("--style",choices=["hangout","standard","entertainment"],
        help="preset by viewer experience: hangout keeps natural pauses (authentic), "
             "entertainment removes nearly all (constant speech)")
    ap.add_argument("--dry-run",action="store_true")
    a=ap.parse_args()
    presets={"hangout":dict(min_silence=1.5,pad=0.35,punch=1.0),
             "standard":dict(min_silence=0.5,pad=0.15),
             "entertainment":dict(min_silence=0.25,pad=0.08,punch=1.12)}
    for k,v in presets.get(a.style,{}).items(): setattr(a,k,v)
    D=duration(a.inp)
    # Pause detection on short RMS windows. (ffmpeg's silencedetect compares
    # sample PEAKS to the threshold, which makes it brittle on noisy or quiet
    # recordings: a 2 dB threshold change can flip from 0 to 20 pauses.)
    WIN=0.05
    e2=subprocess.run(["ffmpeg","-hide_banner","-i",a.inp,"-vn","-af",
        f"aresample=16000,asetnsamples={int(16000*WIN)},astats=metadata=1:reset=1,"
        "ametadata=print:key=lavfi.astats.Overall.RMS_level","-f","null","-"],
        capture_output=True,text=True).stderr
    lv=[float(x) if x!="-inf" else -120.0 for x in re.findall(r"RMS_level=(-?[\d.]+|-inf)",e2)]
    srt=sorted(lv); floor=srt[len(srt)//10] if srt else -60
    thr = floor+6 if a.noise=="auto" else float(str(a.noise).replace("dB",""))
    # smooth over 0.15 s so single loud frames inside a pause don't split it
    k=3; sm=[max(lv[max(0,i-k//2):i+k//2+1]) for i in range(len(lv))]
    st,en=[],[]; run=None
    for i,x in enumerate(sm+[999]):
        if x<thr and run is None: run=i
        elif x>=thr and run is not None:
            if (i-run)*WIN>=a.min_silence: st.append(run*WIN); en.append(i*WIN)
            run=None
    print(json.dumps({"noise_floor_db":round(floor,1),"pause_threshold_db":round(thr,1),
                      "pauses_found":len(st)}))
    prot=[tuple(map(float,p.split("-"))) for p in a.protect]
    pairs=[(s,e) for s,e in zip(st,en)
           if not any(s<pb and e>pa for pa,pb in prot)]
    keep=[]; cur=0.0
    for s,e in pairs:
        s2=max(cur,s+a.pad); 
        if s2-cur>0: keep.append([cur,min(s2,D)])
        cur=max(0,e-a.pad)
    if cur<D: keep.append([cur,D])
    merged=[]
    for k in keep:
        if merged and k[0]-merged[-1][1]<0.05: merged[-1][1]=k[1]
        else: merged.append(k)
    merged=[k for k in merged if k[1]-k[0]>=a.min_keep] or keep
    kept=sum(b-a_ for a_,b in merged)
    info={"original_s":round(D,1),"kept_s":round(kept,1),"removed_s":round(D-kept,1),
          "segments":len(merged)}
    print(json.dumps(info))
    if a.dry_run:
        print(json.dumps([[round(x,2),round(y,2)] for x,y in merged])); return
    # Render each segment separately, then concat (one filter graph with dozens
    # of trims buffers the whole source and gets OOM-killed on real footage).
    import tempfile, os
    w,h=dims(a.inp); tmp=tempfile.mkdtemp(); files=[]
    fps=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
        "stream=r_frame_rate","-of","csv=p=0",a.inp],capture_output=True,text=True).stdout.strip()
    for i,(s_,e) in enumerate(merged):
        z = a.punch if (a.punch>1 and i%2==1) else 1.0
        vf = (f"scale=iw*{z}:-2,crop={w}:{h}:(iw-{w})*{a.punch_x}:(ih-{h})*{a.punch_y},"
              if z>1 else "") + f"setsar=1,fps={fps}"
        L=e-s_; out=os.path.join(tmp,f"s{i:04d}.mp4"); files.append(out)
        subprocess.run(["ffmpeg","-v","error","-y","-ss",f"{s_:.3f}","-i",a.inp,"-t",f"{L:.3f}",
            "-vf",vf,"-af",f"aresample=48000,afade=t=in:d=0.01,afade=t=out:st={max(0,L-0.01):.3f}:d=0.01",
            "-c:v","libx264","-crf","18","-preset","fast","-c:a","aac","-b:a","192k","-ac","2",out],check=True)
    lst=os.path.join(tmp,"list.txt"); open(lst,"w").write("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",lst,"-c","copy",a.out],check=True)
    # timing map: where each kept source segment landed in the output (actual,
    # frame-accurate durations), so graphics/SFX can be placed on source words
    tmap=[]; t=0.0
    for (s_,e),f in zip(merged,files):
        d=duration(f); tmap.append([round(s_,3),round(e,3),round(t,3)]); t+=d
    mp=os.path.splitext(a.out)[0]+".map.json"; json.dump(tmap,open(mp,"w"))
    print(json.dumps({"timing_map":mp,"note":"[src_start, src_end, out_start]; out = out_start + (src - src_start)"}))

if __name__=="__main__": main()
