from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_block6_contract_tracks_current_stable_and_development_lines() -> None:
    text = (ROOT / "docs" / "V1_1_BLOCK6.md").read_text(encoding="utf-8")
    assert "1.1.0.dev0" in text
    assert "eec2f85d117902459178f65c4543b5674de54912" in text
    assert "Block-5 post-merge CI #832" in text
    assert "Stable 1.0 Readiness #94" in text
    assert "does not authorize" in text


def test_package_metadata_stays_on_v11_development_identity() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    runtime = (ROOT / "src" / "catalysis_workbench" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert 'version = "1.1.0.dev0"' in pyproject
    assert '__version__ = "1.1.0.dev0"' in runtime
    assert "catalysis-workbench = \"catalysis_workbench.desktop.cli:main\"" in pyproject
