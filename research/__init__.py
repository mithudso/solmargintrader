"""Keep existing research module entry points after organizing script files."""

from pathlib import Path

__path__.append(str(Path(__file__).with_name("scripts")))
