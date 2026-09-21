"""Standalone, silent updater. The UI DLL never accesses the network.

Freeze this module with PyInstaller to remove the runtime Python dependency.
"""
from __future__ import annotations

import argparse
import configparser
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sys

from holiday_data import atomic_write, fetch_year, update_cache

OWNER = "native-calendar-holidays-autoupdate-v1"
MOD_ID = "local-native-calendar-holidays"
AUTO_INTERVAL = dt.timedelta(days=7)


def automatic_update_due(state: dict, now: dt.datetime | None = None) -> bool:
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        last = dt.datetime.fromisoformat(state["lastSuccessfulCheckAt"])
        if last.tzinfo is None:
            return True
        elapsed = now - last
        # A clock correction must not prevent updates indefinitely.
        return elapsed < dt.timedelta(0) or elapsed >= AUTO_INTERVAL
    except (KeyError, TypeError, ValueError):
        return True


def rolling_years(today: dt.date) -> list[int]:
    return [today.year - 1, today.year, today.year + 1]


def validate_runtime(runtime: Path) -> None:
    parser = configparser.ConfigParser()
    ini = runtime / f"AppData/Engine/Mods/{MOD_ID}.ini"
    parser.read_string(ini.read_text(encoding="utf-16"))
    if parser.get("Mod", "LibraryFileName", fallback="") != "native-calendar-holidays.dll":
        raise ValueError("Unexpected calendar extension configuration")
    if parser.get("Mod", "Include", fallback="") != "ShellExperienceHost.exe":
        raise ValueError("Unexpected target process")
    for relative in ("windhawk.exe", "AppData/Engine/Mods/64/native-calendar-holidays.dll"):
        if not (runtime / relative).is_file():
            raise ValueError(f"Incomplete calendar runtime: {relative}")


def load_config(path: Path) -> tuple[dict, Path]:
    config = json.loads(path.read_text(encoding="utf-8"))
    if config.get("owner") != OWNER:
        raise ValueError("Unrecognized updater configuration")
    runtime = Path(config["runtimePath"]).resolve()
    # The executable, cache and status live in the installation, not the source
    # checkout or Codex's temporary runtime directories.
    if path.resolve().parent != runtime / "AutoUpdate":
        raise ValueError("Updater configuration is outside its runtime directory")
    validate_runtime(runtime)
    return config, runtime


def write_status(path: Path, result: dict) -> None:
    atomic_write(path, (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def run_once(config_path: Path, today: dt.date | None = None, fetcher=fetch_year) -> dict:
    config, runtime = load_config(config_path)
    root = config_path.parent
    status_path = root / "status.json"
    previous = {}
    if status_path.exists():
        try:
            previous = json.loads(status_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            pass
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    years = rolling_years(today or dt.date.today())
    result = {"lastAttemptAt": now, "requestedYears": years,
              "lastSuccessfulCheckAt": previous.get("lastSuccessfulCheckAt"),
              "lastDataChangeAt": previous.get("lastDataChangeAt")}
    try:
        updated = update_cache(root / "data", years, fetcher)
        source = root / "data/holidays.tsv"
        target = runtime / "AppData/Engine/Mods/64/holidays.tsv"
        new_data = source.read_bytes()
        old_data = target.read_bytes() if target.exists() else None
        changed = old_data != new_data
        if changed:
            if old_data is not None:
                atomic_write(target.with_suffix(".tsv.bak"), old_data)
            atomic_write(target, new_data)
            result["lastDataChangeAt"] = now
        atomic_write(target.with_name("holidays.manifest.json"), (root / "data/manifest.json").read_bytes())
        result.update({"status": "partial_failure" if updated["failedYears"] else "ok",
                       "dataChanged": changed, "availableYears": updated["availableYears"],
                       "unpublishedYears": updated["unpublishedYears"],
                       "yearOutcomes": updated["yearOutcomes"], "failedYears": updated["failedYears"],
                       "messages": updated["updateMessages"], "recordCount": updated["entryCount"],
                       "deployedSha256": hashlib.sha256(new_data).hexdigest()})
        if not updated["failedYears"]:
            result["lastSuccessfulCheckAt"] = now
    except Exception as error:
        result.update({"status": "error", "error": str(error)})
    write_status(status_path, result)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Update native calendar data without opening a window")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--force", action="store_true", help="Manual update, ignoring the seven-day interval")
    args = parser.parse_args(argv)
    config_path = args.config.resolve()
    lock = None
    try:
        # Validate before creating files. Task Scheduler also uses IgnoreNew.
        load_config(config_path)
        lock = (config_path.parent / "update.lock").open("a+b")
        if os.name == "nt":
            import msvcrt
            lock.seek(0, 2)
            if lock.tell() == 0:
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                return 0  # Another updater already owns this installation.
        state_path = config_path.parent / "status.json"
        if not args.force and state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                state = {}
            if not automatic_update_due(state):
                state["lastAutomaticSkipAt"] = dt.datetime.now(dt.timezone.utc).isoformat()
                state["automaticIntervalDays"] = 7
                write_status(state_path, state)
                return 0
        result = run_once(config_path)
        return 0 if result["status"] == "ok" else 1
    except Exception as error:
        # Windowless builds have no stdout/stderr. Avoid popup tracebacks.
        if sys.stderr is not None:
            print(str(error), file=sys.stderr)
        return 2
    finally:
        if lock is not None:
            lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
