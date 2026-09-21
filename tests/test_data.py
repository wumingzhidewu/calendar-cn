import copy
import json
from pathlib import Path
import tempfile
import unittest

from holiday_data import DataError, compile_cache, decode_document, update_cache, validate_document


def document(year=2026, date="2026-10-01", off=True, name="国庆节"):
    return {"year": year, "papers": ["https://www.gov.cn/example.htm"],
            "days": [{"date": date, "isOffDay": off, "name": name}]}


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class ValidationTests(unittest.TestCase):
    def test_invalid_dates_are_rejected(self):
        for date in ("2026-02-29", "2026-13-01", "2026-1-01", "2028-01-01"):
            with self.subTest(date=date), self.assertRaises(DataError):
                validate_document(document(date=date), 2026)

    def test_cross_year_december_is_preserved(self):
        self.assertEqual(validate_document(document(date="2025-12-31"), 2026)["days"][0]["date"], "2025-12-31")

    def test_boolean_cannot_be_an_integer_or_string(self):
        for value in (0, 1, "false", None):
            with self.subTest(value=value), self.assertRaises(DataError):
                validate_document(document(off=value), 2026)

    def test_duplicate_dates_rejected(self):
        value = document()
        value["days"].append(copy.deepcopy(value["days"][0]))
        with self.assertRaises(DataError):
            validate_document(value, 2026)

    def test_tsv_injection_rejected(self):
        for name in ("国庆\n20261002\t0\t伪造", "国庆\t节", "", "\x00"):
            with self.subTest(name=name), self.assertRaises(DataError):
                validate_document(document(name=name), 2026)

    def test_unpublished_is_distinct_from_invalid(self):
        self.assertEqual(validate_document({"year": 2027, "papers": [], "days": []}, 2027)["days"], [])
        value = document()
        value["papers"] = []
        with self.assertRaises(DataError):
            validate_document(value, 2026)

    def test_non_government_source_and_wrong_year_rejected(self):
        value = document()
        value["papers"] = ["https://www.gov.cn.example.com/fake"]
        with self.assertRaises(DataError):
            validate_document(value, 2026)
        with self.assertRaises(DataError):
            validate_document(document(), 2027)

    def test_html_error_page_not_accepted(self):
        with self.assertRaises(DataError):
            decode_document(b"<html>rate limited</html>", 2026)


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "years").mkdir()

    def cache(self, year, value):
        (self.root / "years" / f"{year}.json").write_bytes(raw(value))

    def test_network_failure_preserves_existing_data(self):
        self.cache(2026, document())
        before = compile_cache(self.root)
        def offline(year):
            raise OSError("offline")
        after = update_cache(self.root, [2026, 2027], offline)
        self.assertEqual(before["tsvSha256"], after["tsvSha256"])
        self.assertEqual(after["unpublishedYears"], [])
        self.assertIn("fetch failed", after["updateMessages"][1])

    def test_placeholder_does_not_erase_published_cache(self):
        self.cache(2026, document())
        result = update_cache(self.root, [2026], lambda y: raw({"year": y, "papers": [], "days": []}))
        self.assertEqual(result["availableYears"], [2026])
        self.assertIn("retained published cache", result["updateMessages"][0])

    def test_invalid_download_preserves_raw_cache(self):
        self.cache(2026, document())
        prior = (self.root / "years/2026.json").read_bytes()
        update_cache(self.root, [2026], lambda y: b"<html>error</html>")
        self.assertEqual(prior, (self.root / "years/2026.json").read_bytes())

    def test_later_notice_overrides_previous_december(self):
        self.cache(2025, document(2025, "2025-12-31", False))
        self.cache(2026, document(2026, "2025-12-31", True, "元旦"))
        result = compile_cache(self.root)
        self.assertIn("20251231\t1\t元旦", (self.root / "holidays.tsv").read_text(encoding="utf-8"))
        self.assertEqual(result["crossYearOverrides"], [{"date": "2025-12-31", "winningNoticeYear": 2026}])

    def test_empty_only_cache_does_not_replace_existing_tsv(self):
        self.cache(2027, {"year": 2027, "papers": [], "days": []})
        (self.root / "holidays.tsv").write_bytes(b"last known good")
        with self.assertRaises(DataError):
            compile_cache(self.root)
        self.assertEqual((self.root / "holidays.tsv").read_bytes(), b"last known good")

    def test_new_year_keeps_previous_years_and_backup(self):
        self.cache(2025, document(2025, "2025-10-01"))
        compile_cache(self.root)
        previous = (self.root / "holidays.tsv").read_bytes()
        result = update_cache(self.root, [2026], lambda y: raw(document()))
        self.assertEqual(result["availableYears"], [2025, 2026])
        self.assertEqual((self.root / "holidays.tsv.bak").read_bytes(), previous)
        self.assertFalse((self.root / "holidays.tsv").read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_bundled_2026_matches_official_notice(self):
        path = Path(__file__).resolve().parents[1] / "data/years/2026.json"
        days = decode_document(path.read_bytes(), 2026)["days"]
        self.assertEqual(sum(d["isOffDay"] for d in days), 33)
        self.assertEqual({d["date"] for d in days if not d["isOffDay"]},
                         {"2026-01-04", "2026-02-14", "2026-02-28", "2026-05-09", "2026-09-20", "2026-10-10"})


if __name__ == "__main__":
    unittest.main()
