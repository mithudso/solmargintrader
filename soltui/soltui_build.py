"""Build a portable sdist from the monorepo without maintaining duplicate source."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from setuptools import build_meta as _backend

build_wheel = _backend.build_wheel
build_editable = _backend.build_editable
get_requires_for_build_wheel = _backend.get_requires_for_build_wheel
get_requires_for_build_editable = _backend.get_requires_for_build_editable
get_requires_for_build_sdist = _backend.get_requires_for_build_sdist
prepare_metadata_for_build_wheel = _backend.prepare_metadata_for_build_wheel
prepare_metadata_for_build_editable = _backend.prepare_metadata_for_build_editable


def build_sdist(sdist_directory, config_settings=None):
    project = Path(__file__).resolve().parent
    # An extracted sdist already has its in-tree copy and self-contained mapping.
    if (project / "oracle_leverage").is_dir():
        return _backend.build_sdist(sdist_directory, config_settings)
    target = str(Path(sdist_directory).resolve())
    sibling = project.parent / "oracle_leverage"
    if not sibling.is_dir():
        raise RuntimeError("oracle_leverage source is missing from the monorepo")
    with tempfile.TemporaryDirectory(prefix="soltui-sdist-") as temporary:
        staged = Path(temporary) / "soltui"
        staged.mkdir()
        for source in project.glob("*.py"):
            shutil.copy2(source, staged / source.name)
        for name in ("pyproject.toml", "MANIFEST.in", "README.md"):
            source = project / name
            if source.is_file():
                shutil.copy2(source, staged / name)
        bundled = staged / "oracle_leverage"
        bundled.mkdir()
        for source in sibling.glob("*.py"):
            shutil.copy2(source, bundled / source.name)
        config = staged / "pyproject.toml"
        content = config.read_text(encoding="utf-8")
        old = 'oracle_leverage = "../oracle_leverage"'
        if old not in content:
            raise RuntimeError("unexpected monorepo package mapping")
        config.write_text(
            content.replace(old, 'oracle_leverage = "oracle_leverage"'),
            encoding="utf-8",
        )
        previous = Path.cwd()
        try:
            os.chdir(staged)
            return _backend.build_sdist(target, config_settings)
        finally:
            os.chdir(previous)
