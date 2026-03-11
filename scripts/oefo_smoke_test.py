#!/usr/bin/env python3
"""
OEFO Lightweight End-to-End Smoke Test

Verifies that all critical OEFO modules can be imported and basic
functionality works as expected.

Usage:
    python scripts/oefo_smoke_test.py

Exit codes:
    0 - All smoke tests passed
    1 - One or more tests failed
"""

import sys
import traceback


def test_import_oefo() -> tuple[bool, str]:
    """Test: import oefo"""
    try:
        import oefo
        return True, f"✓ import oefo (v{oefo.__version__})"
    except Exception as e:
        return False, f"✗ import oefo: {e}"


def test_import_cli() -> tuple[bool, str]:
    """Test: import oefo.cli"""
    try:
        import oefo.cli
        return True, "✓ import oefo.cli"
    except Exception as e:
        return False, f"✗ import oefo.cli: {e}"


def test_import_storage() -> tuple[bool, str]:
    """Test: import oefo.data.storage"""
    try:
        import oefo.data.storage
        return True, "✓ import oefo.data.storage"
    except Exception as e:
        return False, f"✗ import oefo.data.storage: {e}"


def test_import_dashboard() -> tuple[bool, str]:
    """Test: import oefo.dashboard.server"""
    try:
        import oefo.dashboard.server
        return True, "✓ import oefo.dashboard.server"
    except Exception as e:
        return False, f"✗ import oefo.dashboard.server: {e}"


def test_import_models() -> tuple[bool, str]:
    """Test: import oefo.models"""
    try:
        import oefo.models
        return True, "✓ import oefo.models"
    except Exception as e:
        return False, f"✗ import oefo.models: {e}"


def test_create_parser() -> tuple[bool, str]:
    """Test: oefo.cli.create_parser() returns ArgumentParser"""
    try:
        import argparse
        from oefo.cli import create_parser

        parser = create_parser()
        if isinstance(parser, argparse.ArgumentParser):
            return True, "✓ create_parser() returns ArgumentParser"
        else:
            return False, f"✗ create_parser() returned {type(parser)}, expected ArgumentParser"
    except Exception as e:
        return False, f"✗ create_parser(): {e}"


def test_parser_help() -> tuple[bool, str]:
    """Test: parser.parse_args(['--help']) (expect SystemExit)"""
    try:
        from oefo.cli import create_parser

        parser = create_parser()
        try:
            parser.parse_args(['--help'])
            return False, "✗ parse_args(['--help']) did not raise SystemExit"
        except SystemExit as e:
            if e.code == 0:
                return True, "✓ parse_args(['--help']) raised SystemExit(0)"
            else:
                return False, f"✗ parse_args(['--help']) raised SystemExit({e.code})"
    except Exception as e:
        return False, f"✗ parser --help test: {e}"


def test_parser_version() -> tuple[bool, str]:
    """Test: parser.parse_args(['--version']) (expect SystemExit)"""
    try:
        from oefo.cli import create_parser

        parser = create_parser()
        try:
            parser.parse_args(['--version'])
            return False, "✗ parse_args(['--version']) did not raise SystemExit"
        except SystemExit as e:
            if e.code == 0:
                return True, "✓ parse_args(['--version']) raised SystemExit(0)"
            else:
                return False, f"✗ parse_args(['--version']) raised SystemExit({e.code})"
    except Exception as e:
        return False, f"✗ parser --version test: {e}"


# ============================================================================
# Main
# ============================================================================

def main() -> int:
    """Run all smoke tests"""
    print("\n" + "=" * 70)
    print("OEFO Smoke Test Suite")
    print("=" * 70 + "\n")

    tests = [
        ("Import oefo", test_import_oefo),
        ("Import oefo.cli", test_import_cli),
        ("Import oefo.data.storage", test_import_storage),
        ("Import oefo.dashboard.server", test_import_dashboard),
        ("Import oefo.models", test_import_models),
        ("Create CLI parser", test_create_parser),
        ("Parser --help", test_parser_help),
        ("Parser --version", test_parser_version),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            passed, message = test_func()
            results.append((passed, message))
            print(message)
        except Exception as e:
            msg = f"✗ {test_name}: {e}"
            print(msg)
            if "-v" in sys.argv or "--verbose" in sys.argv:
                traceback.print_exc()
            results.append((False, msg))

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    passed = sum(1 for p, _ in results if p)
    total = len(results)

    print(f"Tests passed: {passed}/{total}\n")

    if passed == total:
        print("✓ All smoke tests passed!")
        return 0
    else:
        print(f"✗ {total - passed} test(s) failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
