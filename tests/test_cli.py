from __future__ import annotations

import subprocess
import sys

from oefo.cli import create_parser


def test_module_help() -> None:
    result = subprocess.run([sys.executable, '-m', 'oefo', '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    assert 'dashboard' in result.stdout


def test_dashboard_default_host() -> None:
    parser = create_parser()
    args = parser.parse_args(['dashboard'])
    assert args.host == '127.0.0.1'
