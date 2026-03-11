#!/usr/bin/env python3
"""
OEFO Environment Preflight Validation Script

Checks all dependencies, system tools, and environment variables required
to run the OEFO data pipeline successfully.

Usage:
    python scripts/oefo_env_check.py

Exit codes:
    0 - All checks passed
    1 - One or more checks failed
"""

import sys
import os
import subprocess
import platform
from pathlib import Path
from shutil import which

# ============================================================================
# Check Functions
# ============================================================================

def check_python_version() -> bool:
    """Check Python version >= 3.10"""
    version = sys.version_info
    required = (3, 10)

    if version >= required:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro} (required >= 3.10)")
        return True
    else:
        print(f"✗ Python {version.major}.{version.minor}.{version.micro} (required >= 3.10)")
        print(f"  → Install Python 3.10 or later from https://www.python.org/downloads/")
        return False


def check_virtual_environment() -> bool:
    """Check if virtual environment is active"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )

    if in_venv:
        venv_path = sys.prefix
        print(f"✓ Virtual environment active: {venv_path}")
        return True
    else:
        print(f"✗ Virtual environment not active")
        print(f"  → Create and activate a virtual environment:")
        print(f"     python -m venv venv")
        print(f"     source venv/bin/activate  # on macOS/Linux")
        print(f"     venv\\Scripts\\activate    # on Windows")
        return False


def check_poppler() -> bool:
    """Check if Poppler tools (pdftoppm, pdfinfo) are installed"""
    tools = ['pdftoppm', 'pdfinfo']
    found = []
    missing = []

    for tool in tools:
        if which(tool):
            found.append(tool)
        else:
            missing.append(tool)

    if not missing:
        print(f"✓ Poppler installed (pdftoppm, pdfinfo found on PATH)")
        return True
    else:
        print(f"✗ Poppler missing: {', '.join(missing)}")
        system = platform.system()

        if system == "Darwin":  # macOS
            print(f"  → macOS (Intel): brew install poppler")
            print(f"  → macOS (Apple Silicon): arch -arm64 brew install poppler")
        elif system == "Linux":
            distro = _detect_linux_distro()
            if distro in ['ubuntu', 'debian']:
                print(f"  → Debian/Ubuntu: sudo apt-get install poppler-utils")
            elif distro in ['fedora', 'rhel', 'centos']:
                print(f"  → Fedora/RHEL: sudo dnf install poppler-utils")
            elif distro == 'arch':
                print(f"  → Arch: sudo pacman -S poppler")
            else:
                print(f"  → Visit: https://poppler.freedesktop.org/")
        elif system == "Windows":
            print(f"  → Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
            print(f"     or use: choco install poppler (if Chocolatey is installed)")

        return False


def check_tesseract() -> bool:
    """Check if Tesseract OCR is installed"""
    if which('tesseract'):
        # Get version
        try:
            result = subprocess.run(
                ['tesseract', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_line = result.stdout.split('\n')[0]
            print(f"✓ Tesseract installed: {version_line}")
            return True
        except Exception:
            print(f"✓ Tesseract found on PATH (version check failed)")
            return True
    else:
        print(f"✗ Tesseract OCR not installed")
        system = platform.system()

        if system == "Darwin":  # macOS
            print(f"  → macOS (Intel): brew install tesseract")
            print(f"  → macOS (Apple Silicon): arch -arm64 brew install tesseract")
        elif system == "Linux":
            distro = _detect_linux_distro()
            if distro in ['ubuntu', 'debian']:
                print(f"  → Debian/Ubuntu: sudo apt-get install tesseract-ocr")
            elif distro in ['fedora', 'rhel', 'centos']:
                print(f"  → Fedora/RHEL: sudo dnf install tesseract")
            elif distro == 'arch':
                print(f"  → Arch: sudo pacman -S tesseract")
            else:
                print(f"  → Visit: https://github.com/UB-Mannheim/tesseract/wiki")
        elif system == "Windows":
            print(f"  → Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
            print(f"     or use: choco install tesseract (if Chocolatey is installed)")

        return False


def check_directories() -> bool:
    """Check if required directories exist and are writable"""
    required_dirs = [
        Path('data'),
        Path('data/raw'),
        Path('data/extracted'),
        Path('data/final'),
        Path('logs'),
    ]

    all_ok = True
    for directory in required_dirs:
        if directory.exists():
            if os.access(directory, os.W_OK):
                print(f"✓ {directory} (exists, writable)")
            else:
                print(f"✗ {directory} (exists, NOT writable)")
                print(f"  → Fix permissions: chmod u+w {directory}")
                all_ok = False
        else:
            print(f"✗ {directory} (does not exist)")
            print(f"  → Create with: mkdir -p {directory}")
            all_ok = False

    return all_ok


def check_api_keys() -> bool:
    """Check if at least one LLM API key is set"""
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    openai_key = os.environ.get('OPENAI_API_KEY')

    keys_found = []
    if anthropic_key:
        keys_found.append('ANTHROPIC_API_KEY')
    if openai_key:
        keys_found.append('OPENAI_API_KEY')

    if keys_found:
        keys_str = ', '.join(keys_found)
        print(f"✓ LLM API key(s) configured: {keys_str}")
        return True
    else:
        print(f"✗ No LLM API keys configured")
        print(f"  → Set one of: ANTHROPIC_API_KEY or OPENAI_API_KEY")
        print(f"  → Add to .env file or environment:")
        print(f"     export ANTHROPIC_API_KEY='sk-ant-...'")
        print(f"     export OPENAI_API_KEY='sk-...'")
        return False


# ============================================================================
# Helper Functions
# ============================================================================

def _detect_linux_distro() -> str:
    """Detect Linux distribution"""
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('ID='):
                    return line.split('=')[1].strip().strip('"')
    except Exception:
        pass
    return 'unknown'


def main() -> int:
    """Run all preflight checks"""
    print("\n" + "=" * 70)
    print("OEFO Environment Preflight Check")
    print("=" * 70 + "\n")

    checks = [
        ("Python Version", check_python_version),
        ("Virtual Environment", check_virtual_environment),
        ("Poppler Tools", check_poppler),
        ("Tesseract OCR", check_tesseract),
        ("Required Directories", check_directories),
        ("LLM API Keys", check_api_keys),
    ]

    results = {}
    for name, check_func in checks:
        print(f"\n[{name}]")
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"✗ Check failed with error: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:.<50} {name}")

    print("=" * 70)
    print(f"Result: {passed}/{total} checks passed\n")

    if passed == total:
        print("✓ All checks passed! Ready to run OEFO.")
        return 0
    else:
        print(f"✗ {total - passed} check(s) failed. See above for remediation steps.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
