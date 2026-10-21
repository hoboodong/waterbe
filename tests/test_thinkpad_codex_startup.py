from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from install_thinkpad_codex_startup import BEGIN,END,merge,install


class StartupTests(unittest.TestCase):
    def test_scoped_merge_preserves_other_instructions(self):
        block=BEGIN+'\nwaterbe only\n'+END
        result=merge('Other project rules\n',block)
        self.assertTrue(result.startswith('Other project rules'))
        self.assertEqual(merge(result,block),result)
        with self.assertRaises(ValueError):
            merge(BEGIN+'\nbroken',block)

    def test_install_preserves_global_rules_and_does_not_override_model(self):
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)
            (home/'.codex').mkdir()
            (home/'.codex/AGENTS.md').write_text('Other rules\n',encoding='utf-8')
            (home/'.npm-global/bin').mkdir(parents=True)
            (home/'.npm-global/bin/codex').touch()
            result=install(home,Path(__file__).resolve().parents[1])
            self.assertFalse(result['model_changed'])
            self.assertTrue((home/'.codex/AGENTS.md').read_text(encoding='utf-8').startswith('Other rules'))
            wrapper=(home/'.local/bin/waterbe-codex').read_text(encoding='utf-8')
            self.assertNotIn('--model',wrapper)
            self.assertIn('"$@"',wrapper)
            self.assertTrue((Path(result['backup'])/'previous-global-AGENTS.md').is_file())


if __name__=='__main__':
    unittest.main()
