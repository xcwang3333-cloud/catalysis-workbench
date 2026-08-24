"""Minimal installed console entry point for CatalysisWorkbench."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from . import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="catalysis-workbench",
        description="CatalysisWorkbench scientific data post-processing toolkit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the installed console entry point without adding scientific CLI workflows."""
    _build_parser().parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
