"""Token discovery must never guess a mint or token decimals."""
import unittest
from unittest.mock import patch

from soltui import jupiter_tokens as tokens

MINT = 'So11111111111111111111111111111111111111112'
OTHER = 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'


def item(mint=MINT, decimals=9, symbol='SOL', verified=True):
    return {'id': mint, 'decimals': decimals, 'symbol': symbol, 'name': 'Solana', 'isVerified': verified}


class JupiterTokenTests(unittest.TestCase):
    @patch.object(tokens, 'get')
    def test_zero_decimals_are_preserved_and_missing_decimals_refused(self, get):
        get.return_value = [item(decimals=0), item(OTHER, decimals=None)]
        self.assertEqual([t['decimals'] for t in tokens.search('SOL')], [0])

    @patch.object(tokens, 'get')
    def test_ambiguous_symbol_requires_mint(self, get):
        get.return_value = [item(), item(OTHER)]
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            tokens.resolve('SOL')
        self.assertEqual(tokens.resolve(MINT)['mint'], MINT)

    @patch.object(tokens, 'get')
    def test_unverified_is_not_resolved(self, get):
        get.return_value = [item(verified=False)]
        with self.assertRaisesRegex(ValueError, 'not verified'):
            tokens.resolve('SOL')

    @patch.object(tokens, 'get')
    def test_malformed_response_fails_closed(self, get):
        get.return_value = {}
        with self.assertRaisesRegex(ValueError, 'invalid'):
            tokens.search('SOL')
