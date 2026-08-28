from __future__ import annotations

from pathlib import Path

import pytest

from catalysis_workbench.application import (
    ApplicationError,
    ApplicationSession,
    create_workspace_in_session,
    import_asset_in_session,
    workspace_snapshot,
)
from catalysis_workbench.visualization import FigureSpec
from catalysis_workbench.workspace import create_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.composition import save_figure_spec_asset
from catalysis_workbench.workspace.evidence import create_evidence_ledger


def test_create_workspace_in_session_and_snapshot(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    session = ApplicationSession()

    state = create_workspace_in_session(session, root)

    assert state.workspace_root == root.resolve()
    snapshot = workspace_snapshot(session)
    assert snapshot.manifest.assets == ()
    assert snapshot.evidence is None

    create_evidence_ledger(root)
    snapshot = workspace_snapshot(session)
    assert snapshot.evidence is not None
    assert snapshot.evidence.records == ()


def test_import_asset_in_session_advances_exact_manifest(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = tmp_path / "raw.dat"
    source.write_bytes(b"selected bytes")
    session = ApplicationSession()
    create_workspace_in_session(session, root)

    reference_state = import_asset_in_session(
        session,
        source,
        asset_id="raw-reference",
        asset_type="source_file",
        policy="reference",
    )
    reference_snapshot = workspace_snapshot(session)
    assert reference_state.workspace_manifest_sha256 == (
        reference_snapshot.manifest.manifest_sha256
    )
    assert reference_snapshot.manifest.assets[0].asset_id == "raw-reference"
    assert reference_snapshot.manifest.assets[0].policy == "reference"

    copy_state = import_asset_in_session(
        session,
        source,
        asset_id="raw-copy",
        asset_type="source_file",
        policy="copy",
        destination="assets/raw.dat",
    )
    copy_snapshot = workspace_snapshot(session)
    assert copy_state.workspace_manifest_sha256 == copy_snapshot.manifest.manifest_sha256
    assert tuple(asset.asset_id for asset in copy_snapshot.manifest.assets) == (
        "raw-reference",
        "raw-copy",
    )
    assert (root / "assets" / "raw.dat").read_bytes() == b"selected bytes"
    assert source.read_bytes() == b"selected bytes"


def test_import_rejects_dirty_presentation_state_before_mutation(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = tmp_path / "raw.dat"
    source.write_bytes(b"raw")
    create_workspace(root)
    save_figure_spec_asset(
        root,
        FigureSpec(title="initial"),
        asset_id="figure",
        destination="figures/spec.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_figure_spec("figure")
    session.update_figure_spec(title="dirty")
    before = workspace_snapshot(session).manifest

    with pytest.raises(ApplicationError, match="dirty"):
        import_asset_in_session(
            session,
            source,
            asset_id="raw",
            asset_type="source_file",
            policy="copy",
            destination="assets/raw.dat",
        )

    assert workspace_snapshot(session).manifest == before
    assert not (root / "assets" / "raw.dat").exists()


def test_snapshot_rejects_external_manifest_drift(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    source = tmp_path / "raw.dat"
    source.write_bytes(b"raw")
    create_workspace(root)
    session = ApplicationSession()
    session.open_workspace(root)

    import_asset(
        root,
        source,
        asset_id="external-change",
        asset_type="source_file",
        policy="reference",
    )

    with pytest.raises(ApplicationError, match="changed outside"):
        workspace_snapshot(session)
