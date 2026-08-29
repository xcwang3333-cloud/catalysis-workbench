"""Compile task-first analysis state into deterministic internal workflow recipes."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from catalysis_workbench.workflow.recipe import RecipeStep, WorkflowRecipe
from catalysis_workbench.workflow.registry import OperationDescriptor, get_operation_descriptor

from .document import AnalysisDocument
from .processing import (
    AnalysisRange,
    FEPartialCurrentAnalysisSpec,
    GenericXYAnalysisSpec,
    LSVAnalysisSpec,
    LSVProcessingSpec,
    PartialCurrentPair,
)

_ANALYSIS_IDENTITY_OP = "catalysis.analysis.identity.v1"
_ANALYSIS_LSV_OP = "catalysis.analysis.lsv_process.v1"
_ANALYSIS_PARTIAL_CURRENT_OP = "catalysis.analysis.partial_current_density.v1"

_LSV_PARAMETER_NAMES = (
    "rhe_mode",
    "rhe_offset_v",
    "reference_potential_vs_she_v",
    "ph",
    "temperature_k",
    "resistance_ohm",
    "ir_correction_fraction",
    "electrode_area_cm2",
    "normalize_to_current_density",
    "current_density_unit",
)

_PRIVATE_DESCRIPTORS = MappingProxyType(
    {
        _ANALYSIS_IDENTITY_OP: OperationDescriptor(
            operation_id=_ANALYSIS_IDENTITY_OP,
            contract_version=1,
            input_ports=("series",),
            output_ports=("series",),
        ),
        _ANALYSIS_LSV_OP: OperationDescriptor(
            operation_id=_ANALYSIS_LSV_OP,
            contract_version=1,
            input_ports=("series",),
            output_ports=("series",),
            required_parameters=_LSV_PARAMETER_NAMES,
        ),
        _ANALYSIS_PARTIAL_CURRENT_OP: OperationDescriptor(
            operation_id=_ANALYSIS_PARTIAL_CURRENT_OP,
            contract_version=1,
            input_ports=("current", "fe"),
            output_ports=("series",),
            required_parameters=("sign_mode",),
        ),
    }
)


@dataclass(frozen=True, slots=True)
class CompiledAnalysis:
    """Internal deterministic recipe plus binding-to-scientific-input identities."""

    task_id: str
    recipe: WorkflowRecipe
    input_data_ids: Mapping[str, str]
    output_sources: Mapping[str, tuple[str, ...]]

    def __post_init__(self) -> None:
        object.__setattr__(self, "input_data_ids", MappingProxyType(dict(self.input_data_ids)))
        object.__setattr__(
            self,
            "output_sources",
            MappingProxyType({key: tuple(value) for key, value in self.output_sources.items()}),
        )


def get_analysis_operation_descriptor(operation_id: str) -> OperationDescriptor:
    """Return a private Block-3 descriptor or fall through to the frozen public registry."""

    descriptor = _PRIVATE_DESCRIPTORS.get(operation_id)
    if descriptor is not None:
        return descriptor
    return get_operation_descriptor(operation_id)


def _processing_parameters(value: LSVProcessingSpec) -> dict[str, Any]:
    return {
        "rhe_mode": value.rhe_mode,
        "rhe_offset_v": value.rhe_offset_v,
        "reference_potential_vs_she_v": value.reference_potential_vs_she_v,
        "ph": value.ph,
        "temperature_k": value.temperature_k,
        "resistance_ohm": value.resistance_ohm,
        "ir_correction_fraction": value.ir_correction_fraction,
        "electrode_area_cm2": value.electrode_area_cm2,
        "normalize_to_current_density": value.normalize_to_current_density,
        "current_density_unit": value.current_density_unit,
    }


def _crop_parameters(value: AnalysisRange) -> dict[str, Any]:
    return {"x_min": value.x_min, "x_max": value.x_max, "inclusive": True}


def _binding(prefix: str, *parts: str) -> str:
    return ":".join((prefix, *parts))


def _append_crop(
    steps: list[RecipeStep],
    *,
    step_id: str,
    source_binding: str,
    output_binding: str,
    analysis_range: AnalysisRange,
) -> str:
    if not analysis_range.enabled:
        return source_binding
    steps.append(
        RecipeStep(
            step_id=step_id,
            operation_id="catalysis.processing.crop.v1",
            inputs={"series": source_binding},
            outputs={"series": output_binding},
            parameters=_crop_parameters(analysis_range),
        )
    )
    return output_binding


def _compile_lsv(document: AnalysisDocument, analysis: LSVAnalysisSpec) -> CompiledAnalysis:
    data_ids = tuple(sorted(item.data_id for item in document.data_series))
    inputs = {_binding("input", data_id): data_id for data_id in data_ids}
    steps: list[RecipeStep] = []
    outputs: dict[str, str] = {}
    output_sources: dict[str, tuple[str, ...]] = {}
    for data_id in data_ids:
        source = _binding("input", data_id)
        processed = _binding("processed", data_id)
        config = analysis.overrides.get(data_id, analysis.common)
        steps.append(
            RecipeStep(
                step_id=_binding("lsv", data_id),
                operation_id=_ANALYSIS_LSV_OP,
                inputs={"series": source},
                outputs={"series": processed},
                parameters=_processing_parameters(config),
            )
        )
        final = _append_crop(
            steps,
            step_id=_binding("range", data_id),
            source_binding=processed,
            output_binding=_binding("ranged", data_id),
            analysis_range=analysis.analysis_range,
        )
        output_name = _binding("processed", data_id)
        outputs[output_name] = final
        output_sources[output_name] = (data_id,)
    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=tuple(inputs),
        steps=tuple(steps),
        outputs=outputs,
    )
    return CompiledAnalysis(
        task_id=document.task_id,
        recipe=recipe,
        input_data_ids=inputs,
        output_sources=output_sources,
    )


def _compile_generic(
    document: AnalysisDocument,
    analysis: GenericXYAnalysisSpec,
) -> CompiledAnalysis:
    data_ids = tuple(sorted(item.data_id for item in document.data_series))
    inputs = {_binding("input", data_id): data_id for data_id in data_ids}
    steps: list[RecipeStep] = []
    outputs: dict[str, str] = {}
    output_sources: dict[str, tuple[str, ...]] = {}
    for data_id in data_ids:
        source = _binding("input", data_id)
        identity = _binding("identity", data_id)
        steps.append(
            RecipeStep(
                step_id=_binding("identity", data_id),
                operation_id=_ANALYSIS_IDENTITY_OP,
                inputs={"series": source},
                outputs={"series": identity},
                parameters={},
            )
        )
        final = _append_crop(
            steps,
            step_id=_binding("range", data_id),
            source_binding=identity,
            output_binding=_binding("ranged", data_id),
            analysis_range=analysis.analysis_range,
        )
        output_name = _binding("processed", data_id)
        outputs[output_name] = final
        output_sources[output_name] = (data_id,)
    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=tuple(inputs),
        steps=tuple(steps),
        outputs=outputs,
    )
    return CompiledAnalysis(
        task_id=document.task_id,
        recipe=recipe,
        input_data_ids=inputs,
        output_sources=output_sources,
    )


def _pair_key(pair: PartialCurrentPair) -> tuple[str, str]:
    return pair.current_data_id, pair.fe_data_id


def _compile_fe(
    document: AnalysisDocument,
    analysis: FEPartialCurrentAnalysisSpec,
) -> CompiledAnalysis:
    pairs = tuple(sorted(analysis.pairs, key=_pair_key))
    referenced = sorted(
        {data_id for pair in pairs for data_id in (pair.current_data_id, pair.fe_data_id)}
    )
    inputs = {_binding("input", data_id): data_id for data_id in referenced}
    steps: list[RecipeStep] = []
    processed_currents: dict[str, str] = {}
    for current_id in sorted({pair.current_data_id for pair in pairs}):
        source = _binding("input", current_id)
        processed = _binding("current", current_id)
        config = analysis.current_overrides.get(current_id, analysis.current_common)
        steps.append(
            RecipeStep(
                step_id=_binding("current", current_id),
                operation_id=_ANALYSIS_LSV_OP,
                inputs={"series": source},
                outputs={"series": processed},
                parameters=_processing_parameters(config),
            )
        )
        processed_currents[current_id] = processed

    outputs: dict[str, str] = {}
    output_sources: dict[str, tuple[str, ...]] = {}
    for pair in pairs:
        pair_id = _binding("pair", pair.current_data_id, pair.fe_data_id)
        partial = _binding("partial", pair.current_data_id, pair.fe_data_id)
        steps.append(
            RecipeStep(
                step_id=pair_id,
                operation_id=_ANALYSIS_PARTIAL_CURRENT_OP,
                inputs={
                    "current": processed_currents[pair.current_data_id],
                    "fe": _binding("input", pair.fe_data_id),
                },
                outputs={"series": partial},
                parameters={"sign_mode": "signed"},
            )
        )
        final = _append_crop(
            steps,
            step_id=_binding("range", pair.current_data_id, pair.fe_data_id),
            source_binding=partial,
            output_binding=_binding("ranged", pair.current_data_id, pair.fe_data_id),
            analysis_range=analysis.analysis_range,
        )
        output_name = _binding("partial", pair.current_data_id, pair.fe_data_id)
        outputs[output_name] = final
        output_sources[output_name] = (pair.current_data_id, pair.fe_data_id)

    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=tuple(inputs),
        steps=tuple(steps),
        outputs=outputs,
    )
    return CompiledAnalysis(
        task_id=document.task_id,
        recipe=recipe,
        input_data_ids=inputs,
        output_sources=output_sources,
    )


def compile_analysis(document: AnalysisDocument) -> CompiledAnalysis:
    """Compile a complete task document into an internal deterministic recipe."""

    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    if not document.data_series:
        raise ValueError("analysis requires at least one mapped data series")
    analysis = document.analysis
    if isinstance(analysis, LSVAnalysisSpec):
        return _compile_lsv(document, analysis)
    if isinstance(analysis, FEPartialCurrentAnalysisSpec):
        if not analysis.pairs:
            raise ValueError("FE & partial-current analysis requires at least one explicit pair")
        return _compile_fe(document, analysis)
    if isinstance(analysis, GenericXYAnalysisSpec):
        return _compile_generic(document, analysis)
    raise TypeError("analysis document has unsupported processing state")


__all__ = [
    "CompiledAnalysis",
    "compile_analysis",
    "get_analysis_operation_descriptor",
]
