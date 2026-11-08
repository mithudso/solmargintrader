"""Select and shard SolTUI tests without silently omitting shared-code coverage."""
from __future__ import annotations

import argparse
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


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


class TimedResult(unittest.TextTestResult):
    def startTest(self, test):
        self._start = time.monotonic()
        super().startTest(test)

    def stopTest(self, test):
        self.timings.append((time.monotonic() - self._start, test.id()))
        super().stopTest(test)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timings = []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--shard', type=int, required=True)
    parser.add_argument('--shards', type=int, default=4)
    parser.add_argument('--base', help='base commit for conservative PR selection')
    args = parser.parse_args()
    if args.shards < 1 or not 0 <= args.shard < args.shards:
        parser.error('shard must be between 0 and shards - 1')
    modules = None
    if args.base:
        # Include both sides of renames and deleted paths; a failed diff fails closed.
        raw = subprocess.check_output(['git', 'diff', '--name-only', '--no-renames', '-z', args.base, 'HEAD'])
        modules = selected_modules(raw.decode().split('\0')[:-1])
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


if __name__ == '__main__':
    raise SystemExit(main())
