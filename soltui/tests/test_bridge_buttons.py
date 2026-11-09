"""Every TUI button is a registry command: a new button cannot skip the registry."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

from soltui import commands, tui

SRC = Path(tui.__file__).read_text()
UI_ONLY = {"#bot-settings-defaults", "#bot-settings-cancel", "#signal-live-forward-link"}


def pressed_selectors() -> list[str]:
    found = []
    for node in ast.walk(ast.parse(SRC)):
        if isinstance(node, ast.FunctionDef):
            for dec in node.decorator_list:
                if (isinstance(dec, ast.Call) and ast.unparse(dec.func) == "on"
                        and dec.args and ast.unparse(dec.args[0]) == "Button.Pressed"
                        and len(dec.args) > 1):
                    found.append(ast.literal_eval(dec.args[1]))
    return found


class ButtonRegistryTests(unittest.TestCase):
    def test_button_handler_count(self) -> None:
        self.assertEqual(len(pressed_selectors()), 122)

    def test_every_button_handler_maps_to_a_registered_command(self) -> None:
        for selector in pressed_selectors():
            if selector in UI_ONLY:
                continue
            with self.subTest(button=selector):
                self.assertIn(selector, tui.BUTTON_COMMANDS, "add it to tui.BUTTON_COMMANDS")
                self.assertIn(tui.BUTTON_COMMANDS[selector], commands.COMMANDS)

    def test_no_stale_mapping_entries(self) -> None:
        self.assertEqual(sorted(tui.BUTTON_COMMANDS), sorted(set(pressed_selectors()) - UI_ONLY))

    def test_every_button_widget_has_a_handler(self) -> None:
        ids = set(re.findall(r'Button\([^)]*?id="([^"]+)"', SRC, flags=re.S))
        handled = {s.lstrip("#") for s in pressed_selectors()}
        self.assertEqual(ids - handled, set(), "button without a Button.Pressed handler")

    def test_the_tui_holds_no_direct_action_calls(self) -> None:
        code = "\n".join(line for line in SRC.splitlines() if not line.lstrip().startswith("#"))
        for forbidden in ("save_settings(", "bgcontrol.start(", "bgcontrol.stop(", "liq.set_kill(",
                          "write_document(", "subprocess.run("):
            self.assertNotIn(forbidden, code, f"tui.py must go through the registry, not {forbidden}")


if __name__ == "__main__":
    unittest.main()
