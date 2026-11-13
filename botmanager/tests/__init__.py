"""Scoped synthetic owner endpoints for Bot Manager tests."""
import os
import socket
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def isolated_default_owner():
    """Select a freshly closed endpoint; never probe an owner's default port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as reservation:
        reservation.bind(("127.0.0.1", 0))
        endpoint = "http://127.0.0.1:" + str(reservation.getsockname()[1])
    with patch.dict(os.environ, {"SOLBOT_SOLTUI_ENDPOINT": endpoint}):
        yield endpoint
