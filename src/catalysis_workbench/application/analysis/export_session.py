"""AnalysisSession bridge for Figure Package export side effects."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from .export_package import (
    FigurePackageExportError,
    FigurePackageOptions,
    FigurePackageResult,
    export_figure_package,
)
from .session import AnalysisSession, AnalysisSessionError


def export_session_figure_package(
    session: AnalysisSession,
    view_id: str,
    destination: str | Path,
    *,
    options: FigurePackageOptions | None = None,
) -> FigurePackageResult:
    """Export one saved/current figure and advance only the workspace baseline.

    Export is a file-system/provenance side effect, not a semantic AnalysisDocument
    revision. A successful export therefore preserves document identity, revision,
    Undo/Redo stacks, and dirty state while adopting the workspace manifest identity
    produced by the provenance transaction.
    """

    if not isinstance(session, AnalysisSession):
        raise TypeError("session must be an AnalysisSession")
    before = session.state
    document = before.document
    if document is None:
        raise AnalysisSessionError("no analysis document is open")
    if before.project_root is None:
        raise AnalysisSessionError("save the analysis project before exporting")
    if before.is_dirty:
        raise AnalysisSessionError("save the current analysis project before exporting")
    if before.workspace_manifest_sha256 is None or before.project_file_sha256 is None:
        raise AnalysisSessionError("saved project identities are unavailable; reopen explicitly")

    evaluation = session.evaluate_analysis()
    if evaluation.status != "success" or evaluation.result is None:
        raise AnalysisSessionError(
            evaluation.message or "analysis must be successful before exporting"
        )
    draft = session.figure_draft(view_id)
    try:
        exported = export_figure_package(
            document,
            evaluation.result,
            draft,
            project_root=before.project_root,
            expected_workspace_manifest_sha256=before.workspace_manifest_sha256,
            expected_project_file_sha256=before.project_file_sha256,
            destination=destination,
            options=options,
        )
    except FigurePackageExportError as exc:
        raise AnalysisSessionError(str(exc)) from exc

    if session.state != before:
        raise AnalysisSessionError(
            "analysis session changed during Figure Package export; reopen explicitly"
        )
    session._state = replace(  # type: ignore[attr-defined]
        before,
        workspace_manifest_sha256=exported.workspace_manifest_sha256,
    )
    return exported


__all__ = ["export_session_figure_package"]
