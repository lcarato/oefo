# OpenClaw integration

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
