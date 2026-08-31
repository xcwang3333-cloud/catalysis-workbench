from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STABLE_SHA = "22b944992bfd3791f91cc951f89eb22e8bf47325"
BLOCK5_MAIN = "eec2f85d117902459178f65c4543b5674de54912"


def test_block6_contract_tracks_current_stable_and_development_lines() -> None:
    text = (ROOT / "docs" / "V1_1_BLOCK6.md").read_text(encoding="utf-8")
    assert "1.1.0.dev0" in text
    assert BLOCK5_MAIN in text
    assert "Block-5 post-merge CI #832" in text
    assert "Stable 1.0 Readiness #94" in text
    assert "does not authorize" in text


def test_central_docs_no_longer_describe_v10_as_unreleased() -> None:
    paths = (
        ROOT / "README.md",
        ROOT / "docs" / "MASTER_PLAN.md",
        ROOT / "docs" / "ROADMAP.md",
        ROOT / "docs" / "DESKTOP.md",
    )
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert STABLE_SHA in text, path
        assert "1.1.0.dev0" in text, path
        assert "PyPI" in text, path
        assert "1.0.0.dev0" not in text, path


def test_package_metadata_stays_on_v11_development_identity() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    runtime = (ROOT / "src" / "catalysis_workbench" / "__init__.py").read_text(
        encoding="utf-8"
    )
    assert 'version = "1.1.0.dev0"' in pyproject
    assert '__version__ = "1.1.0.dev0"' in runtime
    assert "catalysis-workbench = \"catalysis_workbench.desktop.cli:main\"" in pyproject
