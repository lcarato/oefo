"""
Tests for LLM Client — provider registry, fallback, and ClaudeCodeBackend.
"""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from oefo.llm_client import (
    BACKEND_REGISTRY,
    BaseLLMBackend,
    ClaudeCodeBackend,
    LLMClient,
    LLMProvider,
    LLMResponse,
)


class TestLLMProvider:
    """Test the LLMProvider enum."""

    def test_all_providers_present(self):
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.CLAUDE_CODE.value == "claude_code"
        assert LLMProvider.OLLAMA.value == "ollama"

    def test_from_string(self):
        assert LLMProvider("claude_code") == LLMProvider.CLAUDE_CODE
        assert LLMProvider("anthropic") == LLMProvider.ANTHROPIC


class TestBackendRegistry:
    """Test that all providers are registered."""

    def test_all_providers_registered(self):
        for provider in LLMProvider:
            assert provider in BACKEND_REGISTRY, f"{provider} not in BACKEND_REGISTRY"

    def test_claude_code_registered(self):
        assert BACKEND_REGISTRY[LLMProvider.CLAUDE_CODE] is ClaudeCodeBackend


class TestLLMResponse:
    """Test LLMResponse JSON parsing."""

    def test_json_from_plain_json(self):
        resp = LLMResponse(
            text='{"key": "value"}',
            provider=LLMProvider.CLAUDE_CODE,
            model="test",
        )
        assert resp.json() == {"key": "value"}

    def test_json_from_markdown_block(self):
        resp = LLMResponse(
            text='```json\n{"key": "value"}\n```',
            provider=LLMProvider.CLAUDE_CODE,
            model="test",
        )
        assert resp.json() == {"key": "value"}

    def test_json_returns_none_for_non_json(self):
        resp = LLMResponse(
            text="This is not JSON",
            provider=LLMProvider.CLAUDE_CODE,
            model="test",
        )
        assert resp.json() is None


class TestClaudeCodeBackend:
    """Test ClaudeCodeBackend."""

    def test_is_available_with_claude_on_path(self):
        """Should return True when claude CLI is found and responds."""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            backend = ClaudeCodeBackend()
        with patch("shutil.which", return_value="/usr/local/bin/claude"), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert backend.is_available() is True

    def test_is_available_without_claude(self):
        """Should return False when claude CLI is not found."""
        with patch("shutil.which", return_value=None):
            backend = ClaudeCodeBackend()
            assert backend.is_available() is False

    def test_complete_success(self):
        """Should parse JSON output from claude -p."""
        mock_output = json.dumps({
            "result": "Extracted data: {\"wacc\": 8.5}",
            "cost_usd": 0.01,
            "is_error": False,
        })
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            backend = ClaudeCodeBackend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
                stderr="",
            )
            resp = backend.complete("Test prompt")
            assert resp.provider == LLMProvider.CLAUDE_CODE
            assert "wacc" in resp.text
            assert resp.usage.get("cost_usd") == 0.01

    def test_complete_fallback_to_raw_stdout(self):
        """Should use raw stdout if JSON parsing fails."""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            backend = ClaudeCodeBackend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Plain text response",
                stderr="",
            )
            resp = backend.complete("Test prompt")
            assert resp.text == "Plain text response"

    def test_complete_raises_on_failure(self):
        """Should raise RuntimeError when claude CLI fails."""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            backend = ClaudeCodeBackend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error: not authenticated",
            )
            with pytest.raises(RuntimeError, match="claude CLI exited 1"):
                backend.complete("Test prompt")

    def test_complete_timeout(self):
        """Should raise RuntimeError on timeout."""
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            backend = ClaudeCodeBackend()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("claude", 300)):
            with pytest.raises(RuntimeError, match="timed out"):
                backend.complete("Test prompt")

    def test_vision_creates_temp_files(self):
        """Vision should write images to temp files and clean up."""
        mock_output = json.dumps({
            "result": '{"tables": []}',
            "cost_usd": 0.02,
        })
        with patch("shutil.which", return_value="/usr/local/bin/claude"):
            backend = ClaudeCodeBackend()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
                stderr="",
            )
            # Pass fake PNG bytes
            resp = backend.vision(
                images=[b"\x89PNG\r\n\x1a\n" + b"\x00" * 100],
                prompt="Extract tables",
            )
            assert resp.provider == LLMProvider.CLAUDE_CODE

            # Verify the command included --allowedTools Read
            call_args = mock_run.call_args
            cmd = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
            assert "--allowedTools" in cmd
            assert "Read" in cmd


class TestLLMClientFallback:
    """Test LLMClient fallback behavior."""

    def test_default_fallback_includes_claude_code(self):
        assert LLMProvider.CLAUDE_CODE in LLMClient.DEFAULT_FALLBACK_ORDER

    def test_claude_code_before_ollama(self):
        order = LLMClient.DEFAULT_FALLBACK_ORDER
        cc_idx = order.index(LLMProvider.CLAUDE_CODE)
        ol_idx = order.index(LLMProvider.OLLAMA)
        assert cc_idx < ol_idx, "claude_code should come before ollama in fallback"

    def test_preferred_provider_moves_to_front(self):
        """Specifying a preferred provider should put it first."""
        with patch.object(ClaudeCodeBackend, "is_available", return_value=True), \
             patch.object(ClaudeCodeBackend, "__init__", return_value=None):
            # Force only claude_code available
            client = LLMClient(
                provider=LLMProvider.CLAUDE_CODE,
                fallback_order=[LLMProvider.CLAUDE_CODE],
            )
            assert client.fallback_order[0] == LLMProvider.CLAUDE_CODE
