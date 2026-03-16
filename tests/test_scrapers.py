"""
Unit tests for all 8 OEFO web scrapers with mocked HTTP responses.

Tests verify that parsing logic correctly extracts URLs, metadata, and
document links from API/HTML responses without making any network calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ---------------------------------------------------------------------------
# SEC EDGAR
# ---------------------------------------------------------------------------

class TestSECEdgarScraper:
    """Tests for SEC EDGAR scraper search_by_keyword() fixes."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.sec_edgar import SECEdgarScraper
        return SECEdgarScraper(output_dir=str(tmp_path))

    def test_search_by_keyword_params(self, tmp_path):
        """search_by_keyword uses correct API params (forms, not Lucene)."""
        scraper = self._make_scraper(tmp_path)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "ciks": ["0000021076"],
                            "display_names": ["CLOROX CO /DE/  (CLX)"],
                            "form": "10-K",
                            "adsh": "0000021076-24-000042",
                            "file_date": "2024-08-08",
                            "sics": ["2842"],
                        }
                    }
                ],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response) as mock_get:
            results = scraper.search_by_keyword("cost of capital", filing_types=["10-K"])

            # Verify correct params
            call_kwargs = mock_get.call_args
            params = call_kwargs.kwargs.get("params") or call_kwargs[1].get("params")
            assert '"cost of capital"' in params["q"]
            assert params["forms"] == "10-K"
            assert "form_type:" not in params["q"]  # No Lucene syntax

    def test_search_by_keyword_field_mapping(self, tmp_path):
        """Response fields mapped correctly from _source."""
        scraper = self._make_scraper(tmp_path)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "ciks": ["0000021076"],
                            "display_names": ["ACME Corp"],
                            "form": "10-K",
                            "adsh": "0000021076-24-000042",
                            "file_date": "2024-08-08",
                            "sics": ["4911"],  # Energy SIC
                        }
                    }
                ],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            results = scraper.search_by_keyword("cost of capital", filing_types=["10-K"])

        assert len(results) == 1
        filing = results[0]
        assert filing["company"] == "ACME Corp"
        assert filing["cik"] == "21076"
        assert filing["filing_type"] == "10-K"
        assert filing["date"] == "2024-08-08"
        assert "Archives/edgar/data/21076/" in filing["url"]
        assert filing["accession"] == "0000021076-24-000042"

    def test_search_returns_all_sics(self, tmp_path):
        """All filings returned regardless of SIC code (no energy filter)."""
        scraper = self._make_scraper(tmp_path)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "ciks": ["0000000001"],
                            "display_names": ["Tech Corp"],
                            "form": "10-K",
                            "adsh": "0000000001-24-000001",
                            "file_date": "2024-01-01",
                            "sics": ["7372"],  # Software — not energy
                        }
                    },
                    {
                        "_source": {
                            "ciks": ["0000000002"],
                            "display_names": ["Power Co"],
                            "form": "10-K",
                            "adsh": "0000000002-24-000002",
                            "file_date": "2024-01-01",
                            "sics": ["4911"],  # Electric utility — energy
                        }
                    },
                ],
            }
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            results = scraper.search_by_keyword("cost of capital", filing_types=["10-K"])

        # Both filings returned — no SIC filter
        assert len(results) == 2
        assert results[0]["company"] == "Tech Corp"
        assert results[0]["sics"] == ["7372"]
        assert results[1]["company"] == "Power Co"
        assert results[1]["sics"] == ["4911"]

    def test_get_xbrl_financial_data_no_user_agent_error(self, tmp_path):
        """get_xbrl_financial_data uses session (no self.user_agent AttributeError)."""
        scraper = self._make_scraper(tmp_path)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "entityName": "Test Corp",
            "facts": {},
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper.get_xbrl_financial_data("0000012345")

        assert result["company_name"] == "Test Corp"


# ---------------------------------------------------------------------------
# GCF
# ---------------------------------------------------------------------------

class TestGCFScraper:
    """Tests for GCF scraper list_projects() and download_funding_proposal()."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.gcf import GCFScraper
        return GCFScraper(output_dir=str(tmp_path))

    def test_list_projects_uses_sitemap(self, tmp_path):
        """list_projects uses sitemap as primary discovery."""
        scraper = self._make_scraper(tmp_path)

        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset>
            <url><loc>https://www.greenclimate.fund/project/fp001</loc></url>
            <url><loc>https://www.greenclimate.fund/project/fp003</loc></url>
            <url><loc>https://www.greenclimate.fund/about</loc></url>
        </urlset>"""

        def mock_get(url, **kwargs):
            resp = MagicMock()
            if "sitemap.xml" in url:
                resp.status_code = 200
                resp.text = sitemap_xml if "page=1" in url else "<urlset></urlset>"
                resp.raise_for_status = MagicMock()
            else:
                resp.status_code = 404
            return resp

        with patch.object(scraper.session, "get", side_effect=mock_get):
            urls = scraper.list_projects(sector="energy")

        assert len(urls) == 2
        assert any("fp001" in u for u in urls)
        assert any("fp003" in u for u in urls)

    def test_list_projects_fallback_to_head_scan(self, tmp_path):
        """Falls back to HEAD scan when sitemap unavailable."""
        scraper = self._make_scraper(tmp_path)
        scraper.MAX_FP_NUMBER = 5

        call_count = {"sitemap": 0, "head": 0}

        def mock_get(url, **kwargs):
            resp = MagicMock()
            if "sitemap.xml" in url:
                call_count["sitemap"] += 1
                raise ConnectionError("Sitemap unavailable")
            return resp

        def mock_head(url, **kwargs):
            call_count["head"] += 1
            resp = MagicMock()
            if "fp001" in url or "fp003" in url:
                resp.status_code = 200
            else:
                resp.status_code = 404
            return resp

        with patch.object(scraper.session, "get", side_effect=mock_get):
            with patch.object(scraper.session, "head", side_effect=mock_head):
                urls = scraper.list_projects(sector="energy")

        assert len(urls) == 2
        assert call_count["head"] > 0  # Used HEAD fallback

    def test_download_funding_proposal_broadened(self, tmp_path):
        """download_funding_proposal finds PDFs with /document/ URLs."""
        scraper = self._make_scraper(tmp_path)

        html = """
        <html><body>
        <a href="/document/fp001-proposal.pdf">Approved Funding Proposal</a>
        <a href="/other/nav-link">Something else</a>
        </body></html>
        """
        from bs4 import BeautifulSoup
        mock_soup = BeautifulSoup(html, "html.parser")

        mock_path = tmp_path / "test.pdf"
        mock_path.write_bytes(b"%PDF-1.4 test")

        with patch.object(scraper, "get_soup", return_value=mock_soup):
            with patch.object(scraper, "download_pdf", return_value=mock_path):
                result = scraper.download_funding_proposal("https://www.greenclimate.fund/project/fp001")

        assert result is not None


# ---------------------------------------------------------------------------
# EBRD
# ---------------------------------------------------------------------------

class TestEBRDScraper:
    """Tests for EBRD scraper sitemap + search API integration."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.ebrd import EBRDScraper
        return EBRDScraper(output_dir=str(tmp_path))

    def test_search_projects_api(self, tmp_path):
        """_search_projects_api calls the EBRD search servlet."""
        scraper = self._make_scraper(tmp_path)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resultCount": [{"resultCount": 2}],
            "searchResult": [
                {
                    "pagePath": "/content/ebrd_dxp/uk/en/home/work-with-us/projects/psd/53716.html",
                    "title": "Georgian Renewable Power",
                    "publishDate": "20 Oct 2022",
                    "description": "Green Bond",
                    "label": "Project",
                    "tags": "[sectors/energy, project/psd, countries/georgia]",
                },
            ],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper._search_projects_api("energy power renewable project")

        assert len(result["searchResult"]) == 1
        assert result["searchResult"][0]["title"] == "Georgian Renewable Power"

    def test_download_master_csv_uses_sitemap_and_api(self, tmp_path):
        """download_master_csv uses sitemap as primary + search API complement."""
        scraper = self._make_scraper(tmp_path)

        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset>
            <url><loc>https://www.ebrd.com/work-with-us/projects/psd/solar-farm.html</loc></url>
            <url><loc>https://www.ebrd.com/work-with-us/projects/psd/wind-power.html</loc></url>
            <url><loc>https://www.ebrd.com/work-with-us/projects/psd/water-treatment.html</loc></url>
            <url><loc>https://www.ebrd.com/about-us/staff.html</loc></url>
        </urlset>"""

        api_response = {
            "resultCount": [{"resultCount": 1}],
            "searchResult": [
                {
                    "pagePath": "/content/ebrd_dxp/uk/en/home/work-with-us/projects/psd/12345.html",
                    "title": "Solar Power Project",
                    "publishDate": "01 Jan 2024",
                    "label": "Project",
                    "tags": "[sectors/energy, project/psd]",
                },
            ],
        }

        def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.raise_for_status = MagicMock()
            if "sitemap.xml" in url:
                resp.text = sitemap_xml
            else:
                resp.json.return_value = api_response
            return resp

        with patch.object(scraper.session, "get", side_effect=mock_get):
            csv_path = scraper.download_master_csv()

        assert csv_path.exists()
        import pandas as pd
        df = pd.read_csv(csv_path)
        # Should have sitemap projects + API projects
        assert len(df) >= 2
        urls = df["Project URL"].tolist()
        assert any("solar-farm" in u for u in urls)
        assert any("wind-power" in u for u in urls)
        # Non-energy sitemap entries should get "Unknown" sector (not "Energy")
        water_row = df[df["Project URL"].str.contains("water-treatment")]
        assert len(water_row) == 1
        assert water_row.iloc[0]["Sector"] == "Unknown"


# ---------------------------------------------------------------------------
# IFC
# ---------------------------------------------------------------------------

class TestIFCScraper:
    """Tests for IFC scraper sitemap + REST API integration."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.ifc import IFCScraper
        return IFCScraper(output_dir=str(tmp_path))

    def test_has_api_base(self, tmp_path):
        """IFC scraper has the API base URL configured."""
        scraper = self._make_scraper(tmp_path)
        assert scraper.api_base == "https://disclosuresservice.ifc.org"

    def test_extract_project_numbers_from_sitemap(self, tmp_path):
        """_extract_project_numbers_from_sitemap parses AS-SII URLs."""
        scraper = self._make_scraper(tmp_path)

        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset>
            <url><loc>https://disclosures.ifc.org/project-detail/AS-SII/50350</loc></url>
            <url><loc>https://disclosures.ifc.org/project-detail/AS-SII/51976</loc></url>
            <url><loc>https://disclosures.ifc.org/project-detail/AS/SPI/40000</loc></url>
        </urlset>"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sitemap_xml
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            pns = scraper._extract_project_numbers_from_sitemap()

        assert len(pns) == 2
        assert "50350" in pns
        assert "51976" in pns

    def test_get_landing_projects(self, tmp_path):
        """_get_landing_projects parses the landing page API."""
        scraper = self._make_scraper(tmp_path)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "totalProjects": 2,
            "investmentProjects": [
                {
                    "ProjectID": 15165,
                    "ProjectNumber": "50350",
                    "ProjectName": "Vision One",
                    "Industry": "Power",
                },
            ],
            "advisoryProjects": [],
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            projects = scraper._get_landing_projects()

        assert len(projects) == 1
        assert projects[0]["ProjectNumber"] == "50350"

    def test_download_project_documents_json_fallback(self, tmp_path):
        """Saves JSON when SupportingDocuments is empty."""
        scraper = self._make_scraper(tmp_path)

        detail_response = {
            "ProjectName": "Test Energy Project",
            "Country": "India",
            "Industry": "Power",
            "Sector": "Infrastructure",
            "Status": "Active",
            "DisclosedDate": "2024-01-15",
            "SupportingDocuments": [],
            "ProjectOverView": {
                "Project_Description": "<p>A solar power project</p>"
            },
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = detail_response

        with patch.object(scraper.session, "get", return_value=mock_response):
            paths = scraper.download_project_documents("50350")

        assert len(paths) == 1
        assert str(paths[0]).endswith(".json")
        data = json.loads(Path(paths[0]).read_text())
        assert data["project_name"] == "Test Energy Project"
        assert data["description_html"] == "<p>A solar power project</p>"

    def test_no_duplicate_import_time(self, tmp_path):
        """IFC scraper file should not have duplicate 'import time' at end."""
        import inspect
        from oefo.scrapers import ifc
        source = inspect.getsource(ifc)
        # Count occurrences of 'import time' at module level
        lines = [l.strip() for l in source.split("\n") if l.strip() == "import time"]
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# ANEEL
# ---------------------------------------------------------------------------

class TestANEELScraper:
    """Tests for ANEEL scraper known decisions + URL migration fix."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.regulatory.aneel import ANEELScraper
        return ANEELScraper(output_dir=str(tmp_path))

    def test_base_url_updated(self, tmp_path):
        """ANEEL base_url points to gov.br, not aneel.gov.br."""
        scraper = self._make_scraper(tmp_path)
        assert "gov.br/aneel" in scraper.base_url
        assert "aneel.gov.br" not in scraper.base_url

    def test_known_decisions_included(self, tmp_path):
        """list_decisions always includes known submódulo URLs."""
        scraper = self._make_scraper(tmp_path)

        # Even when page scraping returns nothing, known decisions are included
        with patch.object(scraper, "get_soup", side_effect=ConnectionError("fail")):
            with patch.object(scraper, "_get_sitemap_urls", return_value=[]):
                decisions = scraper.list_decisions()

        assert len(decisions) >= 5
        titles = [d["title"] for d in decisions]
        assert any("Custo de Capital" in t for t in titles)
        assert any("Submódulo 2.4" in t for t in titles)
        assert any("Submódulo 12.3" in t for t in titles)

    def test_list_decisions_targets_proret(self, tmp_path):
        """list_decisions tries Proret page for tariff regulation."""
        scraper = self._make_scraper(tmp_path)

        html = """
        <html><body>
        <a href="/aneel/pt-br/doc/custo-de-capital-2024.pdf">Custo de Capital 2024</a>
        <a href="/aneel/pt-br/doc/wacc-review.pdf">Revisão WACC Distribuição</a>
        <a href="/other/nav">Navigation link</a>
        </body></html>
        """
        from bs4 import BeautifulSoup
        mock_soup = BeautifulSoup(html, "html.parser")

        with patch.object(scraper, "get_soup", return_value=mock_soup):
            with patch.object(scraper, "_get_sitemap_urls", return_value=[]):
                decisions = scraper.list_decisions()

        # Known decisions + scraped ones
        assert len(decisions) >= 7
        titles = [d["title"] for d in decisions]
        assert any("Custo de Capital 2024" in t for t in titles)
        assert any("WACC" in t for t in titles)


# ---------------------------------------------------------------------------
# AER
# ---------------------------------------------------------------------------

class TestAERScraper:
    """Tests for AER scraper timeout handling and known documents."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.regulatory.aer import AERScraper
        return AERScraper(output_dir=str(tmp_path))

    def test_known_documents_expanded(self, tmp_path):
        """AER scraper has expanded known documents list."""
        scraper = self._make_scraper(tmp_path)
        docs = scraper._known_documents()
        assert len(docs) >= 3
        titles = [d["title"] for d in docs]
        assert any("2022" in t for t in titles)
        assert any("2018" in t for t in titles)

    def test_known_documents_always_included(self, tmp_path):
        """list_decisions always includes known documents even when site is up."""
        scraper = self._make_scraper(tmp_path)

        html = """
        <html><body>
        <a href="/doc/rate-of-return-2024.pdf">Rate of Return Instrument 2024</a>
        </body></html>
        """

        def mock_get(url, **kwargs):
            resp = MagicMock()
            resp.status_code = 200
            resp.text = html
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(scraper.session, "get", side_effect=mock_get):
            decisions = scraper.list_decisions()

        # Should have both scraped + known documents
        assert len(decisions) >= 3
        urls = [d["url"] for d in decisions]
        # Known docs should be present
        assert any("rate-of-return" in u for u in urls)

    def test_list_decisions_handles_timeout(self, tmp_path):
        """list_decisions handles site timeout gracefully."""
        scraper = self._make_scraper(tmp_path)

        call_count = 0

        def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("ERR_HTTP2_PROTOCOL_ERROR")

        with patch.object(scraper.session, "get", side_effect=mock_get):
            decisions = scraper.list_decisions()

        # Should still return known documents despite all timeouts
        assert len(decisions) >= 3


# ---------------------------------------------------------------------------
# Ofgem
# ---------------------------------------------------------------------------

class TestOfgemScraper:
    """Tests for Ofgem scraper known publications + sitemap."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.regulatory.ofgem import OfgemScraper
        return OfgemScraper(output_dir=str(tmp_path))

    def test_known_publications_included(self, tmp_path):
        """list_decisions always includes known RIIO publication URLs."""
        scraper = self._make_scraper(tmp_path)

        # Even when everything else fails, known publications are returned
        with patch.object(scraper, "_get_sitemap_urls", return_value=[]):
            with patch.object(scraper, "get_soup", side_effect=ConnectionError("fail")):
                decisions = scraper.list_decisions()

        assert len(decisions) >= 6
        titles = [d["title"] for d in decisions]
        assert any("RIIO-ED2 Final Determinations" in t for t in titles)
        assert any("Sector Specific Methodology" in t for t in titles)

    def test_list_decisions_uses_publications_search(self, tmp_path):
        """list_decisions uses /search/publications as complement."""
        scraper = self._make_scraper(tmp_path)

        html = """
        <html><body>
        <a href="/publications/riio-2-final-determinations">RIIO-2 Final Determinations</a>
        <a href="/publications/cost-of-equity-methodology">Cost of equity methodology</a>
        <a href="/contact">Contact us</a>
        </body></html>
        """
        from bs4 import BeautifulSoup
        mock_soup = BeautifulSoup(html, "html.parser")

        urls_called = []
        def mock_get_soup(url):
            urls_called.append(url)
            return mock_soup

        with patch.object(scraper, "_get_sitemap_urls", return_value=[]):
            with patch.object(scraper, "get_soup", side_effect=mock_get_soup):
                decisions = scraper.list_decisions()

        # Should use publications search
        assert any("/search/publications" in url for url in urls_called)
        # Known publications + search results
        assert len(decisions) >= 6


# ---------------------------------------------------------------------------
# FERC
# ---------------------------------------------------------------------------

class TestFERCScraper:
    """Tests for FERC scraper known documents + graceful degradation."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.regulatory.ferc import FERCScraper
        return FERCScraper(output_dir=str(tmp_path))

    def test_has_elibrary_url(self, tmp_path):
        """FERC scraper has eLibrary URL configured."""
        scraper = self._make_scraper(tmp_path)
        assert scraper.elibrary_url == "https://elibrary.ferc.gov"

    def test_known_documents_included(self, tmp_path):
        """list_decisions returns known documents even when eLibrary fails."""
        scraper = self._make_scraper(tmp_path)

        def mock_get(url, **kwargs):
            raise ConnectionError("Angular SPA — WAF blocked")

        with patch.object(scraper.session, "get", side_effect=mock_get):
            decisions = scraper.list_decisions()

        assert len(decisions) >= 5
        titles = [d["title"] for d in decisions]
        assert any("Opinion No. 531" in t for t in titles)
        assert any("ROE" in t or "Return on Equity" in t for t in titles)

    def test_list_decisions_graceful_degradation(self, tmp_path):
        """FERC scraper doesn't hang or crash on eLibrary failure."""
        scraper = self._make_scraper(tmp_path)

        # Simulate Angular SPA response (empty shell, no table rows)
        html = """<!DOCTYPE html><html><head><base href="/eLibrary/">
        <link rel="stylesheet" href="styles.css"></head>
        <body><app-root></app-root></body></html>"""

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            decisions = scraper.list_decisions()

        # Should still return known documents
        assert len(decisions) >= 3
