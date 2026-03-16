"""
Tests for the self-improving pipeline infrastructure:
- Health score computation
- Run ledger append/read/trend
- Source history skip logic
- Strategy registry promote/demote/disable
- Document store persistence
- Structured exception classification
"""

import json
import tempfile
from pathlib import Path

import pytest

from oefo.exceptions import (
    TransientError,
    PermanentError,
    ContentChangedError,
    classify_http_error,
)
from oefo.metrics.health import SourceHealthScore, PipelineHealthScore
from oefo.metrics.ledger import RunLedger
from oefo.metrics.source_history import SourceHistory
from oefo.scrapers.strategies import StrategyRecord, StrategyRegistry


# ── Exception classification ───────────────────────────────────────────


class TestExceptionClassification:
    def test_404_is_permanent(self):
        err = classify_http_error(404, "https://example.com/missing")
        assert isinstance(err, PermanentError)
        assert err.status_code == 404

    def test_403_is_permanent(self):
        err = classify_http_error(403, "https://example.com/forbidden")
        assert isinstance(err, PermanentError)

    def test_429_is_transient(self):
        err = classify_http_error(429, "https://example.com/ratelimit")
        assert isinstance(err, TransientError)
        assert err.status_code == 429

    def test_500_is_transient(self):
        err = classify_http_error(500, "https://example.com/error")
        assert isinstance(err, TransientError)

    def test_503_is_transient(self):
        err = classify_http_error(503, "https://example.com/unavail")
        assert isinstance(err, TransientError)

    def test_diagnostic_context(self):
        err = classify_http_error(
            404, "https://example.com/gone",
            source="IFC",
            response_snippet="Not Found",
        )
        assert err.diagnostic["status_code"] == 404
        assert err.diagnostic["source"] == "IFC"
        assert "Not Found" in err.diagnostic["response_snippet"]

    def test_unknown_5xx_is_transient(self):
        err = classify_http_error(599, "https://example.com")
        assert isinstance(err, TransientError)

    def test_unknown_4xx_is_permanent(self):
        err = classify_http_error(451, "https://example.com")
        assert isinstance(err, PermanentError)


# ── Health score ───────────────────────────────────────────────────────


class TestHealthScore:
    def test_perfect_source(self):
        s = SourceHealthScore(
            source_name="test",
            discovery_count=100,
            download_count=100,
            download_failure_count=0,
            extraction_count=100,
            qc_pass_count=100,
            mean_qc_score=0.95,
        )
        # 40% * 1.0 + 30% * 1.0 + 20% * 0.95 + 10% * 1.0 = 0.99
        assert s.health_score == 0.99

    def test_zero_discovery(self):
        s = SourceHealthScore(source_name="empty", discovery_count=0)
        # yield_rate = 0, download_success = 0/1=0, qc=0, crash_free=1
        assert s.health_score == 0.10  # just crash-free bonus

    def test_crash_penalty(self):
        s = SourceHealthScore(
            source_name="crashed",
            discovery_count=10,
            download_count=10,
            mean_qc_score=0.8,
            error_types={"PermanentError": 5},
        )
        assert not s.crash_free
        # No crash-free bonus
        assert s.health_score < 0.5

    def test_record_error(self):
        s = SourceHealthScore(source_name="test")
        s.record_error(TransientError("timeout"))
        s.record_error(TransientError("timeout"))
        s.record_error(PermanentError("404"))
        assert s.error_types == {"TransientError": 2, "PermanentError": 1}

    def test_pipeline_health_weighted(self):
        big = SourceHealthScore(
            source_name="big",
            discovery_count=100,
            download_count=100,
            mean_qc_score=0.9,
            qc_pass_count=90,
        )
        big.decision = "KEEP"

        small = SourceHealthScore(
            source_name="small",
            discovery_count=10,
            download_count=5,
            download_failure_count=5,
            mean_qc_score=0.5,
        )
        small.decision = "DISCARD"

        pipeline = PipelineHealthScore(source_scores=[big, small])
        # big has 100 discovery, small has 10 — big dominates the weighted avg
        assert pipeline.health_score > 0.5
        assert pipeline.sources_ok == 1
        assert pipeline.total_discovered == 110

    def test_pipeline_summary_line(self):
        s = SourceHealthScore(source_name="test", discovery_count=50)
        s.decision = "KEEP"
        p = PipelineHealthScore(source_scores=[s], run_id="test_run")
        line = p.summary_line()
        assert "Pipeline health" in line
        assert "test_run" not in line  # summary doesn't include run_id

    def test_to_dict_roundtrip(self):
        s = SourceHealthScore(
            source_name="ifc",
            discovery_count=50,
            download_count=48,
        )
        d = s.to_dict()
        assert d["source"] == "ifc"
        assert d["discovery"] == 50
        assert d["downloaded"] == 48


# ── Run ledger ─────────────────────────────────────────────────────────


class TestRunLedger:
    def test_append_and_read(self, tmp_path):
        ledger = RunLedger(path=tmp_path / "ledger.tsv")
        score = PipelineHealthScore(run_id="run_001")
        score.source_scores.append(
            SourceHealthScore(source_name="test", discovery_count=10)
        )
        ledger.append(score, status="SUCCESS", description="test run")

        rows = ledger.read_all()
        assert len(rows) == 1
        assert rows[0]["run_id"] == "run_001"
        assert rows[0]["status"] == "SUCCESS"

    def test_multiple_appends(self, tmp_path):
        ledger = RunLedger(path=tmp_path / "ledger.tsv")
        for i in range(5):
            score = PipelineHealthScore(run_id=f"run_{i:03d}")
            ledger.append(score)

        rows = ledger.read_all()
        assert len(rows) == 5
        recent = ledger.read_recent(3)
        assert len(recent) == 3
        assert recent[0]["run_id"] == "run_004"  # Most recent first

    def test_trend_table(self, tmp_path):
        ledger = RunLedger(path=tmp_path / "ledger.tsv")
        score = PipelineHealthScore(run_id="run_001")
        ledger.append(score)
        table = ledger.trend_table()
        assert "run_001" in table

    def test_sparkline(self, tmp_path):
        ledger = RunLedger(path=tmp_path / "ledger.tsv")
        for i in range(5):
            s = SourceHealthScore(
                source_name="test",
                discovery_count=10 * (i + 1),
                download_count=10 * (i + 1),
                mean_qc_score=0.2 * (i + 1),
                qc_pass_count=2 * (i + 1),
            )
            score = PipelineHealthScore(
                run_id=f"run_{i:03d}",
                source_scores=[s],
            )
            ledger.append(score)

        sparkline = ledger.health_sparkline()
        assert len(sparkline) == 5  # One char per run

    def test_empty_ledger(self, tmp_path):
        ledger = RunLedger(path=tmp_path / "nonexistent.tsv")
        assert ledger.read_all() == []
        assert ledger.trend_table() == "No runs recorded yet."
        assert ledger.health_sparkline() == "No data"


# ── Source history ─────────────────────────────────────────────────────


class TestSourceHistory:
    def test_not_enough_history(self, tmp_path):
        ledger = RunLedger(path=tmp_path / "ledger.tsv")
        history = SourceHistory(ledger=ledger)
        skip, reason = history.should_skip_source("ifc", n=3)
        assert not skip
        assert "Not enough history" in reason

    def test_source_trend_empty(self, tmp_path):
        ledger = RunLedger(path=tmp_path / "ledger.tsv")
        history = SourceHistory(ledger=ledger)
        trend = history.source_trend("ifc")
        assert trend == []

    def test_default_extraction_tier(self, tmp_path):
        ledger = RunLedger(path=tmp_path / "ledger.tsv")
        history = SourceHistory(ledger=ledger)
        assert history.recommended_extraction_tier("ifc") == 1


# ── Strategy registry ─────────────────────────────────────────────────


class TestStrategyRegistry:
    def test_record_and_retrieve(self, tmp_path):
        reg = StrategyRegistry(path=tmp_path / "registry.json")
        reg.record_result("ifc", "sitemap", doc_count=200)
        reg.record_result("ifc", "api", doc_count=50)

        strategies = reg.get_strategies("ifc")
        assert len(strategies) == 2
        assert strategies[0].name == "sitemap"  # First registered
        assert strategies[0].last_doc_count == 200

    def test_promote_strategy(self, tmp_path):
        reg = StrategyRegistry(path=tmp_path / "registry.json")
        reg.record_result("ebrd", "api", doc_count=36)
        reg.record_result("ebrd", "sitemap", doc_count=191)

        # Sitemap has priority 1 (registered second)
        reg.promote("ebrd", "sitemap")
        strategies = reg.get_strategies("ebrd")
        assert strategies[0].name == "sitemap"

    def test_disable_strategy(self, tmp_path):
        reg = StrategyRegistry(path=tmp_path / "registry.json")
        reg.record_result("ferc", "eLibrary", doc_count=0, error="timeout")
        reg.disable("ferc", "eLibrary")

        strategies = reg.get_strategies("ferc")
        assert len(strategies) == 0  # Disabled = filtered out

    def test_auto_adjust(self, tmp_path):
        reg = StrategyRegistry(path=tmp_path / "registry.json")
        # Record many failures for api
        for _ in range(5):
            reg.record_result("ifc", "api", doc_count=0, error="timeout")
        reg.record_result("ifc", "sitemap", doc_count=200)

        reg.auto_adjust("ifc")
        strategies = reg.get_strategies("ifc")
        # Sitemap should be promoted, api may be disabled
        names = [s.name for s in strategies]
        assert "sitemap" in names
        if "api" in names:
            assert strategies[0].name == "sitemap"

    def test_persistence(self, tmp_path):
        path = tmp_path / "registry.json"
        reg1 = StrategyRegistry(path=path)
        reg1.record_result("gcf", "sitemap", doc_count=280)

        # Load fresh instance from same file
        reg2 = StrategyRegistry(path=path)
        strategies = reg2.get_strategies("gcf")
        assert len(strategies) == 1
        assert strategies[0].last_doc_count == 280

    def test_summary_table(self, tmp_path):
        reg = StrategyRegistry(path=tmp_path / "registry.json")
        reg.record_result("ifc", "sitemap", doc_count=200)
        table = reg.summary_table()
        assert "ifc" in table
        assert "sitemap" in table

    def test_success_rate(self):
        r = StrategyRecord(name="test", source="test", success_count=8, failure_count=2)
        assert r.success_rate == 0.8


# ── Document store persistence ─────────────────────────────────────────


class TestDocumentStorePersistence:
    def test_hash_store_persists(self, tmp_path):
        """Verify document hashes survive scraper re-instantiation."""
        from oefo.scrapers.base import BaseScraper

        # Create a concrete subclass for testing
        class DummyScraper(BaseScraper):
            def scrape(self):
                return []

        output_dir = str(tmp_path / "raw" / "test")

        # First instance
        s1 = DummyScraper("test", "https://example.com", output_dir)
        s1.document_store.add("hash_abc123")
        s1.document_store.add("hash_def456")
        s1._save_document_store()

        # Second instance — should load from disk
        s2 = DummyScraper("test", "https://example.com", output_dir)
        assert "hash_abc123" in s2.document_store
        assert "hash_def456" in s2.document_store
        assert len(s2.document_store) == 2

    def test_is_duplicate_uses_persistent_store(self, tmp_path):
        """is_duplicate should detect files already registered in previous runs."""
        from oefo.scrapers.base import BaseScraper

        class DummyScraper(BaseScraper):
            def scrape(self):
                return []

        output_dir = str(tmp_path / "raw" / "test")

        # Create a test file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        # First instance: register the document
        s1 = DummyScraper("test", "https://example.com", output_dir)
        assert not s1.is_duplicate("https://example.com/test.pdf", test_file)
        s1.document_store.add(s1._compute_content_hash(test_file))
        s1._save_document_store()

        # Second instance: should detect as duplicate
        s2 = DummyScraper("test", "https://example.com", output_dir)
        assert s2.is_duplicate("https://example.com/test.pdf", test_file)
