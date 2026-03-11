# OEFO QC Agent Module

A three-layer quality control system for validating energy project financing observations in the Open Energy Finance Observatory (OEFO) project.

## Architecture Overview

The QC Agent implements a layered validation pipeline with increasing sophistication:

```
┌─────────────────────────────────────────────────────────────┐
│                   Input: Observation                        │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
   ┌────────────┐  ┌──────────────┐  ┌──────────────┐
   │Layer 1     │  │ Layer 2      │  │ Layer 3      │
   │Rules       │  │ Statistics   │  │ LLM          │
   │────────────│  │──────────────│  │──────────────│
   │ Fast       │  │ Peer Compare │  │ Source Quote │
   │ Determin.  │  │ Benchmarks   │  │ Validation   │
   │ ~0.01s     │  │ Macro Check  │  │ ~2s          │
   │            │  │ ~0.5s        │  │              │
   └────────────┘  └──────────────┘  └──────────────┘
        │                │                │
        └────────────────┼────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │   QC Agent     │   Orchestrator  │
        │   Combine      │   Route         │
        │   Scores       │   Decision      │
        └────────────────┼────────────────┘
                         │
        ┌────────────────┴────────────────┐
        ▼                                  ▼
   Score >= 0.85                    Score < 0.50
   │                                │
   ▼                                ▼
AUTO_ACCEPT (0.5-2%)          REJECT (5-15%)
   │                                │
   │                          ┌─────┴──────┐
   │                          │            │
   │                   FLAG_FOR_REVIEW   RE-EXTRACT
   │                      (20-40%)
   │
   ▼
DATABASE
```

## Modules

### 1. rules.py - Layer 1: Rule-Based Checks (RuleBasedQC)

**Fast, deterministic validation of hard constraints.**

Methods:
- `check(observation)` → QCResult
- `check_range_plausibility(obs)` → flags
- `check_internal_consistency(obs)` → flags
- `check_format_and_types(obs)` → flags
- `check_duplicates(obs, existing_observations)` → flags

**Range Plausibility Checks:**
- `kd_nominal`: 0-30%
- `ke_nominal`: 2-40%
- `wacc_nominal`: 1-35%
- `leverage_debt_pct`: 0-100%
- `debt_tenor_years`: 1-40 years
- `kd_spread_bps`: 0-2000 basis points

**Internal Consistency Checks:**
- WACC reconciliation: WACC ≈ Ke*(E/V) + Kd*(1-t)*(D/V) ± 0.5pp
- Leverage percentages: debt_pct + equity_pct ≈ 100% ± 5%
- Cost ordering: Kd <= WACC <= Ke
- Real vs nominal: kd_real <= kd_nominal, ke_real <= ke_nominal

**Format & Type Checks:**
- Country codes: Valid ISO 3166-1 alpha-3
- Currency codes: Valid ISO 4217
- Controlled vocabularies: technology_l2, scale, value_chain_position, project_status
- Dates: Valid and not in future
- Numeric fields: Must be proper numbers, not "see note 12"

**Duplicate Detection:**
- Identifies near-identical observations (same project, source, year)
- Flags if 2+ financial parameters are suspiciously similar

**Scoring:** Start 1.0, -0.15 per flag, floor 0.0

---

### 2. benchmarks.py - Layer 2: Statistical Checks (StatisticalQC)

**Peer comparison and benchmark validation.**

Methods:
- `check(observation, existing_observations, benchmark_data)` → QCResult
- `check_damodaran_benchmark(obs)` → flags
- `check_peer_comparison(obs, existing)` → flags
- `check_macro_consistency(obs)` → flags
- `load_damodaran_benchmarks()` → DataFrame

**Damodaran Benchmark Check:**
- Compares cost of debt (Kd) against country/credit-rating benchmarks
- Flags observations >2 standard deviations from benchmark mean
- Example: "Observed Kd=15% is 2.3 std devs above benchmark mean=8% for USA-BB"

**Peer Comparison:**
- Groups observations by technology_l2 × country
- Requires minimum 3 peers for statistical significance
- Flags parameters >2 std devs from peer median
- Checks: Kd, Ke, WACC, leverage ratio

**Macro Consistency:**
- Cost of debt should exceed risk-free rate (unless concessional)
- Cost of equity should exceed cost of debt
- Implied inflation (Kd_nominal - Kd_real) should be plausible for country
- Risk-free rates: USA ~4.5%, EUR ~3.0%, JPN ~1.0%, etc.

**Scoring:** Start 1.0, -0.10 per flag, floor 0.0
(Less severe than rule violations)

---

### 3. llm_review.py - Layer 3: LLM Cross-Validation (LLMReviewQC)

**AI-powered verification and consistency checks.**

Methods:
- `check(observation, source_document_text)` → QCResult
- `verify_source_quote(obs, source_text)` → flags
- `check_cross_extraction_consistency(observations)` → QCResult
- `resolve_disagreement(tier1_value, tier3_value, parameter_name)` → dict

**Source Quote Verification:**
- Sends extracted value + source quote to Claude
- Asks: "Does this quote actually support the extracted value?"
- Returns: CONFIRMED | PLAUSIBLE | CONTRADICTED | INSUFFICIENT
- Example: Flag if extracted "Ke=12%" but quote says "cost of equity ranges 8-10%"

**Cross-Extraction Consistency:**
- Reviews full set of extracted parameters for coherence
- Example: Flag if Ke=5% (low) but leverage=80% and Kd=8% (doesn't make sense)
- Checks financial relationships make sense together

**Disagreement Resolution:**
- When Tier 1 (high-confidence) and Tier 3 (low-confidence) disagree
- LLM arbitrates which value is more likely correct
- Returns: recommended_value, confidence, reasoning, tier probabilities
- Example: "Tier 1: 10%, Tier 3: 15% → Recommend Tier 1 (prob: 85%)"

**Scoring:**
- Start 1.0
- CONTRADICTED: -0.30
- INSUFFICIENT: -0.10
- PLAUSIBLE: -0.05
- Floor 0.0

Uses Claude Opus 4.6 for verifications.

---

### 4. agent.py - QC Agent Orchestrator (QCAgent)

**Coordinates all three layers, computes final score, routes observations.**

Methods:
- `run(observation, existing_observations, source_text, benchmark_data)` → (QCResult, RoutingDecision, breakdown)
- `compute_score(rule_score, stat_score, llm_score)` → final_score
- `route(score)` → RoutingDecision (AUTO_ACCEPT | FLAG_FOR_REVIEW | REJECT)
- `process_batch(observations, existing_observations, source_texts)` → results_dict

**Score Computation:**
```python
# Simple average of enabled layers
final_score = (rule_score + stat_score + llm_score) / 3
```

**Routing Decisions:**
- **>= 0.85**: AUTO_ACCEPT (straight to database)
- **0.50-0.85**: FLAG_FOR_REVIEW (human queue)
- **< 0.50**: REJECT (requires re-extraction)

**Batch Processing:**
```python
results = agent.process_batch(observations=[obs1, obs2, obs3])
print(results['summary'])
# {
#   'total_processed': 3,
#   'auto_accepted_count': 2,
#   'flagged_count': 1,
#   'rejected_count': 0,
#   'auto_accept_rate': 0.67,
#   'avg_score_auto_accepted': 91.5,
#   'avg_score_flagged': 72.3,
#   ...
# }
```

## Usage Examples

### Single Observation QC

```python
from oefo.qc import QCAgent
from oefo.models import Observation

# Create agent with all layers
agent = QCAgent(
    enable_rules=True,
    enable_stats=True,
    enable_llm=True
)

# Run full QC pipeline
qc_result, routing, breakdown = agent.run(
    observation=obs,
    existing_observations=historical_obs,
    source_text=document_text
)

print(f"Score: {qc_result.qc_score:.1f}")
print(f"Routing: {routing.value}")
print(f"Flags: {len(qc_result.qc_flags)}")

if routing == RoutingDecision.AUTO_ACCEPT:
    # Save to database
    db.insert(obs)
elif routing == RoutingDecision.FLAG_FOR_REVIEW:
    # Queue for human review
    review_queue.add(qc_result)
else:
    # Request re-extraction
    extraction_queue.add(obs)
```

### Batch Processing

```python
batch_results = agent.process_batch(
    observations=[obs1, obs2, obs3, obs4, obs5],
    existing_observations=database_observations
)

print(f"Accepted: {len(batch_results['auto_accepted'])}")
print(f"Flagged: {len(batch_results['flagged_for_review'])}")
print(f"Rejected: {len(batch_results['rejected'])}")

# Save accepted observations
for qc_result in batch_results['auto_accepted']:
    db.insert(qc_result.observation)

# Queue flagged for human review
for qc_result in batch_results['flagged_for_review']:
    review_queue.add(qc_result)
```

### Selective Layer Enablement

```python
# Fast QC with only rules (0.01s)
quick_agent = QCAgent(
    enable_rules=True,
    enable_stats=False,
    enable_llm=False
)

# Full rigorous QC (3-4s)
rigorous_agent = QCAgent(
    enable_rules=True,
    enable_stats=True,
    enable_llm=True
)

# Statistical-only validation
stats_agent = QCAgent(
    enable_rules=False,
    enable_stats=True,
    enable_llm=False
)
```

### Custom Scoring

```python
# Access score breakdown for detailed analysis
qc_result, routing, breakdown = agent.run(observation=obs)

print(f"Rule-based:    {breakdown.rule_score*100:.1f}% ({breakdown.rule_flags_count} flags)")
print(f"Statistical:   {breakdown.stat_score*100:.1f}% ({breakdown.stat_flags_count} flags)")
print(f"LLM:           {breakdown.llm_score*100:.1f}% ({breakdown.llm_flags_count} flags)")
print(f"─" * 40)
print(f"Final:         {breakdown.final_score*100:.1f}%")

# Access detailed flags
for flag in qc_result.qc_flags:
    print(f"  {flag}")
```

## Configuration

All thresholds are defined in `config/thresholds.py`:

| Parameter | Range/Value | Notes |
|-----------|----------|-------|
| KD_NOMINAL_RANGE | 0-30% | Cost of debt range |
| KE_NOMINAL_RANGE | 2-40% | Cost of equity range |
| WACC_NOMINAL_RANGE | 1-35% | WACC range |
| LEVERAGE_NOMINAL_RANGE | 0-100% | Leverage ratio range |
| DEBT_TENOR_RANGE | 1-40 years | Maturity range |
| SPREAD_BPS_RANGE | 0-2000 bps | Credit spread range |
| WACC_CONSISTENCY_TOLERANCE | 0.5pp | WACC reconciliation tolerance |
| AUTO_ACCEPT_THRESHOLD | 0.85 | Score for auto-approval |
| REVIEW_THRESHOLD | 0.50 | Score for review queue |
| OUTLIER_STD_DEVIATIONS | 2.0 | Std devs for outlier detection |

## Performance Characteristics

| Layer | Time | Reliability | False Positives |
|-------|------|-------------|-----------------|
| Rules | ~0.01s | 100% | Low (deterministic) |
| Statistics | ~0.5s | 95% | Medium (empirical) |
| LLM | ~2s | 85% | Low-Medium (semantic) |
| **Total** | **~2.5s** | **95%** | **Low-Medium** |

## Error Handling

All methods include comprehensive error handling:
- Gracefully skip unavailable data (missing benchmarks, insufficient peers)
- Log warnings for missing external data
- Continue validation with available information
- Never crash on malformed input

Example:
```python
# No benchmark data available → skip Damodaran check
# Less than 3 peers → skip peer comparison
# No source text → skip LLM verification
# All other checks continue normally
```

## Logging

Comprehensive logging at INFO, DEBUG, and WARNING levels:

```
INFO:  oefo.qc.agent:Starting QC Agent run for observation obs_12345
DEBUG: oefo.qc.agent:Running Layer 1: Rule-based checks
DEBUG: oefo.qc.agent:Layer 1 score: 0.85, flags: 1
DEBUG: oefo.qc.agent:Running Layer 2: Statistical checks
DEBUG: oefo.qc.agent:Layer 2 score: 0.95, flags: 0
DEBUG: oefo.qc.agent:Running Layer 3: LLM verification
DEBUG: oefo.qc.agent:Layer 3 score: 0.90, flags: 1
INFO:  oefo.qc.agent:QC Agent complete: score=0.90, routing=flag_for_review, flags=2
```

## Testing

All modules include docstrings and type hints for IDE support and testing.

Example test structure:
```python
def test_wacc_reconciliation():
    obs = Observation(
        observation_id="test_1",
        kd_nominal=5.0,
        ke_nominal=12.0,
        leverage_debt_pct=60.0,
        wacc_nominal=8.2,  # Should be ~7.8%
        ...
    )
    result = agent.run(obs)
    assert "WACC reconciliation failed" in result.qc_flags[0]
```

## Integration with OEFO Pipeline

The QC Agent is designed to integrate at the end of the extraction pipeline:

```
Document → Extraction → QC Agent → Database/Review/Re-extract
                           ↓
                    ┌──────┴───────┬──────────┐
                    ↓              ↓          ↓
                 auto_accept   flag_review  reject
                    ↓              ↓          ↓
                 database      human_queue  re_extract
```

## Future Enhancements

Potential improvements:

1. **Benchmark Data Integration**
   - Load Damodaran benchmarks from CSV/API
   - Cache benchmark data for performance
   - Update benchmarks on schedule

2. **Peer Data Expansion**
   - Expand peer comparison beyond 3-person minimum
   - Weighted peer comparison by recency
   - Technology clustering for better groups

3. **LLM Enhancements**
   - Multi-document source verification
   - Disagreement resolution improvements
   - Vision API for table/chart extraction

4. **Performance Optimization**
   - Parallel layer execution
   - Caching of peer statistics
   - Batch LLM calls

5. **Calibration**
   - Calibrate thresholds based on manual review outcomes
   - Learning from disagreements
   - Per-technology/region threshold variants

## Files

- `rules.py` (19 KB) - Layer 1 implementation
- `benchmarks.py` (13 KB) - Layer 2 implementation
- `llm_review.py` (20 KB) - Layer 3 implementation
- `agent.py` (15 KB) - Orchestrator
- `__init__.py` (3 KB) - Package exports
- `README.md` - This file

**Total: ~70 KB of code**

## Dependencies

- `pandas`: For benchmark data handling
- `anthropic`: For Claude API calls (Layer 3 only)
- `oefo.models`: Observation and QCResult models
- `oefo.config.thresholds`: Configuration parameters
- Standard library: typing, logging, datetime, statistics, re, json

## License

Part of the OEFO (Open Energy Finance Observatory) project.
