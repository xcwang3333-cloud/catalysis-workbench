"""Immutable workspace manifest state for local reproducible projects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
)


class WorkspaceError(ValueError):
    """Raised when workspace state or persistence semantics are invalid."""


_MANIFEST_FILENAME = "workspace.json"


def _identifier(value: object, *, label: str) -> str:
    if type(value) is not str or not value:
        raise WorkspaceError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise WorkspaceError(f"{label} must not have surrounding whitespace")
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise WorkspaceError(f"{label} must be valid UTF-8") from exc
    return value


def _workspace_owned_path(value: object) -> str:
    if type(value) is not str or not value:
        raise WorkspaceError("workspace asset path must be a non-empty string")
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise WorkspaceError("workspace asset path must be valid UTF-8") from exc

    if "\x00" in value:
        raise WorkspaceError("workspace asset path must not contain NUL")
    if "\\" in value:
        raise WorkspaceError("workspace asset path must use '/' separators")
    if value.startswith("/"):
        raise WorkspaceError("workspace asset path must be relative")
    if PureWindowsPath(value).drive:
        raise WorkspaceError("workspace asset path must not be drive-qualified")

    parts = value.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise WorkspaceError(
            "workspace asset path must not contain empty, '.', or '..' components"
        )

    path = PurePosixPath(value)
    if path.is_absolute():
        raise WorkspaceError("workspace asset path must be relative")
    normalized = path.as_posix()
    if normalized.casefold() == _MANIFEST_FILENAME.casefold():
        raise WorkspaceError(f"{_MANIFEST_FILENAME!r} is reserved workspace metadata")
    return normalized


@dataclass(frozen=True, slots=True)
class WorkspaceAsset:
    """One explicitly identified workspace-owned asset entry."""

    asset_id: str
    asset_type: str
    path: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", _identifier(self.asset_id, label="asset_id"))
        object.__setattr__(
            self,
            "asset_type",
            _identifier(self.asset_type, label="asset_type"),
        )
        object.__setattr__(self, "path", _workspace_owned_path(self.path))


@dataclass(frozen=True, slots=True)
class WorkspaceManifest:
    """Ordered immutable workspace state with deterministic identity."""

    schema_version: int
    assets: Sequence[WorkspaceAsset]
    manifest_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise WorkspaceError("workspace schema_version must be the integer 1")
        if isinstance(self.assets, (str, bytes)) or not isinstance(self.assets, Sequence):
            raise WorkspaceError("workspace assets must be an ordered sequence")

        assets = tuple(self.assets)
        if not all(isinstance(asset, WorkspaceAsset) for asset in assets):
            raise TypeError("workspace assets must contain WorkspaceAsset instances")

        asset_ids = tuple(asset.asset_id for asset in assets)
        if len(set(asset_ids)) != len(asset_ids):
            raise WorkspaceError("workspace asset_id values must be unique")

        paths = tuple(asset.path for asset in assets)
        if len(set(paths)) != len(paths):
            raise WorkspaceError("workspace asset paths must be unique")

        object.__setattr__(self, "assets", assets)
        try:
            digest = canonical_json_sha256(_manifest_to_plain_dict(self))
        except CanonicalJSONError as exc:
            raise WorkspaceError(
                "workspace manifest must contain only strict canonical JSON state"
            ) from exc
        object.__setattr__(self, "manifest_sha256", digest)


_MANIFEST_FIELDS = frozenset({"schema_version", "assets"})
_ASSET_FIELDS = frozenset({"asset_id", "asset_type", "path"})


def _required_fields(
    value: Mapping[object, object],
    *,
    required: frozenset[str],
    label: str,
) -> None:
    if not all(type(key) is str for key in value):
        raise WorkspaceError(f"{label} field names must be strings")
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required)
    if missing or unknown:
        raise WorkspaceError(
            f"invalid {label} fields; missing={missing!r}, unknown={unknown!r}"
        )


def _manifest_to_plain_dict(manifest: WorkspaceManifest) -> dict[str, Any]:
    return {
        "schema_version": manifest.schema_version,
        "assets": [
            {
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type,
                "path": asset.path,
            }
            for asset in manifest.assets
        ],
    }


def _manifest_from_dict(value: object) -> WorkspaceManifest:
    if not isinstance(value, Mapping):
        raise WorkspaceError("serialized workspace manifest must be an object")
    _required_fields(value, required=_MANIFEST_FIELDS, label="workspace manifest")

    assets = value["assets"]
    if not isinstance(assets, list):
        raise WorkspaceError("serialized workspace assets must be a list")

    parsed_assets: list[WorkspaceAsset] = []
    for index, asset in enumerate(assets):
        if not isinstance(asset, Mapping):
            raise WorkspaceError(f"serialized workspace asset {index} must be an object")
        _required_fields(
            asset,
            required=_ASSET_FIELDS,
            label=f"workspace asset {index}",
        )
        parsed_assets.append(
            WorkspaceAsset(
                asset_id=asset["asset_id"],
                asset_type=asset["asset_type"],
                path=asset["path"],
            )
        )

    return WorkspaceManifest(
        schema_version=value["schema_version"],
        assets=parsed_assets,
    )
