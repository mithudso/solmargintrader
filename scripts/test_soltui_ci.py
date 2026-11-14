import io
import unittest
from scripts.soltui_ci import TimedResult, selected_modules, targeted_modules


class SelectionTests(unittest.TestCase):
    def test_only_individual_test_files_are_narrowed(self):
        self.assertEqual(selected_modules(['soltui/tests/test_forwardtest.py', 'soltui/tests/test_bots.py']),
                         ['soltui.tests.test_bots', 'soltui.tests.test_forwardtest'])

    def test_deleted_test_selects_the_full_suite(self):
        self.assertIsNone(selected_modules(['soltui/tests/test_removed.py'], exists=lambda _: False))

    def test_unknown_shared_and_empty_inputs_run_full_suite(self):
        for paths in ([], ['soltui/tui.py'], ['soltui/tests/bridge_support.py'],
                      ['soltui/tests/test_bots.py', 'backtester/core/engine.py'],
                      ['docs/TESTING.md'], ['soltui/tests/fixtures/test_foo.py']):
            with self.subTest(paths=paths):
                self.assertIsNone(selected_modules(paths))


class TimingTests(unittest.TestCase):
    def test_test_may_replace_its_id_attribute(self):
        class MutatesId(unittest.TestCase):
            def runTest(self):
                self.id = "application identifier"

        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=TimedResult).run(MutatesId())
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(len(result.timings), 1)
        self.assertIn('MutatesId', result.timings[0][1])


class TargetedTests(unittest.TestCase):
    def test_manager_owner_changes_keep_control_and_legacy_regressions(self):
        for path in ('soltui/bots.py', 'soltui/commands.py'):
            with self.subTest(path=path):
                modules = targeted_modules([path])
                self.assertIn('soltui.tests.test_manager_controls', modules)
                self.assertIn('soltui.tests.test_bots', modules)

    def test_forwardtest_and_ui_dependencies_are_included(self):
        modules = targeted_modules(['soltui/forwardtest.py', 'soltui/tui.py'])
        for name in ('test_forwardtest', 'test_coin_fit_ui', 'test_v2_shell', 'test_bridge_buttons'):
            self.assertIn('soltui.tests.' + name, modules)

    def test_changed_tests_and_unknown_paths_keep_smoke(self):
        modules = targeted_modules(['soltui/tests/test_bots.py', 'new/unknown.py'], exists=lambda _: True)
        self.assertIn('soltui.tests.test_bots', modules)
        self.assertIn('soltui.tests.test_bridge_parity', modules)
        self.assertNotIn('soltui.tests.test_bots', targeted_modules(['soltui/tests/test_bots.py'], exists=lambda _: False))
