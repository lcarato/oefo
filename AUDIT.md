# OEFO Repository Audit

Date: 2026-03-11

## Current tree

The active package is under `src/oefo/`. `pyproject.toml` is the authoritative
packaging file, and `setup.py` is a minimal compatibility shim (`setup()` only).
Top-level runtime helpers live in `scripts/`, tests live in `tests/`, and CI is
defined in `.github/workflows/ci.yml`.

No root-level shadow copies of `oefo/__init__.py`, `oefo/cli.py`, `oefo/models.py`,
or sibling package directories remain outside `src/oefo/`.

## Findings observed in this session

1. The checked-in `AUDIT.md` and `FINAL_VALIDATION.md` were stale. They described
   a flat-layout repository, old security defaults, and fully green validation
   results that did not match the actual tree or the commands run in this session.
2. Several generated docs under `docs/` still referenced old paths such as
   `data/storage.py`, absolute session-specific filesystem locations, and
   fabricated line counts. Those documents were not safe to treat as current.
3. `scripts/oefo_env_check.py` short-circuited its Poppler checks, so a missing
   `pdftoppm` prevented `pdfinfo` from being reported. It also skipped `.cache`
   in its writable-directory checks.
4. `scripts/oefo_smoke_test.py` and some tests were injecting `src/` onto
   `sys.path` or `PYTHONPATH`, which reduced confidence that validation was
   exercising the installed package state.
5. `oefo config --validate` only accepted `ANTHROPIC_API_KEY`, even though the
   rest of the project and docs support OpenAI keys and local-only Ollama use.

## Risks and blockers encountered

1. A clean editable install required network access so pip could resolve build
   dependencies during installation.
2. `python -m build` also required network access because build isolation creates
   a fresh temporary environment.
3. The macOS host initially lacked `pdftoppm`, `pdfinfo`, and `tesseract`, so
   `scripts/oefo_env_check.py` correctly failed until those host tools were
   installed.

## Remediation targets from this audit

1. Keep `src/oefo/` and `pyproject.toml` authoritative.
2. Make environment and config validation report the real supported provider set.
3. Ensure smoke tests and CLI tests validate the installed package path rather
   than forcing source-tree imports.
4. Rewrite stale documentation conservatively so file paths, commands, and
   validation claims match the current repository.
