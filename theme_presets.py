"""Export native XAML style presets from the theme catalog."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent


def load_catalog():
    themes = json.loads((ROOT / "themes/catalog.json").read_text(encoding="utf-8"))["themes"]
    seen = set()
    for theme in themes:
        if not re.fullmatch(r"[a-z0-9-]+", theme["id"]) or theme["id"] in seen:
            raise ValueError("Invalid or duplicate theme id")
        seen.add(theme["id"])
        for field in ("background", "end", "foreground", "muted", "accent", "border"):
            if not re.fullmatch(r"#[0-9A-Fa-f]{6}", theme[field]):
                raise ValueError(f"Invalid color: {field}")
        if theme["mode"] not in ("Light", "Dark"):
            raise ValueError("Invalid theme mode")
        if theme.get("dayFont", "Microsoft YaHei UI") not in ("Microsoft YaHei UI", "SimSun", "Bahnschrift"):
            raise ValueError("Unsupported calendar font")
    return themes


def style_rules(theme, mode="art"):
    if mode not in ("art", "gradient", "solid"):
        raise ValueError("Unknown background mode")
    if mode == "art":
        background = 'Background:=<ImageBrush ImageSource="{BACKGROUND_URI}" Stretch="UniformToFill" />'
    elif mode == "gradient":
        background = ('Background:=<LinearGradientBrush StartPoint="0,0" EndPoint="1,1">'
                      f'<GradientStop Color="{theme["background"]}" Offset="0" />'
                      f'<GradientStop Color="{theme["end"]}" Offset="1" /></LinearGradientBrush>')
    else:
        background = "Background=" + theme["background"]
    return [
        ("Grid#CalendarCenterGrid", [background, f'RequestedTheme={theme["mode"]}',
                                    f'CornerRadius={theme["radius"]}', f'BorderBrush={theme["border"]}', 'BorderThickness=1']),
        ("ActionCenter.ClockCalendarView#ClockCalendarView", [f'Foreground={theme["foreground"]}']),
        ("Border#CalendarHeaderMinimizedOverlay", ["Background=Transparent"]),
        ("ScrollViewer#CalendarControlScrollViewer", ["Background=Transparent", "BorderBrush=Transparent"]),
        ("CalendarView#CalendarControl", ["Background=Transparent", "CalendarItemBackground=Transparent",
            f'CalendarItemForeground={theme["foreground"]}', f'Foreground={theme["foreground"]}',
            f'OutOfScopeForeground={theme["muted"]}',
            f'SelectedForeground={theme["foreground"]}', f'SelectedBorderBrush={theme["accent"]}']),
        ("CalendarView#CalendarControl > Border", ["Background=Transparent"]),
        ("Grid#FocusGrid", ["Background=Transparent", "BorderBrush=Transparent"]),
        ("Button#DateTextButton", [f'Foreground={theme["foreground"]}']),
        ("Button#ExpandCollapseButton", [f'Foreground={theme["foreground"]}', "Background=Transparent"]),
        ("Button#IncreaseTimeButton", [f'Foreground={theme["foreground"]}']),
        ("Button#DecreaseTimeButton", [f'Foreground={theme["foreground"]}']),
    ]


def export():
    destination = ROOT / "themes/presets"
    destination.mkdir(exist_ok=True)
    for theme in load_catalog():
        for mode in ("art", "gradient", "solid"):
            entries = {"theme": ""}
            for index, (target, rules) in enumerate(style_rules(theme, mode)):
                entries[f"controlStyles[{index}].target"] = target
                for subindex, rule in enumerate(rules):
                    entries[f"controlStyles[{index}].styles[{subindex}]"] = rule
            path = destination / f'{theme["id"]}.{mode}.json'
            path.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(load_catalog())


if __name__ == "__main__":
    print(f"Exported {export()} themes, three background modes each.")
