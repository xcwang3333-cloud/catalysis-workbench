"""Public v1.1 analysis-document application API."""

from .data import (
    AnalysisDataError,
    DataSeriesSpec,
    SourceSpec,
    TabularMappingSpec,
    source_spec_from_file,
)
from .document import AnalysisDocument, AnalysisDocumentError
from .materialization import (
    AnalysisMaterializationError,
    MaterializedInput,
    materialize_data_series,
    verify_source_bytes,
)
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
    "AnalysisDataError",
    "AnalysisDocument",
    "AnalysisDocumentError",
    "AnalysisMaterializationError",
    "AnalysisProjectError",
    "AnalysisProjectSnapshot",
    "AnalysisSession",
    "AnalysisSessionError",
    "AnalysisSessionState",
    "AnalysisTaskDescriptor",
    "AnalysisTaskError",
    "DataSeriesSpec",
    "LegacyWorkspaceError",
    "MaterializedInput",
    "SourceSpec",
    "TabularMappingSpec",
    "analysis_task_catalog",
    "create_analysis_project",
    "get_analysis_task_descriptor",
    "materialize_data_series",
    "open_analysis_project",
    "save_analysis_project",
    "source_spec_from_file",
    "verify_source_bytes",
]
