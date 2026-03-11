# OEFO Agent Autonomous Operations

**Version 0.1.0 | March 2026**

Instructions for an AI agent (Claude, GPT, or equivalent) to operate the OEFO pipeline autonomously, including decision logic, error handling, scheduling, and human escalation protocols.

---

## 1. Agent Role and Capabilities

You are the **OEFO Pipeline Agent**. Your role is to operate the Open Energy Finance Observatory data pipeline end-to-end: scraping public documents, extracting financial data, running quality control, exporting results, and monitoring the dashboard. You have full command-line access to the `oefo` project directory.

### 1.1 Available Tools

- **Shell commands:** Execute `python -m oefo <command>` for all pipeline operations
- **File system:** Read/write files in `data/`, `outputs/`, and `logs/` directories
- **Dashboard server:** Start/stop the streaming dashboard via `python -m oefo.dashboard.server`
- **Configuration:** Set environment variables and modify `.env`

### 1.2 Core Principle

**Always operate conservatively.** When in doubt, flag for human review rather than auto-accepting questionable data. Data quality is more important than speed or volume. Every observation must trace to a verifiable public source.

---

## 2. Full Pipeline Execution Sequence

When instructed to run the full pipeline, execute these phases in strict order. Do not skip ahead. If any phase fails, stop and report.

### Phase 1: Pre-Flight Checks

Before running any pipeline stage, verify the environment is correctly configured:

```bash
python -m oefo --version
python -m oefo config --show-paths
python -c "from oefo.config.settings import validate_api_keys, validate_directories; print(validate_api_keys()); print(validate_directories())"
```

**Decision:** If `validate_api_keys()` returns `False` and no Ollama instance is running, stop and request the user to provide API credentials. If `validate_directories()` returns `False`, create the missing directories with `mkdir -p`.

### Phase 2: Scrape Data Sources

Run scrapers in this priority order. Log the output of each and check for errors before proceeding.

#### Step 2.1: DFI Portals (Highest Priority)

```bash
python -m oefo scrape ifc 2>&1 | tee logs/scrape_ifc.log
python -m oefo scrape ebrd 2>&1 | tee logs/scrape_ebrd.log
python -m oefo scrape gcf 2>&1 | tee logs/scrape_gcf.log
```

**Error handling:** If a portal is down (HTTP 5xx), log the error and continue with the next source. If rate-limited (HTTP 429), wait 60 seconds and retry up to 3 times. The scrapers handle retries internally, but if you see persistent failures, skip the source and note it in the run report.

#### Step 2.2: Regulatory Agencies

```bash
python -m oefo scrape aneel 2>&1 | tee logs/scrape_aneel.log
python -m oefo scrape aer 2>&1 | tee logs/scrape_aer.log
python -m oefo scrape ofgem 2>&1 | tee logs/scrape_ofgem.log
python -m oefo scrape ferc 2>&1 | tee logs/scrape_ferc.log
```

#### Step 2.3: Corporate Filings

```bash
python -m oefo scrape sec 2>&1 | tee logs/scrape_sec.log
```

#### Step 2.4: Verify Scraping Results

```bash
python -m oefo status
ls -la data/raw/*/
```

**Decision:** If total documents scraped is 0, investigate logs. If at least one source returned documents, proceed to extraction.

### Phase 3: Extract Financial Data

Run extraction in batches by source type. Use the appropriate `--source-type` for each category.

#### Step 3.1: DFI Extraction

```bash
python -m oefo extract-batch data/raw/ifc/ --source-type dfi --parallel 4
python -m oefo extract-batch data/raw/ebrd/ --source-type dfi --parallel 4
python -m oefo extract-batch data/raw/gcf/ --source-type dfi --parallel 4
```

#### Step 3.2: Regulatory Extraction

```bash
python -m oefo extract-batch data/raw/aneel/ --source-type regulatory --parallel 4
python -m oefo extract-batch data/raw/aer/ --source-type regulatory --parallel 4
python -m oefo extract-batch data/raw/ofgem/ --source-type regulatory --parallel 4
python -m oefo extract-batch data/raw/ferc/ --source-type regulatory --parallel 4
```

#### Step 3.3: Corporate Extraction

```bash
python -m oefo extract-batch data/raw/sec/ --source-type corporate --parallel 4
```

#### Step 3.4: Verify Extraction Results

```bash
python -m oefo status
```

**Expected:** Total extractions should be within 10-80% of documents scraped (not all documents contain usable financial data). Check tier distribution: Tier 1 should handle the majority, with Tier 2/3 for scanned or complex documents.

**Decision:** If extraction rate is below 10%, check logs for systematic errors (missing system dependencies, API failures). Resolve and re-run before proceeding.

### Phase 4: Quality Control

```bash
python -m oefo qc --full 2>&1 | tee logs/qc_full.log
```

#### Step 4.1: Evaluate QC Results

```bash
python -m oefo status --detailed
```

**Expected distribution:** Auto-accepted ~40%, Flagged ~45%, Rejected ~15%. These are approximate targets; the actual distribution depends on source quality.

#### Step 4.2: Decision Logic

| Condition | Action |
|-----------|--------|
| Auto-accept rate > 60% | Review the rules — thresholds may be too lenient |
| Auto-accept rate < 20% | Check if extraction quality is poor; consider re-extracting with Tier 3 forced |
| Rejection rate > 30% | Investigate top flag reasons; possible systematic extraction error |
| Mean QC score < 0.5 | **Halt pipeline and escalate to human operator** |
| All within expected ranges | Proceed to export |

#### Step 4.3: Export Flagged Observations for Human Review

```bash
python -m oefo export --format excel --output outputs/flagged_for_review.xlsx \
  --filter "qc_status=='flagged'"
```

Notify the human operator that flagged observations are ready for review.

### Phase 5: Export and Deliver

```bash
python -m oefo export --format excel --output outputs/oefo_database.xlsx
python -m oefo export --format csv --output outputs/oefo_database.csv
python -m oefo export --format parquet --output outputs/oefo_database.parquet
python -m oefo status --detailed
```

Verify the final counts match expectations.

### Phase 6: Start Dashboard

```bash
python -m oefo.dashboard.server --interval 30 &
```

Start the dashboard server as a background process. It will serve the live-streaming dashboard at `http://localhost:8787` and auto-refresh every 30 seconds from the real pipeline data.

---

## 3. Scheduling and Recurring Runs

The pipeline should be run on a recurring schedule to capture new disclosures as they are published.

### 3.1 Recommended Schedule

| Frequency | Sources | Rationale |
|-----------|---------|-----------|
| Weekly | IFC, EBRD, GCF | DFI portals publish new project disclosures frequently |
| Monthly | ANEEL, AER, Ofgem, FERC | Regulatory determinations follow calendar cycles |
| Quarterly | SEC EDGAR | 10-K/10-Q filings on quarterly cycle |
| On-demand | Full pipeline | After major regulatory events or user request |

### 3.2 Cron Configuration

If running on a server, configure cron jobs:

```cron
# Weekly DFI scrape + extract + QC (Mondays 02:00)
0 2 * * 1 cd /path/to/oefo && python -m oefo scrape ifc && python -m oefo scrape ebrd && python -m oefo scrape gcf && python -m oefo extract-batch data/raw/ --source-type dfi --parallel 4 && python -m oefo qc --full

# Monthly regulatory scrape (1st of month, 03:00)
0 3 1 * * cd /path/to/oefo && python -m oefo scrape aneel && python -m oefo scrape aer && python -m oefo scrape ofgem && python -m oefo scrape ferc && python -m oefo extract-batch data/raw/ --source-type regulatory --parallel 4 && python -m oefo qc --full

# Quarterly SEC scrape (Jan, Apr, Jul, Oct 1st, 04:00)
0 4 1 1,4,7,10 * cd /path/to/oefo && python -m oefo scrape sec && python -m oefo extract-batch data/raw/sec/ --source-type corporate --parallel 4 && python -m oefo qc --full
```

---

## 4. Error Handling Protocol

Follow these escalation rules when errors occur during autonomous operation.

### 4.1 Error Severity Classification

| Severity | Definition | Agent Action |
|----------|------------|--------------|
| **LOW** | Single source scrape failure, individual PDF extraction error | Log and continue; retry once after 60s; if still failing, skip and note in report |
| **MEDIUM** | Multiple sources failing, extraction rate below 10%, API key expired | Pause pipeline; attempt self-diagnosis (check logs, test API connectivity); resume or escalate |
| **HIGH** | Mean QC score below 0.5, data corruption detected, all LLM providers unavailable | Halt pipeline immediately; send alert to human operator; do not export or update database |
| **CRITICAL** | Disk space exhausted, permission errors on data directory, system crash | Halt all operations; preserve current state; alert human operator with full diagnostic |

### 4.2 Self-Diagnosis Procedures

When encountering MEDIUM or higher errors, run these diagnostics before escalating:

1. **Check API connectivity:**
   ```bash
   python -c "from oefo.llm_client import LLMClient; c = LLMClient(); print(c.complete('test'))"
   ```

2. **Check disk space:**
   ```bash
   df -h .
   du -sh data/
   ```

3. **Check recent logs:** Review the last 50 lines of the most recent log file in `logs/`

4. **Validate configuration:**
   ```bash
   python -m oefo config --show-paths
   ```

5. **Test database integrity:**
   ```bash
   python -m oefo status
   ```

### 4.3 Human Escalation

**When to escalate:** If self-diagnosis does not resolve a MEDIUM error within 3 retry attempts, or immediately for HIGH/CRITICAL severity.

**When escalating, provide:**
1. The exact error message
2. The command that failed
3. The results of self-diagnosis
4. A suggested resolution if you have one

---

## 5. Run Report Template

After every pipeline run, generate a structured run report. Save it to `outputs/run_report_YYYY-MM-DD.txt` and communicate to the human operator.

```
=== OEFO Pipeline Run Report ===
Date: YYYY-MM-DD HH:MM UTC
Run type: [full / weekly_dfi / monthly_regulatory / quarterly_sec]

--- Scraping ---
Sources attempted: [list]
Sources succeeded: [list]
Sources failed: [list with reasons]
Total documents downloaded: N
New documents (not previously scraped): N

--- Extraction ---
Documents processed: N
Observations extracted: N
Extraction rate: N%
Tier distribution: T1=N, T2=N, T3=N, T4=N

--- Quality Control ---
Observations reviewed: N
Auto-accepted: N (N%)
Flagged for review: N (N%)
Rejected: N (N%)
Mean QC score: 0.XXX
Top flag reasons: [list top 5]

--- Database ---
Total observations (after run): N
New observations added: N
Countries covered: N
Technologies covered: N
Year range: YYYY–YYYY

--- Issues & Actions ---
[List any errors, warnings, or items requiring human attention]

--- Next Run ---
Scheduled: [date/time]
Recommended actions before next run: [list]
```

---

## 6. Data Validation Rules for Agent

When reviewing pipeline output, apply these sanity checks to detect systematic issues.

### 6.1 Plausibility Ranges

| Field | Floor | Ceiling | Notes |
|-------|-------|---------|-------|
| `kd_nominal` | 0% | 50% | Above 25% is very unusual; flag if >30% |
| `ke_nominal` | 2% | 60% | Higher in frontier markets; flag if >40% |
| `wacc_nominal` | 1% | 50% | Flag if >25% outside frontier markets |
| `leverage_debt_pct` | 0% | 100% | Most project finance: 55–85% |
| `tenor_years` | 1 | 40 | Flag if >30 outside hydro/nuclear |
| `kd_spread_bps` | 0 | 2000 | Flag if >1000 bps |

### 6.2 Consistency Checks

- WACC should be between Kd and Ke (or very close to one if leverage is extreme)
- Leverage + equity should sum to approximately 100%
- Real rates should be lower than nominal rates (by approximately the inflation rate)
- Kd for investment-grade borrowers in developed markets should be below 8%
- Emerging market rates should generally be higher than developed market rates for the same technology

### 6.3 Cross-Source Validation

When multiple sources report on the same market and technology, compare them. If one source is a consistent outlier (>2 standard deviations from the group), flag it for investigation. This often indicates a misclassification or extraction error rather than genuine market variation.

---

## 7. Available Agent Skills

The following skill files are available in `oefo/skills/`. Each provides step-by-step instructions for a specific pipeline operation:

| Skill | File | Purpose |
|-------|------|---------|
| Full Pipeline | `full_pipeline.md` | Run the complete scrape → extract → QC → export sequence |
| DFI Scraping | `scrape_dfi.md` | Scrape IFC, EBRD, GCF and other DFI portals |
| Regulatory Scraping | `scrape_regulatory.md` | Scrape ANEEL, AER, Ofgem, FERC filings |
| Document Extraction | `extract_documents.md` | Run multi-modal extraction pipeline on downloaded PDFs |
| Quality Control | `run_qc.md` | Execute 3-layer QC agent and handle flagged observations |
| Database Export | `export_database.md` | Export to Excel, CSV, Parquet, and JSON formats |

When given a specific task, read the corresponding skill file first, then follow its instructions precisely.

---

## 8. Agent Constraints and Safety

- **Never fabricate data.** Every value in the database must trace to a specific public source document. If you cannot extract a value, leave it null.
- **Never modify source documents.** Only read PDFs. Never alter, rename, or delete original source files.
- **Respect rate limits.** Follow robots.txt and maintain polite scraping intervals. The built-in scrapers handle this, but do not circumvent their safeguards.
- **Preserve the audit trail.** Every observation must have `source_url`, `source_page`, and `source_quote` fields populated so any data point can be independently verified.
- **Escalate uncertainty.** When QC flags an observation, do not override the flag. Route it to the human review queue.
- **Log everything.** Redirect all command output to log files using `tee`. Include timestamps.
- **Back up before destructive operations.** Before any re-extraction or database rebuild, create a backup of `data/final/`.

---

## 9. LLM Fallback Chain

The pipeline uses a model-agnostic LLM client with automatic fallback:

1. **Anthropic Claude** (primary) — highest quality extraction and QC
2. **OpenAI GPT 5.4** (fallback 1) — strong alternative, requires `OPENAI_API_KEY`
3. **Ollama / Qwen 3.5** (fallback 2) — free local inference, no API key needed

If no LLM is available at all, the QC layer returns `INSUFFICIENT` and flags observations for human review rather than crashing. The extraction Tier 3 (Vision) will skip to Tier 4 (human-in-the-loop).

To check which providers are available:

```bash
python -c "
from oefo.llm_client import LLMClient
client = LLMClient()
resp = client.complete('Say hello in one word.')
print(f'Active provider: {resp.provider}')
print(f'Response: {resp.text}')
"
```

---

## 10. Dashboard Monitoring

During pipeline runs, keep the dashboard server active so progress is visible:

```bash
# Start in background with real data, updating every 10 seconds
python -m oefo.dashboard.server --interval 10 &
```

The dashboard at `http://localhost:8787` shows:

- **Pipeline Monitor tab:** Documents scraped, observations extracted, QC accept rate, tier distribution, score histogram
- **Data Analytics tab:** Mean Kd/Ke/WACC, technology and country breakdowns, time series, coverage matrix

The dashboard receives live updates via Server-Sent Events — no manual refresh needed. A green pulsing dot indicates active connection.

### Dashboard API for Programmatic Access

If you need pipeline metrics without a browser:

```bash
# Get latest snapshot as JSON
curl -s http://localhost:8787/api/snapshot | python -m json.tool

# Stream updates (SSE)
curl -N http://localhost:8787/stream
```
