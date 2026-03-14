from __future__ import annotations

import inspect

from oefo.dashboard import server as dashboard_server


def test_no_wildcard_cors() -> None:
    source = inspect.getsource(dashboard_server)
    assert 'Access-Control-Allow-Origin: *' not in source


def test_start_server_exists() -> None:
    assert hasattr(dashboard_server, 'start_server')
