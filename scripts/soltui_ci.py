"""Select and shard SolTUI tests without silently omitting shared-code coverage."""
from __future__ import annotations

import argparse
import os
import tempfile
import subprocess
import sys
import time
import unittest
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def selected_modules(paths: list[str]) -> list[str] | None:
    """Only narrow a PR consisting entirely of individual SolTUI test files.

    Every other change, including helpers, deleted files, docs, configuration,
    cross-component changes and an empty diff, falls back to the full suite.
    """
    modules = []
    for path in paths:
        p = PurePosixPath(path)
        if len(p.parts) != 3 or p.parts[:2] != ('soltui', 'tests') or not p.name.startswith('test_') or p.suffix != '.py':
            return None
        modules.append(f'soltui.tests.{p.stem}')
    return sorted(set(modules)) if modules else None


# These checks are a bounded PR gate, not a substitute for the opt-in full suite.
SMOKE = {'soltui.tests.test_bridge_buttons', 'soltui.tests.test_bridge_parity'}
DEPENDENCIES = {
    'soltui/bots.py': {'soltui.tests.test_bots', 'soltui.tests.test_manager_controls'},
    'soltui/desk.py': {'soltui.tests.test_desk'},
    'soltui/live_score.py': {'soltui.tests.test_live_score', 'soltui.tests.test_signal_live'},
    'soltui/simulation.py': {'soltui.tests.test_simulation', 'soltui.tests.test_forwardtest',
                              'soltui.tests.test_paper_experiments', 'soltui.tests.test_bgworker'},
    'soltui/config.py': {'soltui.tests.test_simulation', 'soltui.tests.test_status_roster'},
    'soltui/runner.py': {'soltui.tests.test_simulation', 'soltui.tests.test_bgworker'},
    'soltui/forwardtest.py': {'soltui.tests.test_forwardtest'},
    'soltui/coin_fit.py': {'soltui.tests.test_coin_fit', 'soltui.tests.test_coin_fit_ui'},
    'soltui/shell.py': {'soltui.tests.test_v2_shell'},
    'soltui/tui.py': {'soltui.tests.test_forwardtest', 'soltui.tests.test_signal_live', 'soltui.tests.test_coin_fit_ui',
                      'soltui.tests.test_v2_shell', 'soltui.tests.test_bridge_buttons'},
    'soltui/commands.py': {'soltui.tests.test_bridge_buttons', 'soltui.tests.test_bridge_parity',
                           'soltui.tests.test_forwardtest', 'soltui.tests.test_experiment_interface',
                           'soltui.tests.test_bots', 'soltui.tests.test_manager_controls'},
}


def targeted_modules(paths: list[str], exists=lambda p: Path(p).is_file()) -> list[str]:
    """Run mapped tests plus bridge smoke; unknown paths keep the smoke gate.

    This intentionally bounded gate cannot prove the full suite; manual dispatch
    remains available. Never infer an untested source file is irrelevant.
    """
    modules = set(SMOKE)
    for path in paths:
        p = PurePosixPath(path)
        if len(p.parts) == 3 and p.parts[:2] == ('soltui', 'tests') and p.name.startswith('test_') and p.suffix == '.py' and exists(path):
            modules.add(f'soltui.tests.{p.stem}')
        modules.update(DEPENDENCIES.get(path, ()))
    return sorted(modules)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


class TimedResult(unittest.TextTestResult):
    def startTest(self, test):
        self._start = time.monotonic()
        self._test_id = test.id()
        super().startTest(test)

    def stopTest(self, test):
        self.timings.append((time.monotonic() - self._start, self._test_id))
        super().stopTest(test)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings = []


def _run() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--shard', type=int, required=True)
    parser.add_argument('--shards', type=int, default=4)
    parser.add_argument('--base', help='base commit for PR selection')
    parser.add_argument('--targeted', action='store_true', help='run bounded PR smoke and mapped modules')
    args = parser.parse_args()
    if args.shards < 1 or not 0 <= args.shard < args.shards:
        parser.error('shard must be between 0 and shards - 1')
    modules = None
    if args.base:
        # Include both sides of renames and deleted paths; a failed diff fails closed.
        raw = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', '-z', args.base, 'HEAD'])
        paths = raw.decode().split('\0')[:-1]
        modules = targeted_modules(paths) if args.targeted else selected_modules(paths)
    elif args.targeted:
        modules = targeted_modules([])
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromNames(modules) if modules else loader.discover('soltui/tests', top_level_dir='.')
    tests = sorted(flatten(suite), key=lambda test: test.id())
    if not tests or any(t.__class__.__name__ == '_FailedTest' for t in tests):
        print('Test discovery failed or returned no tests', file=sys.stderr)
        return 1
    ids = [test.id() for test in tests]
    if len(ids) != len(set(ids)):
        print('Duplicate test IDs prevent safe sharding', file=sys.stderr)
        return 1
    chosen = tests[args.shard::args.shards]
    print(f"Selection: {modules or 'full suite'}; shard {args.shard + 1}/{args.shards}: {len(chosen)}/{len(tests)} tests", flush=True)
    runner = unittest.TextTestRunner(resultclass=TimedResult, verbosity=1)
    result = runner.run(unittest.TestSuite(chosen))
    print('Slowest tests in this shard:')
    for seconds, test_id in sorted(result.timings, reverse=True)[:20]:
        print(f'{seconds:.2f}s {test_id}')
    return 0 if result.wasSuccessful() else 1


def main() -> int:
    # Autostart and session persistence tests must never edit the owner's saved plan.
    if os.environ.get('SOLTUI_CONFIG_DIR'):
        return _run()
    with tempfile.TemporaryDirectory(prefix='soltui-ci-') as directory:
        os.environ['SOLTUI_CONFIG_DIR'] = directory
        try:
            return _run()
        finally:
            del os.environ['SOLTUI_CONFIG_DIR']


if __name__ == '__main__':
    raise SystemExit(main())
