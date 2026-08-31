from __future__ import annotations

import sys
from pathlib import Path

from catalysis_workbench.desktop import cli


def test_version_path_is_qt_free(capsys) -> None:
    before = {name for name in sys.modules if name == "PySide6" or name.startswith("PySide6.")}
    assert cli.main(("--version",)) == 0
    after = {name for name in sys.modules if name == "PySide6" or name.startswith("PySide6.")}
    assert after == before
    assert capsys.readouterr().out.strip() == "CatalysisWorkbench 1.1.0"


def test_cli_routes_default_and_project_to_task_first_workbench(
    monkeypatch,
    tmp_path: Path,
) -> None:
    calls: list[tuple[Path | None, tuple[str, ...]]] = []

    def fake_run(project: Path | None, *, argv: tuple[str, ...]) -> int:
        calls.append((project, argv))
        return 0

    monkeypatch.setattr(cli, "_run_workbench", fake_run)
    assert cli.main(()) == 0
    project = tmp_path / "analysis-project"
    assert cli.main(("--project", str(project))) == 0
    assert calls == [
        (None, ("catalysis-workbench",)),
        (
            project,
            ("catalysis-workbench", "--project", str(project)),
        ),
    ]
