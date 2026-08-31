"""Fresh-wheel headless smoke for v1.1 Block-6 command routing."""

from __future__ import annotations

import contextlib
import importlib
import io
import sys
import tempfile
from pathlib import Path


def main() -> None:
    assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)
    cli = importlib.import_module("catalysis_workbench.desktop.cli")
    assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        assert cli.main(("--version",)) == 0
    assert output.getvalue().strip() == "CatalysisWorkbench 1.1.0"
    assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)

    calls: list[Path | None] = []
    original = cli._run_workbench

    def fake_run(project: Path | None, *, argv) -> int:
        calls.append(project)
        assert tuple(argv)[0] == "catalysis-workbench"
        return 0

    cli._run_workbench = fake_run
    try:
        assert cli.main(()) == 0
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            assert cli.main(("--project", str(project))) == 0
            assert calls == [None, project]
    finally:
        cli._run_workbench = original

    print("installed v1.1 Block-6 headless smoke: ok")


if __name__ == "__main__":
    main()
