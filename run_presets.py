#!/usr/bin/env python3
import argparse, csv, json, subprocess, sys
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw

def run(cmd):
    print("+"," ".join(str(x) for x in cmd))
    subprocess.run(cmd,check=True)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--output",default="preset_comparison")
    ap.add_argument("--fast",action="store_true")
    args=ap.parse_args()

    out=Path(args.output); out.mkdir(parents=True,exist_ok=True)
    here=Path(__file__).resolve().parent
    py=sys.executable
    rows=[]
    image_paths=[]

    for preset in ["conservative","balanced","aggressive"]:
        d=out/preset
        cmd=[py,str(here/"frog_restore.py"),args.image,"--output",str(d),"--preset",preset]
        if args.fast: cmd.append("--fast")
        run(cmd)
        metrics=json.loads((d/"metrics.json").read_text())
        rows.append(metrics)
        image_paths.append((preset,d/f"restored_{preset}.png"))

    with open(out/"preset_metrics.csv","w",newline="") as fh:
        fields=[
            "preset","estimated_luma_sigma","rms_pixel_change","mean_absolute_pixel_change",
            "ssim_vs_original","mean_cleanup_weight","p95_cleanup_weight",
            "mean_change_smooth_regions","mean_change_textured_regions","smooth_to_texture_change_ratio"
        ]
        wr=csv.DictWriter(fh,fieldnames=fields)
        wr.writeheader()
        for r in rows:
            wr.writerow({k:r.get(k,"") for k in fields})

    # Contact sheet.
    ims=[]
    original=Image.open(args.image).convert("RGB")
    image_paths=[("original",None)]+image_paths
    for label,path in image_paths:
        im=original.copy() if path is None else Image.open(path).convert("RGB")
        target_w=900
        target_h=round(im.height*target_w/im.width)
        im=im.resize((target_w,target_h),Image.Resampling.LANCZOS)
        canvas=Image.new("RGB",(target_w,target_h+50),"white")
        canvas.paste(im,(0,50))
        draw=ImageDraw.Draw(canvas)
        draw.text((15,15),label,fill="black")
        ims.append(canvas)
    sheet=Image.new("RGB",(ims[0].width, sum(i.height for i in ims)),"white")
    y=0
    for im in ims:
        sheet.paste(im,(0,y)); y+=im.height
    sheet.save(out/"preset_contact_sheet.jpg",quality=94)
    print(f"Preset comparison written to {out}")

if __name__=="__main__":
    main()
