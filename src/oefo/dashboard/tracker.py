"""
Pipeline Progress Tracker for OEFO Dashboard

Collects metrics from every pipeline stage — scraping, extraction, QC, and
the final observation store — and writes a single JSON snapshot that the
interactive HTML dashboard reads.

Usage:
    from oefo.dashboard.tracker import PipelineTracker

    tracker = PipelineTracker(data_dir="data/")
    snapshot = tracker.collect()          # dict of all metrics
    tracker.write_snapshot("dashboard/")  # writes pipeline_snapshot.json
"""

import json
import logging
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class PipelineTracker:
    """
    Scans the OEFO data directories and computes pipeline-wide metrics.

    Sections produced:
      1. scraping   — documents downloaded per source, file sizes, dates
      2. extraction — tier breakdown, success/fail rates, pages processed
      3. qc         — pass/flag/reject distribution, score histogram, flag reasons
      4. database   — observation counts by technology, country, year, source type
      5. coverage   — technology × country matrix, gap analysis
      6. financials — WACC/Kd/Ke summary statistics for preliminary results
    """

    def __init__(self, base_dir: Optional[str] = None):
        try:
            from oefo.config.settings import BASE_DIR, RAW_DIR, EXTRACTED_DIR, FINAL_DIR
            self.base_dir = Path(base_dir) if base_dir else BASE_DIR
            self.raw_dir = RAW_DIR
            self.extracted_dir = EXTRACTED_DIR
            self.final_dir = FINAL_DIR
        except ImportError:
            self.base_dir = Path(base_dir or ".")
            self.raw_dir = self.base_dir / "data" / "raw"
            self.extracted_dir = self.base_dir / "data" / "extracted"
            self.final_dir = self.base_dir / "data" / "final"

    # ------------------------------------------------------------------
    # Main entry points
    # ------------------------------------------------------------------

    # Known source directories and their display names / expected totals
    SOURCE_DIRS = {
        "ebrd": {"label": "EBRD", "description": "European Bank for Reconstruction and Development"},
        "ifc": {"label": "IFC", "description": "International Finance Corporation"},
        "gcf": {"label": "GCF", "description": "Green Climate Fund"},
        "sec": {"label": "SEC EDGAR", "description": "U.S. Securities and Exchange Commission"},
        "aneel": {"label": "ANEEL", "description": "Agencia Nacional de Energia Eletrica (Brazil)"},
        "ofgem": {"label": "Ofgem", "description": "Office of Gas and Electricity Markets (UK)"},
        "ferc": {"label": "FERC", "description": "Federal Energy Regulatory Commission (US)"},
        "aer": {"label": "AER", "description": "Australian Energy Regulator"},
    }

    def collect(self) -> Dict[str, Any]:
        """Collect all metrics into a single dict."""
        snapshot = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "pipeline_version": "0.1.0",
            "download_progress": self._download_progress(),
            "scraping": self._scraping_metrics(),
            "extraction": self._extraction_metrics(),
            "qc": self._qc_metrics(),
            "database": self._database_metrics(),
            "coverage": self._coverage_metrics(),
            "financials": self._financial_summary(),
        }
        return snapshot

    def write_snapshot(self, output_dir: Optional[str] = None) -> Path:
        """Collect metrics and write pipeline_snapshot.json."""
        snapshot = self.collect()
        out = Path(output_dir or self.base_dir / "dashboard")
        out.mkdir(parents=True, exist_ok=True)
        path = out / "pipeline_snapshot.json"
        with open(path, "w") as f:
            json.dump(snapshot, f, indent=2, default=str)
        logger.info(f"Snapshot written to {path}")
        return path

    # ------------------------------------------------------------------
    # Section collectors
    # ------------------------------------------------------------------

    def _download_progress(self) -> Dict:
        """Count downloaded files per source directory, with live progress."""
        sources = []
        total_files = 0
        total_size_mb = 0.0

        for dir_name, meta in self.SOURCE_DIRS.items():
            source_dir = self.raw_dir / dir_name
            if not source_dir.exists():
                sources.append({
                    "id": dir_name,
                    "label": meta["label"],
                    "description": meta["description"],
                    "files_downloaded": 0,
                    "size_mb": 0.0,
                    "status": "pending",
                })
                continue

            # Count files (exclude hidden and temp files)
            files = [
                f for f in source_dir.iterdir()
                if f.is_file() and not f.name.startswith(".")
            ]
            file_count = len(files)
            size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
            total_files += file_count
            total_size_mb += size_mb

            # Determine status based on file count
            if file_count == 0:
                status = "pending"
            else:
                # Check if any file was modified in the last 60 seconds
                import time as _time
                now = _time.time()
                recent = any((now - f.stat().st_mtime) < 60 for f in files)
                status = "downloading" if recent else "complete"

            sources.append({
                "id": dir_name,
                "label": meta["label"],
                "description": meta["description"],
                "files_downloaded": file_count,
                "size_mb": round(size_mb, 1),
                "status": status,
            })

        # Sort: downloading first, then by file count descending
        status_order = {"downloading": 0, "complete": 1, "pending": 2}
        sources.sort(key=lambda s: (status_order.get(s["status"], 9), -s["files_downloaded"]))

        return {
            "sources": sources,
            "total_files": total_files,
            "total_size_mb": round(total_size_mb, 1),
            "active_downloads": sum(1 for s in sources if s["status"] == "downloading"),
            "completed_sources": sum(1 for s in sources if s["status"] == "complete"),
        }

    def _scraping_metrics(self) -> Dict:
        """Count raw documents per source, sizes, dates."""
        index_path = self.raw_dir / "document_index.json"
        if not index_path.exists():
            return self._empty_scraping()

        try:
            with open(index_path) as f:
                docs = json.load(f)
        except (json.JSONDecodeError, OSError):
            return self._empty_scraping()

        by_source = Counter()
        by_type = Counter()
        total_size_mb = 0.0
        dates = []

        for doc in docs if isinstance(docs, list) else docs.values():
            src = doc.get("source_institution", "unknown")
            by_source[src] += 1
            by_type[doc.get("source_type", "unknown")] += 1
            size = doc.get("file_size_bytes", 0)
            total_size_mb += size / (1024 * 1024)
            dl = doc.get("download_date") or doc.get("extraction_date")
            if dl:
                dates.append(dl)

        return {
            "total_documents": sum(by_source.values()),
            "by_source": dict(by_source.most_common()),
            "by_type": dict(by_type.most_common()),
            "total_size_mb": round(total_size_mb, 1),
            "earliest_download": min(dates) if dates else None,
            "latest_download": max(dates) if dates else None,
        }

    def _extraction_metrics(self) -> Dict:
        """Tier breakdown, success rates from extracted/ directory."""
        extracted_files = list(self.extracted_dir.glob("*.json")) if self.extracted_dir.exists() else []

        tier_counts = Counter()
        success = 0
        fail = 0
        total_items = 0

        for fp in extracted_files:
            try:
                with open(fp) as f:
                    data = json.load(f)
                records = data if isinstance(data, list) else [data]
                for rec in records:
                    tier = rec.get("extraction_tier", "unknown")
                    tier_counts[tier] += 1
                    items = rec.get("extracted_data", [])
                    total_items += len(items) if isinstance(items, list) else 0
                    if rec.get("confidence", 0) > 0.3:
                        success += 1
                    else:
                        fail += 1
            except (json.JSONDecodeError, OSError):
                fail += 1

        total = success + fail
        return {
            "total_extractions": total,
            "success": success,
            "fail": fail,
            "success_rate": round(success / total, 3) if total else 0,
            "by_tier": dict(tier_counts.most_common()),
            "total_extracted_items": total_items,
        }

    def _qc_metrics(self) -> Dict:
        """QC pass/flag/reject from final observations or QC log."""
        observations = self._load_observations()

        status_counts = Counter()
        scores = []
        flag_reasons = Counter()

        for obs in observations:
            st = obs.get("qc_status", "unknown")
            status_counts[st] += 1
            sc = obs.get("qc_score")
            if sc is not None:
                scores.append(float(sc))
            flags = obs.get("qc_flags", [])
            if isinstance(flags, list):
                for flag in flags:
                    # Extract short reason from flag string
                    reason = flag.split(":")[0].strip() if ":" in flag else flag[:40]
                    flag_reasons[reason] += 1

        total = sum(status_counts.values())
        auto_accepted = status_counts.get("auto_accepted", 0) + status_counts.get("PASSED", 0)
        flagged = status_counts.get("flagged", 0) + status_counts.get("FLAGGED", 0)
        rejected = status_counts.get("rejected", 0) + status_counts.get("FAILED", 0)

        # Score histogram (buckets of 0.1)
        score_histogram = Counter()
        for s in scores:
            bucket = round(int(s * 10) / 10, 1)
            score_histogram[str(bucket)] += 1

        return {
            "total_reviewed": total,
            "auto_accepted": auto_accepted,
            "flagged_for_review": flagged,
            "rejected": rejected,
            "auto_accept_rate": round(auto_accepted / total, 3) if total else 0,
            "mean_score": round(sum(scores) / len(scores), 3) if scores else 0,
            "score_histogram": dict(sorted(score_histogram.items())),
            "top_flag_reasons": dict(flag_reasons.most_common(10)),
        }

    def _database_metrics(self) -> Dict:
        """Observation counts by key dimensions."""
        observations = self._load_observations()

        by_technology = Counter()
        by_country = Counter()
        by_year = Counter()
        by_source_type = Counter()
        by_scale = Counter()
        by_value_chain = Counter()

        for obs in observations:
            by_technology[obs.get("technology_l2", "unknown")] += 1
            by_country[obs.get("country", "unknown")] += 1
            yr = obs.get("year_of_observation")
            if yr:
                by_year[str(yr)] += 1
            by_source_type[obs.get("source_type", "unknown")] += 1
            by_scale[obs.get("scale", "unknown")] += 1
            by_value_chain[obs.get("value_chain_position", "unknown")] += 1

        return {
            "total_observations": len(observations),
            "unique_countries": len([c for c in by_country if c != "unknown"]),
            "unique_technologies": len([t for t in by_technology if t != "unknown"]),
            "year_range": [min(by_year.keys(), default="N/A"), max(by_year.keys(), default="N/A")],
            "by_technology": dict(by_technology.most_common(25)),
            "by_country": dict(by_country.most_common(25)),
            "by_year": dict(sorted(by_year.items())),
            "by_source_type": dict(by_source_type.most_common()),
            "by_scale": dict(by_scale.most_common()),
            "by_value_chain": dict(by_value_chain.most_common()),
        }

    def _coverage_metrics(self) -> Dict:
        """Technology × country coverage matrix and gap analysis."""
        observations = self._load_observations()

        matrix = defaultdict(set)
        for obs in observations:
            tech = obs.get("technology_l2", "unknown")
            country = obs.get("country", "unknown")
            if tech != "unknown" and country != "unknown":
                matrix[tech].add(country)

        # Build coverage summary
        coverage_matrix = {}
        for tech, countries in sorted(matrix.items()):
            coverage_matrix[tech] = sorted(list(countries))

        # Gap analysis: technologies with fewest countries
        tech_coverage = {t: len(c) for t, c in matrix.items()}

        # Top countries by observation count
        country_counts = Counter()
        for obs in observations:
            c = obs.get("country", "unknown")
            if c != "unknown":
                country_counts[c] += 1

        return {
            "technology_country_matrix": coverage_matrix,
            "technologies_by_country_count": dict(
                sorted(tech_coverage.items(), key=lambda x: x[1], reverse=True)[:20]
            ),
            "top_countries": dict(country_counts.most_common(20)),
            "total_tech_country_pairs": sum(len(v) for v in matrix.values()),
        }

    def _financial_summary(self) -> Dict:
        """Preliminary WACC/Kd/Ke summary statistics."""
        observations = self._load_observations()

        kd_values = []
        ke_values = []
        wacc_values = []
        leverage_values = []
        spread_values = []

        kd_by_tech = defaultdict(list)
        wacc_by_country = defaultdict(list)
        ke_by_source = defaultdict(list)

        for obs in observations:
            kd = obs.get("kd_nominal")
            ke = obs.get("ke_nominal")
            wacc = obs.get("wacc_nominal")
            lev = obs.get("leverage_debt_pct")
            spread = obs.get("kd_spread_bps")
            tech = obs.get("technology_l2", "unknown")
            country = obs.get("country", "unknown")
            src = obs.get("source_type", "unknown")

            if kd is not None:
                kd_values.append(float(kd))
                kd_by_tech[tech].append(float(kd))
            if ke is not None:
                ke_values.append(float(ke))
                ke_by_source[src].append(float(ke))
            if wacc is not None:
                wacc_values.append(float(wacc))
                wacc_by_country[country].append(float(wacc))
            if lev is not None:
                leverage_values.append(float(lev))
            if spread is not None:
                spread_values.append(float(spread))

        def _stats(vals):
            if not vals:
                return {"count": 0, "mean": None, "median": None, "min": None, "max": None, "std": None}
            vals_sorted = sorted(vals)
            n = len(vals_sorted)
            mean = sum(vals_sorted) / n
            median = vals_sorted[n // 2] if n % 2 else (vals_sorted[n // 2 - 1] + vals_sorted[n // 2]) / 2
            variance = sum((x - mean) ** 2 for x in vals_sorted) / n if n > 1 else 0
            return {
                "count": n,
                "mean": round(mean, 2),
                "median": round(median, 2),
                "min": round(vals_sorted[0], 2),
                "max": round(vals_sorted[-1], 2),
                "std": round(variance ** 0.5, 2),
            }

        def _grouped_means(grouped):
            return {
                k: {"count": len(v), "mean": round(sum(v) / len(v), 2)}
                for k, v in sorted(grouped.items(), key=lambda x: -len(x[1]))[:15]
                if v
            }

        return {
            "kd_nominal": _stats(kd_values),
            "ke_nominal": _stats(ke_values),
            "wacc_nominal": _stats(wacc_values),
            "leverage_debt_pct": _stats(leverage_values),
            "kd_spread_bps": _stats(spread_values),
            "kd_by_technology": _grouped_means(kd_by_tech),
            "wacc_by_country": _grouped_means(wacc_by_country),
            "ke_by_source_type": _grouped_means(ke_by_source),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_observations(self) -> List[Dict]:
        """Load all observations from the final directory."""
        observations = []

        # Try Parquet first
        parquet_files = list(self.final_dir.glob("*.parquet")) if self.final_dir.exists() else []
        if parquet_files:
            try:
                import pandas as pd
                for pf in parquet_files:
                    df = pd.read_parquet(pf)
                    observations.extend(df.to_dict("records"))
                return observations
            except ImportError:
                pass

        # Fall back to JSON
        json_files = list(self.final_dir.glob("*.json")) if self.final_dir.exists() else []
        for jf in json_files:
            try:
                with open(jf) as f:
                    data = json.load(f)
                if isinstance(data, list):
                    observations.extend(data)
                elif isinstance(data, dict):
                    observations.append(data)
            except (json.JSONDecodeError, OSError):
                continue

        # Also try CSV
        csv_files = list(self.final_dir.glob("*.csv")) if self.final_dir.exists() else []
        if csv_files and not observations:
            try:
                import csv as csvmod
                for cf in csv_files:
                    with open(cf) as f:
                        reader = csvmod.DictReader(f)
                        observations.extend(list(reader))
            except Exception:
                pass

        return observations

    @staticmethod
    def _empty_scraping() -> Dict:
        return {
            "total_documents": 0,
            "by_source": {},
            "by_type": {},
            "total_size_mb": 0,
            "earliest_download": None,
            "latest_download": None,
        }


# ------------------------------------------------------------------
# Demo / sample data generator for dashboard development
# ------------------------------------------------------------------

def generate_sample_snapshot() -> Dict:
    """
    Generate a realistic sample snapshot for dashboard testing.
    Uses plausible values for an early Phase 1 run.
    """
    import random
    random.seed(42)

    technologies = [
        "solar_pv", "wind_onshore", "wind_offshore_fixed", "hydro_large",
        "hydro_small", "gas_ccgt", "storage_battery_grid", "biomass_power",
        "geothermal_power", "nuclear_large", "transmission", "distribution",
        "hydrogen_green", "ccs_industrial", "ev_charging", "coal_power",
        "lng_liquefaction", "biofuels", "solar_csp", "wind_offshore_floating",
    ]
    countries = [
        "BRA", "USA", "GBR", "AUS", "DEU", "IND", "ZAF", "CHL",
        "COL", "MEX", "KEN", "PHL", "FRA", "ESP", "ITA", "NGA",
        "TUR", "IDN", "VNM", "JPN",
    ]
    sources = ["DFI_disclosure", "corporate_filing", "regulatory_filing", "bond_prospectus"]
    years = list(range(2015, 2026))

    # Generate ~850 observations
    observations = []
    for _ in range(847):
        tech = random.choice(technologies)
        country = random.choice(countries)
        src = random.choice(sources)
        year = random.choice(years)

        # Plausible Kd ranges by country income
        emerging = country in ["BRA", "IND", "ZAF", "KEN", "NGA", "COL", "PHL", "IDN", "VNM"]
        kd_base = random.uniform(6.0, 14.0) if emerging else random.uniform(2.5, 6.5)
        ke_base = kd_base + random.uniform(2.0, 8.0)
        leverage = random.uniform(55, 85) if src != "regulatory_filing" else random.uniform(40, 65)
        tax = random.uniform(0.15, 0.35)
        wacc = ke_base * (1 - leverage / 100) + kd_base * (1 - tax) * (leverage / 100)

        qc_score = random.uniform(0.4, 1.0)
        if qc_score > 0.85:
            qc_status = "auto_accepted"
        elif qc_score > 0.50:
            qc_status = "flagged"
        else:
            qc_status = "rejected"

        observations.append({
            "technology_l2": tech,
            "country": country,
            "source_type": src,
            "year_of_observation": year,
            "kd_nominal": round(kd_base, 2),
            "ke_nominal": round(ke_base, 2),
            "wacc_nominal": round(wacc, 2),
            "leverage_debt_pct": round(leverage, 1),
            "kd_spread_bps": round(random.uniform(100, 600), 0),
            "scale": random.choice(["utility_scale", "commercial_industrial", "mega_project", "regulated_asset"]),
            "value_chain_position": random.choice(["generation", "fuel_production", "electricity_transmission", "electricity_storage", "carbon_management"]),
            "qc_score": round(qc_score, 3),
            "qc_status": qc_status,
            "qc_flags": (
                [random.choice(["WARNING: benchmark_outlier", "WARNING: source_quote_unconfirmed", "ERROR: range_outlier", "WARNING: consistency_fail"])]
                if qc_score < 0.85 else []
            ),
            "extraction_tier": random.choice(["tier_1_text", "tier_2_ocr", "tier_3_vision"]),
            "source_institution": random.choice(["IFC", "EBRD", "GCF", "SEC_EDGAR", "ANEEL", "AER", "Ofgem", "FERC"]),
        })

    # Build scraping metrics
    source_counts = Counter(o["source_institution"] for o in observations)
    type_counts = Counter(o["source_type"] for o in observations)
    tier_counts = Counter(o["extraction_tier"] for o in observations)
    status_counts = Counter(o["qc_status"] for o in observations)
    scores = [o["qc_score"] for o in observations]
    flag_reasons = Counter()
    for o in observations:
        for fl in o.get("qc_flags", []):
            reason = fl.split(":")[0].strip()
            flag_reasons[reason] += 1

    by_tech = Counter(o["technology_l2"] for o in observations)
    by_country = Counter(o["country"] for o in observations)
    by_year = Counter(str(o["year_of_observation"]) for o in observations)

    score_histogram = Counter()
    for s in scores:
        bucket = round(int(s * 10) / 10, 1)
        score_histogram[str(bucket)] += 1

    def _stats(vals):
        if not vals:
            return {"count": 0, "mean": None, "median": None, "min": None, "max": None, "std": None}
        vs = sorted(vals)
        n = len(vs)
        mean = sum(vs) / n
        med = vs[n // 2]
        var = sum((x - mean) ** 2 for x in vs) / n
        return {"count": n, "mean": round(mean, 2), "median": round(med, 2),
                "min": round(vs[0], 2), "max": round(vs[-1], 2), "std": round(var ** 0.5, 2)}

    kd_vals = [o["kd_nominal"] for o in observations if o.get("kd_nominal")]
    ke_vals = [o["ke_nominal"] for o in observations if o.get("ke_nominal")]
    wacc_vals = [o["wacc_nominal"] for o in observations if o.get("wacc_nominal")]
    lev_vals = [o["leverage_debt_pct"] for o in observations if o.get("leverage_debt_pct")]
    spread_vals = [o["kd_spread_bps"] for o in observations if o.get("kd_spread_bps")]

    kd_by_tech = defaultdict(list)
    wacc_by_country = defaultdict(list)
    ke_by_source = defaultdict(list)
    for o in observations:
        if o.get("kd_nominal"):
            kd_by_tech[o["technology_l2"]].append(o["kd_nominal"])
        if o.get("wacc_nominal"):
            wacc_by_country[o["country"]].append(o["wacc_nominal"])
        if o.get("ke_nominal"):
            ke_by_source[o["source_type"]].append(o["ke_nominal"])

    def _grouped(d):
        return {k: {"count": len(v), "mean": round(sum(v) / len(v), 2)}
                for k, v in sorted(d.items(), key=lambda x: -len(x[1]))[:15] if v}

    # Coverage matrix
    matrix = defaultdict(set)
    for o in observations:
        matrix[o["technology_l2"]].add(o["country"])
    coverage_matrix = {t: sorted(list(c)) for t, c in sorted(matrix.items())}
    tech_coverage = {t: len(c) for t, c in matrix.items()}

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "pipeline_version": "0.1.0",
        "scraping": {
            "total_documents": 1243,
            "by_source": dict(source_counts.most_common()),
            "by_type": dict(type_counts.most_common()),
            "total_size_mb": 487.3,
            "earliest_download": "2026-02-15",
            "latest_download": "2026-03-10",
        },
        "extraction": {
            "total_extractions": len(observations),
            "success": sum(1 for o in observations if o["qc_score"] > 0.3),
            "fail": sum(1 for o in observations if o["qc_score"] <= 0.3),
            "success_rate": round(sum(1 for o in observations if o["qc_score"] > 0.3) / len(observations), 3),
            "by_tier": dict(tier_counts.most_common()),
            "total_extracted_items": len(observations) * 4,
        },
        "qc": {
            "total_reviewed": len(observations),
            "auto_accepted": status_counts.get("auto_accepted", 0),
            "flagged_for_review": status_counts.get("flagged", 0),
            "rejected": status_counts.get("rejected", 0),
            "auto_accept_rate": round(status_counts.get("auto_accepted", 0) / len(observations), 3),
            "mean_score": round(sum(scores) / len(scores), 3),
            "score_histogram": dict(sorted(score_histogram.items())),
            "top_flag_reasons": dict(flag_reasons.most_common(10)),
        },
        "database": {
            "total_observations": len(observations),
            "unique_countries": len(set(o["country"] for o in observations)),
            "unique_technologies": len(set(o["technology_l2"] for o in observations)),
            "year_range": ["2015", "2025"],
            "by_technology": dict(by_tech.most_common(25)),
            "by_country": dict(by_country.most_common(25)),
            "by_year": dict(sorted(by_year.items())),
            "by_source_type": dict(type_counts.most_common()),
            "by_scale": dict(Counter(o.get("scale", "unknown") for o in observations).most_common()),
            "by_value_chain": dict(Counter(o.get("value_chain_position", "unknown") for o in observations).most_common()),
        },
        "coverage": {
            "technology_country_matrix": coverage_matrix,
            "technologies_by_country_count": dict(sorted(tech_coverage.items(), key=lambda x: -x[1])[:20]),
            "top_countries": dict(Counter(o["country"] for o in observations).most_common(20)),
            "total_tech_country_pairs": sum(len(v) for v in matrix.values()),
        },
        "financials": {
            "kd_nominal": _stats(kd_vals),
            "ke_nominal": _stats(ke_vals),
            "wacc_nominal": _stats(wacc_vals),
            "leverage_debt_pct": _stats(lev_vals),
            "kd_spread_bps": _stats(spread_vals),
            "kd_by_technology": _grouped(kd_by_tech),
            "wacc_by_country": _grouped(wacc_by_country),
            "ke_by_source_type": _grouped(ke_by_source),
        },
    }


if __name__ == "__main__":
    # Generate sample snapshot for testing
    snapshot = generate_sample_snapshot()
    out = Path(__file__).parent / "pipeline_snapshot.json"
    with open(out, "w") as f:
        json.dump(snapshot, f, indent=2)
    print(f"Sample snapshot written to {out}")
    print(f"  Observations: {snapshot['database']['total_observations']}")
    print(f"  Countries: {snapshot['database']['unique_countries']}")
    print(f"  Technologies: {snapshot['database']['unique_technologies']}")
