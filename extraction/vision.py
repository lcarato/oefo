"""
Tier 3: Vision-Based Extraction (Model-Agnostic)

Uses LLM vision capabilities to extract structured financial data from PDF pages.
Supports Claude, GPT-4o, Gemini, and Ollama (LLaVA) with automatic fallback.

Key Features:
- Model-agnostic: works with any vision-capable LLM via oefo.llm_client
- Source-type specific prompts (regulatory, DFI, corporate, bond)
- Multilingual content handling
- Cost optimization through financial page pre-filtering
- Structured JSON output with source quotes and confidence scoring
"""

import base64
import json
import logging
import os
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Optional imports with graceful degradation
try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

try:
    from PIL import Image
except ImportError:
    Image = None

# Vision API defaults
MAX_PAGES_PER_EXTRACTION = 10
DEFAULT_DPI = 250


class VisionExtractor:
    """
    Extract financial data from PDFs using vision-capable LLMs.

    Uses the model-agnostic LLMClient from oefo.llm_client, which supports
    Claude, GPT-4o, Gemini, and local models with automatic fallback.
    """

    def __init__(
        self,
        llm_client=None,
        provider=None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        logger_instance: Optional[logging.Logger] = None,
    ):
        """
        Initialise VisionExtractor.

        Args:
            llm_client: Pre-configured LLMClient instance. If None, creates one.
            provider: Preferred LLM provider (LLMProvider enum). If None, auto-detects.
            api_key: API key for the preferred provider. Falls back to env vars.
            model: Override default model name for vision calls.
            logger_instance: Optional custom logger.
        """
        self.logger = logger_instance or logger
        self.model_override = model
        self._check_dependencies()

        # Initialise LLM client
        if llm_client is not None:
            self.llm = llm_client
        else:
            try:
                from oefo.llm_client import LLMClient, LLMProvider

                kwargs = {}
                if provider:
                    kwargs["provider"] = (
                        provider if isinstance(provider, LLMProvider)
                        else LLMProvider(provider)
                    )
                if api_key and provider:
                    from oefo.llm_client import LLMProvider as LP
                    prov = provider if isinstance(provider, LP) else LP(provider)
                    kwargs["api_keys"] = {prov: api_key}

                self.llm = LLMClient(**kwargs)
            except ImportError:
                # Fallback: try direct Anthropic client
                self.logger.warning(
                    "oefo.llm_client not available. Falling back to direct Anthropic SDK."
                )
                self.llm = self._build_legacy_client(api_key)

        primary = getattr(self.llm, "primary_provider", "legacy-anthropic")
        self.logger.info(f"VisionExtractor initialised. LLM provider: {primary}")

    def _build_legacy_client(self, api_key: Optional[str] = None):
        """Build a minimal wrapper around the Anthropic SDK as legacy fallback."""
        try:
            from anthropic import Anthropic
        except ImportError:
            raise ImportError(
                "No LLM backend available. Install anthropic, openai, or google-generativeai."
            )

        api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("No API key found. Set ANTHROPIC_API_KEY.")

        client = Anthropic(api_key=api_key)

        class _LegacyClient:
            """Minimal shim matching LLMClient interface for vision calls."""

            primary_provider = "anthropic-legacy"

            def vision(self_, images, prompt, system=None, max_tokens=4096,
                       temperature=0.0, model=None):
                content = []
                for i, img_data in enumerate(images):
                    b64 = (
                        base64.b64encode(img_data).decode("utf-8")
                        if isinstance(img_data, bytes)
                        else img_data
                    )
                    content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64},
                    })
                    content.append({"type": "text", "text": f"[Page {i + 1}]"})
                content.append({"type": "text", "text": prompt})

                kwargs = dict(
                    model=model or "claude-sonnet-4-20250514",
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": content}],
                )
                if system:
                    kwargs["system"] = system

                resp = client.messages.create(**kwargs)

                class _Resp:
                    text = resp.content[0].text
                    provider = "anthropic-legacy"
                    model_name = model or "claude-sonnet-4-20250514"
                    usage = {}

                    def json(self_):
                        try:
                            t = self_.text.strip()
                            s = t.find("{")
                            e = t.rfind("}") + 1
                            return json.loads(t[s:e]) if s >= 0 and e > s else None
                        except Exception:
                            return None

                return _Resp()

        return _LegacyClient()

    def _check_dependencies(self) -> None:
        """Verify PDF rendering dependencies."""
        if convert_from_path is None:
            self.logger.warning("pdf2image not installed. pip install pdf2image")
        if Image is None:
            self.logger.warning("Pillow not installed. pip install Pillow")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_financial_data(
        self,
        pdf_path: str,
        pages: Optional[List[int]] = None,
        source_type: str = "regulatory",
        language: Optional[str] = None,
    ) -> List[Dict]:
        """
        Extract financial data from PDF pages using vision LLM.

        Args:
            pdf_path: Path to the PDF file.
            pages: 0-indexed page numbers to process. None = all pages.
            source_type: 'regulatory' | 'dfi' | 'corporate' | 'bond'.
            language: ISO language code hint (e.g., 'pt', 'es'). Auto-detected if None.

        Returns:
            List of extraction result dicts with keys:
                page, extracted_data, confidence, notes
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if convert_from_path is None:
            self.logger.error("pdf2image required for Vision extraction")
            return []

        try:
            images = self.render_pages(str(pdf_path), pages, dpi=DEFAULT_DPI)
            if not images:
                self.logger.warning("No images rendered from PDF")
                return []

            prompt = self.build_prompt(source_type, language)
            response = self.call_vision_api(images, prompt)
            results = self.parse_response(response)

            self.logger.info(f"Extracted data from {len(results)} page(s)")
            return results

        except Exception as e:
            self.logger.error(f"Vision extraction failed: {e}")
            return []

    def render_pages(
        self,
        pdf_path: str,
        pages: Optional[List[int]] = None,
        dpi: int = DEFAULT_DPI,
    ) -> List[Dict]:
        """
        Render PDF pages to base64 PNG images.

        Returns list of dicts: {page_num, image (base64), image_bytes, width, height}
        """
        if Image is None or convert_from_path is None:
            return []

        try:
            all_images = convert_from_path(pdf_path, dpi=dpi)
            if pages is None:
                pages = list(range(len(all_images)))
            pages = pages[:MAX_PAGES_PER_EXTRACTION]

            rendered = []
            for idx in pages:
                if idx < len(all_images):
                    img = all_images[idx]
                    buf = BytesIO()
                    img.save(buf, format="PNG")
                    img_bytes = buf.getvalue()
                    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

                    rendered.append({
                        "page_num": idx,
                        "image": img_b64,
                        "image_bytes": img_bytes,
                        "width": img.width,
                        "height": img.height,
                    })

            self.logger.info(f"Rendered {len(rendered)} pages at {dpi} DPI")
            return rendered
        except Exception as e:
            self.logger.error(f"Page rendering failed: {e}")
            return []

    def build_prompt(self, source_type: str, language: Optional[str] = None) -> str:
        """Build extraction prompt for the given source type."""
        try:
            from oefo.extraction.prompts import get_prompt
            return get_prompt(source_type, language=language)
        except ImportError:
            pass

        # Inline fallback prompts
        base = (
            "You are a financial document analysis expert. "
            "Extract financial parameters from the provided PDF pages.\n\n"
            "Return valid JSON:\n"
            '{"pages": [{"page_num": <int>, "extracted_items": ['
            '{"parameter": "<name>", "value": <float|null>, '
            '"unit": "<percent|bps|ratio|null>", '
            '"basis": "<real|nominal|pre_tax|post_tax|null>", '
            '"source_quote": "<exact text>", '
            '"confidence": <0.0-1.0>, '
            '"notes": "<caveats>"}]}]}\n\n'
            "If a value is ambiguous, return null and explain in notes.\n"
            "Always provide source_quote for each parameter.\n\n"
        )

        type_addons = {
            "regulatory": (
                "REGULATORY DOCUMENT: Extract WACC, Kd, Ke, CAPM parameters "
                "(Rf, beta, ERP, CRP), leverage, allowed ROE, discount rates. "
                "Handle CAPM decomposition tables carefully."
            ),
            "dfi": (
                "DFI DISCLOSURE: Extract loan terms (amount, tenor, rate), "
                "spread over benchmark, D/E ratio, Kd, benchmark rates, "
                "maturity, grace periods."
            ),
            "corporate": (
                "CORPORATE FILING: Extract total debt, interest expense, "
                "cost of debt, WACC, credit rating, maturity schedule, "
                "leverage ratios, tax rates."
            ),
            "bond": (
                "BOND PROSPECTUS: Extract coupon rate, maturity, issue size, "
                "YTM, benchmark + spread, credit rating, use of proceeds."
            ),
        }

        prompt = base + type_addons.get(source_type, "")

        if language:
            prompt += (
                f"\n\nThe document may be in {language}. "
                "Extract values in English but preserve source quotes in the original language."
            )

        return prompt

    def call_vision_api(
        self,
        rendered_pages: List[Dict],
        prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        """
        Call the vision LLM with rendered pages and extraction prompt.

        Uses the model-agnostic LLMClient with automatic fallback.

        Returns:
            Raw response text (JSON string).
        """
        # Prepare images as bytes or base64 depending on what the client expects
        images = []
        for page in rendered_pages:
            if "image_bytes" in page:
                images.append(page["image_bytes"])
            else:
                images.append(page["image"])

        response = self.llm.vision(
            images=images,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.0,
            model=self.model_override,
        )

        response_text = response.text
        self.logger.info(
            f"Vision API response from {response.provider} "
            f"({response.model}): {len(response_text)} chars"
        )
        return response_text

    def parse_response(self, response: str) -> List[Dict]:
        """Parse Vision API JSON response into extraction results."""
        results = []
        try:
            # Extract JSON from possibly wrapped response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                data = json.loads(response[json_start:json_end])
                if "pages" in data:
                    for page_data in data["pages"]:
                        results.append({
                            "page": page_data.get("page_num"),
                            "extracted_data": page_data.get("extracted_items", []),
                            "confidence": self._avg_confidence(
                                page_data.get("extracted_items", [])
                            ),
                            "notes": None,
                        })
                self.logger.info(f"Parsed {len(results)} pages from response")
            else:
                self.logger.error("No JSON found in vision response")
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
        except Exception as e:
            self.logger.error(f"Response parse error: {e}")
        return results

    @staticmethod
    def _avg_confidence(items: List[Dict]) -> float:
        if not items:
            return 0.0
        scores = [item.get("confidence", 0.5) for item in items]
        return sum(scores) / len(scores)
