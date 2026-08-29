"""Deterministic presentation-only figure state for v1.1 analyses."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from catalysis_workbench._canonical_json import CanonicalJSONError, canonical_json_sha256
from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import FigureSpec, SeriesStyle, get_preset, render_curves

if TYPE_CHECKING:
    from .evaluator import AnalysisView


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


def _view_parts(view: AnalysisView) -> tuple[str, tuple[str, ...], tuple[str, ...], tuple[Series, ...]]:
    view_id = _identifier(getattr(view, "view_id", None), label="view_id")
    trace_ids = tuple(getattr(view, "trace_ids", ()))
    identities = tuple(getattr(view, "series_identities", ()))
    series = tuple(getattr(view, "series", ()))
    if not trace_ids or not all(type(item) is str and item for item in trace_ids):
        raise AnalysisFigureError("analysis view does not expose stable trace IDs")
    if len(trace_ids) != len(set(trace_ids)):
        raise AnalysisFigureError("analysis view trace IDs must be unique")
    if len(trace_ids) != len(identities) or len(trace_ids) != len(series):
        raise AnalysisFigureError("analysis view trace identity lengths do not match")
    if not all(isinstance(item, Series) for item in series):
        raise TypeError("analysis view series must contain Series instances")
    checked_identities = tuple(
        _sha256(value, label=f"series identity for {trace_id!r}")
        for trace_id, value in zip(trace_ids, identities, strict=True)
    )
    return view_id, trace_ids, checked_identities, series


def _view_identity_mapping(view: AnalysisView) -> dict[str, str]:
    _view_id, trace_ids, identities, _series = _view_parts(view)
    return dict(zip(trace_ids, identities, strict=True))


def create_figure_draft(
    view: AnalysisView,
    *,
    preset: str = "publication",
) -> FigureDraft:
    """Create a presentation draft and freeze initial labels/colors explicitly."""

    view_id, trace_ids, identities, series = _view_parts(view)
    spec = get_preset(preset)
    colors = spec.style.color_cycle
    for index, (trace_id, item) in enumerate(zip(trace_ids, series, strict=True)):
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
        view_id=view_id,
        trace_identities=dict(zip(trace_ids, identities, strict=True)),
        trace_order=trace_ids,
        figure_spec=spec,
    )


def figure_draft_is_stale(draft: FigureDraft, view: AnalysisView) -> bool:
    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    view_id, _trace_ids, _identities, _series = _view_parts(view)
    if view_id != draft.view_id:
        return True
    return source_view_sha256(view_id, _view_identity_mapping(view)) != draft.source_view_sha256


def refresh_figure_draft(draft: FigureDraft, view: AnalysisView) -> FigureDraft:
    """Explicitly rebind a stale draft while preserving surviving trace styling/order."""

    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    view_id, trace_ids, identities, series = _view_parts(view)
    if view_id != draft.view_id:
        raise AnalysisFigureError(
            f"cannot refresh figure view {draft.view_id!r} from {view_id!r}"
        )
    current = set(trace_ids)
    order = [trace_id for trace_id in draft.trace_order if trace_id in current]
    order.extend(trace_id for trace_id in trace_ids if trace_id not in order)

    spec = draft.figure_spec
    for style_id in tuple(spec.series_styles):
        if style_id not in current:
            spec = spec.without_series_style(style_id)
    by_id = dict(zip(trace_ids, series, strict=True))
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
        view_id=view_id,
        trace_identities=dict(zip(trace_ids, identities, strict=True)),
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


def render_figure_draft(view: AnalysisView, draft: FigureDraft):
    """Render only visible traces; display limits never crop scientific Series arrays."""

    if not isinstance(draft, FigureDraft):
        raise TypeError("draft must be a FigureDraft")
    view_id, trace_ids, _identities, series = _view_parts(view)
    if view_id != draft.view_id or figure_draft_is_stale(draft, view):
        raise AnalysisFigureError(
            "analysis results changed; refresh this figure before previewing"
        )
    by_id = dict(zip(trace_ids, series, strict=True))
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
    "allowed_figure_view_ids",
    "create_figure_draft",
    "figure_draft_is_stale",
    "move_figure_trace",
    "refresh_figure_draft",
    "render_figure_draft",
    "replace_figure_spec",
    "source_view_sha256",
]
