"""Serializable, reproducible FigureSpec preset bundles."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
)

from .presets import _install_presets_atomic
from .specs import FigureSpec, VisualizationError


def _preset_name(value: object) -> str:
    if type(value) is not str or not value:
        raise VisualizationError("preset entry name must be a non-empty string")
    if value != value.strip():
        raise VisualizationError(
            "preset entry name must not contain surrounding whitespace"
        )
    if value != value.lower():
        raise VisualizationError("preset entry name must be lowercase")
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise VisualizationError("preset entry name must be valid UTF-8") from exc
    return value


@dataclass(frozen=True, slots=True)
class FigurePresetEntry:
    """One stable registry name and its immutable presentation specification."""

    name: str
    spec: FigureSpec

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _preset_name(self.name))
        if not isinstance(self.spec, FigureSpec):
            raise TypeError("preset entry spec must be a FigureSpec")


@dataclass(frozen=True, slots=True)
class FigurePresetBundle:
    """An ordered, schema-versioned collection of reusable FigureSpec presets."""

    schema_version: int
    entries: Sequence[FigurePresetEntry]
    bundle_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise VisualizationError("preset bundle schema_version must be the integer 1")
        if isinstance(self.entries, (str, bytes)) or not isinstance(
            self.entries, Sequence
        ):
            raise VisualizationError("preset bundle entries must be an ordered sequence")
        entries = tuple(self.entries)
        if not entries:
            raise VisualizationError("preset bundle must contain at least one entry")
        if not all(isinstance(entry, FigurePresetEntry) for entry in entries):
            raise TypeError("preset bundle entries must contain FigurePresetEntry instances")
        names = tuple(entry.name for entry in entries)
        if len(set(names)) != len(names):
            raise VisualizationError("preset bundle entry names must be unique")
        object.__setattr__(self, "entries", entries)
        try:
            digest = canonical_json_sha256(_bundle_to_plain_dict(self))
        except CanonicalJSONError as exc:
            raise VisualizationError(
                "preset bundle must contain only strict canonical JSON state"
            ) from exc
        object.__setattr__(self, "bundle_sha256", digest)


_BUNDLE_FIELDS = frozenset({"schema_version", "entries"})
_ENTRY_FIELDS = frozenset({"name", "spec"})


def _required_fields(
    value: Mapping[object, object], *, required: frozenset[str], label: str
) -> None:
    if not all(type(key) is str for key in value):
        raise VisualizationError(f"{label} field names must be strings")
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required)
    if missing or unknown:
        raise VisualizationError(
            f"invalid {label} fields; missing={missing!r}, unknown={unknown!r}"
        )


def _bundle_to_plain_dict(bundle: FigurePresetBundle) -> dict[str, Any]:
    return {
        "schema_version": bundle.schema_version,
        "entries": [
            {
                "name": entry.name,
                "spec": entry.spec.to_dict(),
            }
            for entry in bundle.entries
        ],
    }


def _bundle_from_dict(value: object) -> FigurePresetBundle:
    if not isinstance(value, Mapping):
        raise VisualizationError("serialized preset bundle must be an object")
    _required_fields(value, required=_BUNDLE_FIELDS, label="preset bundle")
    entries = value["entries"]
    if not isinstance(entries, list):
        raise VisualizationError("serialized preset bundle entries must be a list")

    parsed_entries: list[FigurePresetEntry] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, Mapping):
            raise VisualizationError(f"serialized preset entry {index} must be an object")
        _required_fields(
            entry,
            required=_ENTRY_FIELDS,
            label=f"preset entry {index}",
        )
        spec = entry["spec"]
        if not isinstance(spec, Mapping):
            raise VisualizationError(
                f"serialized preset entry {index} spec must be an object"
            )
        try:
            figure_spec = FigureSpec.from_dict(spec)
        except (TypeError, ValueError) as exc:
            raise VisualizationError(
                f"invalid FigureSpec in serialized preset entry {index}"
            ) from exc
        parsed_entries.append(
            FigurePresetEntry(
                name=entry["name"],
                spec=figure_spec,
            )
        )
    return FigurePresetBundle(
        schema_version=value["schema_version"],
        entries=parsed_entries,
    )


def save_preset_bundle(
    bundle: FigurePresetBundle,
    path: str | Path,
    *,
    overwrite: bool = False,
) -> None:
    """Write a bundle as canonical UTF-8 JSON with one trailing newline."""

    if not isinstance(bundle, FigurePresetBundle):
        raise TypeError("bundle must be a FigurePresetBundle")
    if type(overwrite) is not bool:
        raise TypeError("overwrite must be a bool")
    try:
        payload = canonical_json_bytes(_bundle_to_plain_dict(bundle)) + b"\n"
    except CanonicalJSONError as exc:
        raise VisualizationError("preset bundle cannot be serialized") from exc
    mode = "wb" if overwrite else "xb"
    with Path(path).open(mode) as stream:
        stream.write(payload)


def load_preset_bundle(path: str | Path) -> FigurePresetBundle:
    """Strictly load and validate a preset bundle from a UTF-8 JSON file."""

    try:
        text = Path(path).read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise VisualizationError(
            f"preset bundle file is not valid UTF-8: {path!s}"
        ) from exc
    try:
        value = loads_strict_json(text)
    except CanonicalJSONError as exc:
        raise VisualizationError(f"cannot load preset bundle from {path!s}") from exc
    return _bundle_from_dict(value)


def install_preset_bundle(
    bundle: FigurePresetBundle,
    *,
    overwrite: bool = False,
) -> None:
    """Install all bundle entries only after complete conflict validation."""

    if not isinstance(bundle, FigurePresetBundle):
        raise TypeError("bundle must be a FigurePresetBundle")
    if type(overwrite) is not bool:
        raise TypeError("overwrite must be a bool")
    _install_presets_atomic(
        tuple((entry.name, entry.spec) for entry in bundle.entries),
        overwrite=overwrite,
    )
