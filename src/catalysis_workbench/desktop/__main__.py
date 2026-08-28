"""Module entry point for ``python -m catalysis_workbench.desktop``."""

from __future__ import annotations

import sys

from . import DesktopDependencyError, launch_desktop


def main() -> int:
    try:
        result = launch_desktop()
    except DesktopDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return int(result)


if __name__ == "__main__":
    raise SystemExit(main())
