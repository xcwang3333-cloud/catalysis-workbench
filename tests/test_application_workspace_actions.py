from __future__ import annotations

from pathlib import Path

import pytest

import catalysis_workbench.application.workspace_actions as workspace_actions
from catalysis_workbench.application import (
    ApplicationError,
    ApplicationSession,
    close_workspace_in_session,
    create_workspace_in_session,
    import_asset_in_session,
    open_workspace_in_session,
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


def test_open_and_close_reject_dirty_state_without_explicit_discard(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    create_workspace(first)
    create_workspace(second)
    save_figure_spec_asset(
        first,
        FigureSpec(title="initial"),
        asset_id="figure",
        destination="figures/spec.json",
    )
    session = ApplicationSession()
    session.open_workspace(first)
    session.select_figure_spec("figure")
    dirty = session.update_figure_spec(title="dirty")

    with pytest.raises(ApplicationError, match="dirty"):
        open_workspace_in_session(session, second)
    assert session.state is dirty

    with pytest.raises(ApplicationError, match="dirty"):
        close_workspace_in_session(session)
    assert session.state is dirty

    opened = open_workspace_in_session(session, second, discard_edits=True)
    assert opened.workspace_root == second.resolve()
    assert opened.figure_spec is None

    closed = close_workspace_in_session(session)
    assert closed.workspace_root is None


def test_import_manifest_race_does_not_commit_session_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "workspace"
    source = tmp_path / "primary.dat"
    concurrent = tmp_path / "concurrent.dat"
    source.write_bytes(b"primary")
    concurrent.write_bytes(b"concurrent")
    create_workspace(root)
    session = ApplicationSession()
    session.open_workspace(root)
    original_state = session.state

    real_open = workspace_actions.open_workspace
    open_calls = 0

    def racing_open(path: str | Path):
        nonlocal open_calls
        open_calls += 1
        if open_calls == 4:
            import_asset(
                root,
                concurrent,
                asset_id="concurrent",
                asset_type="source_file",
                policy="reference",
            )
        return real_open(path)

    monkeypatch.setattr(workspace_actions, "open_workspace", racing_open)

    with pytest.raises(ApplicationError, match="concurrently"):
        workspace_actions.import_asset_in_session(
            session,
            source,
            asset_id="primary",
            asset_type="source_file",
            policy="reference",
        )

    assert session.state is original_state
    manifest = real_open(root)
    assert tuple(asset.asset_id for asset in manifest.assets) == (
        "primary",
        "concurrent",
    )


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
