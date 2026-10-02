#!/usr/bin/env python3
"""'Shut up and show it': insert deliberate pauses into dense narration.
At each timestamp, the voice stops for DUR seconds while the picture holds
(the last frame is frozen). Then cover the pause with a visual layer (B-roll,
graphic, photo) and a matching SFX so the viewer gets a moment to absorb
without being under-stimulated. Timestamps refer to the INPUT timeline; the
script prints where each beat lands in the OUTPUT so overlays/SFX can be placed.
Usage: insert_beats.py in.mp4 out.mp4 --at 12.4:1.0 --at 31.8:2.5"""
import argparse, json, subprocess

def duration(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0",p],capture_output=True,text=True).stdout)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--at",action="append",required=True,help="T:DUR")
    a=ap.parse_args(); D=duration(a.inp)
    beats=sorted((float(x.split(":")[0]),float(x.split(":")[1])) for x in a.at)
    bounds=[0]+[t for t,_ in beats]+[D]; fc=[]; parts=[]; shift=0; placed=[]
    for i in range(len(bounds)-1):
        s,e=bounds[i],bounds[i+1]
        pad = beats[i][1] if i<len(beats) else 0
        v=f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS"
        au=f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=out:st={max(0,e-s-0.02)}:d=0.02"
        if pad:
            v+=f",tpad=stop_mode=clone:stop_duration={pad}"
            au+=f",apad=pad_dur={pad}"
            placed.append({"input_t":e,"output_start":round(e+shift,2),"output_end":round(e+shift+pad,2)})
            shift+=pad
        fc.append(v+f",setsar=1[v{i}]"); fc.append(au+f"[a{i}]"); parts.append(f"[v{i}][a{i}]")
    fc.append("".join(parts)+f"concat=n={len(parts)}:v=1:a=1[v][a]")
    subprocess.run(["ffmpeg","-v","error","-y","-i",a.inp,"-filter_complex",";".join(fc),
        "-map","[v]","-map","[a]","-c:v","libx264","-crf","18","-preset","fast",
        "-c:a","aac","-b:a","192k",a.out],check=True)
    print(json.dumps({"beats":placed,"new_duration":round(D+shift,2)},indent=1))

if __name__=="__main__": main()
