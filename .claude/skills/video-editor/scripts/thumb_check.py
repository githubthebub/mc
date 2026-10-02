#!/usr/bin/env python3
"""Check a thumbnail the way viewers actually meet it: tiny, for about 1 second,
next to competitors. Outputs a preview sheet (actual homepage/mobile/sidebar
sizes + grayscale for brightness contrast) and simple metrics.
Usage: thumb_check.py thumb.png [--compare other1.png other2.png ...] [--out sheet.png]
Metrics: brightness contrast (luma std dev, higher = more separation),
colorfulness (Hasler-Susstrunk), and a clutter proxy (edge density)."""
import argparse, subprocess
from PIL import Image, ImageFilter, ImageStat, ImageDraw
import numpy as np

def metrics(p):
    im=Image.open(p).convert("RGB").resize((1280,720))
    a=np.asarray(im).astype(float); L=np.asarray(im.convert("L")).astype(float)
    rg=a[...,0]-a[...,1]; yb=0.5*(a[...,0]+a[...,1])-a[...,2]
    col=np.sqrt(rg.std()**2+yb.std()**2)+0.3*np.sqrt(rg.mean()**2+yb.mean()**2)
    edges=np.asarray(im.convert("L").resize((320,180)).filter(ImageFilter.FIND_EDGES)).astype(float)
    return {"brightness_contrast":round(float(L.std()),1),"colorfulness":round(float(col),1),
            "clutter_edge_density":round(float((edges>40).mean()*100),1)}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("thumb")
    ap.add_argument("--compare",nargs="*",default=[]); ap.add_argument("--out",default="thumb_check.png")
    a=ap.parse_args()
    sizes=[("mobile feed",360,202),("desktop home",246,138),("sidebar",168,94)]
    items=[a.thumb]+a.compare
    W=20+sum(w+20 for _,w,_ in sizes)+180; rowh=max(h for *_,h in sizes)+40
    sheet=Image.new("RGB",(W,rowh*len(items)+10),(15,15,15)); d=ImageDraw.Draw(sheet)
    for r,p in enumerate(items):
        im=Image.open(p).convert("RGB"); x=20; y=r*rowh+25
        for name,w,h in sizes:
            sheet.paste(im.resize((w,h),Image.LANCZOS),(x,y)); d.text((x,y-15),name if r==0 else "",fill=(200,200,200)); x+=w+20
        sheet.paste(im.convert("L").convert("RGB").resize((168,94)),(x,y)); d.text((x,y-15),"grayscale" if r==0 else "",fill=(200,200,200))
        d.text((x,y+100),("YOURS" if r==0 else f"compare {r}"),fill=(60,200,255))
        print(("YOURS " if r==0 else f"compare{r} ")+p, metrics(p))
    sheet.save(a.out); print("sheet:",a.out)

if __name__=="__main__": main()
