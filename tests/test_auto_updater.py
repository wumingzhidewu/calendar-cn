import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from auto_updater import OWNER, load_config, rolling_years, run_once, main, automatic_update_due
from holiday_data import SOURCE, MIRROR, fetch_year


def notice(year, published=True):
    return json.dumps({"year": year, "papers": ["https://www.gov.cn/notice.htm"] if published else [],
                       "days": [{"date": f"{year}-01-01", "isOffDay": True, "name": "测试元旦"}] if published else []},
                      ensure_ascii=False).encode()


class AutomaticUpdates(unittest.TestCase):
    def test_seven_day_boundary(self):
        now = dt.datetime(2026, 9, 21, tzinfo=dt.timezone.utc)
        for elapsed, expected in [(dt.timedelta(days=7), True),
                                  (dt.timedelta(days=7, seconds=-1), False),
                                  (dt.timedelta(seconds=-1), True)]:
            self.assertEqual(automatic_update_due({"lastSuccessfulCheckAt": (now-elapsed).isoformat()}, now), expected)
        for value in [None, "broken", "2026-09-21T00:00:00"]:
            self.assertTrue(automatic_update_due({"lastSuccessfulCheckAt": value}, now))

    def test_recent_automatic_run_skips_network_but_manual_force_runs(self):
        status = self.auto / "status.json"
        status.write_text(json.dumps({"lastSuccessfulCheckAt": dt.datetime.now(dt.timezone.utc).isoformat()}))
        with patch("auto_updater.run_once", return_value={"status": "ok"}) as run:
            self.assertEqual(main(["--config", str(self.config)]), 0)
            run.assert_not_called()
            self.assertEqual(json.loads(status.read_text())["automaticIntervalDays"], 7)
            self.assertEqual(main(["--config", str(self.config), "--force"]), 0)
            run.assert_called_once()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.runtime = Path(self.temp.name)
        self.auto = self.runtime / "AutoUpdate"
        (self.auto / "data/years").mkdir(parents=True)
        mods = self.runtime / "AppData/Engine/Mods"
        (mods / "64").mkdir(parents=True)
        self.target = mods / "64/holidays.tsv"
        self.target.write_bytes(b"known good original")
        (mods / "64/native-calendar-holidays.dll").touch()
        (self.runtime / "windhawk.exe").touch()
        (mods / "local-native-calendar-holidays.ini").write_text(
            "[Mod]\nLibraryFileName=native-calendar-holidays.dll\nInclude=ShellExperienceHost.exe\n", encoding="utf-16")
        self.config = self.auto / "config.json"
        self.config.write_text(json.dumps({"owner": OWNER, "runtimePath": str(self.runtime)}))
        (self.auto / "data/years/2026.json").write_bytes(notice(2026))

    def test_year_window_rolls_without_editing_configuration(self):
        self.assertEqual(rolling_years(dt.date(2026, 12, 31)), [2025, 2026, 2027])
        self.assertEqual(rolling_years(dt.date(2027, 1, 1)), [2026, 2027, 2028])

    def test_process_lock_is_released_between_runs(self):
        with patch("auto_updater.run_once", return_value={"status": "ok"}) as run:
            self.assertEqual(main(["--config", str(self.config)]), 0)
            self.assertEqual(main(["--config", str(self.config)]), 0)
            self.assertEqual(run.call_count, 2)

    def test_next_year_arrives_and_is_deployed_automatically(self):
        calls = []
        def before(year):
            calls.append(year)
            return notice(year, year <= 2026)
        first = run_once(self.config, dt.date(2026, 9, 21), before)
        self.assertEqual(calls, [2025, 2026, 2027])
        self.assertNotIn(2027, first["availableYears"])
        self.assertEqual(first["yearOutcomes"]["2027"], "unpublished")
        old = self.target.read_bytes()
        second = run_once(self.config, dt.date(2026, 11, 20), lambda year: notice(year))
        self.assertIn(2027, second["availableYears"])
        self.assertIn(b"20270101\t1\t", self.target.read_bytes())
        self.assertEqual(self.target.with_suffix(".tsv.bak").read_bytes(), old)
        self.assertTrue(second["dataChanged"])

    def test_unchanged_data_does_not_rewrite_live_tsv(self):
        run_once(self.config, dt.date(2026, 9, 21), lambda year: notice(year))
        before = self.target.stat().st_mtime_ns
        result = run_once(self.config, dt.date(2026, 9, 22), lambda year: notice(year))
        self.assertFalse(result["dataChanged"])
        self.assertEqual(self.target.stat().st_mtime_ns, before)

    def test_offline_status_preserves_live_data(self):
        initial = run_once(self.config, dt.date(2026, 9, 21), lambda year: notice(year))
        before = self.target.read_bytes()
        def offline(year):
            raise OSError("offline")
        result = run_once(self.config, dt.date(2026, 9, 22), offline)
        self.assertEqual(result["status"], "partial_failure")
        self.assertEqual(result["failedYears"], [2025, 2026, 2027])
        self.assertEqual(result["lastSuccessfulCheckAt"], initial["lastSuccessfulCheckAt"])
        self.assertEqual(self.target.read_bytes(), before)

    def test_config_cannot_write_outside_its_installation(self):
        self.config.write_text(json.dumps({"owner": OWNER, "runtimePath": str(self.runtime / "other")}))
        with self.assertRaises(ValueError):
            load_config(self.config)

    def test_empty_future_year_cannot_erase_announced_year(self):
        run_once(self.config, dt.date(2026, 9, 21), lambda year: notice(year))
        result = run_once(self.config, dt.date(2026, 9, 22), lambda year: notice(year, year != 2027))
        self.assertIn(2027, result["availableYears"])
        self.assertEqual(result["yearOutcomes"]["2027"], "retained-published-cache")

    def test_corrupt_cache_keeps_live_tsv_and_records_error(self):
        (self.auto / "data/years/2024.json").write_bytes(b"broken")
        result = run_once(self.config, dt.date(2026, 9, 21), lambda year: notice(year))
        self.assertEqual(result["status"], "error")
        self.assertEqual(self.target.read_bytes(), b"known good original")

    def test_github_failure_tries_same_repository_cdn(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = notice(2027)
        with patch("holiday_data.urlopen", side_effect=[OSError("blocked"), response]) as fetch:
            self.assertEqual(fetch_year(2027), notice(2027))
            self.assertEqual(fetch.call_args_list[0].args[0].full_url, SOURCE.format(year=2027))
            self.assertEqual(fetch.call_args_list[1].args[0].full_url, MIRROR.format(year=2027))
