import hashlib
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def main():
    catalog=json.loads((ROOT/'themes/catalog.json').read_text(encoding='utf-8'))['themes']
    records=[]
    for i,theme in enumerate(catalog):
        record={key:theme[key] for key in ('id','name','nameEn','mode','background','foreground','accent','border')}
        record['number']=i+1
        record['collection']=theme.get('collection','classic')
        record['category']=theme.get('category','经典主题')
        record['prompt']=f"prompts/{theme['id']}.txt" if theme.get('promptFile') else None
        if theme.get('promptFile'):
            destination=ROOT/'docs/design/prompts'/f"{theme['id']}.txt"
            destination.parent.mkdir(exist_ok=True)
            destination.write_text((ROOT/theme['promptFile']).read_text(encoding='utf-8'),encoding='utf-8')
        record['preview']=f'previews/{i+1:02d}-{theme["id"]}.png'
        records.append(record)
    records.sort(key=lambda t:0 if t['collection']=='expressive' else 1)
    html='''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>calendar-cn · 二次元 / 国风 / 科技幻想</title>
<style>*{box-sizing:border-box}body{margin:0;background:#edf0f5;color:#263246;font:15px/1.6 "Microsoft YaHei UI",sans-serif}header{padding:24px 32px;background:white;border-bottom:1px solid #dae0e8}h1{font-size:24px;margin:0}header p{margin:4px 0 0;color:#6b7788}main{display:grid;grid-template-columns:260px 1fr;min-height:calc(100vh - 115px)}nav{padding:22px;display:flex;flex-direction:column;gap:8px}nav button{padding:12px 14px;display:flex;align-items:center;gap:12px;text-align:left;background:white;border:1px solid #dbe1e8;border-radius:10px;cursor:pointer;color:inherit;font:inherit}nav button[aria-selected=true]{border-color:#4277bc;box-shadow:0 0 0 2px #4277bc33}nav small{display:block;color:#6a778a;font-size:12px}.dot{width:24px;height:24px;border-radius:50%;border:1px solid #bbc4d0;flex-shrink:0}.viewer{padding:25px;display:grid;grid-template-columns:minmax(300px,1fr) 260px;align-items:start;gap:25px}.preview{text-align:center}.preview img{max-width:100%;max-height:calc(100vh - 165px);border-radius:8px;box-shadow:0 12px 35px #1b29401f}.info{background:white;padding:23px;border-radius:14px}.info h2{margin:0;font-size:25px}.en{color:#68758a}.chips{display:flex;gap:10px;margin:20px 0}.chip{width:32px;height:32px;border-radius:8px;border:1px solid #ccd4df}.legend{margin:22px 0}.tag{color:white;padding:2px 6px;border-radius:4px;margin-right:8px}.rest{background:#16834b}.work{background:#b85b00}.hint{color:#68758a;font-size:13px}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px}a,.actions button{font:inherit;color:#315f99;text-decoration:none;border:1px solid #ccd8e8;border-radius:7px;padding:7px 10px;background:white;cursor:pointer}button:focus-visible,a:focus-visible{outline:3px solid #668aba}.index{font-size:13px;color:#8190a1;margin-top:15px}@media(max-width:950px){.viewer{grid-template-columns:1fr}.info{max-width:500px;margin:auto}.preview img{max-height:none}}@media(max-width:620px){main{display:block}nav{display:grid;grid-template-columns:1fr 1fr}header{padding:20px}.viewer{padding:16px}} </style></head>
<body><header><h1>calendar-cn · 二次元 / 国风 / 科技幻想</h1><p>统一展示 2026 年 10 月：1—7 日放假，10 日调休上班。新增十套艺术主题；原有主题保留。可用键盘左右键切换。</p></header><main><nav id="themes" aria-label="主题列表"></nav><section class="viewer"><div class="preview"><a id="full" target="_blank" style="border:0;padding:0;background:none"><img id="preview" alt=""></a></div><aside class="info"><h2 id="name"></h2><div class="en" id="english"></div><div class="en" id="category"></div><div class="chips" id="chips"></div><div id="mode"></div><div class="legend"><div><span class="tag rest">休</span>放假</div><div style="margin-top:8px"><span class="tag work">班</span>调休上班</div></div><p class="hint">设计预览，不是系统实拍。主题配置提供插画、渐变、纯色三种背景；此处展示插画版本。</p><div class="actions"><button id="previous">上一套</button><button id="next">下一套</button><a id="download" download>下载大图</a><a id="prompt" target="_blank">创意提示词</a></div><div class="index" id="index"></div></aside></section></main><script>
const themes=__THEMES__;let selected=0;const nav=document.querySelector('#themes');
themes.forEach((t,i)=>{let b=document.createElement('button');b.innerHTML=`<span class="dot" style="background:${t.background}"></span><span>${String(t.number).padStart(2,'0')} · ${t.name}<small>${t.nameEn}</small></span>`;b.onclick=()=>show(i);nav.appendChild(b)});
function show(i){selected=(i+themes.length)%themes.length;let t=themes[selected];document.querySelector('#preview').src=t.preview;document.querySelector('#preview').alt=t.name+'日历设计预览，含休班标记';document.querySelector('#full').href=t.preview;document.querySelector('#download').href=t.preview;document.querySelector('#name').textContent=t.name;document.querySelector('#english').textContent=t.nameEn;document.querySelector('#category').textContent=t.category;document.querySelector('#prompt').style.display=t.prompt?'inline-block':'none';if(t.prompt)document.querySelector('#prompt').href=t.prompt;document.querySelector('#mode').textContent=t.mode==='Dark'?'深色主题':'浅色主题';document.querySelector('#index').textContent=`${selected+1} / ${themes.length}`;document.querySelector('#chips').innerHTML=[t.background,t.foreground,t.accent,t.border].map(c=>`<span class="chip" title="${c}" style="background:${c}"></span>`).join('');[...nav.children].forEach((b,n)=>b.setAttribute('aria-selected',n===selected?'true':'false'))}
document.querySelector('#previous').onclick=()=>show(selected-1);document.querySelector('#next').onclick=()=>show(selected+1);document.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')show(selected-1);if(e.key==='ArrowRight')show(selected+1)});show(0);
</script></body></html>'''.replace('__THEMES__',json.dumps(records,ensure_ascii=False))
    (ROOT/'docs/design/index.html').write_text(html,encoding='utf-8')
    provenance={'model':'gpt-image-2','reference':'reference/windows-calendar-original.png','layoutReference':'reference/layout-reference.png','artDirectionReference':'reference/expressive-art-direction.png','expressiveLayoutGuide':'reference/expressive-layout-guide.png','sampleMonth':'2026-10','typography':'Deterministic Pillow rendering; Microsoft YaHei UI, SimSun, Bahnschrift','lunarDates':'Windows ChineseLunisolarCalendar','holidayData':'data/years/2026.json','images':[]}
    for theme in catalog:
        source=ROOT/'docs/design/generated-backgrounds'/f'{theme["id"]}.png'
        asset=ROOT/'themes/assets'/f'{theme["id"]}.jpg'
        provenance['images'].append({'id':theme['id'],'collection':theme.get('collection','classic'),'promptFile':theme.get('promptFile'),'dimensions':Image.open(source).size,'generatedSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'runtimeSha256':hashlib.sha256(asset.read_bytes()).hexdigest()})
    (ROOT/'docs/design/provenance.json').write_text(json.dumps(provenance,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
