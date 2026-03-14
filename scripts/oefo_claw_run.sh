#!/usr/bin/env bash
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
