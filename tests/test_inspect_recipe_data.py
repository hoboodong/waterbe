import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("inspect_recipe_data", ROOT / "scripts/inspect_recipe_data.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class RecipeAuditTests(unittest.TestCase):
    def test_read_only_repeatable(self):
        files = sorted((ROOT / "instances/master").rglob("*.yaml"))
        before = {str(p): p.read_bytes() for p in files}
        result = module.inspect()
        self.assertEqual(result, module.inspect())
        self.assertEqual(before, {str(p): p.read_bytes() for p in files})
        self.assertTrue(result["counts"])
        self.assertTrue(result["issues"])


if __name__ == "__main__":
    unittest.main()
