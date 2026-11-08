import unittest
from scripts.soltui_ci import selected_modules


class SelectionTests(unittest.TestCase):
    def test_only_individual_test_files_are_narrowed(self):
        self.assertEqual(selected_modules(['soltui/tests/test_forwardtest.py', 'soltui/tests/test_bots.py']),
                         ['soltui.tests.test_bots', 'soltui.tests.test_forwardtest'])

    def test_unknown_shared_and_empty_inputs_run_full_suite(self):
        for paths in ([], ['soltui/tui.py'], ['soltui/tests/bridge_support.py'],
                      ['soltui/tests/test_bots.py', 'backtester/core/engine.py'],
                      ['docs/TESTING.md'], ['soltui/tests/fixtures/test_foo.py']):
            with self.subTest(paths=paths):
                self.assertIsNone(selected_modules(paths))
