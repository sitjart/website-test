#!/usr/bin/env python3
"""Trim empty space around logo files in public/assets/wp so they read at small sizes.
SVG: measure the drawing's bounding box in a headless browser and tighten the viewBox.
PNG/JPG: crop away transparent or near-white margins and cap the width at 800 px.
Run: python3 -I tools/trim-logos.py   (needs playwright and pillow)"""
import re, sys
from pathlib import Path
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

DIR = Path(__file__).resolve().parent.parent / 'public/assets/wp'
LOGO = re.compile(r'(logo|project-|ro-crate|azn|bioinfo-core)', re.I)
files = [f for f in DIR.iterdir() if LOGO.search(f.name)]

def trim_raster(f):
    im = Image.open(f)
    rgba = im.convert('RGBA')
    alpha = rgba.split()[-1]
    box = alpha.point(lambda a: 255 if a > 8 else 0).getbbox()
    if box is None or box == (0, 0, *rgba.size):  # opaque: trim near-white instead
        bg = Image.new('RGB', rgba.size, (255, 255, 255))
        diff = ImageChops.difference(rgba.convert('RGB'), bg).convert('L').point(lambda v: 255 if v > 18 else 0)
        box = diff.getbbox() or box
    if not box:
        return False
    pad = max(2, int(0.02 * max(box[2] - box[0], box[3] - box[1])))
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(rgba.size[0], box[2] + pad), min(rgba.size[1], box[3] + pad))
    out = rgba.crop(box)
    if out.width > 800:
        out = out.resize((800, round(out.height * 800 / out.width)), Image.LANCZOS)
    out = out if f.suffix.lower() == '.png' else out.convert('RGB')
    out.save(f, optimize=True)
    return True

def trim_svgs(svgs):
    changed = 0
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page()
        for f in svgs:
            src = f.read_text(encoding='utf8', errors='ignore')
            pg.set_content(f'<html><body style="margin:0">{src}</body></html>')
            box = pg.evaluate("""() => { const s = document.querySelector('svg'); if (!s) return null;
              const g = document.createElementNS('http://www.w3.org/2000/svg','g');
              [...s.childNodes].filter(n => !['defs','style','title','metadata'].includes(n.nodeName)).forEach(n => g.appendChild(n));
              s.appendChild(g); const r = g.getBBox(); return [r.x, r.y, r.width, r.height]; }""")
            if not box or box[2] <= 0 or box[3] <= 0:
                continue
            x, y, w, h = box
            pad = 0.02 * max(w, h)
            vb = f'{x - pad:.2f} {y - pad:.2f} {w + 2 * pad:.2f} {h + 2 * pad:.2f}'
            new = re.sub(r'viewBox="[^"]*"', f'viewBox="{vb}"', src, count=1) if 'viewBox=' in src else src.replace('<svg', f'<svg viewBox="{vb}"', 1)
            new = re.sub(r'(<svg[^>]*?)\s(width|height)="[^"]*"', r'\1', new, count=2)
            if new != src:
                f.write_text(new, encoding='utf8'); changed += 1
        b.close()
    return changed

rasters = [f for f in files if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')]
svgs = [f for f in files if f.suffix.lower() == '.svg']
r = sum(trim_raster(f) for f in rasters)
s = trim_svgs(svgs)
print(f'trimmed {r} raster and {s} SVG logos')
