"""Command-line entry point for the task-first v1.1 desktop."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from catalysis_workbench import __version__

from . import DesktopDependencyError


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="catalysis-workbench",
        description="Launch the task-first CatalysisWorkbench v1.1 desktop.",
    )
    parser.add_argument(
        "--project",
        metavar="PATH",
        help="Open an existing v1.1 analysis project instead of Home.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the installed CatalysisWorkbench version without loading Qt.",
    )
    return parser


def _desktop_dependency_error(exc: ModuleNotFoundError) -> DesktopDependencyError:
    return DesktopDependencyError(
        "CatalysisWorkbench Desktop requires the optional desktop dependencies. "
        "Install with: python -m pip install \"catalysis-workbench[desktop]\""
    )


def _run_workbench(project: Path | None, *, argv: Sequence[str]) -> int:
    try:
        from .app import create_workbench_desktop
    except ModuleNotFoundError as exc:
        if exc.name == "PySide6" or (exc.name or "").startswith("PySide6."):
            raise _desktop_dependency_error(exc) from exc
        raise

    handle = create_workbench_desktop(project, argv=argv)
    handle.window.show()
    return int(handle.application.exec())


def main(argv: Sequence[str] | None = None) -> int:
    raw_args = tuple(sys.argv[1:] if argv is None else argv)
    args = _parser().parse_args(raw_args)
    if args.version:
        print(f"CatalysisWorkbench {__version__}")
        return 0

    project = None if args.project is None else Path(args.project).expanduser()
    try:
        return _run_workbench(
            project,
            argv=("catalysis-workbench", *raw_args),
        )
    except DesktopDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"CatalysisWorkbench could not start: {exc}", file=sys.stderr)
        return 1


__all__ = ["main"]
