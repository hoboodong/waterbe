import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("waterbe_api", ROOT / "scripts/waterbe_api.py")
api = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(api)


class ApiTests(unittest.TestCase):
    def test_catalog_guides_and_unique_ids(self):
        entries = api.catalog()["operations"]
        self.assertEqual(len(entries), len({x["id"] for x in entries}))
        for entry in entries:
            self.assertTrue((ROOT / entry["guide"]).is_file())

    def test_no_implicit_write(self):
        self.assertEqual(api.call("scale.text.change", "2026-10-01")["status"], "unsupported")

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_config_not_zero(self):
        result = api.call("sales.daeyoung.read", "2026-10-01")
        self.assertEqual(result["status"], "unavailable")
        self.assertIsNone(result["data"])

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.test", "SUPABASE_SERVICE_ROLE_KEY": "test"}, clear=True)
    def test_missing_source_not_zero(self):
        with patch.object(api, "read_table", return_value=[]):
            self.assertEqual(api.call("sales.daeyoung.read", "2026-10-01")["status"], "missing_source")

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.test", "SUPABASE_SERVICE_ROLE_KEY": "test"}, clear=True)
    def test_import_changed(self):
        with patch.object(api, "read_table", side_effect=[[{"file_id": "a", "row_count": 0}], [], []]):
            self.assertEqual(api.call("sales.daeyoung.read", "2026-10-01")["status"], "unavailable")

    @patch.dict("os.environ", {"SUPABASE_URL": "https://example.test", "SUPABASE_SERVICE_ROLE_KEY": "test"}, clear=True)
    def test_complete_original(self):
        sources = [{"file_id": "a", "row_count": 1}]
        with patch.object(api, "read_table", side_effect=[sources, [{"source_file_id": "a"}], sources]):
            self.assertEqual(api.call("sales.daeyoung.read", "2026-10-01")["status"], "available")


if __name__ == "__main__":
    unittest.main()
