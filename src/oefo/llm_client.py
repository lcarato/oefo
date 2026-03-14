"""
Model-Agnostic LLM Client for OEFO Pipeline

Provides a unified interface for calling different LLM providers with automatic
fallback. The pipeline is not locked into a single vendor.

Supported providers and fallback chain:
  1. Anthropic Claude API (primary)  — claude-sonnet-4-20250514
  2. OpenAI GPT 5.4 (fallback 1) — gpt-5.4
  3. Claude Code CLI (fallback 2) — uses Max Plan subscription, no API key
  4. Ollama / Qwen 3.5 (fallback 3, fully local/offline) — qwen3.5

Usage:
    from oefo.llm_client import LLMClient, LLMProvider

    # Auto-detect available providers, prefer Claude
    client = LLMClient()

    # Force a specific provider
    client = LLMClient(provider=LLMProvider.OPENAI)

    # Text completion
    response = client.complete("Extract financial data from this text...")

    # Vision (image + text)
    response = client.vision(images=[img_bytes], prompt="Extract tables...")
"""

import base64
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from io import BytesIO
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    CLAUDE_CODE = "claude_code"
    OLLAMA = "ollama"


@dataclass
class LLMResponse:
    """Standardised response from any LLM provider."""
    text: str
    provider: LLMProvider
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    raw_response: Any = None

    def json(self) -> Optional[Dict]:
        """Attempt to parse the response text as JSON."""
        try:
            # Handle markdown code blocks
            text = self.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            # Find JSON object or array
            start = min(
                (text.find("{") if text.find("{") >= 0 else float("inf")),
                (text.find("[") if text.find("[") >= 0 else float("inf")),
            )
            if start == float("inf"):
                return None

            bracket = text[int(start)]
            end_bracket = "}" if bracket == "{" else "]"
            end = text.rfind(end_bracket)
            if end < 0:
                return None

            return json.loads(text[int(start):end + 1])
        except (json.JSONDecodeError, ValueError):
            return None


class BaseLLMBackend(ABC):
    """Abstract base class for LLM provider backends."""

    provider: LLMProvider

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is configured and available."""
        ...

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model: Optional[str] = None,
    ) -> LLMResponse:
        """Run a text completion."""
        ...

    @abstractmethod
    def vision(
        self,
        images: List[bytes],
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model: Optional[str] = None,
    ) -> LLMResponse:
        """Run a vision (image + text) completion."""
        ...

    def supports_vision(self) -> bool:
        """Whether this backend supports vision/image inputs."""
        return True


# ---------------------------------------------------------------------------
# Anthropic (Claude) Backend
# ---------------------------------------------------------------------------

class AnthropicBackend(BaseLLMBackend):
    """Anthropic Claude backend."""

    provider = LLMProvider.ANTHROPIC
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_VISION_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from anthropic import Anthropic
                self._client = Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic SDK not installed. pip install anthropic")
        return self._client

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            from anthropic import Anthropic  # noqa: F811
            return True
        except ImportError:
            return False

    def complete(self, prompt, system=None, max_tokens=4096, temperature=0.0, model=None):
        model = model or self.DEFAULT_MODEL
        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
        )
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return LLMResponse(
            text=response.content[0].text,
            provider=self.provider,
            model=model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            raw_response=response,
        )

    def vision(self, images, prompt, system=None, max_tokens=4096, temperature=0.0, model=None):
        model = model or self.DEFAULT_VISION_MODEL
        content = []

        for i, img_data in enumerate(images):
            if isinstance(img_data, bytes):
                b64 = base64.b64encode(img_data).decode("utf-8")
            elif isinstance(img_data, str):
                b64 = img_data  # already base64
            else:
                raise ValueError(f"Image {i}: expected bytes or base64 str")

            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64},
            })
            content.append({"type": "text", "text": f"[Page {i + 1}]"})

        content.append({"type": "text", "text": prompt})

        kwargs = dict(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "user", "content": content}],
        )
        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)
        return LLMResponse(
            text=response.content[0].text,
            provider=self.provider,
            model=model,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            raw_response=response,
        )


# ---------------------------------------------------------------------------
# OpenAI (GPT) Backend
# ---------------------------------------------------------------------------

class OpenAIBackend(BaseLLMBackend):
    """OpenAI GPT backend (GPT 5.4, GPT-4o, etc.)."""

    provider = LLMProvider.OPENAI
    DEFAULT_MODEL = "gpt-5.4"
    DEFAULT_VISION_MODEL = "gpt-5.4"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai SDK not installed. pip install openai")
        return self._client

    def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            from openai import OpenAI  # noqa: F811
            return True
        except ImportError:
            return False

    def complete(self, prompt, system=None, max_tokens=4096, temperature=0.0, model=None):
        model = model or self.DEFAULT_MODEL
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = response.choices[0]
        return LLMResponse(
            text=choice.message.content,
            provider=self.provider,
            model=model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            raw_response=response,
        )

    def vision(self, images, prompt, system=None, max_tokens=4096, temperature=0.0, model=None):
        model = model or self.DEFAULT_VISION_MODEL
        content = []

        for i, img_data in enumerate(images):
            if isinstance(img_data, bytes):
                b64 = base64.b64encode(img_data).decode("utf-8")
            elif isinstance(img_data, str):
                b64 = img_data
            else:
                raise ValueError(f"Image {i}: expected bytes or base64 str")

            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}"},
            })

        content.append({"type": "text", "text": prompt})

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = response.choices[0]
        return LLMResponse(
            text=choice.message.content,
            provider=self.provider,
            model=model,
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            raw_response=response,
        )


# ---------------------------------------------------------------------------
# Ollama (Local) Backend — Qwen 3.5 default
# ---------------------------------------------------------------------------

class OllamaBackend(BaseLLMBackend):
    """
    Ollama local model backend (Qwen 3.5 default).

    Runs entirely on the local machine — no API keys, no network calls to
    third-party services. Useful for privacy-sensitive documents or offline use.
    """

    provider = LLMProvider.OLLAMA
    DEFAULT_MODEL = "qwen3.5"
    DEFAULT_VISION_MODEL = "qwen3.5"

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def is_available(self) -> bool:
        try:
            import requests
            resp = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def complete(self, prompt, system=None, max_tokens=4096, temperature=0.0, model=None):
        import requests
        model_name = model or self.DEFAULT_MODEL

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system

        resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        return LLMResponse(
            text=data.get("response", ""),
            provider=self.provider,
            model=model_name,
            usage={
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
            },
            raw_response=data,
        )

    def vision(self, images, prompt, system=None, max_tokens=4096, temperature=0.0, model=None):
        import requests
        model_name = model or self.DEFAULT_VISION_MODEL

        image_b64_list = []
        for img_data in images:
            if isinstance(img_data, bytes):
                image_b64_list.append(base64.b64encode(img_data).decode("utf-8"))
            elif isinstance(img_data, str):
                image_b64_list.append(img_data)

        payload = {
            "model": model_name,
            "prompt": prompt,
            "images": image_b64_list,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            payload["system"] = system

        resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=300)
        resp.raise_for_status()
        data = resp.json()

        return LLMResponse(
            text=data.get("response", ""),
            provider=self.provider,
            model=model_name,
            usage={
                "input_tokens": data.get("prompt_eval_count", 0),
                "output_tokens": data.get("eval_count", 0),
            },
            raw_response=data,
        )


# ---------------------------------------------------------------------------
# Claude Code CLI Backend — uses Max Plan subscription
# ---------------------------------------------------------------------------

class ClaudeCodeBackend(BaseLLMBackend):
    """
    Claude Code CLI backend — uses the user's Max Plan subscription.

    Calls the ``claude`` CLI in pipe mode (``-p``) to process prompts.
    No API key required — authentication is handled by the Claude Code
    session tied to the user's Max Plan account.

    Requirements:
        - Node.js installed (``brew install node``)
        - Claude Code CLI installed (``npm install -g @anthropic-ai/claude-code``)
        - User authenticated via ``claude login``
    """

    provider = LLMProvider.CLAUDE_CODE
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_VISION_MODEL = "claude-sonnet-4-20250514"

    def __init__(self, claude_bin: Optional[str] = None):
        import shutil
        self.claude_bin = claude_bin or os.getenv(
            "OEFO_CLAUDE_BIN",
            shutil.which("claude") or "claude",
        )

    def is_available(self) -> bool:
        """Check if the ``claude`` CLI is installed and responsive."""
        import shutil
        import subprocess

        if not shutil.which(self.claude_bin):
            return False
        try:
            result = subprocess.run(
                [self.claude_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model: Optional[str] = None,
    ) -> LLMResponse:
        """Run a text completion via ``claude -p``."""
        import subprocess

        cmd = [self.claude_bin, "-p", "--output-format", "json", "--max-turns", "1"]
        if system:
            cmd.extend(["--system-prompt", system])

        logger.debug(f"ClaudeCode complete: prompt length={len(prompt)}")

        try:
            result = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=300,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("claude CLI timed out after 300 s")

        if result.returncode != 0:
            raise RuntimeError(
                f"claude CLI exited {result.returncode}: {result.stderr[:500]}"
            )

        # Parse JSON output  ({"result": "...", "cost_usd": ..., ...})
        data = None
        try:
            data = json.loads(result.stdout)
            text = data.get("result", result.stdout)
            cost = data.get("cost_usd", 0)
        except (json.JSONDecodeError, ValueError):
            text = result.stdout.strip()
            cost = 0

        return LLMResponse(
            text=text,
            provider=self.provider,
            model=model or self.DEFAULT_MODEL,
            usage={"cost_usd": cost},
            raw_response=data if isinstance(data, dict) else None,
        )

    def vision(
        self,
        images: List[bytes],
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model: Optional[str] = None,
    ) -> LLMResponse:
        """
        Run a vision completion via ``claude -p`` with temp image files.

        Images are written to temporary PNG files so the Claude Code agent
        can read them using its built-in Read tool.
        """
        import subprocess
        import tempfile

        temp_files: List[str] = []
        try:
            # Write images to temp files
            for i, img_data in enumerate(images):
                if isinstance(img_data, str):
                    img_data = base64.b64decode(img_data)

                tf = tempfile.NamedTemporaryFile(
                    suffix=".png", prefix=f"oefo_page{i+1}_", delete=False,
                )
                tf.write(img_data)
                tf.close()
                temp_files.append(tf.name)

            # Build compound prompt referencing the image paths
            parts = []
            if system:
                parts.append(system)
            parts.append(
                "I have saved document page images to the following temporary files. "
                "Please read each image file and then answer the extraction prompt below."
            )
            for i, path in enumerate(temp_files):
                parts.append(f"  Page {i + 1}: {path}")
            parts.append("")
            parts.append(prompt)
            full_prompt = "\n".join(parts)

            cmd = [
                self.claude_bin, "-p",
                "--output-format", "json",
                "--max-turns", "5",
                "--allowedTools", "Read",
            ]

            logger.debug(
                f"ClaudeCode vision: {len(images)} images, "
                f"prompt length={len(prompt)}"
            )

            try:
                result = subprocess.run(
                    cmd,
                    input=full_prompt,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
            except subprocess.TimeoutExpired:
                raise RuntimeError("claude CLI vision timed out after 600 s")

            if result.returncode != 0:
                raise RuntimeError(
                    f"claude CLI vision exited {result.returncode}: "
                    f"{result.stderr[:500]}"
                )

            data = None
            try:
                data = json.loads(result.stdout)
                text = data.get("result", result.stdout)
                cost = data.get("cost_usd", 0)
            except (json.JSONDecodeError, ValueError):
                text = result.stdout.strip()
                cost = 0

            return LLMResponse(
                text=text,
                provider=self.provider,
                model=model or self.DEFAULT_VISION_MODEL,
                usage={"cost_usd": cost},
                raw_response=data if isinstance(data, dict) else None,
            )
        finally:
            # Clean up temp files
            for path in temp_files:
                try:
                    os.unlink(path)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# Provider Registry & Unified Client
# ---------------------------------------------------------------------------

BACKEND_REGISTRY: Dict[LLMProvider, type] = {
    LLMProvider.ANTHROPIC: AnthropicBackend,
    LLMProvider.OPENAI: OpenAIBackend,
    LLMProvider.CLAUDE_CODE: ClaudeCodeBackend,
    LLMProvider.OLLAMA: OllamaBackend,
}


class LLMClient:
    """
    Unified, model-agnostic LLM client with automatic fallback.

    Tries the preferred provider first; if it fails (unavailable, rate-limited,
    API error), automatically falls back to the next available provider in the
    configured fallback chain.

    Usage:
        client = LLMClient()                          # auto-detect, prefer Claude
        client = LLMClient(provider=LLMProvider.OPENAI)  # prefer GPT

        # Text
        resp = client.complete("Extract data from ...")
        print(resp.text)

        # Vision
        resp = client.vision([page_bytes], "Extract tables...")
        data = resp.json()  # auto-parse JSON
    """

    # Default fallback order:
    #   1. Anthropic Claude API (primary — needs ANTHROPIC_API_KEY)
    #   2. OpenAI GPT 5.4 (fallback 1 — needs OPENAI_API_KEY)
    #   3. Claude Code CLI (fallback 2 — uses Max Plan, no API key)
    #   4. Ollama / Qwen 3.5 (fallback 3, local)
    DEFAULT_FALLBACK_ORDER = [
        LLMProvider.ANTHROPIC,
        LLMProvider.OPENAI,
        LLMProvider.CLAUDE_CODE,
        LLMProvider.OLLAMA,
    ]

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        fallback_order: Optional[List[LLMProvider]] = None,
        api_keys: Optional[Dict[LLMProvider, str]] = None,
    ):
        """
        Initialise the LLM client.

        Args:
            provider: Preferred provider. If None, uses first available from fallback_order.
            fallback_order: Order in which to try providers. Defaults to
                            [ANTHROPIC, OPENAI, GOOGLE, OLLAMA].
            api_keys: Optional dict mapping provider -> API key. If not provided,
                      keys are read from environment variables.
        """
        self.api_keys = api_keys or {}
        self.fallback_order = list(fallback_order or self.DEFAULT_FALLBACK_ORDER)

        # If a preferred provider is specified, put it first
        if provider and provider in self.fallback_order:
            self.fallback_order.remove(provider)
            self.fallback_order.insert(0, provider)
        elif provider:
            self.fallback_order.insert(0, provider)

        # Instantiate backends
        self._backends: Dict[LLMProvider, BaseLLMBackend] = {}
        for p in self.fallback_order:
            cls = BACKEND_REGISTRY.get(p)
            if cls:
                try:
                    key = self.api_keys.get(p)
                    if p in (LLMProvider.OLLAMA, LLMProvider.CLAUDE_CODE):
                        self._backends[p] = cls()
                    elif key:
                        self._backends[p] = cls(api_key=key)
                    else:
                        self._backends[p] = cls()
                except Exception as e:
                    logger.debug(f"Failed to init {p.value} backend: {e}")

        # Detect available providers
        self._available = [
            p for p in self.fallback_order
            if p in self._backends and self._backends[p].is_available()
        ]

        if self._available:
            logger.info(
                f"LLMClient initialised. Available providers: "
                f"{[p.value for p in self._available]}. "
                f"Primary: {self._available[0].value}"
            )
        else:
            logger.warning(
                "LLMClient: No LLM providers available. "
                "Set ANTHROPIC_API_KEY, OPENAI_API_KEY, "
                "install Claude Code CLI (npm i -g @anthropic-ai/claude-code), "
                "or start Ollama locally (with Qwen 3.5)."
            )

    @property
    def primary_provider(self) -> Optional[LLMProvider]:
        """The currently active primary provider."""
        return self._available[0] if self._available else None

    @property
    def available_providers(self) -> List[LLMProvider]:
        """List of available providers in fallback order."""
        return list(self._available)

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model: Optional[str] = None,
        provider: Optional[LLMProvider] = None,
    ) -> LLMResponse:
        """
        Run a text completion with automatic fallback.

        Args:
            prompt: The user prompt.
            system: Optional system prompt.
            max_tokens: Max output tokens.
            temperature: Sampling temperature (0.0 = deterministic).
            model: Override the default model for the chosen provider.
            provider: Force a specific provider (no fallback).

        Returns:
            LLMResponse with the completion text.

        Raises:
            RuntimeError: If all providers fail.
        """
        providers = [provider] if provider else self._available

        last_error = None
        for p in providers:
            backend = self._backends.get(p)
            if not backend:
                continue
            try:
                return backend.complete(
                    prompt=prompt,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=model,
                )
            except Exception as e:
                logger.warning(f"Provider {p.value} failed for complete(): {e}")
                last_error = e
                continue

        raise RuntimeError(
            f"All LLM providers failed. Last error: {last_error}"
        )

    def vision(
        self,
        images: List[Union[bytes, str]],
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.0,
        model: Optional[str] = None,
        provider: Optional[LLMProvider] = None,
    ) -> LLMResponse:
        """
        Run a vision (image + text) completion with automatic fallback.

        Args:
            images: List of images as bytes or base64-encoded strings.
            prompt: The extraction/analysis prompt.
            system: Optional system prompt.
            max_tokens: Max output tokens.
            temperature: Sampling temperature.
            model: Override the default model.
            provider: Force a specific provider (no fallback).

        Returns:
            LLMResponse with the completion text.

        Raises:
            RuntimeError: If all providers fail.
        """
        providers = [provider] if provider else self._available

        # Filter to providers that support vision
        vision_providers = [
            p for p in providers
            if p in self._backends and self._backends[p].supports_vision()
        ]

        last_error = None
        for p in vision_providers:
            backend = self._backends[p]
            try:
                return backend.vision(
                    images=images,
                    prompt=prompt,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=model,
                )
            except Exception as e:
                logger.warning(f"Provider {p.value} failed for vision(): {e}")
                last_error = e
                continue

        raise RuntimeError(
            f"All vision-capable providers failed. Last error: {last_error}"
        )
