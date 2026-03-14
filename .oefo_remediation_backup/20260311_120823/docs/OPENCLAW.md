# OpenClaw Integration

This document describes how to integrate OEFO with OpenClaw for autonomous scheduled operations. OpenClaw is an agent orchestration system that enables OEFO to run on fixed schedules, validate results, and escalate issues to human operators as needed.

## Overview

OpenClaw executes OEFO commands through a **wrapper-based execution model**. Instead of directly calling Python functions, OpenClaw invokes wrapper scripts that:

1. Validate the environment (API keys, system dependencies, disk space)
2. Execute the OEFO command
3. Capture output and exit codes
4. Report back to OpenClaw with detailed status
5. Trigger escalation protocols if needed

This layer of indirection provides:
- **Safety:** Commands are validated before execution
- **Auditability:** Every operation is logged with timing and outcomes
- **Reliability:** Failed operations can be retried with exponential backoff
- **Transparency:** Humans always know what OpenClaw has done

## Wrapper Commands

OpenClaw has access to the following wrapper commands, defined in `scripts/oefo_claw_run.sh`:

### `oefo_scrape <source> [--limit N]`

Scrape documents from a source (ifc, ebrd, gcf, sec, aneel, aer, ofgem, ferc).

**Execution:**
```bash
scripts/oefo_claw_run.sh scrape ifc --limit 50
```

**Safety Checks:**
- Validates source name against known scrapers
- Checks API credentials (if required by source)
- Confirms disk space available (minimum 500MB)
- Verifies network connectivity

**Output:**
- List of downloaded files with checksums
- Document count and metadata summary
- Any warnings or recoverable errors

**Escalation Triggers:**
- Network timeout after 3 retries → ESCALATE
- Invalid credentials → ESCALATE
- Disk full → ESCALATE
- Source website down → WARN (non-blocking)

---

### `oefo_extract <input_dir> [--source-type TYPE] [--limit N]`

Extract financing observations from a directory of PDFs.

**Execution:**
```bash
scripts/oefo_claw_run.sh extract ./data/raw/ifc --source-type dfi --limit 100
```

**Safety Checks:**
- Validates input directory exists and is readable
- Confirms system dependencies installed (poppler, tesseract)
- Checks LLM provider connectivity with test call
- Validates available memory (minimum 2GB free)

**Output:**
- Number of observations extracted
- Extraction method distribution (Tier 1 text, Tier 2 OCR, Tier 3 vision)
- Average confidence scores by tier
- List of files requiring manual review

**Escalation Triggers:**
- LLM provider unreachable → ESCALATE (blocks extraction)
- Insufficient memory → ESCALATE
- PDF corruption (>5% of batch) → WARN (non-blocking)
- >10% of batch in Tier 3 → WARN (high cost)

---

### `oefo_qc [--full|--rules-only]`

Run quality control validation on extracted observations.

**Execution:**
```bash
scripts/oefo_claw_run.sh qc --full
```

**Safety Checks:**
- Validates observation database exists and is readable
- Checks LLM provider (needed for Layer 3 validation if `--full`)
- Ensures write permissions to database for updating QC status

**Output:**
- Total observations processed
- Pass/Flag/Fail distribution
- Flagged observations requiring manual review (with reasoning)
- Statistical summary (mean/median/std of key metrics)

**Escalation Triggers:**
- >5% of observations flagged → REVIEW (human decision required)
- >2% of observations failed validation → ESCALATE
- QC database corruption → ESCALATE

---

### `oefo_export [--format FORMAT] [--output PATH]`

Export validated observations to a desired output format.

**Execution:**
```bash
scripts/oefo_claw_run.sh export --format excel --output results.xlsx
```

**Safety Checks:**
- Validates output directory is writable
- Checks disk space for output file (minimum 2x estimated size)
- Confirms all exported observations have PASS or FLAG status (not FAIL)

**Output:**
- Output file path
- File size and checksum (SHA256)
- Record count exported
- Format-specific statistics (sheet count in Excel, etc.)

**Escalation Triggers:**
- Output directory not writable → ESCALATE
- Insufficient disk space → ESCALATE
- Output file already exists → WARN (file backed up with timestamp)

---

### `oefo_env_check`

Validate OEFO environment without executing pipeline.

**Execution:**
```bash
scripts/oefo_claw_run.sh env_check
```

**Checks:**
- Python version (3.10+)
- System dependencies (poppler, tesseract, etc.)
- Python package dependencies
- LLM provider connectivity
- Directory permissions
- API key validity (test call to provider if configured)

**Output:**
- Pass/Fail summary for each check
- Detailed error messages for any failures
- Recommendations for fixing issues

**Escalation Triggers:**
- Any critical check fails → ESCALATE (blocks all operations)
- Non-critical warnings → WARN (non-blocking)

---

### `oefo_status [--detailed]`

Report current pipeline status and statistics.

**Execution:**
```bash
scripts/oefo_claw_run.sh status --detailed
```

**Output:**
- Total observations in database
- Distribution by source, status, and date
- Last operation timestamp and duration
- Disk usage statistics
- Latest log entries (last 20 lines)

## Security Model

### What OpenClaw is Allowed to Do

✅ **Read-only operations:**
- Scrape publicly available documents from known sources
- Extract data from PDFs in designated directories
- Run QC validation on observation database
- Export observations in standard formats
- Check environment and status

✅ **Controlled mutations:**
- Update QC status on observations (preserves audit trail)
- Write export files to designated output directory
- Create timestamped backups before overwrites

### What OpenClaw is NOT Allowed to Do

❌ **Permanently destructive operations:**
- Delete observations from database
- Delete source PDF files
- Modify observation values (only QC status can be updated)
- Overwrite existing export files without backup

❌ **Privilege escalation:**
- Install new Python packages
- Modify system files
- Change file permissions
- Execute arbitrary scripts

❌ **External communications:**
- Send email or Slack notifications directly (humans must review first)
- Upload data to external cloud storage
- Modify source websites or APIs

### Validation Architecture

Every OpenClaw command goes through a validation pipeline:

```
OpenClaw Request
    ↓
┌─────────────────────────────────┐
│  1. COMMAND VALIDATION          │
│  ├─ Known command?              │
│  ├─ Valid parameters?           │
│  └─ Authorized operator?        │
└────────────┬────────────────────┘
             ↓
        ┌────────────┐
        │   PASS?    │
        └────┬───┬──┘
         Yes │   │ No
            │    └─→ DENY (return error)
            ↓
┌─────────────────────────────────┐
│  2. ENVIRONMENT VALIDATION      │
│  ├─ Dependencies installed?     │
│  ├─ API keys configured?        │
│  ├─ Disk space available?       │
│  └─ Network connectivity?       │
└────────────┬────────────────────┘
             ↓
        ┌────────────┐
        │   PASS?    │
        └────┬───┬──┘
         Yes │   │ No
            │    └─→ ESCALATE (human review)
            ↓
┌─────────────────────────────────┐
│  3. EXECUTION                   │
│  ├─ Run command with timeout    │
│  ├─ Capture output              │
│  └─ Log all activity            │
└────────────┬────────────────────┘
             ↓
        ┌────────────┐
        │ Success?   │
        └────┬───┬──┘
         Yes │   │ No
            │    └─→ ESCALATE (human review)
            ↓
        SUCCESS (logged)
```

## Cron Setup (Scheduled Operations)

OEFO can be run on a fixed schedule via OpenClaw cron jobs. To minimize cost and reduce manual overhead, cron jobs should only run **after validation has passed** (i.e., environment is green).

### Recommended Cron Schedule

```cron
# Daily environment validation (low cost, non-blocking)
0 0 * * * openclaw oefo_env_check

# Nightly scrape (after env validation passes)
0 2 * * * openclaw oefo_scrape ifc --limit 100
0 3 * * * openclaw oefo_scrape ebrd --limit 100
0 4 * * * openclaw oefo_scrape regulatory --limit 50

# Early morning extraction (after scrapes complete)
0 7 * * * openclaw oefo_extract ./data/raw --limit 500

# Mid-morning QC validation (critical, blocks export)
0 10 * * * openclaw oefo_qc --full

# Noon export (only if QC passes)
0 12 * * * openclaw oefo_export --format excel --output ./outputs/daily.xlsx
```

### Conditional Execution Logic

In OpenClaw's scheduler configuration, use exit codes to gate subsequent jobs:

```yaml
jobs:
  - name: env_check
    command: oefo_env_check
    schedule: "0 0 * * *"
    # Exit 0 = continue, Exit 1 = skip downstream

  - name: scrape_ifc
    command: oefo_scrape ifc --limit 100
    schedule: "0 2 * * *"
    dependsOn: env_check
    skipIfPrevious: FAILED

  - name: extract
    command: oefo_extract ./data/raw --limit 500
    schedule: "0 7 * * *"
    dependsOn: scrape_ifc
    skipIfPrevious: FAILED

  - name: qc
    command: oefo_qc --full
    schedule: "0 10 * * *"
    dependsOn: extract
    escalateIfFailed: true  # Human must approve before export

  - name: export
    command: oefo_export --format excel --output ./outputs/daily.xlsx
    schedule: "0 12 * * *"
    dependsOn: qc
    skipIfPrevious: ESCALATED
```

### Escalation Path

If any cron job fails or is escalated:

1. **Automatic Retry** — Failed jobs are retried once after 5 minutes
2. **Human Notification** — If retry fails, human operator is notified via email/Slack with:
   - Job name and timestamp
   - Error message and logs
   - Link to remediation guide
3. **Manual Intervention** — Operator investigates, fixes issue, and approves re-run
4. **Resumption** — Downstream jobs resume only after explicit human approval

## Approval Requirements for Mutating Operations

Certain operations require explicit human approval before OpenClaw can execute them:

### Tier 1: No Approval Needed (Read-Only)
- `oefo_scrape` — Downloads new documents (non-destructive)
- `oefo_extract` — Extracts from PDFs (non-destructive)
- `oefo_status` — Reads pipeline state
- `oefo_env_check` — Validates environment

### Tier 2: Automated with Escalation
- `oefo_qc --full` — May flag >5% of observations for review
  - Automatic escalation if threshold exceeded
  - Human reviews flagged observations before export
- `oefo_export` — Overwrites existing file if it exists
  - File is automatically backed up with timestamp
  - Operator is notified of backup location

### Tier 3: Manual Approval Required (if implemented)
- Database deletion or hard reset
- API key rotation or credential changes
- Configuration file modifications

To add a Tier 3 operation in the future, request human approval via:

```python
from oefo.config import escalation

escalation.request_human_approval(
    operation="delete_observations",
    reason="Removing corrupted batch from 2024-01-15",
    scope="1,247 observations matching: source=ebrd AND date<2024-01-15",
    impact="Irreversible; recommending 24-hour review period"
)
```

Human operator receives approval request in Slack/email with detailed reasoning, and explicitly confirms (`/approve <request_id>`) before operation proceeds.

## Monitoring and Alerting

### OpenClaw Dashboard Integration

OEFO integrates with OpenClaw's native dashboard:

```
openclaw.example.com/jobs/oefo
├── Job History
│   ├── Last 30 runs of each OEFO job
│   ├── Success/Failure/Escalation rates
│   └── Average runtime and cost per job
├── Current Status
│   ├── Running jobs (with progress bars)
│   ├── Scheduled next runs
│   └── Recent escalations
└── Logs & Alerts
    ├── Real-time log streaming
    ├── Error summaries and patterns
    └── Cost breakdown by job
```

### Alert Configuration

Configure OpenClaw to alert on:

| Condition | Severity | Action |
|-----------|----------|--------|
| Job fails (exit code >0) | HIGH | Email ops + Slack |
| >5% of QC flagged | MEDIUM | Email reviewer + Slack |
| >$10 LLM cost in single run | LOW | Slack #budget channel |
| Environment validation fails | HIGH | Email ops, block downstream |
| No successful run in 48 hours | MEDIUM | Email ops |
| Database corruption detected | CRITICAL | Email ops, page on-call |

## Cost Management

OEFO operations have variable costs depending on LLM usage:

| Operation | Cost per Unit | Notes |
|-----------|---------------|-------|
| Scrape | $0 | Web scraping only, no LLM |
| Extract Tier 1/2 | $0 | Text + OCR, no LLM |
| Extract Tier 3 | $0.01–0.05 per document | Vision API calls to Claude |
| QC Layer 1/2 | $0 | Rules + statistics, no LLM |
| QC Layer 3 | $0.001 per observation | LLM cross-validation |

To control costs in OpenClaw cron jobs:

1. **Limit extraction batches** — Set `--limit` flag on `oefo_extract`
   ```bash
   oefo_scrape ifc --limit 50  # Download max 50 new docs per night
   ```

2. **Run QC only on needed observations** — Use rules-only mode by default
   ```bash
   oefo_qc --rules-only  # Layer 1 only, $0 cost
   ```
   - Schedule full QC (with Layer 3) less frequently (e.g., weekly)

3. **Monitor cost via logs**
   ```bash
   tail -f logs/oefo_claw.log | grep "LLM_COST:"
   ```

4. **Set hard budget caps in OpenClaw**
   ```yaml
   budgetCaps:
     monthly: $500
     perJob:
       extract: $100
       qc_full: $50
   ```

## Troubleshooting OpenClaw Integration

### "Command not found: oefo"

Ensure OEFO is installed in OpenClaw's Python environment:

```bash
# On OpenClaw server
python -m pip install -e /path/to/oefo
which oefo  # Should show path to oefo executable
```

### "LLM provider unreachable"

Environment validation failed. Check:

```bash
python scripts/oefo_env_check.py
# Verify API key is set: env | grep ANTHROPIC_API_KEY
```

### "Disk space exceeded" during export

Check available space:

```bash
df -h ./outputs/
# If needed, move old exports to archive: mv ./outputs/2024-* ./archive/
```

### Job hangs or times out

Default timeout is 30 minutes. Check for:

- Network issues affecting PDF downloads
- LLM provider rate limiting (CloudFlare 429 errors)
- Stuck processes: `ps aux | grep oefo`

To increase timeout in OpenClaw config:

```yaml
jobs:
  - name: extract
    timeout: 60m  # Increase from 30m default
```

## Next Steps

1. Install OEFO following [Installation Guide](INSTALL.md)
2. Configure `.env` with API keys
3. Validate environment: `python scripts/oefo_env_check.py`
4. Test manual commands: `oefo scrape ifc --limit 5`
5. Register OEFO commands with OpenClaw (consult OpenClaw docs)
6. Set up cron schedule with staged dependencies
7. Configure alerts and monitoring

For questions or issues, contact the ET Finance team.

