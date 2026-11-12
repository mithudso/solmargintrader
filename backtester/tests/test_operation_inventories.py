"""Inventory discovery is static and drift checks cannot execute or change tools."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_operation_inventories as inventories

PYTHON_REGISTRY = '''
raise AssertionError("source must never execute")
def command(name, description, *, read_only=True, requires_confirm=False, long_running=False):
    raise AssertionError("decorator must never execute")
@command("preview", "Read a preview.")
def preview():
    raise AssertionError("handler must never execute")
@command("submit", "Guarded submission.", read_only=False, requires_confirm=True)
def submit():
    raise AssertionError("handler must never execute")
'''

JAVASCRIPT_REGISTRY = '''
export const COMMANDS = {
  preview: {
    describe: 'Read a preview.',
    params: [],
    readOnly: true,
    handler() { throw new Error('must never execute'); },
  },
  submit: {
    describe: 'Guarded submission.',
    params: [],
    handler() { throw new Error('must never execute'); },
  },
};
'''


class InventoryTests(unittest.TestCase):
    def test_python_decorators_are_parsed_without_import_or_handler_execution(self):
        rows = inventories.python_commands(PYTHON_REGISTRY)
        self.assertEqual([row["name"] for row in rows], ["preview", "submit"])
        self.assertTrue(rows[0]["read_only"])
        self.assertFalse(rows[1]["read_only"])
        self.assertTrue(rows[1]["requires_confirm"])

    def test_unknown_flags_and_duplicate_names_refuse(self):
        for source in (PYTHON_REGISTRY.replace("read_only=False", "read_only=UNKNOWN"),
                       PYTHON_REGISTRY.replace('"submit"', '"preview"')):
            with self.subTest(source=source), self.assertRaises(inventories.InventoryError):
                inventories.python_commands(source)
        with self.assertRaises(inventories.InventoryError):
            inventories.javascript_commands(JAVASCRIPT_REGISTRY.replace("readOnly: true", "readOnly: UNKNOWN"))

    def test_expanded_unknown_and_duplicate_python_keywords_refuse(self):
        replacements = ("**{'read_only': False}", "unknown_option=False",
                        "read_only=False, read_only=True")
        for replacement in replacements:
            with self.subTest(replacement=replacement), self.assertRaises(inventories.InventoryError):
                inventories.python_commands(PYTHON_REGISTRY.replace("read_only=False", replacement))

    def test_js_spread_alias_and_duplicate_metadata_refuse(self):
        sources = [JAVASCRIPT_REGISTRY.replace("};", "  ...dynamicCommands,\n};"),
                   JAVASCRIPT_REGISTRY.replace("};", "    alias: externalCommand,\n};"),
                   JAVASCRIPT_REGISTRY.replace("readOnly: true,", "readOnly: true,\n    readOnly: false,"),
                   JAVASCRIPT_REGISTRY.replace("readOnly: true,", "readOnly: true, readOnly: false,"),
                   JAVASCRIPT_REGISTRY.replace("readOnly: true,", "['readOnly']: true,"),
                   JAVASCRIPT_REGISTRY.replace("readOnly: true,", "readOnly,"),
                   JAVASCRIPT_REGISTRY.replace("readOnly: true,", "    ...metadata,")]
        for source in sources:
            with self.subTest(source=source), self.assertRaises(inventories.InventoryError):
                inventories.javascript_commands(source)

    def test_duplicate_installed_tool_ids_across_manifests_refuse(self):
        with patch.object(inventories, "COMPONENTS", ("oracle", "oracle")), \
                self.assertRaises(inventories.InventoryError):
            inventories.build()

    def test_extension_mutation_is_not_inferred_read_only_from_missing_flag(self):
        rows = inventories.javascript_commands(JAVASCRIPT_REGISTRY)
        self.assertTrue(rows[0]["read_only"])
        self.assertFalse(rows[1]["read_only"])

    def test_inline_flag_is_read_from_its_object_not_nested_parameter_or_handler_fields(self):
        source = JAVASCRIPT_REGISTRY.replace("params: [],\n    readOnly: true,", "params: [{readOnly: false}], readOnly: true,")
        self.assertTrue(inventories.javascript_commands(source)[0]["read_only"])
        nested = source.replace("throw new Error('must never execute');", "return {readOnly: false};")
        self.assertTrue(inventories.javascript_commands(nested)[0]["read_only"])

    def test_multiline_extension_description_only_concatenates_literal_text(self):
        source = JAVASCRIPT_REGISTRY.replace("describe: 'Read a preview.',",
            "describe:\n      'Read a '\n      + 'preview.',")
        self.assertEqual(inventories.javascript_commands(source)[0]["description"], "Read a preview.")
        with self.assertRaises(inventories.InventoryError):
            inventories.javascript_commands(source.replace("'preview.'", "run_handler()"))

    def test_future_unsupported_extension_entry_syntax_refuses_instead_of_omitting(self):
        with self.assertRaises(inventories.InventoryError):
            inventories.javascript_commands(JAVASCRIPT_REGISTRY.replace("  submit:", '  "submit":'))

    def test_check_reports_missing_and_stale_files_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = {"docs/operations-registry.json": {"schema_version": "1.0.0", "operations": []}}
            with patch.object(inventories, "build", return_value=value):
                self.assertEqual(inventories.materialize(root, check=True), list(value))
                self.assertFalse((root / "docs").exists())
                inventories.materialize(root)
                path = root / "docs/operations-registry.json"
                self.assertEqual(inventories.materialize(root, check=True), [])
                path.write_text("stale bytes")
                self.assertEqual(inventories.materialize(root, check=True), list(value))
                self.assertEqual(path.read_text(), "stale bytes")

    def test_source_and_destination_symlinks_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as other:
            root = Path(directory)
            external = Path(other) / "private-source"
            external.write_text("unrelated bytes")
            (root / "source.py").symlink_to(external)
            with self.assertRaises(inventories.InventoryError):
                inventories._read(root, "source.py", {})
            (root / "docs").symlink_to(Path(other), target_is_directory=True)
            with patch.object(inventories, "build", return_value={"docs/inventory.json": {}}), \
                    self.assertRaises(inventories.InventoryError):
                inventories.materialize(root)
            self.assertEqual(external.read_text(), "unrelated bytes")


if __name__ == "__main__":
    unittest.main()
