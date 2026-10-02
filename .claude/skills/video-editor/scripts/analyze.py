#!/usr/bin/env python3
"""Analyze a video's edit: pacing (cuts), dead air (silences), loudness.
Usage: analyze.py input.mp4 [--out report.json] [--sheet sheet.png] [--scene 0.3]
Prints a human-readable summary and writes JSON."""
import argparse, json, re, subprocess, sys

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stderr

def duration(path):
    out = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                          "-of","csv=p=0",path],capture_output=True,text=True).stdout
    return float(out.strip())

def cuts(path, thresh):
    # scdet reports scene scores; downscale for speed
    # select+scene is more sensitive than scdet; still a LOWER BOUND
    # (misses slow animated graphics and same-framing jump cuts)
    err = run(["ffmpeg","-hide_banner","-i",path,"-vf",
               f"scale=160:-2,select='gt(scene,{thresh})',showinfo","-an","-f","null","-"])
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", err)]

def silences(path, noise="-35dB", d=0.5):
    err = run(["ffmpeg","-hide_banner","-i",path,"-vn","-af",
               f"silencedetect=noise={noise}:d={d}","-f","null","-"])
    starts = [float(x) for x in re.findall(r"silence_start:\s*([\d.]+)", err)]
    ends = re.findall(r"silence_end:\s*([\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)", err)
    return [{"start":s,"end":float(e),"dur":float(dd)} for s,(e,dd) in zip(starts,ends)]

def loudness(path):
    err = run(["ffmpeg","-hide_banner","-i",path,"-vn","-af","ebur128=framelog=quiet",
               "-f","null","-"])
    summ = err.split("Summary:")[-1]
    g = lambda k: float(re.search(k+r":\s*(-?[\d.]+)", summ).group(1)) if re.search(k+r":\s*(-?[\d.]+)", summ) else None
    return {"integrated_lufs":g("I"),"loudness_range_lu":g("LRA")}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input"); ap.add_argument("--out"); ap.add_argument("--sheet")
    ap.add_argument("--scene", type=float, default=0.12)
    a = ap.parse_args()
    D = duration(a.input); c = cuts(a.input, a.scene); s = silences(a.input); L = loudness(a.input)
    shots = [b-a_ for a_,b in zip([0]+c, c+[D])]
    hook = [t for t in c if t <= 30]
    def cpm(t0,t1):
        n=len([t for t in c if t0<=t<t1]); return round(n/((t1-t0)/60),1) if t1>t0 else 0
    thirds=[cpm(0,min(60,D))]+[cpm(i*D/3,(i+1)*D/3) for i in range(3)]
    r = {
      "file":a.input,"duration_s":round(D,1),
      "cuts":len(c),"cuts_per_min":round(len(c)/(D/60),1),
      "avg_shot_s":round(sum(shots)/len(shots),2),
      "longest_shots":sorted([{"start":round(st,1),"len":round(l,1)} for st,l in zip([0]+c,shots)],
                             key=lambda x:-x["len"])[:5],
      "cuts_first_30s":len(hook),
      "cuts_per_min_first60_then_by_third":thirds,
      "silences_over_0.5s":len(s),
      "silence_total_s":round(sum(x["dur"] for x in s),1),
      "longest_silences":sorted(s,key=lambda x:-x["dur"])[:5],
      **L}
    if a.sheet:
        subprocess.run(["ffmpeg","-v","error","-y","-i",a.input,"-vf",
            f"fps={24/D},scale=320:-2,tile=6x4",a.sheet])
    print(json.dumps(r,indent=2))
    if a.out: json.dump(r,open(a.out,"w"),indent=2)

if __name__=="__main__": main()
