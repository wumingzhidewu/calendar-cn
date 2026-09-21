"""Validated holiday-cn JSON cache -> the native extension's UTF-8 TSV.

Python 3.10+, standard library only. Data files are grouped by notice year;
the following year's notice can override dates in the preceding December.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SOURCE = "https://raw.githubusercontent.com/NateScarlet/holiday-cn/master/{year}.json"
MIRROR = "https://cdn.jsdelivr.net/gh/NateScarlet/holiday-cn@master/{year}.json"
MAX_BYTES = 2_000_000


class DataError(ValueError):
    pass


def validate_document(document: object, year: int) -> dict:
    if not isinstance(document, dict) or type(document.get("year")) is not int or document["year"] != year:
        raise DataError(f"Expected notice year {year}")
    papers, days = document.get("papers"), document.get("days")
    if not isinstance(papers, list) or not isinstance(days, list):
        raise DataError("papers and days must be lists")
    for paper in papers:
        if not isinstance(paper, str):
            raise DataError("Invalid government source URL")
        parsed = urlparse(paper)
        if parsed.scheme not in ("http", "https") or not (parsed.hostname or "").endswith(".gov.cn"):
            raise DataError("A government .gov.cn source is required")
    if not papers and days:
        raise DataError("Nonempty data without a government notice")
    if papers and not days:
        raise DataError("Government notice provided but days are empty")
    seen = set()
    for entry in days:
        if not isinstance(entry, dict):
            raise DataError("Invalid day entry")
        date, name, off = entry.get("date"), entry.get("name"), entry.get("isOffDay")
        if not isinstance(date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise DataError("Date must use YYYY-MM-DD")
        try:
            parsed_date = dt.date.fromisoformat(date)
        except ValueError as error:
            raise DataError(f"Invalid calendar date: {date}") from error
        # Cross-year ranges exist in official notices; don't drop December.
        if not year - 1 <= parsed_date.year <= year + 1:
            raise DataError(f"Date outside the notice's adjacent years: {date}")
        if date in seen:
            raise DataError(f"Duplicate date in one notice year: {date}")
        seen.add(date)
        if type(off) is not bool:
            raise DataError("isOffDay must be a JSON boolean")
        if not isinstance(name, str) or not name.strip() or len(name) > 80 or any(ord(c) < 32 for c in name):
            raise DataError("Invalid holiday name")
    return document


def decode_document(raw: bytes, year: int) -> dict:
    if len(raw) > MAX_BYTES:
        raise DataError("Data response is too large")
    try:
        return validate_document(json.loads(raw.decode("utf-8-sig")), year)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise DataError("Response is not UTF-8 holiday JSON") from error


def fetch_year(year: int) -> bytes:
    failures = []
    for template in (SOURCE, MIRROR):
        try:
            request = Request(template.format(year=year), headers={"User-Agent": "NativeCalendarHolidays/0.2.0"})
            with urlopen(request, timeout=20) as response:
                raw = response.read(MAX_BYTES + 1)
            decode_document(raw, year)
            return raw
        except (OSError, DataError) as error:
            failures.append(str(error))
    raise OSError("GitHub and CDN fetch failed: " + "; ".join(failures))


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def compile_cache(data_dir: Path) -> dict:
    records, sources, pending, overrides = {}, [], [], []
    for path in sorted((data_dir / "years").glob("[0-9][0-9][0-9][0-9].json")):
        year = int(path.stem)
        raw = path.read_bytes()
        document = decode_document(raw, year)
        if not document["days"]:
            pending.append(year)
            continue
        sources.append({"year": year, "url": SOURCE.format(year=year), "papers": document["papers"],
                        "sha256": hashlib.sha256(raw).hexdigest(), "entries": len(document["days"])})
        for entry in document["days"]:
            key = entry["date"]
            if key in records and records[key] != entry:
                overrides.append({"date": key, "winningNoticeYear": year})
            records[key] = entry
    if not records:
        raise DataError("No published holiday data; existing TSV was left untouched")
    text = "# NativeCalendarHolidays TSV v1: YYYYMMDD<TAB>isOffDay(1/0)<TAB>name\n"
    text += "# Only dates explicitly present in the source are marked. Missing dates are not classified.\n"
    for date, entry in sorted(records.items()):
        text += f"{date.replace('-', '')}\t{int(entry['isOffDay'])}\t{entry['name']}\n"
    encoded = text.encode("utf-8")
    result = {"generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
              "availableYears": [source["year"] for source in sources], "unpublishedYears": pending,
              "entryCount": len(records), "tsvSha256": hashlib.sha256(encoded).hexdigest(),
              "sources": sources, "crossYearOverrides": overrides}
    target = data_dir / "holidays.tsv"
    if target.exists() and target.read_bytes() != encoded:
        atomic_write(data_dir / "holidays.tsv.bak", target.read_bytes())
    atomic_write(target, encoded)
    atomic_write(data_dir / "manifest.json", (json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return result


def update_cache(data_dir: Path, years: list[int], fetcher=fetch_year) -> dict:
    messages = []
    outcomes = {}
    for year in sorted(set(years)):
        if not 2000 <= year <= 2100:
            raise DataError("Year must be between 2000 and 2100")
        target = data_dir / "years" / f"{year}.json"
        try:
            raw = fetcher(year)
            document = decode_document(raw, year)
            if not document["days"] and target.exists() and decode_document(target.read_bytes(), year)["days"]:
                messages.append(f"{year}: empty upstream response; retained published cache")
                outcomes[str(year)] = "retained-published-cache"
                continue
            atomic_write(target, raw)
            messages.append(f"{year}: updated" if document["days"] else f"{year}: unpublished (empty placeholder)")
            outcomes[str(year)] = "published" if document["days"] else "unpublished"
        except (OSError, DataError) as error:
            # Network errors are not evidence that a holiday schedule is unpublished.
            messages.append(f"{year}: fetch failed ({error}); retained cache if available")
            outcomes[str(year)] = "fetch-failed"
    result = compile_cache(data_dir)
    result["updateMessages"] = messages
    result["yearOutcomes"] = outcomes
    result["failedYears"] = [int(year) for year, outcome in outcomes.items() if outcome == "fetch-failed"]
    return result
