"""Exercise the load fixture's real cleanup block without spawning a worker."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace


class LoadCleanupTests(unittest.TestCase):
    def test_optimizer_is_reaped_even_if_supervisor_close_fails(self):
        source = Path(__file__).with_name('test_load.py').read_text()
        module = ast.parse(source)
        method = next(node for node in ast.walk(module)
                      if isinstance(node, ast.FunctionDef) and node.name == 'run_load_fixture')
        final = next(node.finalbody for node in ast.walk(method)
                     if isinstance(node, ast.Try) and node.finalbody
                     and any(isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
                             and child.func.attr == 'set' for child in ast.walk(ast.Module(body=node.finalbody, type_ignores=[]))))
        cleanup = ast.fix_missing_locations(ast.Module(body=final[:1], type_ignores=[]))
        events = []
        def fail():
            raise RuntimeError('fixture close failed')
        supervisor = SimpleNamespace(close=fail)
        stop = SimpleNamespace(set=lambda: events.append('stop'))
        optimizer = SimpleNamespace(join=lambda seconds: events.append(('join', seconds)),
                                    is_alive=lambda: True, kill=lambda: events.append('kill'),
                                    exitcode=0, close=lambda: events.append('close'))
        with self.assertRaisesRegex(RuntimeError, 'fixture close failed'):
            exec(compile(cleanup, '<fixture cleanup>', 'exec'), {'supervisor': supervisor, 'stop': stop, 'optimizer': optimizer})  # noqa: S102 - AST from owned test source
        self.assertEqual(events, ['stop', ('join', 5), 'kill', ('join', 2), 'close'])
