"""Versioned source-controlled publication figure presets."""

from __future__ import annotations

from dataclasses import dataclass

from catalysis_workbench._canonical_json import (
    canonical_json_bytes,
    canonical_json_sha256,
)

from .specs import FigureSpec


@dataclass(frozen=True, slots=True)
class _PublicationPresetAsset:
    name: str
    asset_version: int
    figure_spec: FigureSpec

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise TypeError("publication preset name must be a non-empty string")
        if self.name != self.name.strip():
            raise ValueError("publication preset name must not contain surrounding whitespace")
        if type(self.asset_version) is not int or self.asset_version <= 0:
            raise ValueError("publication preset asset_version must be a positive integer")
        if not self.name.endswith(f".v{self.asset_version}"):
            raise ValueError("publication preset name/version mismatch")
        if not isinstance(self.figure_spec, FigureSpec):
            raise TypeError("publication preset figure_spec must be a FigureSpec")


_PUBLICATION_PRESETS = (
    _PublicationPresetAsset(
        name="catalysis.publication.single-column.v1",
        asset_version=1,
        figure_spec=FigureSpec(),
    ),
)


def _get_asset(name: str) -> _PublicationPresetAsset:
    if type(name) is not str:
        raise TypeError("publication preset name must be a string")
    for asset in _PUBLICATION_PRESETS:
        if asset.name == name:
            return asset
    raise KeyError(name)


def list_publication_presets() -> tuple[str, ...]:
    """Return bundled publication preset names in source-controlled order."""

    return tuple(asset.name for asset in _PUBLICATION_PRESETS)


def get_publication_preset(name: str) -> FigureSpec:
    """Return one exact immutable bundled publication figure specification."""

    return _get_asset(name).figure_spec


def publication_preset_manifest(name: str) -> dict[str, object]:
    """Return a deterministic JSON-safe manifest suitable for supplementary information."""

    asset = _get_asset(name)
    figure_spec = asset.figure_spec.to_dict()
    manifest: dict[str, object] = {
        "manifest_schema_version": 1,
        "preset_name": asset.name,
        "asset_version": asset.asset_version,
        "figure_spec": figure_spec,
        "figure_spec_sha256": canonical_json_sha256(figure_spec),
    }
    canonical_json_bytes(manifest)
    return manifest
