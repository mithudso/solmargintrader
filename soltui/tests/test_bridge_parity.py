"""One registry, four surfaces: the same call returns the same envelope bytes everywhere.

Driven by the registry itself, so a command added tomorrow is covered the day it is registered (the way
extension/test/surfaces.test.js covers the extension's registry).
"""

from __future__ import annotations

import json
import unittest
from contextlib import ExitStack

from soltui import commands

from .bridge_support import (ApiServer, World, default_params, stub_heavy, via_api, via_cli,
                             via_host, via_tui)


class ParityTests(unittest.TestCase):
    def test_every_command_returns_identical_bytes_on_all_four_surfaces(self) -> None:
        params_for = default_params()
        with World() as world, ExitStack() as stack, ApiServer() as server:
            stub_heavy(stack)
            surfaces = {"tui": via_tui, "cli": via_cli, "api": via_api(server), "host": via_host}
            names = ["list"] + sorted(commands.COMMANDS)
            self.assertGreaterEqual(len(names), 41)
            for name in names:
                params = params_for.get(name, {})
                seen = {}
                for surface, run in surfaces.items():
                    world.reset_state()
                    seen[surface] = run(name, params)
                with self.subTest(command=name):
                    baseline = seen["tui"]
                    json.loads(baseline)
                    for surface, text in seen.items():
                        self.assertEqual(text, baseline, f"{name}: {surface} differs from tui")

    def test_every_required_param_command_has_a_fixture(self) -> None:
        fixtures = default_params()
        for name, cmd in commands.COMMANDS.items():
            if any(p.required for p in cmd.params) and not cmd.requires_confirm:
                self.assertIn(name, fixtures, f"add a valid call for {name} to bridge_support")

    def test_parity_covers_failures_too(self) -> None:
        bad = {"nope.nothing": {}, "roster.add": {"name": 5}, "liquidity.resume": {}}
        with World() as world, ApiServer() as server:
            for name, params in bad.items():
                outs = set()
                for run in (via_tui, via_cli, via_api(server), via_host):
                    world.reset_state()
                    outs.add(run(name, params))
                with self.subTest(command=name):
                    self.assertEqual(len(outs), 1)
                    self.assertFalse(json.loads(outs.pop())["ok"])

    def test_envelope_carries_no_surface_time_or_request_id(self) -> None:
        with World():
            env = commands.dispatch("settings.get", {}, surface="cli")
            self.assertEqual(set(env), {"ok", "command", "result", "error"})
            text = commands.dumps(env)
            for word in ("cli", "surface", "ms", "request"):
                self.assertNotIn(f'"{word}"', text)

    def test_registry_metadata_is_complete(self) -> None:
        for name, cmd in commands.COMMANDS.items():
            self.assertRegex(name, r"^[a-z0-9]+\.[a-z0-9_]+$")
            self.assertTrue(cmd.describe)
            for p in cmd.params:
                self.assertIn(p.type, commands.PARAM_TYPES)
                self.assertTrue(p.describe)
        resume = commands.COMMANDS["liquidity.resume"]
        kill = commands.COMMANDS["liquidity.kill"]
        self.assertTrue(resume.requires_confirm)
        self.assertFalse(kill.requires_confirm)
        self.assertEqual([n for n, c in commands.COMMANDS.items() if c.requires_confirm],
                         ["liquidity.resume"])


if __name__ == "__main__":
    unittest.main()
