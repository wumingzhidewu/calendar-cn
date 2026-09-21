"""Native Calendar Holidays project CLI (Python 3.10+, no pip dependencies)."""
from __future__ import annotations

import argparse
import ctypes
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from holiday_data import DataError, atomic_write, compile_cache, update_cache

ROOT = Path(__file__).resolve().parent
PROJECT = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
MOD = "local-native-calendar-holidays"
MARKER = ".native-calendar-holidays.json"
OWNER = "native-calendar-holidays-project-v1"


def default_install() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "NativeCalendarHolidaysProject"


def require_windows() -> None:
    if sys.platform != "win32":
        raise RuntimeError("Build and runtime management require Windows x64")


def execute(args: list[str], **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def owned_install(path: Path) -> dict:
    marker = path / MARKER
    if path.is_symlink() or not marker.is_file():
        raise RuntimeError("This is not a managed project installation")
    data = json.loads(marker.read_text(encoding="utf-8"))
    if data.get("owner") != OWNER or Path(data.get("path", "")).resolve() != path.resolve():
        raise RuntimeError("Installation marker does not match the target directory")
    return data


def build(windhawk: Path) -> dict:
    require_windows()
    engine = windhawk / "Engine" / PROJECT["windhawkVersion"]
    compiler = windhawk / "Compiler/bin/clang++.exe"
    if not compiler.is_file() or not (engine / "64/windhawk.lib").is_file():
        raise RuntimeError("Pass the extracted Windhawk 1.7.3 directory with Compiler and Engine")
    original = (ROOT / "vendor/notification-center-styler.wh.cpp").read_bytes()
    if hashlib.sha256(original).hexdigest() != PROJECT["upstreamStylerSha256"].lower():
        raise RuntimeError("Vendored source checksum mismatch")
    source = original.decode("utf-8")
    replacements = {
        "// @id              windows-11-notification-center-styler": f"// @id              {MOD}",
        "// @name            Windows 11 Notification Center Styler": "// @name            Native Calendar China Holiday Badges",
        "// @version         1.7\n": "// @version         0.1.0\n",
        "void MergeResourceVariables();": '#include <map>\n#include "native-holidays.inc"\n\nvoid MergeResourceVariables();',
        "void ApplyCustomizations(ElementId elementId,\n                         FrameworkElement element,\n                         PCWSTR fallbackClassName) {":
        "void ApplyCustomizations(ElementId elementId,\n                         FrameworkElement element,\n                         PCWSTR fallbackClassName) {\n    NativeHolidays::Track(element);",
        "void UninitializeForCurrentThread() {": "void UninitializeForCurrentThread() {\n    NativeHolidays::Stop();",
    }
    for old, new in replacements.items():
        if source.count(old) != 1:
            raise RuntimeError(f"Upstream integration point changed: {old[:65]}")
        source = source.replace(old, new)
    out = ROOT / "build"
    out.mkdir(exist_ok=True)
    generated = out / "native-calendar-holidays.wh.cpp"
    generated.write_text(source, encoding="utf-8")
    shutil.copy2(ROOT / "src/native-holidays.inc", out / "native-holidays.inc")
    library = out / "native-calendar-holidays.dll"
    execute([str(compiler), "-std=c++23", "-O2", "-shared", "-DUNICODE", "-D_UNICODE",
             "-DWINVER=0x0A00", "-D_WIN32_WINNT=0x0A00", "-D_WIN32_IE=0x0A00",
             "-DNTDDI_VERSION=0x0A000008", "-D__USE_MINGW_ANSI_STDIO=0", "-DWH_MOD",
             f'-DWH_MOD_ID=L"{MOD}"', '-DWH_MOD_VERSION=L"0.1.0"',
             str(engine / "64/windhawk.lib"), str(generated), "-include", "windhawk_api.h",
             "-target", "x86_64-w64-mingw32", "-Wl,--export-all-symbols", "-o", str(library),
             "-lcomctl32", "-lole32", "-loleaut32", "-lruntimeobject", "-lshlwapi"])
    return {"library": str(library), "sha256": hashlib.sha256(library.read_bytes()).hexdigest()}


def write_ini(path: Path, text: str) -> None:
    atomic_write(path, text.replace("\n", "\r\n").encode("utf-16"))


def install(windhawk: Path, dest: Path, auto_update: bool = True) -> dict:
    require_windows()
    dest = dest.resolve()
    # Never adopt/overwrite the earlier prototype or another Windhawk install.
    if dest.exists():
        raise RuntimeError("Destination already exists; use a new directory or uninstall the managed copy first")
    library = ROOT / "build/native-calendar-holidays.dll"
    engine = windhawk / "Engine" / PROJECT["windhawkVersion"]
    runtime = windhawk / "Compiler/x86_64-w64-mingw32/bin"
    needed = [library, windhawk / "windhawk.exe", windhawk / "windhawk-x64-helper.exe",
              engine / "32/windhawk.dll", engine / "64/windhawk.dll",
              runtime / "libc++.dll", runtime / "libunwind.dll", runtime / "windhawk-mod-shim.dll"]
    if not all(path.is_file() for path in needed):
        raise RuntimeError("Build first and supply the full Windhawk 1.7.3 toolchain")
    if auto_update and not (ROOT / "build/NativeCalendarHolidayUpdater.exe").is_file():
        raise RuntimeError("Build the automatic updater first with build-updater, or pass --no-auto-update")
    compile_cache(ROOT / "data")
    dest.mkdir(parents=True)
    atomic_write(dest / MARKER, json.dumps({"owner": OWNER, "path": str(dest),
                                         "version": PROJECT["version"]}).encode())
    for name in ("windhawk.exe", "windhawk-x64-helper.exe"):
        shutil.copy2(windhawk / name, dest / name)
    shutil.copytree(engine, dest / "Engine" / PROJECT["windhawkVersion"])
    write_ini(dest / "windhawk.ini", "[Storage]\nPortable=1\nCompilerPath=Compiler\nEnginePath=Engine\\1.7.3\nUIPath=UI\nAppDataPath=AppData\n")
    # These paths are relative to the pinned engine directory, not the toolchain.
    write_ini(dest / "Engine/1.7.3/engine.ini", "[Storage]\nPortable=1\nAppDataPath=..\\..\\AppData\\Engine\n")
    write_ini(dest / "AppData/settings.ini", "[Settings]\nLanguage=zh-CN\nLoggingVerbosity=0\nHideTrayIcon=1\nDontAutoShowToolkit=1\nDisableToolkitHotkey=1\nSafeMode=0\n")
    write_ini(dest / "AppData/Engine/settings.ini", "[Settings]\nLoggingVerbosity=0\nInclude=ShellExperienceHost.exe\nExclude=*\nInjectIntoCriticalProcesses=0\nInjectIntoIncompatiblePrograms=0\nInjectIntoGames=0\n")
    mods = dest / "AppData/Engine/Mods"
    write_ini(mods / f"{MOD}.ini", "[Mod]\nLibraryFileName=native-calendar-holidays.dll\nDisabled=0\nInclude=ShellExperienceHost.exe\nExclude=\nArchitecture=x86-64\nVersion=0.1.0\nLoggingEnabled=0\nDebugLoggingEnabled=0\n[Settings]\ntheme=\n")
    (mods / "64").mkdir(parents=True)
    shutil.copy2(library, mods / "64" / library.name)
    for source, target in (("libc++.dll", "libc++.whl"), ("libunwind.dll", "libunwind.whl"),
                           ("windhawk-mod-shim.dll", "windhawk-mod-shim.dll")):
        shutil.copy2(runtime / source, mods / "64" / target)
    shutil.copy2(ROOT / "data/holidays.tsv", mods / "64/holidays.tsv")
    shutil.copy2(ROOT / "data/manifest.json", mods / "64/holidays.manifest.json")
    writable = dest / "AppData/Engine/ModsWritable"
    writable.mkdir(parents=True)
    # Only the newly created runtime gets read access; writes are limited to
    # Windhawk's runtime state folder. No system-wide permissions are changed.
    execute(["icacls", str(dest), "/grant", "*S-1-15-2-1:(OI)(CI)(RX)", "*S-1-15-2-2:(OI)(CI)(RX)", "/Q"], stdout=subprocess.DEVNULL)
    execute(["icacls", str(writable), "/grant", "*S-1-15-2-1:(OI)(CI)(M)", "*S-1-15-2-2:(OI)(CI)(M)", "/Q"], stdout=subprocess.DEVNULL)
    execute(["icacls", str(writable), "/setintegritylevel", "(OI)(CI)L", "/Q"], stdout=subprocess.DEVNULL)
    result = {"installedAt": str(dest), "started": False, "autostart": False}
    if auto_update:
        import scheduler
        result["autoUpdate"] = scheduler.enable(dest)
    return result


def running_windhawk() -> list[dict]:
    script = "[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false); @(Get-Process windhawk -ErrorAction SilentlyContinue | Select-Object Id,Path) | ConvertTo-Json -Compress"
    result = execute(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script], capture_output=True)
    text = result.stdout.decode("utf-8", errors="replace").strip()
    if not text:
        return []
    value = json.loads(text)
    return value if isinstance(value, list) else [value]


def control(dest: Path, start: bool) -> dict:
    require_windows()
    owned_install(dest)
    executable = (dest / "windhawk.exe").resolve()
    running = running_windhawk()
    # Windhawk's control mutex is global to the login session. Never stop or
    # restart another installation, including the existing prototype.
    if any(not item.get("Path") or Path(item["Path"]).resolve() != executable for item in running):
        raise RuntimeError("Another Windhawk installation is running; close it yourself before operating this copy")
    if start and not ctypes.windll.shell32.IsUserAnAdmin():
        raise RuntimeError("Start from an Administrator terminal to load the shell extension")
    if start:
        subprocess.Popen([str(executable), "-tray-only"], creationflags=subprocess.CREATE_NO_WINDOW)
    elif running:
        execute([str(executable), "-exit", "-wait"], timeout=35, creationflags=subprocess.CREATE_NO_WINDOW)
    return {"requested": "start" if start else "stop", "path": str(dest),
            "note": "A start request is not proof of successful injection; inspect status."}


def deploy_data(dest: Path) -> dict:
    owned_install(dest)
    target = dest / "AppData/Engine/Mods/64/holidays.tsv"
    if target.exists():
        atomic_write(target.with_suffix(".tsv.bak"), target.read_bytes())
    atomic_write(target, (ROOT / "data/holidays.tsv").read_bytes())
    atomic_write(target.with_name("holidays.manifest.json"), (ROOT / "data/manifest.json").read_bytes())
    return {"deployed": str(target), "reloadWithinSeconds": 60}


def status(dest: Path) -> dict:
    owned_install(dest)
    state = dest / f"AppData/Engine/ModsWritable/{MOD}.ini"
    manifest = dest / "AppData/Engine/Mods/64/holidays.manifest.json"
    result = {"path": str(dest), "data": json.loads(manifest.read_text(encoding="utf-8")),
              "lastRecordedState": state.read_text(encoding="utf-16") if state.exists() else None,
              "note": "Recorded state may be from an earlier run; it does not prove visual correctness."}
    if sys.platform == "win32":
        result["runningWindhawk"] = running_windhawk()
    return result


def uninstall(dest: Path) -> dict:
    require_windows()
    installation = owned_install(dest)
    if installation.get("installerManaged"):
        raise RuntimeError("Use Windows Installed Apps or Uninstall.exe for the desktop installer edition")
    resolved = dest.resolve()
    if resolved == Path(resolved.anchor) or resolved in (Path.home().resolve(), ROOT.resolve(), ROOT.parent.resolve()):
        raise RuntimeError("Refusing unsafe removal target")
    if any(path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()) for path in resolved.rglob("*")):
        raise RuntimeError("Installation contains a link/junction; inspect it before uninstalling")
    if (resolved / "AutoUpdate/config.json").exists():
        import scheduler
        scheduler.disable(resolved)
    control(resolved, False)
    shutil.rmtree(resolved)
    return {"removed": str(resolved)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Native Windows calendar holiday badges (preview)")
    commands = parser.add_subparsers(dest="command", required=True)
    data = commands.add_parser("data", help="Merge and validate cached annual JSON files offline")
    data.add_argument("--data-dir", type=Path, default=ROOT / "data")
    update = commands.add_parser("update", help="Fetch annual data; retain caches on failure")
    update.add_argument("--years", type=int, nargs="+", default=[dt.date.today().year - 1, dt.date.today().year, dt.date.today().year + 1])
    update.add_argument("--installed", type=Path, help="Also deploy to this managed installation")
    commands.add_parser("build-updater", help="Build a standalone automatic updater using PyInstaller")
    for name in ("build", "install"):
        sub = commands.add_parser(name)
        sub.add_argument("--windhawk", required=True, type=Path, help="Extracted Windhawk 1.7.3 directory")
        if name == "install":
            sub.add_argument("--path", type=Path, default=default_install())
            sub.add_argument("--no-auto-update", action="store_true")
    for name in ("enable-auto", "disable-auto", "auto-status"):
        sub = commands.add_parser(name)
        sub.add_argument("--path", type=Path, default=default_install())
        if name == "enable-auto":
            sub.add_argument("--attach-existing", action="store_true", help="Attach data updates to the known earlier prototype without replacing its DLL")
    for name in ("start", "stop", "status", "uninstall", "deploy-data"):
        sub = commands.add_parser(name)
        sub.add_argument("--path", type=Path, default=default_install())
    args = parser.parse_args(argv)
    try:
        if args.command == "build-updater":
            require_windows()
            import scheduler
            result = scheduler.build_updater()
        elif args.command in ("enable-auto", "disable-auto", "auto-status"):
            require_windows()
            import scheduler
            runtime = args.path.resolve()
            if args.command == "enable-auto":
                if not args.attach_existing:
                    owned_install(runtime)
                result = scheduler.enable(runtime)
            elif args.command == "disable-auto":
                result = scheduler.disable(runtime)
            else:
                result = scheduler.status(runtime)
        elif args.command == "data":
            result = compile_cache(args.data_dir)
        elif args.command == "update":
            result = update_cache(ROOT / "data", args.years)
            if args.installed:
                result["deployment"] = deploy_data(args.installed.resolve())
        elif args.command == "build":
            result = build(args.windhawk.resolve())
        elif args.command == "install":
            result = install(args.windhawk.resolve(), args.path.resolve(), not args.no_auto_update)
        elif args.command in ("start", "stop"):
            result = control(args.path.resolve(), args.command == "start")
        elif args.command == "status":
            result = status(args.path.resolve())
        elif args.command == "uninstall":
            result = uninstall(args.path.resolve())
        else:
            result = deploy_data(args.path.resolve())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
