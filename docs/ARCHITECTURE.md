# Architecture

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
