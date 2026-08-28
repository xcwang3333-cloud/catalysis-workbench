from __future__ import annotations

from pathlib import Path

import pytest

from catalysis_workbench.workspace import assets as assets_module
from catalysis_workbench.workspace import create_workspace, open_workspace


def test_copy_save_failure_preserves_preexisting_empty_parent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "workspace"
    source = tmp_path / "source.bin"
    source.write_bytes(b"source-bytes")
    original = create_workspace(root)
    existing_parent = root / "existing"
    existing_parent.mkdir()

    def fail_save(*args: object, **kwargs: object) -> None:
        raise RuntimeError("forced manifest persistence failure")

    monkeypatch.setattr(assets_module, "save_workspace", fail_save)
    with pytest.raises(RuntimeError, match="forced manifest persistence failure"):
        assets_module.import_asset(
            root,
            source,
            asset_id="copy",
            asset_type="source-file",
            policy="copy",
            destination="existing/new/copied.bin",
        )

    assert existing_parent.is_dir()
    assert tuple(existing_parent.iterdir()) == ()
    assert source.read_bytes() == b"source-bytes"
    assert open_workspace(root) == original
