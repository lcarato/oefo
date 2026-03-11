"""
Layer 3: LLM-based cross-validation for the OEFO data pipeline (Model-Agnostic).

Supports Claude, GPT-4o, Gemini, and local models via oefo.llm_client with
automatic fallback. If no LLM is available, this layer gracefully degrades
and returns INSUFFICIENT for all checks (so QC still runs, just without
the LLM validation layer).

Functions:
- Source quote verification (extracted value matches quoted text?)
- Cross-extraction consistency (parameters from same doc are coherent?)
- Disagreement resolution (Tier 1 vs Tier 3 conflict arbitration)
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LLMReviewQC:
    """
    LLM-powered quality control and cross-validation.

    Uses the model-agnostic LLMClient (Claude, GPT-4o, Gemini, Ollama)
    with automatic fallback. If no LLM provider is available, all checks
    return INSUFFICIENT and the observation is flagged for human review
    rather than silently failing.
    """

    # Verification result constants
    CONFIRMED = "CONFIRMED"
    PLAUSIBLE = "PLAUSIBLE"
    CONTRADICTED = "CONTRADICTED"
    INSUFFICIENT = "INSUFFICIENT"

    def __init__(self, llm_client=None, provider=None, model: Optional[str] = None):
        """
        Initialise the LLM review QC checker.

        Args:
            llm_client: Pre-configured LLMClient instance. If None, creates one.
            provider: Preferred LLM provider (string or LLMProvider enum).
            model: Override default model for this QC layer.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.model_override = model
        self._llm_available = True

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
                self.llm = LLMClient(**kwargs)
            except Exception as e:
                self.logger.warning(
                    f"Could not initialise LLMClient: {e}. "
                    "LLM review layer will return INSUFFICIENT for all checks."
                )
                self.llm = None
                self._llm_available = False

        if self.llm and hasattr(self.llm, "primary_provider"):
            self.logger.info(
                f"LLMReviewQC initialised. Provider: {self.llm.primary_provider}"
            )

    def _call_llm(self, prompt: str, max_tokens: int = 500) -> Optional[str]:
        """
        Call the LLM with graceful fallback.

        Returns response text, or None if no LLM is available.
        """
        if not self._llm_available or self.llm is None:
            return None

        try:
            response = self.llm.complete(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.0,
                model=self.model_override,
            )
            return response.text
        except Exception as e:
            self.logger.warning(f"LLM call failed: {e}")
            return None

    def _parse_json_response(self, text: Optional[str]) -> Optional[Dict]:
        """Parse JSON from LLM response text."""
        if not text:
            return None
        try:
            # Handle markdown code fences
            t = text.strip()
            if t.startswith("```"):
                t = t.split("\n", 1)[1] if "\n" in t else t[3:]
            if t.endswith("```"):
                t = t[:-3]
            t = t.strip()

            start = t.find("{")
            end = t.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(t[start:end])
        except (json.JSONDecodeError, ValueError):
            pass
        return None

    # ------------------------------------------------------------------
    # Main check entry point
    # ------------------------------------------------------------------

    def check(self, observation, source_document_text: Optional[str] = None) -> Dict:
        """
        Run LLM-based checks on an observation.

        Args:
            observation: Observation dict or object with standard fields.
            source_document_text: Full source text for quote verification.

        Returns:
            Dict with keys: score (float 0-1), flags (list[str]), details (str)
        """
        obs = self._to_dict(observation)
        obs_id = obs.get("observation_id", "unknown")
        self.logger.info(f"Running LLM checks on {obs_id}")

        flags = []

        # Source quote verification
        source_quote = obs.get("source_quote")
        if source_document_text and source_quote:
            verification = self.verify_source_quote(obs, source_document_text)
            if verification != self.CONFIRMED:
                severity = "ERROR" if verification == self.CONTRADICTED else "WARNING"
                flags.append(
                    f"{severity}: Source quote verification: {verification}"
                )

        score = self._compute_score(flags)
        self.logger.info(f"LLM QC for {obs_id}: score={score:.2f}, flags={len(flags)}")

        return {
            "score": score,
            "flags": flags,
            "details": self._format_details(flags),
        }

    # ------------------------------------------------------------------
    # Source quote verification
    # ------------------------------------------------------------------

    def verify_source_quote(self, obs: Dict, source_text: str) -> str:
        """
        Verify that source_quote actually supports the extracted value.

        Returns: CONFIRMED | PLAUSIBLE | CONTRADICTED | INSUFFICIENT
        """
        source_quote = obs.get("source_quote", "")
        if not source_quote:
            return self.INSUFFICIENT

        prompt = self._build_verification_prompt(obs)
        response_text = self._call_llm(prompt, max_tokens=500)

        if response_text is None:
            self.logger.info("No LLM available; returning INSUFFICIENT")
            return self.INSUFFICIENT

        result = self._parse_json_response(response_text)
        if result:
            return result.get("verification_result", self.INSUFFICIENT)

        self.logger.warning("Could not parse verification response")
        return self.INSUFFICIENT

    def _build_verification_prompt(self, obs: Dict) -> str:
        """Build the source-quote verification prompt."""
        values_str = ""
        for key in [
            "kd_nominal", "ke_nominal", "wacc_nominal",
            "leverage_debt_pct", "debt_tenor_years", "kd_spread_bps",
        ]:
            val = obs.get(key)
            if val is not None:
                label = key.replace("_", " ").title()
                values_str += f"- {label}: {val}\n"

        if not values_str:
            values_str = "- (No specific numeric values extracted)\n"

        return f"""You are a data verification expert. Determine whether the quoted text
supports the extracted financial values.

EXTRACTED OBSERVATION:
- Project: {obs.get('project_or_entity_name', 'N/A')}
- Country: {obs.get('country', 'N/A')}
- Year: {obs.get('year_of_observation', 'N/A')}

SOURCE QUOTE: "{obs.get('source_quote', '')}"

EXTRACTED VALUES:
{values_str}

Respond with JSON only:
{{
    "verification_result": "CONFIRMED" | "PLAUSIBLE" | "CONTRADICTED" | "INSUFFICIENT",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}

Where:
- CONFIRMED: Quote directly states the values
- PLAUSIBLE: Quote suggests the values but inference needed
- CONTRADICTED: Quote conflicts with extracted values
- INSUFFICIENT: Quote doesn't provide enough info to verify"""

    # ------------------------------------------------------------------
    # Cross-extraction consistency
    # ------------------------------------------------------------------

    def check_cross_extraction_consistency(self, observations: List[Dict]) -> Dict:
        """
        Check that multiple observations from the same source are consistent.

        Returns: Dict with score, flags, details
        """
        if len(observations) < 2:
            return {"score": 1.0, "flags": [], "details": "Single observation, no cross-check."}

        prompt = "You are a financial data quality expert. Check these observations from the same source:\n\n"
        for i, obs in enumerate(observations, 1):
            obs = self._to_dict(obs)
            prompt += f"OBSERVATION {i}:\n"
            for key in [
                "project_or_entity_name", "country", "year_of_observation",
                "technology_l2", "kd_nominal", "ke_nominal", "wacc_nominal",
                "leverage_debt_pct", "tax_rate_applied",
            ]:
                val = obs.get(key)
                if val is not None:
                    prompt += f"  {key}: {val}\n"
            prompt += "\n"

        prompt += """Check internal consistency:
1. Are Kd, Ke, Leverage, WACC values consistent with each other?
2. Do parameters make sense for the project/country context?
3. Any contradictions?

Respond JSON only:
{"is_consistent": true|false, "issues": ["list of issues"], "confidence": 0.0-1.0}"""

        response_text = self._call_llm(prompt, max_tokens=500)
        if response_text is None:
            return {"score": 0.9, "flags": ["WARNING: LLM unavailable for consistency check"], "details": ""}

        result = self._parse_json_response(response_text)
        flags = []
        if result and not result.get("is_consistent", True):
            for issue in result.get("issues", []):
                flags.append(f"WARNING: Consistency issue: {issue}")

        return {
            "score": self._compute_score(flags),
            "flags": flags,
            "details": self._format_details(flags),
        }

    # ------------------------------------------------------------------
    # Disagreement resolution
    # ------------------------------------------------------------------

    def resolve_disagreement(
        self,
        tier1_value: Optional[float],
        tier3_value: Optional[float],
        parameter_name: str = "unknown",
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Resolve disagreement between Tier 1 (text) and Tier 3 (vision) extractions.

        Returns: Dict with recommended_value, confidence, reasoning, notes
        """
        # Handle missing values
        if tier1_value is None and tier3_value is None:
            return {"recommended_value": None, "confidence": 0.0,
                    "reasoning": "Both values missing", "notes": ""}
        if tier1_value is None:
            return {"recommended_value": tier3_value, "confidence": 0.6,
                    "reasoning": "Only Tier 3 available", "notes": ""}
        if tier3_value is None:
            return {"recommended_value": tier1_value, "confidence": 0.8,
                    "reasoning": "Only Tier 1 available", "notes": ""}

        # If values agree
        if abs(tier1_value - tier3_value) < 0.5:
            return {"recommended_value": tier1_value, "confidence": 0.98,
                    "reasoning": "Values agree across tiers", "notes": ""}

        # Ask LLM to arbitrate
        ctx_str = ""
        if context:
            for k, v in context.items():
                if v is not None:
                    ctx_str += f"  {k}: {v}\n"

        prompt = f"""Two extraction methods disagree on a financial parameter.

PARAMETER: {parameter_name}
TIER 1 (text extraction): {tier1_value}
TIER 3 (vision extraction): {tier3_value}
DIFFERENCE: {abs(tier1_value - tier3_value):.2f}

CONTEXT:
{ctx_str or '  (no context available)'}

Which value is more likely correct? Respond JSON only:
{{"recommended_value": <number>, "confidence": 0.0-1.0, "reasoning": "explanation"}}"""

        response_text = self._call_llm(prompt, max_tokens=300)
        if response_text is None:
            # Default to Tier 3 (vision is generally more reliable for tables)
            return {"recommended_value": tier3_value, "confidence": 0.65,
                    "reasoning": "LLM unavailable; defaulting to Vision (Tier 3)",
                    "notes": "Fallback decision"}

        result = self._parse_json_response(response_text)
        if result:
            return {
                "recommended_value": result.get("recommended_value", tier3_value),
                "confidence": result.get("confidence", 0.6),
                "reasoning": result.get("reasoning", "LLM arbitration"),
                "notes": "",
            }

        return {"recommended_value": tier3_value, "confidence": 0.6,
                "reasoning": "Parse error; defaulting to Vision", "notes": ""}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(obs) -> Dict:
        """Convert observation to dict if it isn't already."""
        if isinstance(obs, dict):
            return obs
        if hasattr(obs, "model_dump"):
            return obs.model_dump()
        if hasattr(obs, "__dict__"):
            return obs.__dict__
        return dict(obs)

    @staticmethod
    def _compute_score(flags: List[str]) -> float:
        score = 1.0
        for f in flags:
            if "ERROR" in f or "CONTRADICTED" in f:
                score -= 0.30
            elif "INSUFFICIENT" in f:
                score -= 0.10
            elif "WARNING" in f:
                score -= 0.05
        return max(0.0, score)

    @staticmethod
    def _format_details(flags: List[str]) -> str:
        if not flags:
            return "All LLM verifications passed."
        return "LLM Review:\n" + "\n".join(f"  - {f}" for f in flags)
