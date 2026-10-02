#!/usr/bin/env python3
"""Find a song's 'hits and dips' (energy pickups and drops) so a pickup can be
lined up with a topic shift (e.g. problem -> solution).
Usage: music_points.py song.mp3 [--win 0.5] [--jump 4]
Prints pickups/dips (song time) and an energy timeline. To land a pickup at
song time P on video time T, in a music section starting at video time S,
use mix_audio.py --music song.mp3@S-E~OFF with OFF = P - (T - S)."""
import argparse, re, subprocess

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("song")
    ap.add_argument("--win",type=float,default=0.5); ap.add_argument("--jump",type=float,default=4,
        help="dB change between adjacent 2 s averages that counts as a hit/dip")
    a=ap.parse_args()
    n=int(48000*a.win)
    err=subprocess.run(["ffmpeg","-hide_banner","-i",a.song,"-af",
        f"aresample=48000,asetnsamples={n},astats=metadata=1:reset=1,"
        "ametadata=print:key=lavfi.astats.Overall.RMS_level","-f","null","-"],
        capture_output=True,text=True).stderr
    vals=[float(v) if v!="-inf" else -90.0 for v in re.findall(r"RMS_level=(-?[\d.inf]+)",err)]
    k=max(1,int(2/a.win)); pts=[]
    ds=[0.0]*len(vals)
    for i in range(k,len(vals)-k):
        ds[i]=sum(vals[i:i+k])/k-sum(vals[i-k:i])/k
    # keep only local extremes of the change curve (the actual moment of change)
    for i in range(k,len(vals)-k):
        d=ds[i]; nb=ds[max(0,i-k):i+k+1]
        if abs(d)>=a.jump and abs(d)==max(abs(x) for x in nb):
            if not pts or i*a.win-pts[-1][0]>2:
                pts.append((round(i*a.win,1),"PICKUP" if d>0 else "DIP",round(d,1)))
    for t,kind,d in pts: print(f"{t:7.1f}s  {kind:6s} {d:+.1f} dB")
    print("energy (dB per 2 s):"," ".join(f"{int(sum(vals[i:i+k])/k)}" for i in range(0,len(vals),k)))

if __name__=="__main__": main()
