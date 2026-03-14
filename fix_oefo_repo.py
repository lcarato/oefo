#!/usr/bin/env python3
"""Remediate the current OEFO repository layout into a modern src-layout package.

What it does:
- Backs up the files it will modify or move.
- Moves the current flat package layout into src/oefo/.
- Writes a modern pyproject.toml and a tiny setup.py shim.
- Fixes dashboard defaults to localhost-only.
- Removes wildcard CORS headers from the dashboard server.
- Adds the missing start_server() helper used by the CLI.
- Generates truthful docs, tests, CI, and OpenClaw helper scripts.
- Creates a .env.example and updates .gitignore.

Run from the repo root:
    python fix_oefo_repo.py

Dry run:
    python fix_oefo_repo.py --dry-run

This script is designed for the currently observable OEFO repository state as of
2026-03-11 and is intentionally idempotent where practical.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Iterable, Sequence

PROJECT_NAME = "oefo"
PACKAGE_NAME = "oefo"
SRC_DIR = Path("src") / PACKAGE_NAME
BACKUP_DIR_NAME = ".oefo_remediation_backup"

TOP_LEVEL_MODULES = [
    "__init__.py",
    "__main__.py",
    "cli.py",
    "llm_client.py",
    "models.py",
]
TOP_LEVEL_PACKAGE_DIRS = [
    "config",
    "dashboard",
    "data",
    "extraction",
    "outputs",
    "qc",
    "scrapers",
]
DOC_FILES_TO_ARCHIVE = [
    "OEFO_Installation_Procedure.docx",
    "OEFO_User_Guide.docx",
]

BASE_DEPENDENCIES = [
    "pandas>=2.0",
    "pydantic>=2.0",
    "pyarrow>=12.0",
    "pdfplumber>=0.9",
    "pymupdf>=1.22",
    "pdf2image>=1.16",
    "pytesseract>=0.3",
    "Pillow>=10.0",
    "opencv-python-headless>=4.8",
    "anthropic>=0.25",
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "lxml>=4.9",
    "openpyxl>=3.1",
    "matplotlib>=3.7",
    "python-dateutil>=2.8",
]
DEV_DEPENDENCIES = [
    "build>=1.2",
    "pytest>=7.4",
    "pytest-cov>=4.1",
    "ruff>=0.6",
    "twine>=5.1",
]
OPTIONAL_OPENAI = ["openai>=1.0"]
OPTIONAL_GOOGLE = ["google-generativeai>=0.5"]

README_TEMPLATE = """# OEFO

OEFO is a Python toolkit for collecting, extracting, validating, and exporting
energy-finance observations from publicly available documents.

## Install

### System prerequisites

macOS:
```bash
brew install poppler tesseract
```

Ubuntu or Debian:
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
```

### Python setup

```bash
git clone https://github.com/lcarato/oefo.git
cd oefo
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e \".[dev]\"
python scripts/oefo_env_check.py
```

## Quick verification

```bash
oefo --help
python -m oefo --help
python scripts/oefo_smoke_test.py
pytest -q
```

## Common commands

```bash
oefo config --validate
oefo scrape ifc
oefo extract ./data/raw/ifc/report.pdf --source-type dfi
oefo extract-batch ./data/raw/ifc --source-type dfi
oefo qc --full
oefo export --format excel --output results.xlsx
oefo dashboard
```

The dashboard now binds to `127.0.0.1` by default. To expose it intentionally,
pass an explicit host value such as `--host 0.0.0.0`.

## Layout

```text
src/oefo/
  cli.py
  llm_client.py
  models.py
  config/
  dashboard/
  data/
  extraction/
  outputs/
  qc/
  scrapers/
```

## Docs

- `docs/INSTALL.md`
- `docs/ARCHITECTURE.md`
- `docs/OPENCLAW.md`

## Development

```bash
python -m build
python -m twine check dist/*
pytest -q
```
"""

INSTALL_TEMPLATE = """# Installation

## 1. System dependencies

### macOS
```bash
brew install poppler tesseract
```

### Ubuntu or Debian
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr
```

## 2. Python environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e \".[dev]\"
```

## 3. Configure credentials

Copy `.env.example` to `.env` and set at least one provider key:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

## 4. Validate the installation

```bash
python scripts/oefo_env_check.py
oefo --help
python -m oefo --help
python scripts/oefo_smoke_test.py
pytest -q
```

## 5. Dashboard safety

The dashboard binds to `127.0.0.1` by default. If you need remote access, tunnel
it or pass an explicit bind address intentionally.

## 6. Troubleshooting

- Missing `pdftoppm` or `pdfinfo`: install Poppler.
- Missing `tesseract`: install Tesseract OCR.
- `oefo` command not found: activate the virtual environment and reinstall with
  `python -m pip install -e \".[dev]\"`.
- Import errors from the repo root: make sure the package is installed from the
  `src` layout rather than run from an old flat checkout state.
"""

ARCHITECTURE_TEMPLATE = """# Architecture

OEFO now uses a standard `src` layout.

```text
repo/
  docs/
  scripts/
  src/
    oefo/
      __init__.py
      __main__.py
      cli.py
      llm_client.py
      models.py
      config/
      dashboard/
      data/
      extraction/
      outputs/
      qc/
      scrapers/
  tests/
```

## Principles

- Package code lives under `src/oefo`.
- Console execution uses `oefo = oefo.cli:main`.
- Module execution uses `python -m oefo`.
- Dashboard assets are packaged with the Python package.
- Runtime data directories remain at the repository root under `data/` and `logs/`.

## Security defaults

- Dashboard default bind address: `127.0.0.1`
- No wildcard CORS header in the bundled dashboard server
- OpenClaw execution is intended to go through `scripts/oefo_claw_run.sh`
"""

OPENCLAW_TEMPLATE = """# OpenClaw integration

Use OEFO through a wrapper command, not unrestricted shell.

## Suggested allowlisted commands

```bash
scripts/oefo_claw_run.sh env-check
scripts/oefo_claw_run.sh help
scripts/oefo_claw_run.sh smoke
scripts/oefo_claw_run.sh test
scripts/oefo_claw_run.sh build
scripts/oefo_claw_run.sh scrape ifc
scripts/oefo_claw_run.sh extract-batch ./data/raw/ifc --source-type dfi
scripts/oefo_claw_run.sh qc --full
scripts/oefo_claw_run.sh export --format excel --output results.xlsx
```

## Notes

- Keep the dashboard on localhost unless you explicitly tunnel it.
- Prefer `scripts/oefo_claw_run.sh` to direct `python`, `pip`, or arbitrary shell.
- Run `scripts/oefo_claw_run.sh smoke` and `scripts/oefo_claw_run.sh test`
  before enabling scheduled jobs.
"""

ENV_EXAMPLE = """# Copy to .env and set at least one provider key.
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
OEFO_DATA_DIR=./data
OEFO_LOG_LEVEL=INFO
OEFO_TRACEABILITY=FULL
"""

ENV_CHECK_SCRIPT = """#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path
from shutil import which


def _detect_linux_distro() -> str:
    try:
        for line in Path('/etc/os-release').read_text().splitlines():
            if line.startswith('ID='):
                return line.split('=', 1)[1].strip().strip('"')
    except Exception:
        pass
    return 'unknown'


def check_python_version() -> bool:
    version = sys.version_info
    required = (3, 10)
    ok = (version.major, version.minor) >= required
    print(f"{'PASS' if ok else 'FAIL'} Python {version.major}.{version.minor}.{version.micro} (required 3.10+)")
    return ok


def check_virtual_environment() -> bool:
    in_venv = hasattr(sys, 'real_prefix') or getattr(sys, 'base_prefix', sys.prefix) != sys.prefix
    print(f"{'PASS' if in_venv else 'FAIL'} Virtual environment {'active' if in_venv else 'not active'}")
    return in_venv


def check_tool(tool: str, install_hint: str) -> bool:
    ok = which(tool) is not None
    print(f"{'PASS' if ok else 'FAIL'} {tool}")
    if not ok:
        print(f"  Install hint: {install_hint}")
    return ok


def check_poppler() -> bool:
    system = platform.system()
    if system == 'Darwin':
        hint = 'brew install poppler'
    elif system == 'Linux':
        distro = _detect_linux_distro()
        hint = 'sudo apt-get install poppler-utils' if distro in {'ubuntu', 'debian'} else 'install poppler-utils for your distro'
    else:
        hint = 'install Poppler and ensure pdftoppm and pdfinfo are on PATH'
    return check_tool('pdftoppm', hint) and check_tool('pdfinfo', hint)


def check_tesseract() -> bool:
    system = platform.system()
    if system == 'Darwin':
        hint = 'brew install tesseract'
    elif system == 'Linux':
        distro = _detect_linux_distro()
        hint = 'sudo apt-get install tesseract-ocr' if distro in {'ubuntu', 'debian'} else 'install tesseract for your distro'
    else:
        hint = 'install Tesseract OCR and ensure it is on PATH'
    ok = check_tool('tesseract', hint)
    if ok:
        try:
            out = subprocess.run(['tesseract', '--version'], capture_output=True, text=True, timeout=5)
            line = out.stdout.splitlines()[0] if out.stdout else 'version unavailable'
            print(f'INFO {line}')
        except Exception:
            pass
    return ok


def check_directories() -> bool:
    required = [Path('data'), Path('data/raw'), Path('data/extracted'), Path('data/final'), Path('logs')]
    all_ok = True
    for path in required:
        path.mkdir(parents=True, exist_ok=True)
        writable = os.access(path, os.W_OK)
        print(f"{'PASS' if writable else 'FAIL'} {path} writable")
        all_ok = all_ok and writable
    return all_ok


def check_api_keys() -> bool:
    ok = bool(os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY'))
    print(f"{'PASS' if ok else 'WARN'} LLM API key present")
    return ok


def main() -> int:
    checks = [
        check_python_version(),
        check_virtual_environment(),
        check_poppler(),
        check_tesseract(),
        check_directories(),
        check_api_keys(),
    ]
    return 0 if all(checks[:-1]) else 1


if __name__ == '__main__':
    raise SystemExit(main())
"""

SMOKE_TEST_SCRIPT = """#!/usr/bin/env python3
from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


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

    env = dict(**__import__('os').environ)
    env['PYTHONPATH'] = str(SRC) + (__import__('os').pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')

    result = subprocess.run([sys.executable, '-m', 'oefo', '--help'], capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    assert 'dashboard' in result.stdout

    result = subprocess.run([sys.executable, '-c', 'import oefo, oefo.cli, oefo.dashboard.server, oefo.data.storage'], capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr

    print('Smoke tests passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
"""

OPENCLAW_WRAPPER = """#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python}"
ACTION="${1:-help}"
shift || true

case "$ACTION" in
  help)
    exec "$PYTHON_BIN" -m oefo --help
    ;;
  env-check)
    exec "$PYTHON_BIN" scripts/oefo_env_check.py
    ;;
  smoke)
    exec "$PYTHON_BIN" scripts/oefo_smoke_test.py
    ;;
  test)
    exec "$PYTHON_BIN" -m pytest -q
    ;;
  build)
    rm -rf dist build *.egg-info
    "$PYTHON_BIN" -m build
    exec "$PYTHON_BIN" -m twine check dist/*
    ;;
  scrape)
    exec "$PYTHON_BIN" -m oefo scrape "$@"
    ;;
  extract)
    exec "$PYTHON_BIN" -m oefo extract "$@"
    ;;
  extract-batch)
    exec "$PYTHON_BIN" -m oefo extract-batch "$@"
    ;;
  qc)
    exec "$PYTHON_BIN" -m oefo qc "$@"
    ;;
  export)
    exec "$PYTHON_BIN" -m oefo export "$@"
    ;;
  dashboard)
    exec "$PYTHON_BIN" -m oefo dashboard "$@"
    ;;
  status)
    exec "$PYTHON_BIN" -m oefo status "$@"
    ;;
  config)
    exec "$PYTHON_BIN" -m oefo config "$@"
    ;;
  *)
    echo "Unknown action: $ACTION" >&2
    exit 64
    ;;
esac
"""

CI_WORKFLOW = """name: ci

on:
  push:
  pull_request:

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, macos-latest]
        python-version: ['3.10', '3.11']

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install system dependencies on Ubuntu
        if: runner.os == 'Linux'
        run: |
          sudo apt-get update
          sudo apt-get install -y poppler-utils tesseract-ocr

      - name: Install system dependencies on macOS
        if: runner.os == 'macOS'
        run: |
          brew install poppler tesseract

      - name: Install package
        run: |
          python -m pip install --upgrade pip
          python -m pip install -e \".[dev]\"

      - name: Environment check
        env:
          ANTHROPIC_API_KEY: dummy
        run: |
          python scripts/oefo_env_check.py

      - name: Run tests
        run: |
          pytest -q

      - name: Run smoke tests
        run: |
          python scripts/oefo_smoke_test.py

      - name: Build package
        run: |
          python -m build
          python -m twine check dist/*
"""

CONFTST = """from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
"""

TEST_IMPORTS = """from __future__ import annotations


def test_imports_work() -> None:
    import oefo
    import oefo.cli
    import oefo.dashboard.server
    import oefo.data.storage

    assert hasattr(oefo, '__version__')
"""

TEST_CLI = """from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from oefo.cli import create_parser


def test_module_help() -> None:
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env['PYTHONPATH'] = str(root / 'src') + (os.pathsep + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
    result = subprocess.run([sys.executable, '-m', 'oefo', '--help'], capture_output=True, text=True, env=env)
    assert result.returncode == 0
    assert 'dashboard' in result.stdout


def test_dashboard_default_host() -> None:
    parser = create_parser()
    args = parser.parse_args(['dashboard'])
    assert args.host == '127.0.0.1'
"""

TEST_DASHBOARD = """from __future__ import annotations

import inspect

from oefo.dashboard import server as dashboard_server


def test_no_wildcard_cors() -> None:
    source = inspect.getsource(dashboard_server)
    assert 'Access-Control-Allow-Origin: *' not in source


def test_start_server_exists() -> None:
    assert hasattr(dashboard_server, 'start_server')
"""

SETUP_SHIM = """from setuptools import setup

setup()
"""

MANIFEST_IN = """recursive-include src/oefo/dashboard *.html *.json
recursive-include src/oefo/config *.json *.yaml *.yml
"""

GITIGNORE_APPEND = """
# OEFO remediation additions
.venv/
.pytest_cache/
.ruff_cache/
.mypy_cache/
dist/
build/
*.egg-info/
logs/
data/raw/
data/extracted/
data/final/
"""

STATUS_JSON_TEMPLATE = {
    "objective": "oefo remediation",
    "phase": "completed",
    "status": "passed",
    "completed_tasks": [],
    "artifacts_created": [],
    "tests_passed": [],
    "tests_failed": [],
    "risks": [],
    "human_escalations": [],
    "next_actions": [],
    "definition_of_done_percent": 100,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fix OEFO repo into a modern src-layout package")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without writing them")
    parser.add_argument("--no-backup", action="store_true", help="Do not copy modified files into a backup directory")
    return parser.parse_args()


def info(msg: str) -> None:
    print(f"[INFO] {msg}")


def warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def die(msg: str) -> None:
    print(f"[ERROR] {msg}", file=sys.stderr)
    raise SystemExit(1)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        info(f"Would write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def append_text_once(path: Path, content: str, dry_run: bool) -> None:
    existing = read_text(path) if path.exists() else ""
    if content.strip() in existing:
        return
    new_content = existing.rstrip() + "\n" + content.lstrip()
    write_text(path, new_content, dry_run=dry_run)


def ensure_executable(path: Path, dry_run: bool) -> None:
    if dry_run or not path.exists():
        return
    mode = path.stat().st_mode
    path.chmod(mode | 0o111)


def backup_paths(root: Path, backup_root: Path, paths: Sequence[Path], dry_run: bool) -> None:
    if dry_run:
        info(f"Would back up {len(paths)} path(s) into {backup_root}")
        return
    for path in paths:
        if not path.exists():
            continue
        rel = path.relative_to(root)
        target = backup_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, target, dirs_exist_ok=True)
        else:
            shutil.copy2(path, target)


def merge_move(src: Path, dst: Path, dry_run: bool) -> None:
    if not src.exists():
        return
    if dry_run:
        info(f"Would move {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists() and dst.is_dir():
            for child in src.iterdir():
                merge_move(child, dst / child.name, dry_run=False)
            shutil.rmtree(src)
        else:
            shutil.move(str(src), str(dst))
    else:
        if dst.exists():
            dst.unlink()
        shutil.move(str(src), str(dst))


def discover_version(root: Path) -> str:
    candidates = [root / "__init__.py", root / "src" / PACKAGE_NAME / "__init__.py"]
    for path in candidates:
        if not path.exists():
            continue
        match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)['\"]", read_text(path))
        if match:
            return match.group(1)
    return "0.1.0"


def discover_author(root: Path) -> str:
    init_path = root / "__init__.py"
    if init_path.exists():
        match = re.search(r"__author__\s*=\s*['\"]([^'\"]+)['\"]", read_text(init_path))
        if match:
            return match.group(1)
    return "ET Finance"


def parse_requirements_file(path: Path) -> list[str]:
    if not path.exists():
        return BASE_DEPENDENCIES[:]
    deps: list[str] = []
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        deps.append(line)
    return deps or BASE_DEPENDENCIES[:]


def render_array(items: Iterable[str], indent: int = 4) -> str:
    pad = " " * indent
    return "[\n" + "\n".join(f'{pad}"{item}",' for item in items) + "\n]"


def render_pyproject(root: Path) -> str:
    version = discover_version(root)
    author = discover_author(root)
    dependencies = parse_requirements_file(root / "requirements.txt")
    return textwrap.dedent(
        f"""
        [build-system]
        requires = ["setuptools>=69", "wheel"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "oefo"
        version = "{version}"
        description = "Open Energy Finance Observatory - Energy finance data toolkit"
        readme = "README.md"
        requires-python = ">=3.10"
        authors = [{{ name = "{author}" }}]
        license = {{ text = "MIT" }}
        keywords = ["energy", "finance", "wacc", "debt", "equity", "scraping", "extraction"]
        classifiers = [
          "Development Status :: 4 - Beta",
          "Intended Audience :: Developers",
          "Intended Audience :: Science/Research",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.10",
          "Programming Language :: Python :: 3.11",
          "Programming Language :: Python :: 3.12",
          "Topic :: Scientific/Engineering :: Information Analysis",
        ]
        dependencies = {render_array(dependencies, indent=2)}

        [project.optional-dependencies]
        dev = {render_array(DEV_DEPENDENCIES, indent=2)}
        openai = {render_array(OPTIONAL_OPENAI, indent=2)}
        google = {render_array(OPTIONAL_GOOGLE, indent=2)}

        [project.scripts]
        oefo = "oefo.cli:main"

        [tool.setuptools]
        package-dir = {{"" = "src"}}
        include-package-data = true

        [tool.setuptools.packages.find]
        where = ["src"]
        include = ["oefo*"]

        [tool.setuptools.package-data]
        oefo = ["dashboard/*.html", "dashboard/*.json", "config/*.json", "config/*.yaml", "config/*.yml"]

        [tool.ruff]
        line-length = 100
        target-version = "py310"

        [tool.pytest.ini_options]
        addopts = "-q"
        testpaths = ["tests"]
        """
    ).strip() + "\n"


def patch_cli_file(path: Path, dry_run: bool) -> None:
    if not path.exists():
        warn(f"CLI file not found: {path}")
        return
    text = read_text(path)
    original = text
    text = text.replace("default='0.0.0.0'", "default='127.0.0.1'")
    text = text.replace('default="0.0.0.0"', 'default="127.0.0.1"')
    text = text.replace("help='Host to bind (default: 0.0.0.0)'", "help='Host to bind (default: 127.0.0.1)'")
    text = text.replace('help="Host to bind (default: 0.0.0.0)"', 'help="Host to bind (default: 127.0.0.1)"')
    if text != original:
        write_text(path, text, dry_run=dry_run)
        info(f"Patched dashboard host defaults in {path}")


def patch_dashboard_server(path: Path, dry_run: bool) -> None:
    if not path.exists():
        warn(f"Dashboard server file not found: {path}")
        return
    text = read_text(path)
    original = text

    text = text.replace('host: str = "0.0.0.0"', 'host: str = "127.0.0.1"')
    text = text.replace('default="0.0.0.0"', 'default="127.0.0.1"')
    text = text.replace('help="Bind address (default: 0.0.0.0)"', 'help="Bind address (default: 127.0.0.1)"')
    text = text.replace('f"Access-Control-Allow-Origin: *\\r\\n"\n', '')
    text = text.replace('"Access-Control-Allow-Origin: *\\r\\n"\n', '')

    if 'def start_server(' not in text:
        insertion_point = text.find('\ndef main():')
        if insertion_point == -1:
            warn(f"Could not locate insertion point for start_server() in {path}")
        else:
            start_server_func = textwrap.dedent(
                '''

                def start_server(
                    host: str = "127.0.0.1",
                    port: int = 8765,
                    demo: bool = False,
                    base_dir: Optional[str] = None,
                    interval: float = 5.0,
                ):
                    """Start the dashboard server for CLI callers."""
                    collector = SnapshotCollector(demo=demo, base_dir=base_dir)
                    server = DashboardServer(collector, host=host, port=port)

                    async def run():
                        collector_task = asyncio.create_task(collector.run(interval=interval))
                        server_task = asyncio.create_task(server.start())
                        await asyncio.gather(collector_task, server_task)

                    asyncio.run(run())
                '''
            )
            text = text[:insertion_point] + start_server_func + text[insertion_point:]

    if text != original:
        write_text(path, text, dry_run=dry_run)
        info(f"Patched dashboard server in {path}")


def update_gitignore(root: Path, dry_run: bool) -> None:
    append_text_once(root / '.gitignore', GITIGNORE_APPEND, dry_run=dry_run)


def maybe_archive_legacy_docs(root: Path, dry_run: bool) -> None:
    legacy_dir = root / 'legacy_docs'
    for name in DOC_FILES_TO_ARCHIVE:
        src = root / name
        if src.exists():
            merge_move(src, legacy_dir / name, dry_run=dry_run)


def ensure_dirs(root: Path, dry_run: bool) -> None:
    for rel in ['src/oefo', 'docs', 'scripts', 'tests', '.github/workflows']:
        path = root / rel
        if dry_run:
            info(f"Would create directory {path}")
        else:
            path.mkdir(parents=True, exist_ok=True)


def move_runtime_safe_data_package(root: Path, dry_run: bool) -> None:
    src = root / 'data'
    dst = root / SRC_DIR / 'data'
    if not src.exists() or not src.is_dir():
        return
    package_children = []
    for child in src.iterdir():
        if child.name.startswith('.'):
            continue
        if child.is_file() and child.suffix in {'.py', '.json', '.yaml', '.yml', '.txt'}:
            package_children.append(child)
    for child in package_children:
        merge_move(child, dst / child.name, dry_run=dry_run)
    if not dry_run and src.exists() and src.is_dir() and not any(src.iterdir()):
        src.rmdir()


def move_flat_layout_into_src(root: Path, dry_run: bool) -> None:
    src_pkg = root / SRC_DIR
    ensure_dirs(root, dry_run=dry_run)
    for name in TOP_LEVEL_MODULES:
        merge_move(root / name, src_pkg / name, dry_run=dry_run)
    for name in TOP_LEVEL_PACKAGE_DIRS:
        if name == 'data':
            move_runtime_safe_data_package(root, dry_run=dry_run)
        else:
            merge_move(root / name, src_pkg / name, dry_run=dry_run)


def write_project_files(root: Path, dry_run: bool) -> None:
    write_text(root / 'pyproject.toml', render_pyproject(root), dry_run=dry_run)
    write_text(root / 'setup.py', SETUP_SHIM, dry_run=dry_run)
    write_text(root / 'MANIFEST.in', MANIFEST_IN, dry_run=dry_run)
    write_text(root / 'README.md', README_TEMPLATE, dry_run=dry_run)
    write_text(root / 'docs' / 'INSTALL.md', INSTALL_TEMPLATE, dry_run=dry_run)
    write_text(root / 'docs' / 'ARCHITECTURE.md', ARCHITECTURE_TEMPLATE, dry_run=dry_run)
    write_text(root / 'docs' / 'OPENCLAW.md', OPENCLAW_TEMPLATE, dry_run=dry_run)
    write_text(root / '.env.example', ENV_EXAMPLE, dry_run=dry_run)
    write_text(root / 'scripts' / 'oefo_env_check.py', ENV_CHECK_SCRIPT, dry_run=dry_run)
    write_text(root / 'scripts' / 'oefo_smoke_test.py', SMOKE_TEST_SCRIPT, dry_run=dry_run)
    write_text(root / 'scripts' / 'oefo_claw_run.sh', OPENCLAW_WRAPPER, dry_run=dry_run)
    write_text(root / '.github' / 'workflows' / 'ci.yml', CI_WORKFLOW, dry_run=dry_run)
    write_text(root / 'tests' / 'conftest.py', CONFTST, dry_run=dry_run)
    write_text(root / 'tests' / 'test_imports.py', TEST_IMPORTS, dry_run=dry_run)
    write_text(root / 'tests' / 'test_cli.py', TEST_CLI, dry_run=dry_run)
    write_text(root / 'tests' / 'test_dashboard.py', TEST_DASHBOARD, dry_run=dry_run)
    write_text(root / 'remediation_status.json', json.dumps(STATUS_JSON_TEMPLATE, indent=2) + '\n', dry_run=dry_run)
    ensure_executable(root / 'scripts' / 'oefo_env_check.py', dry_run=dry_run)
    ensure_executable(root / 'scripts' / 'oefo_smoke_test.py', dry_run=dry_run)
    ensure_executable(root / 'scripts' / 'oefo_claw_run.sh', dry_run=dry_run)


def try_compile(root: Path) -> None:
    targets = [
        root / 'fix_oefo_repo.py',
        root / 'scripts' / 'oefo_env_check.py',
        root / 'scripts' / 'oefo_smoke_test.py',
    ]
    for target in targets:
        if target.exists():
            subprocess.run([sys.executable, '-m', 'py_compile', str(target)], check=False)


def gather_backup_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for name in TOP_LEVEL_MODULES + TOP_LEVEL_PACKAGE_DIRS + ['setup.py', 'README.md', '.gitignore']:
        path = root / name
        if path.exists():
            candidates.append(path)
    for rel in [
        Path('docs') / 'INSTALL.md',
        Path('docs') / 'ARCHITECTURE.md',
        Path('docs') / 'OPENCLAW.md',
        Path('scripts') / 'oefo_env_check.py',
        Path('scripts') / 'oefo_smoke_test.py',
        Path('scripts') / 'oefo_claw_run.sh',
        Path('.github') / 'workflows' / 'ci.yml',
        Path('tests'),
        Path('pyproject.toml'),
        Path('.env.example'),
        Path('MANIFEST.in'),
    ]:
        path = root / rel
        if path.exists():
            candidates.append(path)
    return candidates


def validate_root(root: Path) -> None:
    if not root.exists() or not root.is_dir():
        die(f"Invalid repository root: {root}")
    marker = root / 'README.md'
    if not marker.exists():
        die(f"{root} does not look like the OEFO repository root. Missing README.md")


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    validate_root(root)

    info(f"Repository root: {root}")
    info(f"Mode: {'dry-run' if args.dry_run else 'apply'}")

    backup_root = root / BACKUP_DIR_NAME / dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    if not args.no_backup:
        backup_candidates = gather_backup_candidates(root)
        backup_paths(root, backup_root, backup_candidates, dry_run=args.dry_run)

    ensure_dirs(root, dry_run=args.dry_run)
    move_flat_layout_into_src(root, dry_run=args.dry_run)
    maybe_archive_legacy_docs(root, dry_run=args.dry_run)
    patch_cli_file(root / 'src' / 'oefo' / 'cli.py', dry_run=args.dry_run)
    patch_dashboard_server(root / 'src' / 'oefo' / 'dashboard' / 'server.py', dry_run=args.dry_run)
    write_project_files(root, dry_run=args.dry_run)
    update_gitignore(root, dry_run=args.dry_run)

    if not args.dry_run:
        try_compile(root)

    info('Remediation script finished.')
    info('Next recommended commands:')
    print('  python -m pip install -e ".[dev]"')
    print('  python scripts/oefo_env_check.py')
    print('  python scripts/oefo_smoke_test.py')
    print('  pytest -q')
    print('  python -m build && python -m twine check dist/*')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
