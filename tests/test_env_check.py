from __future__ import annotations

import importlib.util
from pathlib import Path


def load_env_check_module():
    script_path = Path(__file__).resolve().parents[1] / 'scripts' / 'oefo_env_check.py'
    spec = importlib.util.spec_from_file_location('oefo_env_check', script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_check_poppler_checks_both_tools(monkeypatch) -> None:
    module = load_env_check_module()
    checked_tools: list[str] = []

    def fake_check_tool(tool: str, install_hint: str) -> bool:
        checked_tools.append(tool)
        return False

    monkeypatch.setattr(module.platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(module, 'check_tool', fake_check_tool)

    assert module.check_poppler() is False
    assert checked_tools == ['pdftoppm', 'pdfinfo']


def test_main_does_not_fail_only_for_missing_api_keys(monkeypatch) -> None:
    module = load_env_check_module()

    monkeypatch.setattr(module, 'check_python_version', lambda: True)
    monkeypatch.setattr(module, 'check_virtual_environment', lambda: True)
    monkeypatch.setattr(module, 'check_poppler', lambda: True)
    monkeypatch.setattr(module, 'check_tesseract', lambda: True)
    monkeypatch.setattr(module, 'check_directories', lambda: True)
    monkeypatch.setattr(module, 'check_api_keys', lambda: False)

    assert module.main() == 0
