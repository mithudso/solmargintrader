"""Declared card schemas apply equally to defaults and per-horizon presets."""
from contextlib import redirect_stdout
import io
import unittest
from backtester.core import strategy_cards as cards
from backtester.tests import test_strategy_cards as fixtures


class CardInputTests(unittest.TestCase):
    def _load(self, extra):
        fields = fixtures.TestCardValidation.BASE
        text = '\n'.join(['---', *[f'{key}: {value}' for key, value in fields.items()], *extra, '---', 'Body'])
        return cards.load_card('demo.md', text=text)

    def test_unknown_type_and_out_of_schema_values_refuse_at_load(self):
        for extra in [
            ['params:', '  a: {default: 1, type: intt}'],
            ['params:', '  a: {default: 1, type: int, min: 2}'],
            ['params:', '  a: {default: 2, type: int, min: 1, max: 5}', 'presets:', '  short: {a: two}'],
            ['params:', '  a: {default: 2, type: int, min: 1, max: 5}', 'presets:', '  short: {a: 6}'],
        ]:
            with self.subTest(card=extra), self.assertRaises(cards.CardError):
                self._load(extra)

    def test_inventory_help_is_parse_only(self):
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaises(SystemExit) as error:
            cards.main(['--help'])
        self.assertEqual(error.exception.code, 0)
        self.assertIn('Example:', output.getvalue())


if __name__ == '__main__':
    unittest.main()
