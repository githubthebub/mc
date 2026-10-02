#!/usr/bin/env python3
"""Compress a long stretch that lacks conflict (planning, building, travel,
grinding) into a short montage that still shows clear progression, e.g. two
months of building -> a 20-second build montage.
Picks evenly spaced chunks across each range so every stage of progress is
represented (skipping progression points causes confusion), optionally speeds
them up, and joins them. Original audio is dropped by default (lay music over
it with mix_audio.py) or kept quietly with --keep-audio.
Usage: montage.py in.mp4 out.mp4 --range 120-900 [--range 950-1400]
         [--target 20] [--chunk 1.0] [--speed 1.5] [--keep-audio -12]
Prints each chunk's source time so you can check nothing key was skipped."""
import argparse, json, subprocess

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--range",action="append",required=True)
    ap.add_argument("--target",type=float,default=20); ap.add_argument("--chunk",type=float,default=1.0)
    ap.add_argument("--speed",type=float,default=1.0)
    ap.add_argument("--keep-audio",type=float,help="keep original audio at this dB")
    a=ap.parse_args()
    rs=[tuple(map(float,r.split("-"))) for r in a.range]; total=sum(b-x for x,b in rs)
    src_per_chunk=a.chunk*a.speed; n=max(2,int(round(a.target/a.chunk)))
    chunks=[]
    for x,b in rs:
        k=max(1,round(n*(b-x)/total)); step=(b-x-src_per_chunk)/max(1,k-1) if k>1 else 0
        chunks+=[(round(x+i*step,2),round(x+i*step+src_per_chunk,2)) for i in range(k)]
    # extract each chunk separately with fast seeking (a single filter graph
    # with many trims buffers the whole source and runs out of memory)
    import tempfile, os
    tmp=tempfile.mkdtemp(); files=[]
    W,H,fps=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries",
        "stream=width,height,r_frame_rate","-of","csv=p=0",a.inp],capture_output=True,text=True).stdout.strip().split(",")
    for i,(s_,e) in enumerate(chunks):
        out=os.path.join(tmp,f"c{i:03d}.mp4"); files.append(out)
        vf=f"setpts=PTS/{a.speed},scale={W}:{H},setsar=1,fps={fps}"
        if a.keep_audio is not None:
            af=(f"atempo={a.speed},volume={a.keep_audio}dB,aresample=48000,"
                f"afade=t=in:d=0.03,afade=t=out:st={max(0,a.chunk-0.03)}:d=0.03")
            aud=["-af",af]; extra=[]
        else:
            aud=["-map","0:v","-map","1:a","-shortest"]; extra=["-f","lavfi","-i","anullsrc=r=48000:cl=stereo"]
        subprocess.run(["ffmpeg","-v","error","-y","-ss",str(s_),"-t",str(e-s_),"-i",a.inp,*extra,
            "-vf",vf,*aud,"-c:v","libx264","-crf","18","-preset","fast","-c:a","aac","-ar","48000","-ac","2",out],check=True)
    lst=os.path.join(tmp,"list.txt"); open(lst,"w").write("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",lst,"-c","copy",a.out],check=True)
    print(json.dumps({"chunks":len(chunks),"duration_s":round(len(chunks)*a.chunk,1),
                      "source_times":chunks}))

if __name__=="__main__": main()
