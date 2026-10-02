#!/usr/bin/env python3
"""Synthesize ORIGINAL placeholder audio when the user has no licensed
music/SFX: rights-free because it's generated from scratch. Quality is basic;
always tell the user these are placeholders and name what to replace them
with (e.g. from a licensed library).
Usage:
  synth_audio.py sfx OUTDIR                 whoosh(x3) pop(x3) riser hit shutter click(x2)
  synth_audio.py music OUT.wav --mood playful|tense|build --bpm 110 --dur 60 [--key 0]
  --mood playful: major, bouncy plucks + soft kick (light, fun sections)
  --mood tense:   minor, staccato low pulse + ticking (debate / spicy / suspense)
  --mood build:   tense + hats and rising energy (escalation toward a payoff)
Music beds have a clear PICKUP (drums enter) at bar 3, findable with music_points.py."""
import argparse, os, wave
import numpy as np
SR=48000

def save(path,x,stereo=True):
    x=np.clip(x/ (np.max(np.abs(x))+1e-9)*0.89,-1,1)
    y=(x*32767).astype(np.int16)
    if stereo: y=np.stack([y,y],1).ravel()
    with wave.open(path,"wb") as w:
        w.setnchannels(2 if stereo else 1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(y.tobytes())

def env(n,a=0.005,d=0.1,s=0.0,r=0.05):
    t=np.arange(n)/SR; e=np.ones(n)*s
    A=int(a*SR); D=int(d*SR)
    e[:A]=np.linspace(0,1,A,endpoint=False) if A else 1
    e[A:A+D]=np.linspace(1,s,min(D,max(0,n-A)))[:len(e[A:A+D])]
    R=int(r*SR); e[-R:]*=np.linspace(1,0,R) if R<n else 1
    return e

def lp(x,alpha):  # one-pole lowpass, alpha can be array
    y=np.zeros_like(x); acc=0.0
    al=np.broadcast_to(alpha,x.shape)
    for i in range(len(x)): acc+=al[i]*(x[i]-acc); y[i]=acc
    return y

def noise(n,seed=0): return np.random.default_rng(seed).standard_normal(n)

def whoosh(d=0.55,seed=0,up=True):
    n=int(d*SR); t=np.linspace(0,1,n)
    cut=(0.02+0.25*t) if up else (0.27-0.25*t)
    x=lp(noise(n,seed),cut)-lp(noise(n,seed),cut*0.2)
    return x*np.sin(np.pi*t)**1.5

def pop(f=900,seed=0):
    n=int(0.12*SR); t=np.arange(n)/SR
    fr=f*np.exp(-t*25); ph=2*np.pi*np.cumsum(fr)/SR
    return np.sin(ph)*np.exp(-t*40)

def riser(d=3.0):
    n=int(d*SR); t=np.linspace(0,1,n)
    fr=200+1800*t**2; ph=2*np.pi*np.cumsum(fr)/SR
    tone=np.sin(ph)*0.5+np.sin(ph*1.5)*0.2
    nz=lp(noise(n,3),0.02+0.3*t)
    x=(tone+nz*1.5)*t**2
    x[-int(0.02*SR):]*=np.linspace(1,0,int(0.02*SR))
    return x

def hit():
    n=int(1.4*SR); t=np.arange(n)/SR
    boom=np.sin(2*np.pi*np.cumsum(55*np.exp(-t*3)+35)/SR)*np.exp(-t*3.5)
    crack=lp(noise(n,5),0.4)*np.exp(-t*18)
    return boom*1.2+crack*0.6

def shutter():
    n=int(0.18*SR); t=np.arange(n)/SR
    c1=lp(noise(n,7),0.6)*np.exp(-t*90); c2=np.roll(lp(noise(n,8),0.5)*np.exp(-t*70),int(0.07*SR))
    return c1+c2*0.8

def click(seed=0):
    n=int(0.05*SR); t=np.arange(n)/SR
    return lp(noise(n,seed+11),0.7)*np.exp(-t*200)

# ---- music ----
def note(f,d,kind="pluck",vel=1.0):
    n=int(d*SR); t=np.arange(n)/SR
    if kind=="pluck":
        x=(np.sin(2*np.pi*f*t)+0.3*np.sin(4*np.pi*f*t)+0.1*np.sin(6*np.pi*f*t))*np.exp(-t*6)
    elif kind=="pad":
        x=(np.sin(2*np.pi*f*t)+0.5*np.sin(2*np.pi*f*1.003*t)+0.25*np.sin(4*np.pi*f*t))*env(n,0.3,0.2,0.8,0.4)
    elif kind=="stab":
        x=np.sign(np.sin(2*np.pi*f*t))*0.4*np.exp(-t*14); x=lp(x,0.15)
    elif kind=="bass":
        x=np.sin(2*np.pi*f*t)*env(n,0.005,0.15,0.6,0.05)
    return x*vel

def drum(kind,seed=0):
    if kind=="kick":
        n=int(0.35*SR); t=np.arange(n)/SR
        return np.sin(2*np.pi*np.cumsum(50+90*np.exp(-t*30))/SR)*np.exp(-t*9)
    if kind=="hat":
        n=int(0.06*SR); t=np.arange(n)/SR
        x=noise(n,seed); x=x-lp(x,0.5); return x*np.exp(-t*60)*0.35
    if kind=="tick":
        n=int(0.03*SR); t=np.arange(n)/SR
        return np.sin(2*np.pi*2200*t)*np.exp(-t*150)*0.25

def music(mood,bpm,dur,key):
    beat=60/bpm; n=int(dur*SR); out=np.zeros(n+SR*2)
    def put(x,t):
        i=int(t*SR); out[i:i+len(x)]+=x[:max(0,len(out)-i)]
    mf=lambda m: 440*2**((m-69+key)/12)
    if mood=="playful":
        prog=[[60,64,67],[57,60,64],[53,57,60],[55,59,62]]   # C Am F G
    else:
        prog=[[57,60,64],[53,57,60],[50,53,57],[52,56,59]]   # Am F Dm E
    bars=int(dur/(4*beat))+1
    for b in range(bars):
        ch=prog[b%4]; t0=b*4*beat
        put(sum(note(mf(m),4*beat,"pad",0.12) for m in ch),t0)
        if b>=2: put(note(mf(ch[0]-24),4*beat*0.9,"bass",0.5),t0)
        for s in range(8):  # eighth-note figure
            t=t0+s*beat/2
            if mood=="playful":
                m=ch[[0,1,2,1,0,2,1,2][s]]+12; put(note(mf(m),beat/2,"pluck",0.35 if b>=2 else 0.15),t)
            else:
                if s%2==0 and b>=2: put(note(mf(ch[0]-12),beat/2,"stab",0.5),t)
                put(drum("tick"),t)
        if b>=2:  # PICKUP: drums enter at bar 3
            for q in range(4):
                if mood=="playful" and q in(0,2): put(drum("kick")*0.7,t0+q*beat)
                if mood!="playful" and q==0: put(drum("kick")*0.8,t0)
                if mood=="build":
                    for e in range(2): put(drum("hat",b*8+q*2+e),t0+q*beat+e*beat/2)
                    if q==2: put(drum("kick")*0.6,t0+q*beat)
        if mood=="build": pass
    out=out[:n]
    if mood=="build": out*=np.linspace(0.6,1.0,n)
    out[-int(0.5*SR):]*=np.linspace(1,0,int(0.5*SR))
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("what",choices=["sfx","music"]); ap.add_argument("out")
    ap.add_argument("--mood",default="playful"); ap.add_argument("--bpm",type=float,default=110)
    ap.add_argument("--dur",type=float,default=60); ap.add_argument("--key",type=int,default=0)
    a=ap.parse_args()
    if a.what=="sfx":
        os.makedirs(a.out,exist_ok=True)
        for i in range(3): save(f"{a.out}/whoosh{i+1}.wav",whoosh(0.45+0.08*i,seed=i,up=i!=1))
        for i,f in enumerate([900,700,1150]): save(f"{a.out}/pop{i+1}.wav",pop(f))
        save(f"{a.out}/riser.wav",riser()); save(f"{a.out}/hit.wav",hit())
        save(f"{a.out}/shutter.wav",shutter())
        for i in range(2): save(f"{a.out}/click{i+1}.wav",click(i))
        print("wrote",sorted(os.listdir(a.out)))
    else:
        save(a.out,music(a.mood,a.bpm,a.dur,a.key)); print("wrote",a.out)

if __name__=="__main__": main()
