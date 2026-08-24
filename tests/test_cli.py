"""Regression coverage for the installed console entry point."""

from __future__ import annotations

import pytest

from catalysis_workbench import __version__
from catalysis_workbench.cli import main


def test_cli_no_arguments_is_a_noop() -> None:
    assert main([]) == 0


def test_cli_version_reports_runtime_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"catalysis-workbench {__version__}"
