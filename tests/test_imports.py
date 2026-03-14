from __future__ import annotations


def test_imports_work() -> None:
    import oefo
    import oefo.cli
    import oefo.dashboard.server
    import oefo.data.storage

    assert hasattr(oefo, '__version__')
