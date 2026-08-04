"""py2app entry point for the menu-bar app.

## Why this file exists

py2app executes its target as a **top-level script**, not as a module inside a
package. `soltui/app.py` uses relative imports (`from .config import ...`), which
under that execution model fail with:

    ImportError: attempted relative import with no known parent package

Pointing py2app at this launcher instead fixes it without contorting `app.py`
into absolute imports it does not otherwise need. The launcher puts the repo root
on `sys.path` and then imports `soltui.app` as a proper package, so every relative
import inside the package resolves normally.

Found empirically: the first bundle built cleanly, signed, and stayed *running* --
but only because py2app was displaying a "Launch error" dialog. A liveness check
alone would have called that a success. The stderr log is the real signal.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# In an alias build this file lives in the source tree, so the repo root is its
# grandparent. Resolving symlinks matters because py2app's bundle may reach this
# file through one.
REPO = Path(__file__).resolve().parent.parent

if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# launchd starts processes with no LANG, which makes the locale encoding
# US-ASCII; the status glyphs are non-ASCII. The agent plist sets these too --
# this is the belt to that braces, and it also covers a manual Finder launch.
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("LANG", "en_US.UTF-8")

# Working directory: an app bundle launched from Finder or launchd starts at "/",
# so relative paths in Settings (data_dir="data") would miss. Anchor to the repo.
try:
    os.chdir(REPO)
except OSError:
    pass

from soltui.app import main  # noqa: E402 - must follow the sys.path insertion

if __name__ == "__main__":
    raise SystemExit(main())
