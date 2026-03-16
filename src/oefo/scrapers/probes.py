"""
Scraper probes — fast health checks that detect breakage in <30 seconds.

Inspired by autoresearch's fast-fail NaN detection: detect broken sources
before committing to a full scrape run. Each probe checks reachability,
sitemap availability, and sample URL validity.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import requests

from ..config.settings import USER_AGENT

logger = logging.getLogger(__name__)

# Traffic-light status constants
GREEN = "GREEN"    # All checks pass
YELLOW = "YELLOW"  # Reachable but degraded (sitemap missing or sample URLs failing)
RED = "RED"        # Unreachable or completely broken


@dataclass
class ProbeResult:
    """Result of a single source health probe."""

    source: str
    reachable: bool = False
    status_code: int = 0
    sitemap_available: bool = False
    sitemap_url_count: int = 0
    sample_urls_valid: int = 0
    sample_urls_checked: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    @property
    def status(self) -> str:
        """Traffic-light status: GREEN / YELLOW / RED."""
        if not self.reachable:
            return RED
        if self.sitemap_available and self.sample_urls_valid > 0:
            return GREEN
        if self.sample_urls_valid > 0 or self.sitemap_available:
            return YELLOW
        return RED

    @property
    def status_emoji(self) -> str:
        return {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}[self.status]

    def summary(self) -> str:
        parts = [
            f"{self.status_emoji} {self.source:<8}",
            f"reach={'✓' if self.reachable else '✗'}",
            f"sitemap={'✓' if self.sitemap_available else '✗'}",
            f"urls={self.sample_urls_valid}/{self.sample_urls_checked}",
            f"{self.latency_ms:.0f}ms",
        ]
        if self.error:
            parts.append(f"err={self.error[:60]}")
        return "  ".join(parts)


# Source configuration: base URL, sitemap URL, sample URLs to check
_SOURCE_CONFIG: dict[str, dict] = {
    "IFC": {
        "base_url": "https://disclosures.ifc.org",
        "sitemap_url": "https://disclosures.ifc.org/project-detail.xml",
        "sitemap_pattern": r"<loc>",
        "sample_urls": [
            "https://disclosures.ifc.org/project-detail/SII/44768",
        ],
    },
    "EBRD": {
        "base_url": "https://www.ebrd.com",
        "sitemap_url": "https://www.ebrd.com/sitemap.xml",
        "sitemap_pattern": r"<loc>",
        "sample_urls": [
            "https://www.ebrd.com/home/work-with-us/projects/psd.html",
        ],
    },
    "GCF": {
        "base_url": "https://www.greenclimate.fund",
        "sitemap_url": "https://www.greenclimate.fund/sitemap.xml?page=1",
        "sitemap_pattern": r"<loc>",
        "sample_urls": [
            "https://www.greenclimate.fund/project/fp001",
        ],
    },
    "SEC": {
        "base_url": "https://efts.sec.gov",
        "sitemap_url": None,
        "sample_urls": [
            "https://efts.sec.gov/LATEST/search-index?q=%22cost+of+capital%22&dateRange=custom&startdt=2023-01-01&enddt=2026-12-31&forms=10-K",
        ],
    },
    "ANEEL": {
        "base_url": "https://www.gov.br/aneel/pt-br",
        "sitemap_url": "https://www.gov.br/aneel/pt-br/sitemap.xml",
        "sitemap_pattern": r"<loc>",
        "sample_urls": [
            "https://www.gov.br/aneel/pt-br/assuntos/tarifas",
        ],
    },
    "OFGEM": {
        "base_url": "https://www.ofgem.gov.uk",
        "sitemap_url": "https://www.ofgem.gov.uk/sitemap.xml?page=1",
        "sitemap_pattern": r"<loc>",
        "sample_urls": [
            "https://www.ofgem.gov.uk/publications/riio-ed2-final-determinations",
        ],
    },
    "FERC": {
        "base_url": "https://www.ferc.gov",
        "sitemap_url": None,
        "sample_urls": [
            "https://www.ferc.gov/industries-data/electric/industry-activities/electric-rate-cases",
        ],
    },
    "AER": {
        "base_url": "https://www.aer.gov.au",
        "sitemap_url": None,
        "sample_urls": [
            "https://www.aer.gov.au/industry/networks/rate-of-return",
        ],
    },
}


def probe_source(source: str, timeout: float = 10.0) -> ProbeResult:
    """
    Run a fast health check for a single source.

    Target: <30 seconds total. Checks:
    1. Base URL reachability (HEAD request)
    2. Sitemap availability and URL count
    3. Sample URLs returning 2xx

    Args:
        source: Source name (e.g. "IFC", "EBRD")
        timeout: HTTP timeout per request in seconds

    Returns:
        ProbeResult with detailed check results
    """
    config = _SOURCE_CONFIG.get(source.upper())
    if not config:
        return ProbeResult(source=source, error=f"Unknown source: {source}")

    result = ProbeResult(source=source)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # 1. Base URL reachability
    t0 = time.time()
    try:
        resp = session.head(config["base_url"], timeout=timeout, allow_redirects=True)
        result.reachable = resp.status_code < 400
        result.status_code = resp.status_code
        result.latency_ms = (time.time() - t0) * 1000
    except Exception as e:
        result.latency_ms = (time.time() - t0) * 1000
        result.error = str(e)[:200]
        return result

    # 2. Sitemap check
    sitemap_url = config.get("sitemap_url")
    if sitemap_url:
        try:
            resp = session.get(sitemap_url, timeout=timeout)
            if resp.status_code == 200:
                pattern = config.get("sitemap_pattern", r"<loc>")
                urls = re.findall(pattern, resp.text)
                result.sitemap_available = len(urls) > 0
                result.sitemap_url_count = len(urls)
        except Exception:
            pass

    # 3. Sample URLs
    for url in config.get("sample_urls", []):
        result.sample_urls_checked += 1
        try:
            resp = session.head(url, timeout=timeout, allow_redirects=True)
            if resp.status_code < 400:
                result.sample_urls_valid += 1
        except Exception:
            pass

    session.close()
    return result


def probe_all(sources: Optional[list[str]] = None, timeout: float = 10.0) -> list[ProbeResult]:
    """Run probes for configured sources.

    Args:
        sources: Optional list of source names to probe. If None, probes all.
        timeout: HTTP timeout per request in seconds.

    Returns:
        List of ProbeResult objects, sorted by status (RED first).
    """
    targets = [s.upper() for s in sources] if sources else list(_SOURCE_CONFIG.keys())
    results = []
    for source in targets:
        if source.upper() in _SOURCE_CONFIG:
            logger.info(f"Probing {source}...")
            results.append(probe_source(source, timeout=timeout))

    # Sort: RED first, then YELLOW, then GREEN
    order = {RED: 0, YELLOW: 1, GREEN: 2}
    results.sort(key=lambda r: order.get(r.status, 9))
    return results


def format_probe_table(results: list[ProbeResult]) -> str:
    """Format probe results as a printable table."""
    lines = [
        f"{'':>3} {'Source':<8} {'Reach':>5} {'Sitemap':>7} {'URLs':>8} {'Latency':>8} {'Error'}",
        "-" * 70,
    ]
    for r in results:
        lines.append(
            f"{r.status_emoji:>3} {r.source:<8} "
            f"{'✓' if r.reachable else '✗':>5} "
            f"{'✓' if r.sitemap_available else '—':>7} "
            f"{r.sample_urls_valid}/{r.sample_urls_checked:>6} "
            f"{r.latency_ms:>7.0f}ms "
            f"{(r.error or '')[:40]}"
        )
    green = sum(1 for r in results if r.status == GREEN)
    yellow = sum(1 for r in results if r.status == YELLOW)
    red = sum(1 for r in results if r.status == RED)
    lines.append("-" * 70)
    lines.append(f"🟢 {green} GREEN  🟡 {yellow} YELLOW  🔴 {red} RED")
    return "\n".join(lines)
