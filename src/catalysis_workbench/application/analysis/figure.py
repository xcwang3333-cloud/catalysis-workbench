"""Deterministic presentation-only figure state for v1.1 analyses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from catalysis_workbench._canonical_json import CanonicalJSONError, canonical_json_sha256
from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import FigureSpec, SeriesStyle, get_preset, render_curves


class AnalysisFigureError(ValueError):
    """Raised when persisted Figure Workbench state is invalid or stale."""


_ALLOWED_VIEW_IDS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "lsv": ("processed",),
        "generic_xy": ("processed",),
        "fe_partial_current": ("fe", "partial_current"),
    }
)


def allowed_figure_view_ids(task_id: str) -> tuple[str, ...]:
    try:
        return _ALLOWED_VIEW_IDS[task_id]
    except KeyError as exc:
        raise AnalysisFigureError(f"unsupported analysis task for figures: {task_id!r}") from exc


def _identifier(value: object, *, label: str) -> str:
    if type(value) is not str or not value or value != value.strip():
        raise AnalysisFigureError(
            f"{label} must be a non-empty string without surrounding whitespace"
        )
    return value


def _sha256(value: object, *, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or value != value.lower()
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise AnalysisFigureError(f"{label} must be a lowercase SHA-256")
    return value


def source_view_sha256(view_id: str, trace_identities: Mapping[str, str]) -> str:
    """Return a scientific-view identity independent of presentation ordering."""

    checked_view = _identifier(view_id, label="view_id")
    if not isinstance(trace_identities, Mapping):
        raise TypeError("trace_identities must be a mapping")
    checked: dict[str, str] = {}
    for key, value in trace_identities.items():
        trace_id = _identifier(key, label="trace identity key")
        if trace_id in checked:
            raise AnalysisFigureError("trace identity keys must be unique")
        checked[trace_id] = _sha256(value, label=f"trace identity for {trace_id!r}")
    if not checked:
        raise AnalysisFigureError("figure source view requires at least one trace")
    try:
        return canonical_json_sha256(
            {
                "identity_schema_version": 1,
                "view_id": checked_view,
                "trace_identities": dict(sorted(checked.items())),
            }
        )
    except CanonicalJSONError as exc:
        raise AnalysisFigureError("figure source identity cannot be canonicalized") from exc


@dataclass(frozen=True, slots=True)
class FigureSourceView:
    """Runtime-only exact scientific content behind one Figure Workbench result view."""

    view_id: str
    trace_ids: Sequence[str]
    series_identities: Sequence[str]
    series: Sequence[Series]
    source_view_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        view_id = _identifier(self.view_id, label="view_id")
        if isinstance(self.trace_ids, (str, bytes)) or not isinstance(
            self.trace_ids, Sequence
        ):
            raise TypeError("trace_ids must be an ordered sequence")
        trace_ids = tuple(_identifier(item, label="trace_id") for item in self.trace_ids)
        if not trace_ids or len(trace_ids) != len(set(trace_ids)):
            raise AnalysisFigureError("figure source trace IDs must be non-empty and unique")
        if isinstance(self.series_identities, (str, bytes)) or not isinstance(
            self.series_identities, Sequence
        ):
            raise TypeError("series_identities must be an ordered sequence")
        identities = tuple(
            _sha256(item, label=f"series identity for {trace_id!r}")
            for trace_id, item in zip(trace_ids, self.series_identities, strict=True)
        )
        series = tuple(self.series)
        if len(series) != len(trace_ids) or len(identities) != len(trace_ids):
            raise AnalysisFigureError("figure source trace identity lengths do not match")
        if not all(isinstance(item, Series) for item in series):
            raise TypeError("figure source series must contain Series instances")
        mapping = dict(zip(trace_ids, identities, strict=True))
        object.__setattr__(self, "view_id", view_id)
        object.__setattr__(self, "trace_ids", trace_ids)
        object.__setattr__(self, "series_identities", identities)
        object.__setattr__(self, "series", series)
        object.__setattr__(self, "source_view_sha256", source_view_sha256(view_id, mapping))

    @property
    def trace_identities(self) -> Mapping[str, str]:
        return MappingProxyType(
            dict(zip(self.trace_ids, self.series_identities, strict=True))
        )


@dataclass(frozen=True, slots=True)
class FigureDraft:
    """Persisted publication presentation state bound to exact scientific traces."""

    schema_version: int
    view_id: str
    trace_identities: Mapping[str, str]
    trace_order: Sequence[str]
    figure_spec: FigureSpec
    source_view_sha256: str = field(init=False)
    figure_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise AnalysisFigureError("figure draft schema_version must be the integer 1")
        view_id = _identifier(self.view_id, label="view_id")
        if not isinstance(self.trace_identities, Mapping):
            raise TypeError("trace_identities must be a mapping")
        identities: dict[str, str] = {}
        for key, value in self.trace_identities.items():
            trace_id = _identifier(key, label="trace identity key")
            if trace_id in identities:
                raise AnalysisFigureError("trace identity keys must be unique")
            identities[trace_id] = _sha256(
                value, label=f"trace identity for {trace_id!r}"
            )
        if not identities:
            raise AnalysisFigureError("figure draft requires at least one trace")
        if isinstance(self.trace_order, (str, bytes)) or not isinstance(
            self.trace_order, Sequence
        ):
            raise TypeError("trace_order must be an ordered sequence")
        order = tuple(
            _identifier(item, label="trace_order item") for item in self.trace_order
        )
        if len(order) != len(set(order)):
            raise AnalysisFigureError("trace_order values must be unique")
        if set(order) != set(identities):
            raise AnalysisFigureError(
                "trace_order must contain every trace identity exactly once"
            )
        if not isinstance(self.figure_spec, FigureSpec):
            raise TypeError("figure_spec must be a FigureSpec")
        unknown_styles = set(self.figure_spec.series_styles) - set(identities)
        if unknown_styles:
            raise AnalysisFigureError(
                f"FigureSpec references unknown trace IDs: {sorted(unknown_styles)!r}"
            )

        object.__setattr__(self, "view_id", view_id)
        object.__setattr__(self, "trace_identities", MappingProxyType(identities))
        object.__setattr__(self, "trace_order", order)
        source_digest = source_view_sha256(view_id, identities)
        object.__setattr__(self, "source_view_sha256", source_digest)
        try:
            figure_digest = canonical_json_sha256(_figure_draft_to_plain_dict(self))
        except CanonicalJSONError as exc:
            raise AnalysisFigureError("figure draft cannot be canonicalized") from exc
        object.__setattr__(self, "figure_sha256", figure_digest)


_FIGURE_DRAFT_FIELDS = frozenset(
    {"schema_version", "view_id", "trace_identities", "trace_order", "figure_spec"}
)


def _figure_draft_to_plain_dict(draft: FigureDraft) -> dict[str, Any]:
    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    return {
        "schema_version": 1,
        "view_id": draft.view_id,
        "trace_identities": dict(sorted(draft.trace_identities.items())),
        "trace_order": list(draft.trace_order),
        "figure_spec": draft.figure_spec.to_dict(),
    }


def _figure_draft_from_dict(value: object) -> FigureDraft:
    if not isinstance(value, dict):
        raise AnalysisFigureError("serialized figure draft must be an object")
    if not all(type(key) is str for key in value):
        raise AnalysisFigureError("figure draft field names must be strings")
    fields = set(value)
    missing = sorted(_FIGURE_DRAFT_FIELDS - fields)
    unknown = sorted(fields - _FIGURE_DRAFT_FIELDS)
    if missing or unknown:
        raise AnalysisFigureError(
            f"invalid figure draft fields; missing={missing!r}, unknown={unknown!r}"
        )
    identities = value["trace_identities"]
    order = value["trace_order"]
    spec = value["figure_spec"]
    if not isinstance(identities, dict):
        raise AnalysisFigureError("serialized trace_identities must be an object")
    if not isinstance(order, list):
        raise AnalysisFigureError("serialized trace_order must be an array")
    if not isinstance(spec, dict):
        raise AnalysisFigureError("serialized figure_spec must be an object")
    try:
        figure_spec = FigureSpec.from_dict(spec)
    except (TypeError, ValueError) as exc:
        raise AnalysisFigureError("serialized figure_spec is invalid") from exc
    return FigureDraft(
        schema_version=value["schema_version"],
        view_id=value["view_id"],
        trace_identities=identities,
        trace_order=order,
        figure_spec=figure_spec,
    )


def _pair_trace_id(current_data_id: str, fe_data_id: str) -> str:
    digest = canonical_json_sha256(
        {
            "identity_schema_version": 1,
            "current_data_id": current_data_id,
            "fe_data_id": fe_data_id,
        }
    )
    return f"pair-{digest}"


def _output_identity_by_source(document: object, result: object) -> dict[tuple[str, ...], str]:
    from .compiler import compile_analysis

    compiled = compile_analysis(document)  # type: ignore[arg-type]
    run = result.workflow_run  # type: ignore[attr-defined]
    identities: dict[tuple[str, ...], str] = {}
    for output_name, source in compiled.output_sources.items():
        try:
            digest = run.output_identities[output_name]
        except KeyError as exc:
            raise AnalysisFigureError(
                f"analysis result is missing output identity {output_name!r}"
            ) from exc
        identities[tuple(source)] = _sha256(
            digest, label=f"workflow output identity {output_name!r}"
        )
    return identities


def figure_source_view(document: object, result: object, view_id: str) -> FigureSourceView:
    """Resolve one current analysis view into logical trace IDs and scientific identities."""

    from .document import AnalysisDocument
    from .evaluator import AnalysisResult
    from .processing import FEPartialCurrentAnalysisSpec

    if not isinstance(document, AnalysisDocument):
        raise TypeError("document must be an AnalysisDocument")
    if not isinstance(result, AnalysisResult):
        raise TypeError("result must be an AnalysisResult")
    checked_view_id = _identifier(view_id, label="view_id")
    if checked_view_id not in allowed_figure_view_ids(document.task_id):
        raise AnalysisFigureError(
            f"view {checked_view_id!r} is not available for task {document.task_id!r}"
        )
    view = next((item for item in result.views if item.view_id == checked_view_id), None)
    if view is None:
        raise AnalysisFigureError(f"analysis result does not contain view {checked_view_id!r}")

    if checked_view_id == "processed":
        identity_by_source = _output_identity_by_source(document, result)
        trace_ids = tuple(item.data_id for item in document.data_series)
        identities = tuple(identity_by_source[(data_id,)] for data_id in trace_ids)
        return FigureSourceView(
            view_id=checked_view_id,
            trace_ids=trace_ids,
            series_identities=identities,
            series=view.series,
        )

    analysis = document.analysis
    if not isinstance(analysis, FEPartialCurrentAnalysisSpec):
        raise AnalysisFigureError("FE figure views require FE & partial-current processing state")
    if checked_view_id == "fe":
        fe_ids: list[str] = []
        for pair in analysis.pairs:
            if pair.fe_data_id not in fe_ids:
                fe_ids.append(pair.fe_data_id)
        by_id = {item.data_id: item for item in document.data_series}
        identities = tuple(
            _sha256(by_id[data_id].input_sha256, label=f"input identity {data_id!r}")
            for data_id in fe_ids
        )
        return FigureSourceView(
            view_id=checked_view_id,
            trace_ids=tuple(fe_ids),
            series_identities=identities,
            series=view.series,
        )

    identity_by_source = _output_identity_by_source(document, result)
    trace_ids = tuple(
        _pair_trace_id(pair.current_data_id, pair.fe_data_id) for pair in analysis.pairs
    )
    identities = tuple(
        identity_by_source[(pair.current_data_id, pair.fe_data_id)]
        for pair in analysis.pairs
    )
    return FigureSourceView(
        view_id=checked_view_id,
        trace_ids=trace_ids,
        series_identities=identities,
        series=view.series,
    )


def create_figure_draft(
    document: object,
    result: object,
    view_id: str,
    *,
    preset: str = "publication",
) -> FigureDraft:
    """Create a presentation draft and freeze initial labels/colors explicitly."""

    source = figure_source_view(document, result, view_id)
    spec = get_preset(preset)
    colors = spec.style.color_cycle
    for index, (trace_id, item) in enumerate(
        zip(source.trace_ids, source.series, strict=True)
    ):
        label = item.label or item.key or trace_id
        spec = spec.with_series_style(
            trace_id,
            SeriesStyle(
                color=colors[index % len(colors)],
                label=label,
                visible=True,
            ),
        )
    return FigureDraft(
        schema_version=1,
        view_id=source.view_id,
        trace_identities=source.trace_identities,
        trace_order=source.trace_ids,
        figure_spec=spec,
    )


def figure_draft_is_stale(draft: FigureDraft, document: object, result: object) -> bool:
    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    source = figure_source_view(document, result, draft.view_id)
    return source.source_view_sha256 != draft.source_view_sha256


def refresh_figure_draft(draft: FigureDraft, document: object, result: object) -> FigureDraft:
    """Explicitly rebind a stale draft while preserving surviving trace styling/order."""

    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    source = figure_source_view(document, result, draft.view_id)
    current = set(source.trace_ids)
    order = [trace_id for trace_id in draft.trace_order if trace_id in current]
    order.extend(trace_id for trace_id in source.trace_ids if trace_id not in order)

    spec = draft.figure_spec
    for style_id in tuple(spec.series_styles):
        if style_id not in current:
            spec = spec.without_series_style(style_id)
    by_id = dict(zip(source.trace_ids, source.series, strict=True))
    colors = spec.style.color_cycle
    for index, trace_id in enumerate(order):
        if trace_id in spec.series_styles:
            continue
        item = by_id[trace_id]
        spec = spec.with_series_style(
            trace_id,
            SeriesStyle(
                color=colors[index % len(colors)],
                label=item.label or item.key or trace_id,
                visible=True,
            ),
        )
    return FigureDraft(
        schema_version=1,
        view_id=source.view_id,
        trace_identities=source.trace_identities,
        trace_order=order,
        figure_spec=spec,
    )


def replace_figure_spec(draft: FigureDraft, spec: FigureSpec) -> FigureDraft:
    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    if not isinstance(spec, FigureSpec):
        raise TypeError("spec must be a FigureSpec")
    return FigureDraft(
        schema_version=1,
        view_id=draft.view_id,
        trace_identities=draft.trace_identities,
        trace_order=draft.trace_order,
        figure_spec=spec,
    )


def move_figure_trace(draft: FigureDraft, trace_id: str, new_index: int) -> FigureDraft:
    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    checked = _identifier(trace_id, label="trace_id")
    if checked not in draft.trace_identities:
        raise AnalysisFigureError(f"unknown figure trace_id: {checked!r}")
    if type(new_index) is not int or not 0 <= new_index < len(draft.trace_order):
        raise AnalysisFigureError("new figure trace index is out of range")
    order = list(draft.trace_order)
    old_index = order.index(checked)
    if old_index == new_index:
        return draft
    order.pop(old_index)
    order.insert(new_index, checked)
    return FigureDraft(
        schema_version=1,
        view_id=draft.view_id,
        trace_identities=draft.trace_identities,
        trace_order=order,
        figure_spec=draft.figure_spec,
    )


def _visible_render_spec(draft: FigureDraft, visible_ids: Sequence[str]) -> FigureSpec:
    plain = draft.figure_spec.to_dict()
    visible = set(visible_ids)
    plain["series_styles"] = {
        key: value
        for key, value in plain["series_styles"].items()
        if key in visible
    }
    return FigureSpec.from_dict(plain)


def render_figure_draft(document: object, result: object, draft: FigureDraft):
    """Render only visible traces; display limits never crop scientific Series arrays."""

    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    source = figure_source_view(document, result, draft.view_id)
    if source.source_view_sha256 != draft.source_view_sha256:
        raise AnalysisFigureError(
            "analysis results changed; refresh this figure before previewing"
        )
    by_id = dict(zip(source.trace_ids, source.series, strict=True))
    visible_ids = tuple(
        trace_id
        for trace_id in draft.trace_order
        if draft.figure_spec.series_styles.get(trace_id, SeriesStyle()).visible
    )
    if not visible_ids:
        raise AnalysisFigureError("at least one figure trace must remain visible")
    rendered: list[Series] = []
    for trace_id in visible_ids:
        item = by_id[trace_id]
        rendered.append(
            Series(
                x=item.x,
                y=item.y,
                label=item.label,
                key=trace_id,
                x_axis=item.x_axis,
                y_axis=item.y_axis,
                metadata=item.metadata_dict(),
            )
        )
    spec = _visible_render_spec(draft, visible_ids)
    data: Series | Dataset
    if len(rendered) == 1:
        data = rendered[0]
    else:
        data = Dataset(tuple(rendered))
    return render_curves(data, spec)


__all__ = [
    "AnalysisFigureError",
    "FigureDraft",
    "FigureSourceView",
    "allowed_figure_view_ids",
    "create_figure_draft",
    "figure_draft_is_stale",
    "figure_source_view",
    "move_figure_trace",
    "refresh_figure_draft",
    "render_figure_draft",
    "replace_figure_spec",
    "source_view_sha256",
]
