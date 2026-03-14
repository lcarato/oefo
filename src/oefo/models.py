"""
Core data models for the Open Energy Finance Observatory (OEFO) project.

This module defines Pydantic v2 models for:
- Observation: The primary data entity containing energy project financing parameters
- ExtractionResult: Intermediate result from extraction pipeline
- QCResult: Output of QC agent validation
- RawDocument: Metadata for downloaded source documents
- ScrapingTask: Tracking information for data scraping tasks
- ProvenanceChain: Full traceability record linking observations to source documents

All models include cross-field validation and type hints.
Every observation carries a complete provenance chain ensuring full traceability
back to the original source document, page, and verbatim quote.
"""

from datetime import date, datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

# Import canonical enum definitions from taxonomy (single source of truth)
from oefo.config.taxonomy import (
    Scale,
    DebtType,
    ProjectStatus,
    ExtractionTier,
    ValueChainPosition,
    SourceType,
    ConfidenceLevel,
    QCStatus,
    ExtractionMethod,
    KEEstimationMethod,
    KDRateBenchmark,
    LeverageBasis,
)


# ============================================================================
# Enum Classes (models-only — not in taxonomy.py)
# ============================================================================

class DocumentStatus(str, Enum):
    """Status of scraped/downloaded documents."""
    PENDING = "pending"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    FAILED = "failed"
    ERROR = "error"


class TraceabilityLevel(str, Enum):
    """Traceability completeness level for an observation."""
    FULL = "full"          # All provenance fields present (URL + page + quote)
    PARTIAL = "partial"    # Some provenance fields missing
    MINIMAL = "minimal"    # Only source type and institution known


# ============================================================================
# Provenance Chain Model
# ============================================================================

class ProvenanceChain(BaseModel):
    """
    Complete provenance record linking an observation to its original source.

    Every observation must carry a ProvenanceChain that records:
    - WHERE the data came from (document URL, local path, content hash)
    - WHAT page/section/table the data was found on
    - The VERBATIM quote supporting each extracted value
    - HOW the data was extracted (tier, model, prompt)
    - WHEN each step occurred (download, extraction, QC timestamps)

    This ensures full traceability from any data point in the final database
    back to the original source document and exact location within it.
    """

    # Document identity — links to RawDocument
    source_document_id: str = Field(
        ...,
        description="Foreign key to RawDocument.document_id"
    )
    source_document_url: str = Field(
        ...,
        description="URL where the source document was obtained"
    )
    source_document_hash: Optional[str] = Field(
        None,
        description="SHA-256 hash of the source document for integrity verification"
    )
    source_local_path: Optional[str] = Field(
        None,
        description="Local file path to the cached source document"
    )

    # Location within document
    source_page_numbers: List[int] = Field(
        default_factory=list,
        description="Page number(s) where the data was found (1-indexed)"
    )
    source_table_or_section: Optional[str] = Field(
        None,
        description="Table name, section heading, or figure reference within the document"
    )

    # Verbatim evidence
    source_quotes: List[str] = Field(
        default_factory=list,
        description="Verbatim quote(s) from the source document supporting extracted values"
    )
    source_context: Optional[str] = Field(
        None,
        description="Broader context around the quote (e.g., surrounding paragraph)"
    )

    # Extraction metadata
    extraction_tier: Optional[str] = Field(
        None,
        description="Extraction tier used: TIER_1_TEXT, TIER_2_OCR, TIER_3_VISION, TIER_4_HUMAN"
    )
    extraction_model: Optional[str] = Field(
        None,
        description="LLM model used for extraction (e.g., 'claude-opus-4.6', 'gpt-5.4')"
    )
    extraction_prompt_version: Optional[str] = Field(
        None,
        description="Version/hash of the extraction prompt used"
    )

    # Timestamps
    document_download_date: Optional[datetime] = Field(
        None,
        description="When the source document was downloaded"
    )
    extraction_timestamp: Optional[datetime] = Field(
        None,
        description="When the data was extracted from the document"
    )

    # Traceability assessment
    traceability_level: TraceabilityLevel = Field(
        default=TraceabilityLevel.MINIMAL,
        description="Self-assessed completeness of provenance information"
    )

    @model_validator(mode="after")
    def compute_traceability_level(self) -> "ProvenanceChain":
        """Automatically compute traceability level based on field completeness."""
        has_url = bool(self.source_document_url)
        has_pages = len(self.source_page_numbers) > 0
        has_quotes = len(self.source_quotes) > 0

        if has_url and has_pages and has_quotes:
            self.traceability_level = TraceabilityLevel.FULL
        elif has_url and (has_pages or has_quotes):
            self.traceability_level = TraceabilityLevel.PARTIAL
        else:
            self.traceability_level = TraceabilityLevel.MINIMAL

        return self


# ============================================================================
# Main Data Models
# ============================================================================

class Observation(BaseModel):
    """
    Core observation model representing a single energy project financing data point.

    This model combines:
    - Source and extraction metadata
    - Project identification and location
    - Technology and operational parameters
    - Financial parameters (debt, equity, capital structure, WACC)
    - Quality control and provenance information
    """

    # Identification & Source Metadata
    observation_id: str = Field(
        ...,
        description="Unique identifier for this observation"
    )
    source_type: SourceType = Field(
        ...,
        description="Type of source document"
    )
    source_institution: str = Field(
        ...,
        description="Name of institution that published the source document"
    )
    source_document_url: Optional[str] = Field(
        None,
        description="URL to the source document"
    )
    source_document_date: Optional[date] = Field(
        None,
        description="Publication/filing date of the source document"
    )
    extraction_date: date = Field(
        ...,
        description="Date when data was extracted from the document"
    )
    extraction_method: str = Field(
        ...,
        description="Method used for extraction (e.g., 'manual', 'ocr', 'llm', 'web_scrape')"
    )
    confidence_level: ConfidenceLevel = Field(
        ...,
        description="Confidence level in the extracted data"
    )

    # Project Identification
    project_or_entity_name: str = Field(
        ...,
        description="Name of the energy project or entity"
    )
    country: str = Field(
        ...,
        description="ISO 3166-1 alpha-3 country code where project is located"
    )
    region: Optional[str] = Field(
        None,
        description="Geographic region or subnational area"
    )

    # Technology Dimensions
    technology_l2: str = Field(
        ...,
        description="Level 2 technology classification from controlled vocabulary (~55 values)"
    )
    technology_l3: Optional[str] = Field(
        None,
        description="Level 3 technology classification or free text specification"
    )
    scale: Optional[Scale] = Field(
        None,
        description="Project scale category"
    )
    value_chain_position: Optional[ValueChainPosition] = Field(
        None,
        description="Position in the energy value chain"
    )
    project_status: Optional[ProjectStatus] = Field(
        None,
        description="Current project status"
    )
    project_capacity_mw: Optional[float] = Field(
        None,
        gt=0,
        description="Installed capacity in megawatts"
    )
    project_capacity_mwh: Optional[float] = Field(
        None,
        gt=0,
        description="Energy storage capacity in megawatt-hours"
    )
    project_capex_usd: Optional[float] = Field(
        None,
        gt=0,
        description="Capital expenditure in USD"
    )
    year_of_observation: int = Field(
        ...,
        ge=1990,
        le=2100,
        description="Year the observation applies to"
    )

    # Debt Parameters
    kd_nominal: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Nominal cost of debt in percentage points (e.g. 5.5 for 5.5%)"
    )
    kd_real: Optional[float] = Field(
        None,
        ge=-50,
        le=100,
        description="Real cost of debt in percentage points, inflation-adjusted"
    )
    kd_benchmark: Optional[str] = Field(
        None,
        description="Benchmark used to estimate cost of debt (e.g., 'SOFR', 'LIBOR', 'country_risk')"
    )
    kd_spread_bps: Optional[float] = Field(
        None,
        ge=0,
        description="Credit spread over benchmark in basis points"
    )
    debt_tenor_years: Optional[float] = Field(
        None,
        gt=0,
        description="Debt maturity/tenor in years"
    )
    debt_amount_usd: Optional[float] = Field(
        None,
        gt=0,
        description="Amount of debt financing in USD"
    )
    debt_currency: Optional[str] = Field(
        None,
        description="Currency of debt (ISO 4217 code)"
    )
    debt_type: Optional[DebtType] = Field(
        None,
        description="Type of debt instrument"
    )
    credit_rating: Optional[str] = Field(
        None,
        description="Credit rating of the debt (e.g., 'AAA', 'BB-', 'not_rated')"
    )

    # -- Concessional finance
    is_concessional: Optional[bool] = Field(
        None,
        description="Whether the debt includes concessional elements (below-market rates, longer tenors, grace periods from DFIs)"
    )
    concessional_element_description: Optional[str] = Field(
        None,
        description="Description of the concessional element if is_concessional is True"
    )

    # -- FX conversion
    debt_amount_original_currency: Optional[float] = Field(
        None, ge=0,
        description="Debt amount in original currency (millions)"
    )
    fx_rate_to_usd: Optional[float] = Field(
        None, gt=0,
        description="Exchange rate to USD at source_document_date (units of local currency per 1 USD)"
    )
    fx_rate_date: Optional[date] = Field(
        None,
        description="Date of the FX rate used for conversion"
    )

    # Equity Parameters
    ke_nominal: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Nominal cost of equity in percentage points (e.g. 12.0 for 12%)"
    )
    ke_real: Optional[float] = Field(
        None,
        ge=-50,
        le=100,
        description="Real cost of equity in percentage points, inflation-adjusted"
    )
    ke_estimation_method: Optional[str] = Field(
        None,
        description="Method used to estimate cost of equity (e.g., 'CAPM', 'dividend_growth', 'implied')"
    )

    # Capital Structure
    leverage_debt_pct: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Debt as percentage of total capital"
    )
    leverage_equity_pct: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Equity as percentage of total capital"
    )
    leverage_basis: Optional[str] = Field(
        None,
        description="Basis for leverage calculation: 'project_level' or 'corporate_level'"
    )

    # WACC (Weighted Average Cost of Capital)
    wacc_nominal: Optional[float] = Field(
        None,
        ge=-50,
        le=100,
        description="Weighted average cost of capital (nominal) in percentage points"
    )
    wacc_real: Optional[float] = Field(
        None,
        ge=-50,
        le=100,
        description="Weighted average cost of capital (real) in percentage points"
    )
    tax_rate_applied: Optional[float] = Field(
        None,
        ge=0,
        le=1,
        description="Tax rate used in WACC calculation"
    )

    # -- Concessional-adjusted WACC
    wacc_nominal_market_equivalent: Optional[float] = Field(
        None,
        ge=0, le=50,
        description="WACC computed using estimated market-equivalent debt rate instead of actual concessional rate (%)"
    )
    wacc_real_market_equivalent: Optional[float] = Field(
        None,
        ge=0, le=50,
        description="Real WACC computed using estimated market-equivalent debt rate (%)"
    )

    # Quality Control & Provenance
    extraction_tier: Optional[ExtractionTier] = Field(
        None,
        description="Data extraction tier/quality classification"
    )
    source_quote: Optional[str] = Field(
        None,
        description="Direct quote from source document supporting the data"
    )
    source_page_number: Optional[int] = Field(
        None,
        ge=1,
        description="Page number in source document where data was found"
    )
    source_document_id: Optional[str] = Field(
        None,
        description="Foreign key to RawDocument.document_id for traceability"
    )
    source_table_or_section: Optional[str] = Field(
        None,
        description="Table name, section heading, or figure reference within the document"
    )
    provenance: Optional[ProvenanceChain] = Field(
        None,
        description="Full provenance chain linking this observation to its source"
    )
    traceability_level: Optional[TraceabilityLevel] = Field(
        None,
        description="Completeness of provenance information for this observation"
    )
    qc_score: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Quality control score (0-100)"
    )
    qc_status: Optional[QCStatus] = Field(
        None,
        description="Quality control review status"
    )
    qc_flags: Optional[List[str]] = Field(
        None,
        description="List of QC flags or issues identified"
    )
    human_reviewer: Optional[str] = Field(
        None,
        description="Name or ID of human reviewer"
    )
    human_review_date: Optional[date] = Field(
        None,
        description="Date of human review"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes about this observation"
    )

    model_config = {"use_enum_values": False, "str_strip_whitespace": True}

    @field_validator("country")
    @classmethod
    def validate_country_code(cls, v: str) -> str:
        """Validate that country is a 3-letter ISO code."""
        if not (isinstance(v, str) and len(v) == 3 and v.isupper()):
            raise ValueError("Country must be ISO 3166-1 alpha-3 code (e.g., 'USA', 'GBR')")
        return v

    @model_validator(mode="after")
    def validate_leverage_sum(self) -> "Observation":
        """Validate that leverage percentages sum to approximately 100% if both provided."""
        if self.leverage_debt_pct is not None and self.leverage_equity_pct is not None:
            total = self.leverage_debt_pct + self.leverage_equity_pct
            if not (95 <= total <= 105):  # Allow 5% tolerance
                raise ValueError(
                    f"Leverage percentages must sum to ~100%: "
                    f"debt={self.leverage_debt_pct}%, equity={self.leverage_equity_pct}%, "
                    f"total={total}%"
                )
        return self

    @model_validator(mode="after")
    def compute_traceability(self) -> "Observation":
        """
        Compute traceability level based on available provenance fields.

        Traceability levels:
        - FULL: source_document_url + source_page_number + source_quote all present
        - PARTIAL: source_document_url present but missing page or quote
        - MINIMAL: Only source_type and source_institution known
        """
        has_url = bool(self.source_document_url)
        has_page = self.source_page_number is not None
        has_quote = bool(self.source_quote)

        if has_url and has_page and has_quote:
            self.traceability_level = TraceabilityLevel.FULL
        elif has_url and (has_page or has_quote):
            self.traceability_level = TraceabilityLevel.PARTIAL
        else:
            self.traceability_level = TraceabilityLevel.MINIMAL

        # If provenance chain exists, sync its level
        if self.provenance:
            self.traceability_level = self.provenance.traceability_level

        return self

    @model_validator(mode="after")
    def validate_cost_consistency(self) -> "Observation":
        """
        Validate cost of capital consistency:
        - kd_real should be less than kd_nominal
        - ke_real should be less than ke_nominal
        - kd should be less than ke
        - WACC should be between kd and ke
        """
        if self.kd_nominal is not None and self.kd_real is not None:
            if self.kd_real > self.kd_nominal:
                raise ValueError(
                    f"Real cost of debt ({self.kd_real}) cannot exceed nominal ({self.kd_nominal})"
                )

        if self.ke_nominal is not None and self.ke_real is not None:
            if self.ke_real > self.ke_nominal:
                raise ValueError(
                    f"Real cost of equity ({self.ke_real}) cannot exceed nominal ({self.ke_nominal})"
                )

        if self.kd_nominal is not None and self.ke_nominal is not None:
            if self.kd_nominal > self.ke_nominal:
                raise ValueError(
                    f"Cost of debt ({self.kd_nominal}) cannot exceed cost of equity ({self.ke_nominal})"
                )

        if self.wacc_nominal is not None:
            if self.kd_nominal is not None and self.wacc_nominal < self.kd_nominal:
                raise ValueError(
                    f"WACC ({self.wacc_nominal}) cannot be less than cost of debt ({self.kd_nominal})"
                )
            if self.ke_nominal is not None and self.wacc_nominal > self.ke_nominal:
                raise ValueError(
                    f"WACC ({self.wacc_nominal}) cannot exceed cost of equity ({self.ke_nominal})"
                )

        return self



class ExtractionResult(BaseModel):
    """
    Intermediate result from the extraction pipeline before QC validation.

    This represents data extracted by the LLM or other extraction method
    before it has been reviewed by the QC agent.
    """

    extraction_id: str = Field(
        ...,
        description="Unique identifier for this extraction attempt"
    )
    observation: Observation = Field(
        ...,
        description="The extracted observation data"
    )
    source_document_url: str = Field(
        ...,
        description="URL of the source document"
    )
    extraction_timestamp: datetime = Field(
        ...,
        description="When the extraction occurred"
    )
    extraction_agent: str = Field(
        ...,
        description="Name of the agent/method that performed extraction"
    )
    raw_extraction_text: Optional[str] = Field(
        None,
        description="Raw text from which data was extracted"
    )
    extraction_prompt: Optional[str] = Field(
        None,
        description="The prompt used to guide extraction (for transparency)"
    )
    extraction_model: Optional[str] = Field(
        None,
        description="Model/version used for extraction (e.g., 'claude-opus-4.6')"
    )
    processing_time_seconds: Optional[float] = Field(
        None,
        ge=0,
        description="Time taken to perform extraction"
    )


class QCResult(BaseModel):
    """
    Output of the QC agent validation process.

    Contains validation results, flags, and human-actionable feedback
    for each extracted observation.
    """

    qc_id: str = Field(
        ...,
        description="Unique identifier for this QC review"
    )
    observation_id: str = Field(
        ...,
        description="Reference to the observation being reviewed"
    )
    extraction_id: Optional[str] = Field(
        None,
        description="Reference to the extraction result"
    )
    qc_timestamp: datetime = Field(
        ...,
        description="When the QC review was conducted"
    )
    qc_agent: str = Field(
        ...,
        description="Name of the QC agent/process"
    )

    # Validation Results
    qc_status: QCStatus = Field(
        ...,
        description="Overall QC status"
    )
    qc_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Overall quality score (0-100)"
    )

    # Issue Tracking
    qc_flags: List[str] = Field(
        default_factory=list,
        description="List of issues or flags identified during QC"
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors that failed"
    )
    validation_warnings: List[str] = Field(
        default_factory=list,
        description="List of validation warnings (non-blocking)"
    )

    # Detailed Feedback
    summary: Optional[str] = Field(
        None,
        description="Summary of QC findings"
    )
    details: Optional[str] = Field(
        None,
        description="Detailed explanation of issues and recommendations"
    )
    recommended_action: Optional[str] = Field(
        None,
        description="Recommended action (e.g., 'approve', 'request_revision', 'reject')"
    )

    # Human Review Linkage
    human_reviewer: Optional[str] = Field(
        None,
        description="Human reviewer assigned to this QC result"
    )
    human_review_timestamp: Optional[datetime] = Field(
        None,
        description="When human review was completed"
    )
    human_review_notes: Optional[str] = Field(
        None,
        description="Notes from human reviewer"
    )


class RawDocument(BaseModel):
    """
    Metadata for downloaded/scraped source documents.

    Tracks document location, integrity, and properties to support
    deduplication and audit trails.
    """

    document_id: str = Field(
        ...,
        description="Unique identifier for this document"
    )
    source_url: str = Field(
        ...,
        description="URL where document was downloaded from"
    )
    local_file_path: Optional[str] = Field(
        None,
        description="Local file system path where document is stored"
    )
    content_hash: str = Field(
        ...,
        description="SHA-256 hash of document content for deduplication"
    )
    source_type: SourceType = Field(
        ...,
        description="Type of source"
    )
    source_institution: Optional[str] = Field(
        None,
        description="Name of institution that published the document"
    )

    # Download Metadata
    download_date: datetime = Field(
        ...,
        description="When the document was downloaded"
    )
    download_status: DocumentStatus = Field(
        default=DocumentStatus.DOWNLOADED,
        description="Status of the download attempt"
    )
    download_error: Optional[str] = Field(
        None,
        description="Error message if download failed"
    )

    # Document Properties
    file_size_bytes: Optional[int] = Field(
        None,
        ge=0,
        description="File size in bytes"
    )
    mime_type: Optional[str] = Field(
        None,
        description="MIME type of the document (e.g., 'application/pdf')"
    )
    document_date: Optional[date] = Field(
        None,
        description="Publication/filing date of the document (if extractable)"
    )
    document_title: Optional[str] = Field(
        None,
        description="Title of the document (if extractable)"
    )

    # Processing
    extracted_count: int = Field(
        default=0,
        ge=0,
        description="Number of observations extracted from this document"
    )
    last_processed_date: Optional[datetime] = Field(
        None,
        description="Last time this document was processed for data extraction"
    )

    # Audit
    notes: Optional[str] = Field(
        None,
        description="Additional notes about the document"
    )


class ScrapingTask(BaseModel):
    """
    Tracking information for data scraping/collection tasks.

    Used to manage and monitor ongoing data collection from specific
    sources or URLs.
    """

    task_id: str = Field(
        ...,
        description="Unique identifier for this scraping task"
    )
    source_name: str = Field(
        ...,
        description="Human-readable name of the data source"
    )
    url_pattern: str = Field(
        ...,
        description="URL pattern or base URL for scraping"
    )
    source_type: SourceType = Field(
        ...,
        description="Type of source being scraped"
    )

    # Task Status
    status: DocumentStatus = Field(
        default=DocumentStatus.PENDING,
        description="Current status of the scraping task"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this task should be executed"
    )

    # Scheduling
    last_run: Optional[datetime] = Field(
        None,
        description="Timestamp of the last scraping run"
    )
    next_run: Optional[datetime] = Field(
        None,
        description="Timestamp of the next scheduled scraping run"
    )
    run_frequency_days: Optional[int] = Field(
        None,
        ge=1,
        description="How often to run this task (in days)"
    )

    # Results Tracking
    documents_found: int = Field(
        default=0,
        ge=0,
        description="Number of documents found in last run"
    )
    documents_downloaded: int = Field(
        default=0,
        ge=0,
        description="Number of documents successfully downloaded in last run"
    )
    documents_total: int = Field(
        default=0,
        ge=0,
        description="Total documents downloaded for this source"
    )

    # Error Tracking
    last_error: Optional[str] = Field(
        None,
        description="Description of the last error encountered"
    )
    error_count: int = Field(
        default=0,
        ge=0,
        description="Number of consecutive errors"
    )

    # Configuration
    request_timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Request timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retries on failure"
    )

    # Metadata
    created_date: datetime = Field(
        ...,
        description="When this task was created"
    )
    updated_date: datetime = Field(
        ...,
        description="Last time this task was updated"
    )
    notes: Optional[str] = Field(
        None,
        description="Additional notes about this scraping task"
    )


# ============================================================================
# Export public API
# ============================================================================

__all__ = [
    "Observation",
    "ExtractionResult",
    "QCResult",
    "RawDocument",
    "ScrapingTask",
    "ProvenanceChain",
    "SourceType",
    "ConfidenceLevel",
    "ProjectStatus",
    "Scale",
    "ValueChainPosition",
    "DebtType",
    "ExtractionTier",
    "QCStatus",
    "DocumentStatus",
    "TraceabilityLevel",
]
