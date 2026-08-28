"""GUI-neutral workspace actions used by desktop and other application frontends."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from catalysis_workbench.workspace import WorkspaceManifest, create_workspace, open_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.evidence import EvidenceLedger, open_evidence_ledger

from .session import ApplicationError, ApplicationSession, ApplicationState


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    """Read-only workspace/catalog/evidence snapshot for presentation layers."""

    manifest: WorkspaceManifest
    evidence: EvidenceLedger | None


def _open_root(session: ApplicationSession) -> Path:
    root = session.state.workspace_root
    if root is None:
        raise ApplicationError("no workspace is open")
    return root


def create_workspace_in_session(
    session: ApplicationSession,
    root: str | Path,
) -> ApplicationState:
    """Create one explicit workspace and open it in the supplied session."""

    if not isinstance(session, ApplicationSession):
        raise TypeError("session must be an ApplicationSession")
    if session.state.recipe_dirty or session.state.figure_spec_dirty:
        raise ApplicationError(
            "save or discard dirty recipe/FigureSpec state before creating a workspace"
        )
    create_workspace(root)
    return session.open_workspace(root)


def import_asset_in_session(
    session: ApplicationSession,
    source: str | Path,
    *,
    asset_id: str,
    asset_type: str,
    policy: str,
    destination: str | None = None,
) -> ApplicationState:
    """Import one explicit asset and advance session state only to that exact manifest."""

    if not isinstance(session, ApplicationSession):
        raise TypeError("session must be an ApplicationSession")
    state = session.state
    if state.recipe_dirty or state.figure_spec_dirty:
        raise ApplicationError(
            "save or discard dirty recipe/FigureSpec state before importing an asset"
        )
    root = _open_root(session)
    before = open_workspace(root)
    if before.manifest_sha256 != state.workspace_manifest_sha256:
        raise ApplicationError(
            "workspace changed outside the application session; refresh explicitly"
        )

    updated = import_asset(
        root,
        source,
        asset_id=asset_id,
        asset_type=asset_type,
        policy=policy,
        destination=destination,
    )
    if (
        len(updated.assets) != len(before.assets) + 1
        or tuple(updated.assets[:-1]) != tuple(before.assets)
    ):
        raise ApplicationError(
            "workspace changed concurrently with asset import; refresh explicitly"
        )

    observed = open_workspace(root)
    if observed.manifest_sha256 != updated.manifest_sha256:
        raise ApplicationError(
            "workspace changed concurrently with asset import; refresh explicitly"
        )
    refreshed = session.refresh_workspace()
    if refreshed.workspace_manifest_sha256 != updated.manifest_sha256:
        raise ApplicationError(
            "application session did not advance to the imported workspace manifest"
        )
    return refreshed


def workspace_snapshot(session: ApplicationSession) -> WorkspaceSnapshot:
    """Return a presentation-safe snapshot without executing or mutating scientific state."""

    if not isinstance(session, ApplicationSession):
        raise TypeError("session must be an ApplicationSession")
    root = _open_root(session)
    state = session.state
    manifest = open_workspace(root)
    if manifest.manifest_sha256 != state.workspace_manifest_sha256:
        raise ApplicationError(
            "workspace changed outside the application session; refresh explicitly"
        )
    try:
        evidence = open_evidence_ledger(root)
    except FileNotFoundError:
        evidence = None
    observed = open_workspace(root)
    if observed.manifest_sha256 != manifest.manifest_sha256:
        raise ApplicationError(
            "workspace changed while the presentation snapshot was being read"
        )
    return WorkspaceSnapshot(manifest=manifest, evidence=evidence)
