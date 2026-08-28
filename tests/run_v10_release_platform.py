"""Create isolated base/desktop environments for release-platform smoke tests."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLATFORM_SMOKE = ROOT / "tests" / "installed_v10_platform_smoke.py"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel-dir", type=Path, required=True)
    parser.add_argument("--expected-version", required=True)
    return parser.parse_args()


def _venv_python(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _run(command: list[str], *, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, check=True, env=env)


def _install_and_smoke(
    wheel: Path,
    *,
    mode: str,
    expected_version: str,
    parent: Path,
) -> None:
    environment = parent / mode
    venv.EnvBuilder(with_pip=True, clear=True).create(environment)
    python = _venv_python(environment)
    _run([str(python), "-m", "pip", "install", "--upgrade", "pip"])

    requirement = str(wheel)
    if mode == "desktop":
        requirement = f"catalysis-workbench[desktop] @ {wheel.resolve().as_uri()}"
    _run([str(python), "-m", "pip", "install", requirement])
    _run([str(python), "-m", "pip", "check"])

    env = os.environ.copy()
    env["CATALYSIS_WORKBENCH_EXPECTED_VERSION"] = expected_version
    _run([str(python), str(PLATFORM_SMOKE), "--mode", mode], env=env)


def main() -> None:
    args = _parse_args()
    wheels = sorted(args.wheel_dir.glob("catalysis_workbench-*.whl"))
    assert len(wheels) == 1, f"expected exactly one candidate wheel, found: {wheels!r}"
    wheel = wheels[0].resolve()

    temp_root = Path(tempfile.mkdtemp(prefix="catalysis-workbench-release-"))
    try:
        _install_and_smoke(
            wheel,
            mode="base",
            expected_version=args.expected_version,
            parent=temp_root,
        )
        _install_and_smoke(
            wheel,
            mode="desktop",
            expected_version=args.expected_version,
            parent=temp_root,
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)

    print("cross-platform release candidate environments: ok")


if __name__ == "__main__":
    main()
