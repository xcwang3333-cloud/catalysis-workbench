"""GUI-neutral live evaluation for deterministic v1.1 scientific analyses."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Literal

from catalysis_workbench import __version__
from catalysis_workbench._canonical_json import canonical_json_sha256
from catalysis_workbench.core import Series
from catalysis_workbench.experimental.echem.lsv import (
    LSVProcessingConfig,
    process_lsv,
    rhe_offset_from_she,
)
from catalysis_workbench.experimental.echem.partial_current_series import (
    partial_current_density_series,
)
from catalysis_workbench.experimental.echem.quantities import (
    is_current_density_unit,
    is_current_unit,
)
from catalysis_workbench.processing import crop
from catalysis_workbench.workflow import _adapters as workflow_adapters
from catalysis_workbench.workflow.execution import (
    StepExecutionRecord,
    WorkflowRun,
    _derive_output_identity,
)

from .compiler import CompiledAnalysis, compile_analysis, get_analysis_operation_descriptor
from .document import AnalysisDocument
from .materialization import MaterializedInput
from .processing import FEPartialCurrentAnalysisSpec, LSVProcessingSpec

AnalysisEvaluationStatus = Literal["success", "incomplete", "error"]


@dataclass(frozen=True, slots=True)
class AnalysisView:
    """One named ordered collection of Series suitable for live preview."""

    view_id: str
    label: str
    series: tuple[Series, ...]

    def __post_init__(self) -> None:
        if type(self.view_id) is not str or not self.view_id:
            raise ValueError("view_id must be a non-empty string")
        if type(self.label) is not str or not self.label:
            raise ValueError("view label must be a non-empty string")
        values = tuple(self.series)
        if not all(isinstance(item, Series) for item in values):
            raise TypeError("analysis view values must be Series instances")
        object.__setattr__(self, "series", values)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Successful runtime-only scientific result backed by a deterministic WorkflowRun."""

    document_sha256: str
    workflow_run: WorkflowRun
    views: tuple[AnalysisView, ...]

    def __post_init__(self) -> None:
        if type(self.document_sha256) is not str or len(self.document_sha256) != 64:
            raise ValueError("document_sha256 must be a SHA-256 string")
        if not isinstance(self.workflow_run, WorkflowRun):
            raise TypeError("workflow_run must be a WorkflowRun")
        views = tuple(self.views)
        if not views or not all(isinstance(item, AnalysisView) for item in views):
            raise ValueError("successful analysis result requires at least one AnalysisView")
        object.__setattr__(self, "views", views)


@dataclass(frozen=True, slots=True)
class AnalysisEvaluation:
    """Explicit live-evaluation state; errors never masquerade as successful current output."""

    status: AnalysisEvaluationStatus
    result: AnalysisResult | None = None
    message: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"success", "incomplete", "error"}:
            raise ValueError("invalid analysis evaluation status")
        if self.status == "success" and self.result is None:
            raise ValueError("successful evaluation requires a result")
        if self.status != "success" and self.result is not None:
            raise ValueError("non-success evaluation must not contain a result")
        if self.message is not None and (type(self.message) is not str or not self.message):
            raise ValueError("evaluation message must be a non-empty string or None")


class AnalysisEvaluator:
    """Compile, materialize, and execute one analysis without importing any GUI toolkit."""

    def evaluate(
        self,
        document: AnalysisDocument,
        materialize: Callable[[str], MaterializedInput],
    ) -> AnalysisEvaluation:
        if not isinstance(document, AnalysisDocument):
            raise TypeError("document must be an AnalysisDocument")
        if not callable(materialize):
            raise TypeError("materialize must be callable")
        if not document.data_series:
            return AnalysisEvaluation(
                status="incomplete",
                message="Add and map at least one data series to run the analysis.",
            )
        if isinstance(document.analysis, FEPartialCurrentAnalysisSpec) and not document.analysis.pairs:
            return AnalysisEvaluation(
                status="incomplete",
                message="Add at least one explicit current ↔ FE pair.",
            )
        try:
            compiled = compile_analysis(document)
            materialized = self._materialize_inputs(compiled, materialize)
            run = _execute_compiled(compiled, materialized)
            views = _build_views(document, compiled, materialized, run)
        except (OSError, TypeError, ValueError, RuntimeError) as exc:
            return AnalysisEvaluation(status="error", message=str(exc))
        return AnalysisEvaluation(
            status="success",
            result=AnalysisResult(
                document_sha256=document.document_sha256,
                workflow_run=run,
                views=views,
            ),
        )

    @staticmethod
    def _materialize_inputs(
        compiled: CompiledAnalysis,
        materialize: Callable[[str], MaterializedInput],
    ) -> Mapping[str, MaterializedInput]:
        by_data_id: dict[str, MaterializedInput] = {}
        for data_id in sorted(set(compiled.input_data_ids.values())):
            item = materialize(data_id)
            if not isinstance(item, MaterializedInput):
                raise TypeError("materialize callback must return MaterializedInput")
            if item.data_id != data_id:
                raise ValueError(
                    f"materialized data identity mismatch: expected {data_id!r}, got {item.data_id!r}"
                )
            by_data_id[data_id] = item
        return MappingProxyType(by_data_id)


def _validate_lsv_input(series: Series) -> None:
    if series.x_axis.name.casefold() != "potential":
        raise ValueError("LSV/current processing requires x_role='potential'")
    y_name = series.y_axis.name.casefold()
    if y_name == "current":
        if not is_current_unit(series.y_axis.unit):
            raise ValueError("current input requires an electrochemical current unit")
        return
    if y_name == "current_density":
        if not is_current_density_unit(series.y_axis.unit):
            raise ValueError("current-density input requires a supported current-density unit")
        return
    raise ValueError("LSV/current processing requires y_role='current' or 'current_density'")


def _lsv_config(parameters: Mapping[str, Any], series: Series) -> LSVProcessingConfig:
    spec = LSVProcessingSpec(**dict(parameters))
    offset: float | None = None
    source_reference: str | None = None
    if spec.rhe_mode == "direct":
        offset = spec.rhe_offset_v
    elif spec.rhe_mode == "she_ph":
        assert spec.reference_potential_vs_she_v is not None
        assert spec.ph is not None
        offset = rhe_offset_from_she(
            spec.reference_potential_vs_she_v,
            spec.ph,
            temperature_k=spec.temperature_k,
        )
    if offset is not None:
        declared = series.x_axis.metadata.get("reference")
        if declared is not None:
            source_reference = str(declared)
    return LSVProcessingConfig(
        rhe_offset_v=offset,
        source_reference=source_reference,
        resistance_ohm=spec.resistance_ohm,
        ir_correction_fraction=spec.ir_correction_fraction,
        electrode_area_cm2=spec.electrode_area_cm2,
        normalize_to_current_density=spec.normalize_to_current_density,
        current_density_unit=spec.current_density_unit,
    )


def _private_parameters(operation_id: str, parameters: Mapping[str, Any]) -> dict[str, Any]:
    descriptor = get_analysis_operation_descriptor(operation_id)
    provided = set(parameters)
    allowed = set(descriptor.parameter_names)
    missing = sorted(set(descriptor.required_parameters) - provided)
    unknown = sorted(provided - allowed)
    if missing or unknown:
        raise ValueError(
            f"invalid parameters for {operation_id!r}; missing={missing!r}, unknown={unknown!r}"
        )
    if operation_id == "catalysis.analysis.identity.v1":
        return {}
    if operation_id == "catalysis.analysis.lsv_process.v1":
        return _lsv_processing_parameters(LSVProcessingSpec(**dict(parameters)))
    if operation_id == "catalysis.analysis.partial_current_density.v1":
        if parameters.get("sign_mode") != "signed":
            raise ValueError("Block-3 partial current requires sign_mode='signed'")
        return {"sign_mode": "signed"}
    return workflow_adapters.validate_parameters(operation_id, parameters)


def _lsv_processing_parameters(value: LSVProcessingSpec) -> dict[str, Any]:
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


def _execute_operation(
    operation_id: str,
    inputs: Mapping[str, object],
    parameters: Mapping[str, Any],
) -> dict[str, Series]:
    if operation_id == "catalysis.analysis.identity.v1":
        series = inputs.get("series")
        if not isinstance(series, Series):
            raise TypeError("analysis identity operation requires Series input 'series'")
        return {"series": series}
    if operation_id == "catalysis.analysis.lsv_process.v1":
        series = inputs.get("series")
        if not isinstance(series, Series):
            raise TypeError("LSV analysis operation requires Series input 'series'")
        _validate_lsv_input(series)
        return {"series": process_lsv(series, _lsv_config(parameters, series))}
    if operation_id == "catalysis.analysis.partial_current_density.v1":
        current = inputs.get("current")
        fe = inputs.get("fe")
        if not isinstance(current, Series) or not isinstance(fe, Series):
            raise TypeError("partial-current analysis requires Series inputs 'current' and 'fe'")
        return {
            "series": partial_current_density_series(
                current,
                fe,
                sign_mode="signed",
            )
        }
    return workflow_adapters.execute_operation(operation_id, inputs, parameters)


def _plain_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _plain_json_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain_json_value(item) for item in value]
    return value


def _execute_compiled(
    compiled: CompiledAnalysis,
    materialized: Mapping[str, MaterializedInput],
) -> WorkflowRun:
    recipe = compiled.recipe
    input_values = {
        binding: materialized[data_id].value
        for binding, data_id in compiled.input_data_ids.items()
    }
    input_identities = {
        binding: materialized[data_id].input_sha256
        for binding, data_id in compiled.input_data_ids.items()
    }
    bindings: dict[str, object] = dict(input_values)
    binding_identities: dict[str, str] = dict(input_identities)
    records: list[StepExecutionRecord] = []

    for step in recipe.steps:
        descriptor = get_analysis_operation_descriptor(step.operation_id)
        if set(step.inputs) != set(descriptor.input_ports) or set(step.outputs) != set(
            descriptor.output_ports
        ):
            raise ValueError(f"step {step.step_id!r} does not match its operation port contract")
        effective = _private_parameters(step.operation_id, step.parameters)
        port_inputs = {
            port: bindings[binding_name]
            for port, binding_name in step.inputs.items()
        }
        port_input_identities = {
            port: binding_identities[binding_name]
            for port, binding_name in step.inputs.items()
        }
        outputs = _execute_operation(step.operation_id, port_inputs, effective)
        if set(outputs) != set(descriptor.output_ports):
            raise TypeError(f"{step.operation_id!r} returned unexpected output ports")
        output_identities = {
            port: _derive_output_identity(
                operation_id=step.operation_id,
                contract_version=descriptor.contract_version,
                input_identities=port_input_identities,
                effective_parameters=effective,
                output_port=port,
            )
            for port in descriptor.output_ports
        }
        for port in descriptor.output_ports:
            value = outputs[port]
            if not isinstance(value, Series):
                raise TypeError(f"{step.operation_id!r} output {port!r} is not a Series")
            binding_name = step.outputs[port]
            bindings[binding_name] = value
            binding_identities[binding_name] = output_identities[port]
        records.append(
            StepExecutionRecord(
                step_id=step.step_id,
                operation_id=step.operation_id,
                contract_version=descriptor.contract_version,
                input_identities=port_input_identities,
                effective_parameters=effective,
                output_identities=output_identities,
            )
        )

    final_outputs = {
        name: bindings[binding_name]
        for name, binding_name in recipe.outputs.items()
    }
    if not all(isinstance(value, Series) for value in final_outputs.values()):
        raise TypeError("analysis workflow outputs must be Series values")
    final_identities = {
        name: binding_identities[binding_name]
        for name, binding_name in recipe.outputs.items()
    }
    step_records = tuple(records)
    content_sha256 = canonical_json_sha256(
        {
            "identity_schema_version": 1,
            "recipe_sha256": recipe.recipe_sha256,
            "inputs": input_identities,
            "steps": [record._identity_dict() for record in step_records],
            "outputs": final_identities,
        }
    )
    environment = {"catalysis_workbench_version": __version__}
    record_sha256 = canonical_json_sha256(
        {
            "record_schema_version": 1,
            "content_sha256": content_sha256,
            "environment": environment,
            "status": "success",
        }
    )
    return WorkflowRun(
        recipe_sha256=recipe.recipe_sha256,
        content_sha256=content_sha256,
        record_sha256=record_sha256,
        outputs=final_outputs,
        output_identities=final_identities,
        steps=step_records,
        environment_evidence=environment,
    )


def _output_lookup(
    compiled: CompiledAnalysis,
    run: WorkflowRun,
) -> dict[tuple[str, ...], Series]:
    return {
        compiled.output_sources[name]: value
        for name, value in run.outputs.items()
    }


def _crop_for_preview(series: Series, analysis_range: object) -> Series:
    if getattr(analysis_range, "enabled", False):
        return crop(
            series,
            x_min=analysis_range.x_min,
            x_max=analysis_range.x_max,
            inclusive=True,
        )
    return series


def _build_views(
    document: AnalysisDocument,
    compiled: CompiledAnalysis,
    materialized: Mapping[str, MaterializedInput],
    run: WorkflowRun,
) -> tuple[AnalysisView, ...]:
    outputs = _output_lookup(compiled, run)
    if isinstance(document.analysis, FEPartialCurrentAnalysisSpec):
        fe_ids: list[str] = []
        for pair in document.analysis.pairs:
            if pair.fe_data_id not in fe_ids:
                fe_ids.append(pair.fe_data_id)
        fe_series = tuple(
            _crop_for_preview(
                materialized[data_id].value,
                document.analysis.analysis_range,
            )
            for data_id in fe_ids
        )
        partial = tuple(
            outputs[(pair.current_data_id, pair.fe_data_id)]
            for pair in document.analysis.pairs
        )
        return (
            AnalysisView(view_id="fe", label="FE", series=fe_series),
            AnalysisView(
                view_id="partial_current",
                label="Partial current",
                series=partial,
            ),
        )

    ordered = tuple(outputs[(spec.data_id,)] for spec in document.data_series)
    return (AnalysisView(view_id="processed", label="Processed", series=ordered),)


__all__ = [
    "AnalysisEvaluation",
    "AnalysisEvaluationStatus",
    "AnalysisEvaluator",
    "AnalysisResult",
    "AnalysisView",
]
