"""Public v1.1 analysis-document application API."""

from .compiler import CompiledAnalysis, compile_analysis
from .data import (
    AnalysisDataError,
    DataSeriesSpec,
    SourceSpec,
    TabularMappingSpec,
    source_spec_from_file,
)
from .document import AnalysisDocument, AnalysisDocumentError
from .evaluator import (
    AnalysisEvaluation,
    AnalysisEvaluationStatus,
    AnalysisEvaluator,
    AnalysisResult,
    AnalysisView,
)
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
from .processing import (
    AnalysisDependencyImpact,
    AnalysisProcessingError,
    AnalysisRange,
    AnalysisSpec,
    FEPartialCurrentAnalysisSpec,
    GenericXYAnalysisSpec,
    LSVAnalysisSpec,
    LSVProcessingSpec,
    PartialCurrentPair,
    default_analysis_spec,
    dependency_impact,
    remap_analysis_data_id,
    remove_analysis_data_id,
    validate_analysis_spec,
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
    "AnalysisDependencyImpact",
    "AnalysisDocument",
    "AnalysisDocumentError",
    "AnalysisEvaluation",
    "AnalysisEvaluationStatus",
    "AnalysisEvaluator",
    "AnalysisMaterializationError",
    "AnalysisProcessingError",
    "AnalysisProjectError",
    "AnalysisProjectSnapshot",
    "AnalysisRange",
    "AnalysisResult",
    "AnalysisSession",
    "AnalysisSessionError",
    "AnalysisSessionState",
    "AnalysisSpec",
    "AnalysisTaskDescriptor",
    "AnalysisTaskError",
    "AnalysisView",
    "CompiledAnalysis",
    "DataSeriesSpec",
    "FEPartialCurrentAnalysisSpec",
    "GenericXYAnalysisSpec",
    "LSVAnalysisSpec",
    "LSVProcessingSpec",
    "LegacyWorkspaceError",
    "MaterializedInput",
    "PartialCurrentPair",
    "SourceSpec",
    "TabularMappingSpec",
    "analysis_task_catalog",
    "compile_analysis",
    "create_analysis_project",
    "default_analysis_spec",
    "dependency_impact",
    "get_analysis_task_descriptor",
    "materialize_data_series",
    "open_analysis_project",
    "remap_analysis_data_id",
    "remove_analysis_data_id",
    "save_analysis_project",
    "source_spec_from_file",
    "validate_analysis_spec",
    "verify_source_bytes",
]
