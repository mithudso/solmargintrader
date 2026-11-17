"""Metadata tools validate their consumers' boundaries using disposable inputs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts import bootstrap_ecosystem, build_ecosystem_wiki as wiki_builder
from scripts import build_tradingview_script_profiles as profiles
from scripts import check_tradingview_cards as cards
from scripts import check_tradingview_strategy_profiles as strategy_profiles


class ToolBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_stop_does_not_require_the_startup_health_gate(self):
        venv = self.root / 'venv'
        python = venv / 'bin/python'
        python.parent.mkdir(parents=True)
        python.touch()
        with patch('ecosystem.installation.verify_environment', return_value={'status': 'failed'}) as verify, patch.object(bootstrap_ecosystem.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as run:
            self.assertEqual(bootstrap_ecosystem.main(['--venv', str(venv), 'stop']), 0)
        verify.assert_not_called()
        self.assertEqual(run.call_args.args[0], [str(python), '-I', '-m', 'ecosystem.cli', 'stop'])

    def wiki_fixture(self):
        (self.root / 'README.md').write_text('# Synthetic fixture\nPublic documentation.\n')
        template = self.root / 'empty-template'
        template.mkdir()
        env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
                   GIT_TEMPLATE_DIR=str(template))
        commands = [['init', '--template=' + str(template), '-q'], ['add', 'README.md'], ['-c', 'core.hooksPath=/dev/null', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture']]
        for command in commands:
            subprocess.run(['git', '-C', str(self.root), *command], check=True, capture_output=True, env=env)
        output = self.root / 'output'
        output.mkdir()
        manifest, _ = wiki_builder.compile_snapshot(self.root, output)
        return output, json.loads(manifest)

    def test_invalid_retained_wiki_provenance_is_regenerated(self):
        output, manifest = self.wiki_fixture()
        for commit, state in [('not-a-commit', 'committed'), (None, 'committed')]:
            with self.subTest(commit=commit, state=state):
                manifest['pages'][0].update(source_commit=commit, source_state=state)
                (output / 'manifest.json').write_text(json.dumps(manifest))
                generated, _ = wiki_builder.compile_snapshot(self.root, output)
                row = json.loads(generated)['pages'][0]
                self.assertRegex(row['source_commit'], r'^[0-9a-f]{40}$')
                self.assertEqual(row['source_state'], 'committed')

    def test_wiki_builder_refuses_both_consumer_byte_limits(self):
        output, _ = self.wiki_fixture()
        for field in ('MAX_BUNDLE_BYTES', 'MAX_MANIFEST_BYTES'):
            with self.subTest(field=field), patch.object(wiki_builder, field, 1):
                with self.assertRaisesRegex(ValueError, 'consumer_limit'):
                    wiki_builder.compile_snapshot(self.root, output)

    def test_duplicate_publications_cannot_replace_missing_inventory_entries(self):
        research = self.root / 'research'
        research.mkdir()
        ids = [f'fixture-{i:03}' for i in range(742)]
        (research / 'tradingview-strategy-understanding.json').write_text(json.dumps({'publications': [{'publication_id': key} for key in ids[:21]]}))
        (research / 'tradingview-card-coverage.json').write_text(json.dumps({'rows': [{'kind': 'script', 'publication_id': key, 'disposition': 'non-signal'} for key in ids]}))
        source = self.root / 'html'
        source.mkdir()
        for i in range(742):
            (source / f'{i:03}.html').write_text('fixture')
        def publication(path):
            index = int(path.stem)
            key = ids[0] if index == 741 else ids[index]
            return {'uuid': key, 'name': key, 'chart_url': '/fixture/' + key}
        with patch.object(profiles, 'ROOT', self.root), patch.object(profiles, 'CACHE', self.root / 'cache'), patch.object(profiles, 'WORK', self.root / 'work.json'), patch.object(profiles, 'publication', side_effect=publication):
            with self.assertRaisesRegex(ValueError, 'inventory'):
                profiles.prepare(source)
        self.assertFalse((self.root / 'cache').exists())

    def test_repeated_sources_must_satisfy_each_declared_digest(self):
        (self.root / 'docs').mkdir()
        (self.root / 'research').mkdir()
        names = [f'fixture-{i}' for i in range(114)]
        (self.root / 'docs/TRADINGVIEW-REFERENCE.md').write_text('### 1. Catalog of built-in indicators\n' + '\n'.join(f'| `{name}` | fixture |' for name in names) + '\n### Standard equations\n')
        (self.root / 'research/tradingview-card-readiness.json').write_text('{}')
        source = self.root / 'source.md'
        source.write_text('synthetic public input')
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        rows = [{'name': name, 'kind': 'builtin', 'disposition': 'non-signal', 'reason': 'fixture'} for name in names]
        for row, expected in zip(rows, [digest, '0' * 64]):
            row['sources'] = [{'path': 'source.md', 'scope': 'repository', 'sha256': expected}]
        data = {'created_card_ids': [], 'existing_card_ids': [], 'rows': rows, 'source_publication_counts': dict(script=0, chart=0, support=0, other=0)}
        with patch.object(cards, 'load_catalog', return_value=({}, {})), patch.object(cards, 'validate_readiness'):
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                cards.validate(data, self.root)

    def test_missing_coin_readiness_cannot_promote_a_strategy_card(self):
        research = self.root / 'research'
        research.mkdir()
        profile = {'publication_id': 'demo', 'card_path': 'backtester/strategy_cards/demo.md', 'card_sha256': 'a' * 64, 'source_sha256': 'b' * 64, 'raw_description_sha256': 'c' * 64, 'description_characters': 7}
        accepted = research / 'tradingview-strategy-understanding.json'
        accepted.write_text(json.dumps({'publications': [profile]}))
        entry = {**profile, 'original_card_path': profile['card_path'], 'current_card_path': profile['card_path'], 'readiness': {'status': 'usable-specification', 'reason': 'fixture', 'gaps': []}, 'evidence': [{'quote': 'fixture', 'start': 0, 'end': 7}], 'source_read_ranges': [[0, 7]]}
        receipt = {'schema_version': 1, 'verdict': 'pass', 'accepted_manifest_sha256': hashlib.sha256(accepted.read_bytes()).hexdigest(), 'publications': [entry]}
        (research / 'tradingview-strategy-card-locations.json').write_text(json.dumps(receipt))
        with self.assertRaises(ValueError):
            strategy_profiles.card_location(self.root, profile)


if __name__ == '__main__':
    unittest.main()
