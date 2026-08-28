"""Public v1.1 analysis-document application API."""

from .document import AnalysisDocument, AnalysisDocumentError
from .persistence import (
    AnalysisProjectError,
    AnalysisProjectSnapshot,
    LegacyWorkspaceError,
    create_analysis_project,
    open_analysis_project,
    save_analysis_project,
)
from .session import AnalysisSession, AnalysisSessionError, AnalysisSessionState
from .tasks import (
    AnalysisTaskDescriptor,
    AnalysisTaskError,
    analysis_task_catalog,
    get_analysis_task_descriptor,
)

__all__ = [
    "AnalysisDocument",
    "AnalysisDocumentError",
    "AnalysisProjectError",
    "AnalysisProjectSnapshot",
    "AnalysisSession",
    "AnalysisSessionError",
    "AnalysisSessionState",
    "AnalysisTaskDescriptor",
    "AnalysisTaskError",
    "LegacyWorkspaceError",
    "analysis_task_catalog",
    "create_analysis_project",
    "get_analysis_task_descriptor",
    "open_analysis_project",
    "save_analysis_project",
]
