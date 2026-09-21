"""Render exact Chinese calendar typography over generated background assets."""
import datetime as dt
import json
from pathlib import Path
import sys
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
FONT = Path("C:/Windows/Fonts/msyh.ttc")
BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")


def font(size, bold=False):
    return ImageFont.truetype(str(BOLD if bold else FONT), size)


def center(draw, xy, text, size, color, bold=False, family=None):
    paths={'SimSun':'C:/Windows/Fonts/simsun.ttc','Bahnschrift':'C:/Windows/Fonts/bahnschrift.ttf'}
    face=ImageFont.truetype(paths[family],size) if family in paths else font(size,bold)
    draw.text(xy, text, font=face, fill=color, anchor="mm")


def lunar_text(day, month):
    if day == 1:
        return ["正月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "冬月", "腊月"][month - 1]
    if day == 10: return "初十"
    if day == 20: return "二十"
    if day == 30: return "三十"
    digits = "一二三四五六七八九"
    return ("初" if day < 10 else "十" if day < 20 else "廿") + digits[(day - 1) % 10]


def render(theme, number, dates, holidays):
    dark = theme["mode"] == "Dark"
    canvas = Image.new("RGB", (1080, 1580), "#10141C" if dark else "#F2F3F4")
    draw = ImageDraw.Draw(canvas)
    heading = "#F1F3F8" if dark else "#1B2532"
    secondary = "#9AA7BA" if dark else "#697784"
    draw.text((60, 40), theme["name"], font=font(43, True), fill=heading)
    draw.text((62, 103), theme["nameEn"], font=font(23), fill=secondary)
    draw.text((1020, 55), f"{number:02d}", font=font(43), fill=secondary, anchor="ra")
    box = (60, 160, 1020, 1460)
    radius = round(theme["radius"] * 2.2)
    mask = Image.new("L", (960, 1300), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 959, 1299), radius=radius, fill=255)
    art = ImageOps.fit(Image.open(ROOT / "themes/assets" / f'{theme["id"]}.jpg').convert("RGB"), (960, 1300))
    shadow = Image.new("RGBA", canvas.size)
    ImageDraw.Draw(shadow).rounded_rectangle((61, 173, 1019, 1467), radius=radius, fill=(0, 0, 0, 45))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(18)))
    canvas.paste(art, (60, 160), mask)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(box, radius=radius, outline=theme["border"], width=2)
    fg, muted, accent = theme["foreground"], theme["muted"], theme["accent"]
    draw.text((105, 210), "10月1日，星期四", font=font(35), fill=fg)
    draw.text((105, 266), "八月廿一", font=font(27), fill=muted)
    draw.rounded_rectangle((890, 210, 968, 284), radius=16, fill=theme["background"], outline=theme["border"], width=1)
    draw.line([(917, 241), (929, 253), (941, 241)], fill=fg, width=3)
    draw.line((95, 326, 985, 326), fill=theme["border"], width=2)
    draw.text((105, 364), "2026年10月", font=font(37, True), fill=fg)
    draw.polygon(((870, 390), (880, 374), (890, 390)), fill=muted)
    draw.polygon(((933, 376), (943, 392), (953, 376)), fill=muted)
    left, top, step, row_height = 95, 497, 127, 121
    for col, label in enumerate("一二三四五六日"):
        center(draw, (left + col * step + 63, 463), label, 28, muted)
    rest, work = "#16834B", "#B85B00"
    for index, date_info in enumerate(dates):
        date = dt.date.fromisoformat(date_info["date"])
        row, col = divmod(index, 7)
        x, y = left + col * step, top + row * row_height
        current_month = date.month == 10
        entry = holidays.get(date.isoformat()) if current_month else None
        if entry:
            overlay = Image.new("RGBA", canvas.size)
            od = ImageDraw.Draw(overlay)
            shade = (22, 131, 75, 35 if dark else 19) if entry["isOffDay"] else (184, 91, 0, 44 if dark else 24)
            od.rounded_rectangle((x+7, y+3, x+118, y+112), radius=16 if theme["radius"] > 12 else 6, fill=shade)
            canvas = Image.alpha_composite(canvas, overlay)
            draw = ImageDraw.Draw(canvas)
        if date == dt.date(2026, 10, 1):
            draw.rounded_rectangle((x+29, y+8, x+97, y+76), radius=36, outline=accent, width=3)
        center(draw, (x+63, y+43), str(date.day), 34, fg if current_month else muted, date.day==1 and current_month,theme.get('dayFont'))
        lunar = "国庆节" if date == dt.date(2026, 10, 1) else lunar_text(date_info["day"], date_info["month"])
        center(draw, (x+63, y+90), lunar, 22, muted)
        if entry:
            color = rest if entry["isOffDay"] else work
            draw.rounded_rectangle((x+90,y+6,x+120,y+37),radius=6,fill=color)
            center(draw,(x+105,y+21),"休" if entry["isOffDay"] else "班",21,"#FFFFFF",True)
    draw.line((95, 1285, 985, 1285), fill=theme["border"], width=2)
    for x, sign in ((105,"−"),(374,"+")):
        draw.rounded_rectangle((x,1338,x+65,1407),radius=15,fill=theme["background"],outline=theme["border"],width=1)
        center(draw,(x+32,1370),sign,34,fg)
    center(draw,(241,1372),"30",39,fg)
    draw.text((291,1352),"分钟",font=font(26),fill=muted)
    draw.rounded_rectangle((656,1338,960,1407),radius=17,fill=theme["background"],outline=theme["border"],width=2)
    draw.polygon(((688,1359),(688,1384),(707,1372)),fill=accent)
    center(draw,(824,1370),"开始专注",29,fg,True)
    draw.rounded_rectangle((60,1500,90,1530),radius=6,fill=rest);center(draw,(75,1515),"休",19,"white",True)
    draw.text((102,1499),"放假",font=font(22),fill=secondary)
    draw.rounded_rectangle((218,1500,248,1530),radius=6,fill=work);center(draw,(233,1515),"班",19,"white",True)
    draw.text((260,1499),"调休上班",font=font(22),fill=secondary)
    draw.text((1020,1501),"设计预览 · 非系统实拍",font=font(20),fill=secondary,anchor="ra")
    output = ROOT / "docs/design/previews" / f'{number:02d}-{theme["id"]}.png'
    output.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(output, optimize=True)
    return output


def main():
    themes = json.loads((ROOT / "themes/catalog.json").read_text(encoding="utf-8"))["themes"]
    dates = json.loads((ROOT / "docs/design/sample-lunar-dates.json").read_text(encoding="utf-8"))
    holidays = {d["date"]: d for d in json.loads((ROOT / "data/years/2026.json").read_text(encoding="utf-8"))["days"]}
    images = [render(theme, i+1, dates, holidays) for i, theme in enumerate(themes)]
    for collection,title,filename in [('classic','经典主题','contact-sheet.jpg'),('expressive','新作：二次元 / 国风 / 科技幻想','expressive-contact-sheet.jpg')]:
        chosen=[path for path,t in zip(images,themes) if t.get('collection','classic')==collection]
        if not chosen:continue
        sheet = Image.new("RGB", (2500, 1600), "#E9EDF2")
        draw = ImageDraw.Draw(sheet)
        draw.text((48,26), "calendar-cn / "+title, font=font(40,True), fill="#203044")
        draw.text((48,86), "2026年10月 · 10月1—7日休 / 10月10日班 · 设计预览", font=font(23), fill="#617084")
        for i, path in enumerate(chosen):
            thumb = Image.open(path); thumb.thumbnail((470,690))
            x,y=35+(i%5)*495,145+(i//5)*718
            sheet.paste(thumb,(x+(470-thumb.width)//2,y))
        sheet.save(ROOT / "docs/design" / filename, quality=94)
    print(f"Rendered {len(images)} previews with deterministic dates and holiday badges.")


if __name__ == "__main__":
    main()
