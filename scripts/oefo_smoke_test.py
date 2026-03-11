#!/usr/bin/env python3
from __future__ import annotations

import inspect
import os
import subprocess
import sys


def main() -> int:
    import oefo
    from oefo.cli import create_parser
    from oefo.dashboard import server as dashboard_server

    assert hasattr(oefo, '__version__')

    parser = create_parser()
    args = parser.parse_args(['dashboard'])
    assert args.host == '127.0.0.1', f'Unexpected dashboard default host: {args.host}'

    source = inspect.getsource(dashboard_server)
    assert 'Access-Control-Allow-Origin: *' not in source, 'Wildcard CORS header still present'
    assert hasattr(dashboard_server, 'start_server'), 'Missing start_server helper'

    env = dict(os.environ)

    result = subprocess.run([sys.executable, '-m', 'oefo', '--help'], capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    assert 'dashboard' in result.stdout

    result = subprocess.run([sys.executable, '-c', 'import oefo, oefo.cli, oefo.dashboard.server, oefo.data.storage'], capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr

    print('Smoke tests passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
