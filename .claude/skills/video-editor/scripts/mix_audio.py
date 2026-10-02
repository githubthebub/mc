#!/usr/bin/env python3
"""Sound pass implementing the four-layer approach.
Music (layer 1):
  --music FILE[@START-END[~OFF]][:DB]  repeatable; one track per emotional section.
                                  ~OFF starts the song OFF seconds in (to sync a
                                  pickup to a topic shift; see music_points.py).
                                  DB = music loudness RELATIVE TO THE VOICE target
                                  (each file is measured first, so quiet and loud
                                  songs behave the same). Default -10: present in
                                  gaps, and ducking pushes it further under speech.
                                  Defaults: whole video. Loops if short.
  --duck RATIO                    sidechain duck under the voice (default 8)
  --dropout A-B                   hard-cut all music (emphasis / punchline / takeaway)
  --fadeout A-B                   ramp music to silence over A..B (~20 s) to signal
                                  a section is wrapping up; stays silent until the
                                  next --music track starts after B
  --swell A-B[:+DB]               ramp music up by DB (default +6) over A..B to build
                                  anticipation toward a payoff at B
Voiceover:
  --vo FILE@T[:DB]                repeatable; recorded voiceover lines (e.g. added
                                  context: what's happening / why it matters /
                                  what could go wrong). Joins the voice bus, so
                                  music ducks under it too.
SFX / audio cues (layers 2-3):
  --sfx FILE@T[:DB]               repeatable. Consecutive uses of the same file are
                                  automatically varied in pitch/speed so no sound
                                  repeats identically twice in a row.
Voice:
  --voice-clean                   highpass + FFT denoise + gentle compression on the
                                  original voice (room noise, uneven levels)
Master:
  --lufs -14                      loudness target (two-pass loudnorm)
Video is stream-copied."""
import argparse, json, re, subprocess

def duration(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0",p],capture_output=True,text=True).stdout)

def file_lufs(p):
    err=subprocess.run(["ffmpeg","-hide_banner","-i",p,"-vn","-af","ebur128=framelog=quiet",
        "-f","null","-"],capture_output=True,text=True).stderr
    m=re.findall(r"I:\s*(-?[\d.]+) LUFS",err)
    return float(m[-1]) if m else -14.0

def rng(s):
    a,b=s.split("-"); return float(a),float(b)

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--music",action="append",default=[])
    ap.add_argument("--duck",type=float,default=8)
    ap.add_argument("--dropout",action="append",default=[])
    ap.add_argument("--fadeout",action="append",default=[])
    ap.add_argument("--swell",action="append",default=[])
    ap.add_argument("--sfx",action="append",default=[])
    ap.add_argument("--vo",action="append",default=[])
    ap.add_argument("--voice-clean",action="store_true")
    ap.add_argument("--lufs",type=float,default=-14)
    a=ap.parse_args(); D=duration(a.inp)
    inputs=["-i",a.inp]; fc=[]; idx=1; voice="[0:a]"; mixes=[]
    if a.voice_clean:
        fc.append("[0:a]aresample=48000,highpass=f=80,afftdn=nr=12:nf=-45:tn=1,"
                  "acompressor=threshold=0.1:ratio=3:attack=10:release=150:makeup=2[vclean]")
        voice="[vclean]"
    if a.vo:
        vos=[]
        for v in a.vo:
            f,rest=v.rsplit("@",1); t,_,g=rest.partition(":"); ms=int(float(t)*1000)
            inputs+=["-i",f]
            fc.append(f"[{idx}:a]aresample=48000,volume={g or 0}dB,adelay={ms}|{ms}[vo{idx}]")
            vos.append(f"[vo{idx}]"); idx+=1
        fc.append(f"{voice}aresample=48000"+"[orig]")
        fc.append("[orig]"+"".join(vos)+f"amix=inputs={1+len(vos)}:duration=first:normalize=0[vbus]")
        voice="[vbus]"

    if a.music:
        fc.append(f"{voice}asplit=2[vox][sc]"); voice="[vox]"; tracks=[]
        for i,m in enumerate(a.music):
            f=m; st,en,db,off=0.0,D,-10.0,0.0
            if "@" in m:
                f,rest=m.rsplit("@",1)
                r,_,g=rest.partition(":"); db=float(g) if g else db
                r,_,o=r.partition("~"); st,en=rng(r); off=float(o) if o else 0.0
            elif re.search(r":-?\d+(\.\d+)?$",m):
                f,g=m.rsplit(":",1); db=float(g)
            L=en-st; fin=0.5 if st>0 else 2.0; fout=0.5 if en<D else 2.0
            db=(a.lufs+db)-file_lufs(f)   # absolute gain that lands it relative to voice
            # per-track fadeouts that fall inside this track's span
            auto=[]
            for fo in a.fadeout:
                A,B=rng(fo)
                if st<=A<en:
                    auto.append(f"volume='if(lt(t,{A}),1,if(lt(t,{B}),1-(t-{A})/{B-A},0))':eval=frame")
            inputs+=["-stream_loop","-1","-i",f]
            chain=(f"[{idx}:a]aresample=48000,atrim={off}:{off+L},asetpts=PTS-STARTPTS,volume={db}dB,"
                   f"afade=t=in:d={fin},afade=t=out:st={max(0,L-fout)}:d={fout},"
                   f"adelay={int(st*1000)}|{int(st*1000)},apad=whole_dur={D}")
            if auto: chain+=","+",".join(auto)
            fc.append(chain+f"[m{i}]"); tracks.append(f"[m{i}]"); idx+=1
        bus="".join(tracks)+(f"amix=inputs={len(tracks)}:normalize=0" if len(tracks)>1 else "anull")
        for sw in a.swell:
            r,_,g=sw.partition(":"); A,B=rng(r); g=float(g or 6)
            bus+=f",volume='if(between(t,{A},{B}),pow(10,{g}*(t-{A})/{B-A}/20),1)':eval=frame"
        for d in a.dropout:
            A,B=rng(d); bus+=f",volume=enable='between(t,{A},{B})':volume=0"
        fc.append(bus+"[mus]")
        fc.append(f"[mus][sc]sidechaincompress=threshold=0.02:ratio={a.duck}:attack=20:release=400[ducked]")
        mixes.append("[ducked]")

    # SFX with automatic variation for back-to-back repeats
    variants=[1.0,1.08,0.93,1.04,0.96]; last=None; streak=0
    for s in sorted(a.sfx,key=lambda x:float(x.rsplit("@",1)[1].split(":")[0])):
        f,rest=s.rsplit("@",1); t,_,g=rest.partition(":"); g=g or "0"
        streak = streak+1 if f==last else 0; last=f
        r=variants[streak%len(variants)]
        inputs+=["-i",f]; ms=int(float(t)*1000)
        vary=f"asetrate={int(48000*r)},aresample=48000," if r!=1.0 else ""
        fc.append(f"[{idx}:a]aresample=48000,{vary}volume={g}dB,adelay={ms}|{ms}[s{idx}]")
        mixes.append(f"[s{idx}]"); idx+=1

    pre=voice+"".join(mixes)
    mixexpr=(pre+f"amix=inputs={1+len(mixes)}:duration=first:normalize=0" if mixes else voice+"anull")

    # two-pass loudnorm: measure, then apply linear normalization
    meas=subprocess.run(["ffmpeg","-hide_banner",*inputs,"-filter_complex",
        ";".join(fc+[mixexpr+f",loudnorm=I={a.lufs}:TP=-1.5:LRA=11:print_format=json[x]"]),
        "-map","[x]","-f","null","-"],capture_output=True,text=True).stderr
    m=json.loads(meas[meas.rfind("{"):meas.rfind("}")+1])
    # loudnorm's own second pass silently switches to "dynamic" mode (which
    # reshapes the mix) whenever peaks or range exceed its targets. Instead:
    # static gain to the target + a true-peak limiter, so the balance of voice,
    # music and SFX is preserved exactly.
    gain=a.lufs-float(m["input_i"])
    ln=f"volume={gain:.2f}dB,alimiter=limit=0.84:attack=5:release=50:level=disabled"
    subprocess.run(["ffmpeg","-v","error","-y",*inputs,"-filter_complex",
        ";".join(fc+[mixexpr+f",{ln},aresample=48000[aout]"]),
        "-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","192k",a.out],check=True)

if __name__=="__main__": main()
