"""Prepare local JPEG backgrounds; keep the original generated PNGs intact."""
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
themes=json.loads((ROOT/'themes/catalog.json').read_text(encoding='utf-8'))['themes']

def rgb(hex_color):
    return np.array([int(hex_color[i:i+2],16)/255 for i in (1,3,5)],dtype=np.float32)

def luminance(values):
    linear=np.where(values<=.04045,values/12.92,((values+.055)/1.055)**2.4)
    return linear[...,0]*.2126+linear[...,1]*.7152+linear[...,2]*.0722

def contrast(value,reference):
    return (np.maximum(value,reference)+.05)/(np.minimum(value,reference)+.05)

def prepare_reading_plane(image,theme):
    values=np.asarray(image,dtype=np.float32)/255
    base=rgb(theme['background'])
    fg=luminance(rgb(theme['foreground']))
    muted=luminance(rgb(theme['muted']))
    lo=np.full(values.shape[:2],.44 if theme['mode']=='Dark' else .50,dtype=np.float32)
    hi=np.full(values.shape[:2],.92,dtype=np.float32)
    for _ in range(11):
        alpha=(lo+hi)/2
        mixed=values*(1-alpha[...,None])+base*alpha[...,None]
        light=luminance(mixed)
        valid=(contrast(light,fg)>=5.0)&(contrast(light,muted)>=3.1)
        hi=np.where(valid,alpha,hi);lo=np.where(valid,lo,alpha)
    # The shape is a glass/vellum reading plane, not a flattened whole image.
    w,h=image.size
    mask=Image.new('L',image.size,0)
    ImageDraw.Draw(mask).rounded_rectangle((int(w*.035),int(h*.218),int(w*.965),int(h*.835)),radius=26,fill=255)
    mask=mask.filter(ImageFilter.GaussianBlur(10))
    alpha=hi*(np.asarray(mask,dtype=np.float32)/255)
    prepared=Image.fromarray(np.clip((values*(1-alpha[...,None])+base*alpha[...,None])*255,0,255).astype('uint8'))
    # Protect the date heading and the unboxed duration label. Faces and hero
    # details in the upper-right remain untouched.
    small=Image.new('L',image.size,0);draw=ImageDraw.Draw(small)
    draw.rounded_rectangle((int(w*.018),int(h*.018),int(w*.585),int(h*.215)),radius=35,fill=150)
    draw.rounded_rectangle((int(w*.035),int(h*.875),int(w*.46),int(h*.995)),radius=28,fill=155)
    small=small.filter(ImageFilter.GaussianBlur(24))
    prepared=Image.composite(Image.new('RGB',image.size,theme['background']),prepared,small)
    return prepared,round(float(np.mean(hi[int(h*.26):int(h*.78),int(w*.08):int(w*.92)])),3)

report=[]
for theme in themes:
    image=Image.open(ROOT/'docs/design/generated-backgrounds'/f'{theme["id"]}.png').convert('RGB')
    if theme['id']=='moon-ink':
        # Bamboo crossed the date heading in the first draft. Fade that area
        # into the paper tone while retaining the original artwork at the edge.
        mask=Image.new('L',image.size,0)
        ImageDraw.Draw(mask).rounded_rectangle((18,38,680,295),radius=85,fill=190)
        mask=mask.filter(ImageFilter.GaussianBlur(55))
        image=Image.composite(Image.new('RGB',image.size,theme['background']),image,mask)
    if theme.get('readingVeil'):
        image,mean_alpha=prepare_reading_plane(image,theme)
        report.append({'id':theme['id'],'meanReadingPlaneOpacity':mean_alpha,'originalArtworkPreserved':True})
    image.save(ROOT/'themes/assets'/f'{theme["id"]}.jpg',quality=94,optimize=True,subsampling=0)
(ROOT/'docs/design/expressive/reading-plane-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
