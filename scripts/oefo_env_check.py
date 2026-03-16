#!/usr/bin/env python3
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
    if in_venv:
        print("PASS Virtual environment active")
    else:
        print("WARN Virtual environment not active (recommended for local development)")
    # Return True always — venv is recommended, not required
    return True


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
    pdftoppm_ok = check_tool('pdftoppm', hint)
    pdfinfo_ok = check_tool('pdfinfo', hint)
    return pdftoppm_ok and pdfinfo_ok


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
    required = [
        Path('data'),
        Path('data/raw'),
        Path('data/extracted'),
        Path('data/final'),
        Path('logs'),
        Path('.cache'),
    ]
    all_ok = True
    for path in required:
        path.mkdir(parents=True, exist_ok=True)
        writable = os.access(path, os.W_OK)
        print(f"{'PASS' if writable else 'FAIL'} {path} writable")
        all_ok = all_ok and writable
    return all_ok


def check_api_keys() -> bool:
    providers = []
    if os.environ.get('ANTHROPIC_API_KEY'):
        providers.append('anthropic')
    if os.environ.get('OPENAI_API_KEY'):
        providers.append('openai')

    if providers:
        print(f"PASS LLM API key present ({', '.join(providers)})")
        return True

    if os.environ.get('OEFO_LLM_PROVIDER', '').lower() == 'ollama':
        print('INFO No cloud API key present; OEFO_LLM_PROVIDER=ollama')
        return True

    print('WARN No cloud LLM API key present')
    return False


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
