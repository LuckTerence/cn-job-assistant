import importlib.util
import sys
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from salary_lookup import format_entry  # noqa: E402 root shim re-export


class FormatEntryTests(unittest.TestCase):
    def test_zero_count_is_displayed_as_zero(self):
        entry = {
            "company": "Example Corp",
            "city": "",
            "categories": {
                "public_data": {
                    "count": 0,
                    "index": 100.0,
                },
            },
        }

        rendered = format_entry(entry, {"index_baseline": 100, "index_label": "Index"})

        self.assertRegex(rendered, r"Public Data\s+0\s+100\.0")

    def test_text_index_does_not_crash(self):
        entry = {
            "company": "Example Corp",
            "city": "",
            "categories": {
                "sample": {
                    "count": 3,
                    "index": "private",
                },
            },
        }

        rendered = format_entry(entry, {"index_baseline": 100, "index_label": "Index"})

        self.assertIn("private", rendered)

    def test_legacy_module_loads(self):
        path = ROOT / "integrations" / "legacy" / "salary_lookup.py"
        self.assertTrue(path.is_file())
        spec = importlib.util.spec_from_file_location("legacy_salary", path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, "format_entry"))

    def test_root_shim_warns_on_cli(self):
        import salary_lookup as sl

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # no salary_data.json → exit 1 after warning
            rc = sl.main(["--list-all"])
        self.assertTrue(any(issubclass(w.category, UserWarning) for w in caught))
        # missing data file → non-zero from legacy
        self.assertNotEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
