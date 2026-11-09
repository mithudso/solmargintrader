"""Expand content-verified experiment sources without duplicating search indexes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import zipfile

DEFAULT_EXPERIMENT = Path(__file__).resolve().parent / 'strategy_experiment'


def ensure_snapshots(experiment: Path = DEFAULT_EXPERIMENT) -> None:
    """Never overwrite an existing source tree; verify every distributed member."""
    experiment = Path(experiment)
    manifest_path = experiment / 'archives.json'
    if not manifest_path.exists():
        if all((experiment / variant / 'core/strategies/__init__.py').exists()
               for variant in ('original', 'candidate')):
            return  # Initial authoring, before archive packaging.
        raise FileNotFoundError(f'missing snapshot archives manifest: {manifest_path}')
    manifest = json.loads(manifest_path.read_text())
    for variant in ('original', 'candidate'):
        root = experiment / variant
        expected = manifest[variant]['files']
        if not root.exists():
            archive = experiment / f'{variant}.zip'
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            if digest != manifest[variant]['archive_sha256']:
                raise ValueError(f'{variant} archive checksum mismatch')
            with zipfile.ZipFile(archive) as zipped:
                if set(zipped.namelist()) != set(expected):
                    raise ValueError(f'{variant} archive member list mismatch')
                for member in zipped.infolist():
                    target = (root / member.filename).resolve()
                    if not target.is_relative_to(root.resolve()):
                        raise ValueError('snapshot archive contains an unsafe member')
                    content = zipped.read(member)
                    if hashlib.sha256(content).hexdigest() != expected[member.filename]:
                        raise ValueError(f'{variant} member checksum mismatch')
                # All members checked before creating a source tree.
                for member in zipped.infolist():
                    target = root / member.filename
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(zipped.read(member))
        actual = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        if actual != expected:
            raise ValueError(f'{variant} expanded sources differ from frozen manifest')
