"""Install the standalone updater and its per-user Windows scheduled task."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

from auto_updater import OWNER, load_config, validate_runtime
from holiday_data import atomic_write

ROOT = Path(__file__).resolve().parent
EXE = "NativeCalendarHolidayUpdater.exe"


def build_updater() -> dict:
    # Build dependency only; the resulting exe includes its Python runtime.
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed",
                    "--noupx", "--name", "NativeCalendarHolidayUpdater", "--distpath", str(ROOT / "build"),
                    "--workpath", str(ROOT / "build/pyinstaller-work"),
                    "--specpath", str(ROOT / "build"), str(ROOT / "auto_updater.py")], check=True)
    output = ROOT / "build" / EXE
    return {"executable": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def task_action(runtime: Path, action: str) -> dict:
    script = runtime / "AutoUpdate/Configure-AutoUpdate.ps1"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script),
                             "-Action", action, "-RuntimePath", str(runtime)],
                            check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    return json.loads(result.stdout.decode("utf-8-sig"))


def enable(runtime: Path) -> dict:
    runtime = runtime.resolve()
    validate_runtime(runtime)
    binary = ROOT / "build" / EXE
    if not binary.is_file():
        raise RuntimeError("Build the standalone updater first: manage.py build-updater")
    destination = runtime / "AutoUpdate"
    if destination.exists():
        load_config(destination / "config.json")
    destination.mkdir(exist_ok=True)
    config = {"owner": OWNER, "runtimePath": str(runtime), "version": "0.5.3-preview",
              "taskName": "NativeCalendarHolidays-DataUpdate-" + hashlib.sha256(str(runtime).lower().encode()).hexdigest()[:12],
              "schedule": {"intervalDays": 7, "atLogon": False, "retryCount": 0},
              "yearPolicy": "previous-current-next", "source": "NateScarlet/holiday-cn"}
    shutil.copy2(binary, destination / EXE)
    shutil.copy2(ROOT / "Configure-AutoUpdate.ps1", destination / "Configure-AutoUpdate.ps1")
    # Keep source and licensing with the installed standalone application.
    for name in ("auto_updater.py", "holiday_data.py", "LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, destination / name)
    notices = ROOT / "licenses"
    if notices.is_dir():
        shutil.copytree(notices, destination / "licenses", dirs_exist_ok=True)
    years_dir = destination / "data/years"
    years_dir.mkdir(parents=True, exist_ok=True)
    for source in (ROOT / "data/years").glob("*.json"):
        target = years_dir / source.name
        if not target.exists():
            shutil.copy2(source, target)
    shutil.copy2(ROOT / "data/LICENSE", destination / "data/LICENSE")
    atomic_write(destination / "config.json", (json.dumps(config, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return {"updaterDirectory": str(destination), "task": task_action(runtime, "Enable")}


def disable(runtime: Path) -> dict:
    load_config(runtime / "AutoUpdate/config.json")
    return task_action(runtime, "Disable")


def status(runtime: Path) -> dict:
    load_config(runtime / "AutoUpdate/config.json")
    state = runtime / "AutoUpdate/status.json"
    return {"task": task_action(runtime, "Status"),
            "lastRun": json.loads(state.read_text(encoding="utf-8")) if state.exists() else None}
