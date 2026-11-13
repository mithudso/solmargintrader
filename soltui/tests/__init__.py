"""soltui tests.

The suite must never read or write the owner's real state, so the directories soltui resolves at
import time are pointed at a throwaway tree before any soltui module is imported (this package is
imported first by `unittest discover -s soltui/tests -t .`). Individual tests that need a clean slate
create their own directories and patch the module constants.
"""

import atexit
import os
import shutil
import tempfile

_ROOT = tempfile.mkdtemp(prefix="soltui-tests-")
atexit.register(shutil.rmtree, _ROOT, ignore_errors=True)
for _name, _sub in (("SOLTUI_CONFIG_DIR", "config"), ("SOLTUI_LOG_DIR", "logs"),
                    ("SOLTUI_SUPPORT_DIR", "support"), ("SOLMARGINTRADER_STORAGE", "manual-storage"),
                    ("SOLBOT_HOME", "manager"), ("SOLBOT_ECOSYSTEM_HOME", "ecosystem"),
                    ("AERO_LP_HOME", "liquidity"), ("SOLMT_DATA_DIR", "market-data"),
                    ("SOLTUI_KEY_DIR", "keys")):
    # Inherited settings may be the real owner environment. Tests always own a
    # fresh root; individual fixtures can explicitly patch their own subpaths.
    os.environ[_name] = os.path.join(_ROOT, _sub)
