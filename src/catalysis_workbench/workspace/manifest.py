"""Immutable workspace manifest state for local reproducible projects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath, PureWindowsPath
from string import hexdigits
from typing import Any

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
)


class WorkspaceError(ValueError):
    """Raised when workspace state or persistence semantics are invalid."""


_MANIFEST_FILENAME = "workspace.json"
_RESERVED_WORKSPACE_METADATA = frozenset(
    {
        _MANIFEST_FILENAME,
        "project.json",
        "workspace-evidence.json",
        "workspace-composition.json",
    }
)
_ASSET_POLICIES = frozenset({"copy", "reference"})


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


def _asset_policy(value: object) -> str:
    if type(value) is not str or value not in _ASSET_POLICIES:
        raise WorkspaceError("asset policy must be 'copy' or 'reference'")
    return value


def _content_sha256(value: object | None) -> str | None:
    if value is None:
        return None
    if type(value) is not str or len(value) != 64:
        raise WorkspaceError("content_sha256 must be a 64-character lowercase SHA-256")
    if value != value.lower() or any(character not in hexdigits.lower() for character in value):
        raise WorkspaceError("content_sha256 must be a 64-character lowercase SHA-256")
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
    reserved = {name.casefold() for name in _RESERVED_WORKSPACE_METADATA}
    if normalized.casefold() in reserved:
        raise WorkspaceError(f"{normalized!r} is reserved workspace metadata")
    return normalized


def _external_reference_path(value: object) -> str:
    if type(value) is not str or not value:
        raise WorkspaceError("external reference path must be a non-empty string")
    try:
        canonical_json_bytes(value)
    except CanonicalJSONError as exc:
        raise WorkspaceError("external reference path must be valid UTF-8") from exc
    if "\x00" in value:
        raise WorkspaceError("external reference path must not contain NUL")

    posix = PurePosixPath(value)
    windows = PureWindowsPath(value)
    if not posix.is_absolute() and not windows.is_absolute():
        raise WorkspaceError("external reference path must be absolute")
    return value


@dataclass(frozen=True, slots=True)
class WorkspaceAsset:
    """One explicitly identified workspace asset entry."""

    asset_id: str
    asset_type: str
    path: str
    policy: str = "copy"
    content_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset_id", _identifier(self.asset_id, label="asset_id"))
        object.__setattr__(
            self,
            "asset_type",
            _identifier(self.asset_type, label="asset_type"),
        )
        policy = _asset_policy(self.policy)
        object.__setattr__(self, "policy", policy)
        if policy == "copy":
            checked_path = _workspace_owned_path(self.path)
        else:
            checked_path = _external_reference_path(self.path)
        object.__setattr__(self, "path", checked_path)
        digest = _content_sha256(self.content_sha256)
        if policy == "reference" and digest is None:
            raise WorkspaceError("reference assets require content_sha256")
        object.__setattr__(self, "content_sha256", digest)


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

        locations = tuple((asset.policy, asset.path) for asset in assets)
        if len(set(locations)) != len(locations):
            raise WorkspaceError("workspace asset paths must be unique within each policy")

        object.__setattr__(self, "assets", assets)
        try:
            digest = canonical_json_sha256(_manifest_to_plain_dict(self))
        except CanonicalJSONError as exc:
            raise WorkspaceError(
                "workspace manifest must contain only strict canonical JSON state"
            ) from exc
        object.__setattr__(self, "manifest_sha256", digest)


_MANIFEST_FIELDS = frozenset({"schema_version", "assets"})
_ASSET_REQUIRED_FIELDS = frozenset({"asset_id", "asset_type", "path"})
_ASSET_OPTIONAL_FIELDS = frozenset({"policy", "content_sha256"})


def _required_fields(
    value: Mapping[object, object],
    *,
    required: frozenset[str],
    optional: frozenset[str] = frozenset(),
    label: str,
) -> None:
    if not all(type(key) is str for key in value):
        raise WorkspaceError(f"{label} field names must be strings")
    fields = set(value)
    missing = sorted(required - fields)
    unknown = sorted(fields - required - optional)
    if missing or unknown:
        raise WorkspaceError(
            f"invalid {label} fields; missing={missing!r}, unknown={unknown!r}"
        )


def _asset_to_plain_dict(asset: WorkspaceAsset) -> dict[str, Any]:
    result: dict[str, Any] = {
        "asset_id": asset.asset_id,
        "asset_type": asset.asset_type,
        "path": asset.path,
    }
    if asset.policy != "copy" or asset.content_sha256 is not None:
        result["policy"] = asset.policy
    if asset.content_sha256 is not None:
        result["content_sha256"] = asset.content_sha256
    return result


def _manifest_to_plain_dict(manifest: WorkspaceManifest) -> dict[str, Any]:
    return {
        "schema_version": manifest.schema_version,
        "assets": [_asset_to_plain_dict(asset) for asset in manifest.assets],
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
            required=_ASSET_REQUIRED_FIELDS,
            optional=_ASSET_OPTIONAL_FIELDS,
            label=f"workspace asset {index}",
        )
        parsed_assets.append(
            WorkspaceAsset(
                asset_id=asset["asset_id"],
                asset_type=asset["asset_type"],
                path=asset["path"],
                policy=asset.get("policy", "copy"),
                content_sha256=asset.get("content_sha256"),
            )
        )

    return WorkspaceManifest(
        schema_version=value["schema_version"],
        assets=parsed_assets,
    )
