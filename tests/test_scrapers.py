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

    def test_search_filters_non_energy_sic(self, tmp_path):
        """Non-energy SIC codes are filtered out."""
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

        assert len(results) == 1
        assert results[0]["company"] == "Power Co"

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

    def test_list_projects_uses_fp_pattern(self, tmp_path):
        """list_projects iterates /project/fpNNN, not /projects/."""
        scraper = self._make_scraper(tmp_path)
        # Limit range for test speed
        scraper.MAX_FP_NUMBER = 5

        def mock_head(url, **kwargs):
            resp = MagicMock()
            # FP001 and FP003 exist
            if "fp001" in url or "fp003" in url:
                resp.status_code = 200
            else:
                resp.status_code = 404
            return resp

        with patch.object(scraper.session, "head", side_effect=mock_head):
            with patch.object(scraper, "_is_energy_project", return_value=True):
                urls = scraper.list_projects(sector="energy")

        assert len(urls) == 2
        assert any("fp001" in u for u in urls)
        assert any("fp003" in u for u in urls)
        # No /projects/ (plural) URLs
        assert not any("/projects/" in u for u in urls)

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
    """Tests for EBRD scraper search API integration."""

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

    def test_download_master_csv_uses_api(self, tmp_path):
        """download_master_csv builds CSV from search API, not dead CSV URL."""
        scraper = self._make_scraper(tmp_path)

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

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = api_response
        mock_response.raise_for_status = MagicMock()

        with patch.object(scraper.session, "get", return_value=mock_response):
            csv_path = scraper.download_master_csv()

        assert csv_path.exists()
        import pandas as pd
        df = pd.read_csv(csv_path)
        assert len(df) >= 1
        assert "Solar Power Project" in df["Project Name"].values


# ---------------------------------------------------------------------------
# IFC
# ---------------------------------------------------------------------------

class TestIFCScraper:
    """Tests for IFC scraper REST API integration."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.ifc import IFCScraper
        return IFCScraper(output_dir=str(tmp_path))

    def test_has_api_base(self, tmp_path):
        """IFC scraper has the API base URL configured."""
        scraper = self._make_scraper(tmp_path)
        assert scraper.api_base == "https://disclosuresservice.ifc.org"

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

    def test_search_projects_returns_numbers(self, tmp_path):
        """search_projects returns project numbers, not URLs."""
        scraper = self._make_scraper(tmp_path)

        landing_data = {
            "investmentProjects": [
                {"ProjectNumber": "50001", "Industry": "Power"},
                {"ProjectNumber": "50002", "Industry": "Power"},
            ],
            "advisoryProjects": [],
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = landing_data
        mock_response.raise_for_status = MagicMock()

        # Mock landing page success, search API returns empty
        search_response = MagicMock()
        search_response.status_code = 400

        with patch.object(
            scraper.session, "get", return_value=mock_response
        ):
            with patch.object(scraper.session, "post", return_value=search_response):
                results = scraper.search_projects(sector="energy")

        assert all(isinstance(r, str) for r in results)
        assert "50001" in results

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
    """Tests for ANEEL scraper URL migration fix."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.regulatory.aneel import ANEELScraper
        return ANEELScraper(output_dir=str(tmp_path))

    def test_base_url_updated(self, tmp_path):
        """ANEEL base_url points to gov.br, not aneel.gov.br."""
        scraper = self._make_scraper(tmp_path)
        assert "gov.br/aneel" in scraper.base_url
        assert "aneel.gov.br" not in scraper.base_url

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
            decisions = scraper.list_decisions()

        assert len(decisions) >= 2
        titles = [d["title"] for d in decisions]
        assert any("Custo de Capital" in t for t in titles)
        assert any("WACC" in t for t in titles)


# ---------------------------------------------------------------------------
# AER
# ---------------------------------------------------------------------------

class TestAERScraper:
    """Tests for AER scraper fallback chain."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.regulatory.aer import AERScraper
        return AERScraper(output_dir=str(tmp_path))

    def test_known_documents_fallback(self, tmp_path):
        """AER scraper returns known documents when all else fails."""
        scraper = self._make_scraper(tmp_path)
        docs = scraper._known_documents()
        assert len(docs) >= 1
        assert "Rate of Return" in docs[0]["title"]

    def test_list_decisions_tries_multiple_urls(self, tmp_path):
        """list_decisions tries multiple URL patterns before giving up."""
        scraper = self._make_scraper(tmp_path)

        call_count = 0

        def mock_get_soup(url):
            nonlocal call_count
            call_count += 1
            # All pages fail — simulate site outage
            raise ConnectionError("ERR_HTTP2_PROTOCOL_ERROR")

        with patch.object(scraper, "get_soup", side_effect=mock_get_soup):
            decisions = scraper.list_decisions()

        # Should have tried multiple URLs and fallen back to known documents
        assert call_count >= 4  # 4 URL patterns + search attempts
        assert len(decisions) >= 1  # Known documents fallback


# ---------------------------------------------------------------------------
# Ofgem
# ---------------------------------------------------------------------------

class TestOfgemScraper:
    """Tests for Ofgem scraper publications search fix."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.regulatory.ofgem import OfgemScraper
        return OfgemScraper(output_dir=str(tmp_path))

    def test_list_decisions_uses_publications_search(self, tmp_path):
        """list_decisions uses /search/publications, not old broken URL."""
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

        with patch.object(scraper, "get_soup", side_effect=mock_get_soup):
            decisions = scraper.list_decisions()

        # Should use publications search, not the old broken URL
        assert any("/search/publications" in url for url in urls_called)
        assert len(decisions) >= 2


# ---------------------------------------------------------------------------
# FERC
# ---------------------------------------------------------------------------

class TestFERCScraper:
    """Tests for FERC scraper eLibrary search fix."""

    def _make_scraper(self, tmp_path):
        from oefo.scrapers.regulatory.ferc import FERCScraper
        return FERCScraper(output_dir=str(tmp_path))

    def test_has_elibrary_url(self, tmp_path):
        """FERC scraper has eLibrary URL configured."""
        scraper = self._make_scraper(tmp_path)
        assert scraper.elibrary_url == "https://elibrary.ferc.gov"

    def test_list_decisions_uses_elibrary(self, tmp_path):
        """list_decisions uses eLibrary search, not /search/orders."""
        scraper = self._make_scraper(tmp_path)

        html = """
        <html><body>
        <table>
        <tr>
            <td>Issuance</td>
            <td>20240101-0001</td>
            <td>2024-01-01</td>
            <td></td>
            <td></td>
            <td>Order on Cost of Equity for Pipeline Co</td>
            <td>Order | Rate Case</td>
            <td></td>
            <td><a href="/doc/20240101-0001.pdf">PDF</a></td>
        </tr>
        </table>
        </body></html>
        """
        from bs4 import BeautifulSoup
        mock_soup = BeautifulSoup(html, "html.parser")

        urls_called = []
        def mock_get_soup(url):
            urls_called.append(url)
            return mock_soup

        with patch.object(scraper, "get_soup", side_effect=mock_get_soup):
            decisions = scraper.list_decisions()

        # Should use eLibrary, not /search/orders
        assert any("eLibrary" in url for url in urls_called)
        assert not any("/search/orders" in url for url in urls_called)
        assert len(decisions) >= 1
        assert "Cost of Equity" in decisions[0]["title"]
