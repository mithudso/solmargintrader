"""A failed spawn still releases its Process object when journaling fails."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


class SpawnCleanupTests(unittest.TestCase):
    def test_failed_journal_does_not_skip_process_close(self):
        source = (Path(__file__).parents[1] / 'src/botmanager/supervisor.py').read_text()
        module = ast.parse(source)
        step = next(node for node in ast.walk(module)
                    if isinstance(node, ast.FunctionDef) and node.name == 'step')
        handler = next(handler for node in ast.walk(step) if isinstance(node, ast.Try)
                       for handler in node.handlers
                       if any(isinstance(child, ast.Constant) and child.value == 'worker_spawn_failed'
                              for child in ast.walk(handler)))
        cleanup = ast.fix_missing_locations(ast.Module(body=handler.body[:1], type_ignores=[]))
        closed = []
        class FixtureManagerError(RuntimeError):
            pass
        def failed(*args):
            raise FixtureManagerError('fixture journal unavailable')
        obj = SimpleNamespace(ledger=SimpleNamespace(failed=failed), _pending_failures={})
        process = SimpleNamespace(close=lambda: closed.append(True))
        with self.assertRaisesRegex(RuntimeError, 'fixture journal unavailable'):
            exec(compile(cleanup, '<spawn cleanup>', 'exec'),  # noqa: S102 - owned source AST
                 {'self': obj, 'bot_id': 'fixture', 'generation': 1, 'process': process,
                  'ManagerError': FixtureManagerError})
        self.assertEqual(closed, [True])
        self.assertEqual(obj._pending_failures, {'fixture': (1, 'worker_spawn_failed')})
