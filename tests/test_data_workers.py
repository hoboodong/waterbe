import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkerCatalogTests(unittest.TestCase):
    def test_sources_and_api_links(self):
        registry = json.loads((ROOT / "config/data_workers.json").read_text(encoding="utf-8"))
        api = json.loads((ROOT / "config/api_catalog.json").read_text(encoding="utf-8"))
        operations = {item["id"] for item in api["operations"]}
        workers = registry["workers"]
        self.assertEqual(registry["partition_by"], "source_kind")
        self.assertEqual(registry["deployment_status"], "design_only")
        self.assertEqual(len(workers), len({w["id"] for w in workers}))
        for worker in workers:
            self.assertTrue(worker["inputs"] and worker["outputs"])
            self.assertTrue(set(worker["operations"]) <= operations)
            self.assertEqual(worker["new_processing_status"], "planned")


if __name__ == "__main__":
    unittest.main()
