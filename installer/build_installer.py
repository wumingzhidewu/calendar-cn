"""Build a complete end-user installer; Python is used only on the build machine."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def copy(source: Path, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def ini(target: Path, content: str):
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-16")


def build(windhawk: Path, nsis: Path, output: Path):
    compiler = windhawk / "Compiler/bin/clang++.exe"
    manager = ROOT / "build/CalendarManager.exe"
    manager.parent.mkdir(exist_ok=True)
    themes=json.loads((ROOT/'themes/catalog.json').read_text(encoding='utf-8'))['themes']
    menu_themes=sorted(themes,key=lambda t:0 if t.get('collection')=='expressive' else 1)
    options=[('system','系统默认')]+[(t['id'],('新 · ' if t.get('collection')=='expressive' else '')+t['name']) for t in menu_themes]
    header='struct ThemeOption { const wchar_t* id; const wchar_t* label; };\nstatic const ThemeOption kThemes[]={\n'
    header+='\n'.join('{L'+json.dumps(i,ensure_ascii=False)+',L'+json.dumps(n,ensure_ascii=False)+'},' for i,n in options)+'\n};\n'
    (ROOT/'build/theme_names.inc').write_text(header,encoding='utf-8')
    subprocess.run([str(compiler), "-std=c++17", "-O2", "-static", "-municode", "-mwindows",
                    "-DUNICODE", "-D_UNICODE", "-I", str(ROOT/'build'), str(ROOT / "installer/CalendarManager.cpp"),
                    "-o", str(manager), "-luser32", "-lgdi32", "-lshell32"], check=True)
    with tempfile.TemporaryDirectory(prefix="ncal-installer-") as temporary:
        stage = Path(temporary) / "payload"
        stage.mkdir()
        for name in ("windhawk.exe", "windhawk-x64-helper.exe"):
            copy(windhawk / name, stage / name)
        # This mod hooks exported APIs only; the optional Microsoft symbol
        # tooling and the Windhawk editor/compiler are not runtime dependencies.
        for arch in ("32", "64"):
            copy(windhawk / f"Engine/1.7.3/{arch}/windhawk.dll", stage / f"Engine/1.7.3/{arch}/windhawk.dll")
        ini(stage / "windhawk.ini", "[Storage]\nPortable=1\nCompilerPath=Compiler\nEnginePath=Engine\\1.7.3\nUIPath=UI\nAppDataPath=AppData\n")
        ini(stage / "Engine/1.7.3/engine.ini", "[Storage]\nPortable=1\nAppDataPath=..\\..\\AppData\\Engine\n")
        ini(stage / "AppData/settings.ini", "[Settings]\nLanguage=zh-CN\nLoggingVerbosity=0\nHideTrayIcon=1\nDontAutoShowToolkit=1\nDisableToolkitHotkey=1\nSafeMode=0\n")
        ini(stage / "AppData/Engine/settings.ini", "[Settings]\nLoggingVerbosity=0\nInclude=ShellExperienceHost.exe\nExclude=*\nInjectIntoCriticalProcesses=0\nInjectIntoIncompatiblePrograms=0\nInjectIntoGames=0\n")
        mods = stage / "AppData/Engine/Mods"
        ini(mods / "local-native-calendar-holidays.ini", "[Mod]\nLibraryFileName=native-calendar-holidays.dll\nDisabled=0\nInclude=ShellExperienceHost.exe\nExclude=\nArchitecture=x86-64\nVersion=0.1.0\nLoggingEnabled=0\nDebugLoggingEnabled=0\n[Settings]\ntheme=\n")
        copy(ROOT / "build/native-calendar-holidays.dll", mods / "64/native-calendar-holidays.dll")
        for source, target in (("libc++.dll", "libc++.whl"), ("libunwind.dll", "libunwind.whl"),
                               ("windhawk-mod-shim.dll", "windhawk-mod-shim.dll")):
            copy(windhawk / "Compiler/x86_64-w64-mingw32/bin" / source, mods / "64" / target)
        copy(ROOT / "data/holidays.tsv", mods / "64/holidays.tsv")
        copy(ROOT / "data/manifest.json", mods / "64/holidays.manifest.json")
        copy(manager, stage / manager.name)
        for name in ("SetupRuntime.ps1", "Runtime.ps1", "Theme.ps1"):
            # Windows PowerShell 5.1 requires a BOM for non-ASCII script text.
            (stage / name).write_text((ROOT / "installer" / name).read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
        copy(ROOT / "installer/使用说明.html", stage / "使用说明.html")
        shutil.copytree(ROOT/'themes', stage/'themes')
        auto = stage / "AutoUpdate"
        copy(ROOT / "build/NativeCalendarHolidayUpdater.exe", auto / "NativeCalendarHolidayUpdater.exe")
        copy(ROOT / "Configure-AutoUpdate.ps1", auto / "Configure-AutoUpdate.ps1")
        shutil.copytree(ROOT / "data/years", auto / "data/years")
        copy(ROOT / "data/LICENSE", auto / "data/LICENSE")
        for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "auto_updater.py", "holiday_data.py"):
            copy(ROOT / name, stage / name)
        shutil.copytree(ROOT / "licenses", stage / "licenses")
        copy(windhawk / "Compiler/LICENSE.TXT", stage / "licenses/LLVM-LICENSE.txt")
        copy(ROOT / "LICENSE", stage / "licenses/Windhawk-GPL-3.0.txt")
        copy(ROOT / "vendor/windhawk-1.7.3-source.zip", stage / "Source/windhawk-1.7.3-source.zip")
        # Ship corresponding project source with the binary installer.
        with zipfile.ZipFile(stage / "Source/native-calendar-holidays-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(ROOT.rglob("*")):
                rel = path.relative_to(ROOT)
                if not path.is_file() or ".git" in rel.parts or "__pycache__" in rel.parts or rel.parts[0] in ("build", "releases", "work") or path.suffix in (".zip", ".pyc", ".bak") or rel.parts[:2] == ('docs','design'):
                    continue
                archive.write(path, rel)
        package_files = {str(p.relative_to(stage)): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in stage.rglob("*") if p.is_file()}
        (stage / "package-files.json").write_text(json.dumps(package_files, indent=2), encoding="utf-8")
        script = Path(temporary) / "setup.nsi"
        script.write_text((ROOT / "installer/setup.nsi").read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
        subprocess.run([str(nsis), "/V3", f"/DPAYLOAD={stage}", f"/DOUTPUT={output}", str(script)], check=True)
    print(json.dumps({"installer": str(output), "bytes": output.stat().st_size,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--windhawk", required=True, type=Path)
    parser.add_argument("--nsis", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    build(options.windhawk.resolve(), options.nsis.resolve(), options.output.resolve())
