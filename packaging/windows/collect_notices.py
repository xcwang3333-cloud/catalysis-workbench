"""Generate a conservative third-party license inventory for the frozen build."""

from __future__ import annotations

import argparse
import importlib.metadata as metadata
import sys
from pathlib import Path

_BUILD_ONLY = {
    "altgraph",
    "packaging",
    "pefile",
    "pip",
    "pyinstaller",
    "pyinstaller-hooks-contrib",
    "pywin32-ctypes",
    "setuptools",
    "wheel",
}
_PROJECT = {"catalysis-workbench"}
_LICENSE_NAMES = ("LICENSE", "LICENCE", "COPYING", "NOTICE")


def _normalized(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def _license_files(dist: metadata.Distribution) -> list[Path]:
    found: list[Path] = []
    for file in dist.files or ():
        filename = Path(str(file)).name.upper()
        if any(filename.startswith(prefix) for prefix in _LICENSE_NAMES):
            located = Path(dist.locate_file(file))
            if located.is_file():
                found.append(located)
    return sorted(set(found), key=lambda item: str(item).lower())


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def generate() -> str:
    lines = [
        "CatalysisWorkbench Windows installer — third-party notices",
        "",
        "This is an automated build-time inventory for redistribution review.",
        "It is evidence, not legal advice, and does not by itself establish that",
        "every listed distribution is embedded or that all obligations are satisfied.",
        "",
        f"Bundled Python runtime: {sys.version.split()[0]}",
    ]

    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.is_file():
        lines.extend(
            [
                "",
                "===== Python runtime license =====",
                _read_text(python_license).rstrip(),
            ]
        )

    distributions = sorted(
        metadata.distributions(),
        key=lambda dist: _normalized(dist.metadata.get("Name", "")),
    )
    for dist in distributions:
        name = dist.metadata.get("Name")
        if not name:
            continue
        normalized = _normalized(name)
        if normalized in _BUILD_ONLY or normalized in _PROJECT:
            continue
        version = dist.version
        license_expression = (
            dist.metadata.get("License-Expression")
            or dist.metadata.get("License")
            or "not declared in package metadata"
        )
        lines.extend(
            [
                "",
                f"===== {name} {version} =====",
                f"License metadata: {license_expression}",
            ]
        )
        home_page = dist.metadata.get("Home-page") or dist.metadata.get("Project-URL")
        if home_page:
            lines.append(f"Project metadata: {home_page}")
        license_files = _license_files(dist)
        if not license_files:
            lines.append("License files: none discovered in installed distribution metadata")
            continue
        for license_file in license_files:
            lines.extend(
                [
                    "",
                    f"--- {license_file.name} ---",
                    _read_text(license_file).rstrip(),
                ]
            )

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generate(), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
