"""Strict canonical JSON primitives used by reproducible artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


class CanonicalJSONError(ValueError):
    """Raised when a value is not strict canonical JSON."""


def _validated_string(value: str, *, location: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalJSONError(f"string is not valid UTF-8 at {location}") from exc
    return value


def _validated_plain_value(
    value: object,
    *,
    location: str = "$",
    active_containers: set[int] | None = None,
) -> Any:
    if value is None or type(value) is bool:
        return value
    if type(value) is str:
        return _validated_string(value, location=location)
    if type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise CanonicalJSONError(f"non-finite float at {location}")
        return value
    if isinstance(value, (list, Mapping)):
        active = set() if active_containers is None else active_containers
        container_id = id(value)
        if container_id in active:
            raise CanonicalJSONError(f"cyclic JSON container at {location}")
        active.add(container_id)
        try:
            if isinstance(value, list):
                return [
                    _validated_plain_value(
                        item,
                        location=f"{location}[{index}]",
                        active_containers=active,
                    )
                    for index, item in enumerate(value)
                ]
            result: dict[str, Any] = {}
            for key, item in value.items():
                if type(key) is not str:
                    raise CanonicalJSONError(f"non-string object key at {location}")
                checked_key = _validated_string(key, location=f"{location} object key")
                result[checked_key] = _validated_plain_value(
                    item,
                    location=f"{location}.{checked_key}",
                    active_containers=active,
                )
            return result
        finally:
            active.remove(container_id)
    raise CanonicalJSONError(
        f"unsupported value type at {location}: {type(value).__name__}"
    )


def canonical_json_bytes(value: object) -> bytes:
    """Return strict canonical JSON encoded as UTF-8."""

    try:
        plain_value = _validated_plain_value(value)
    except RecursionError as exc:
        raise CanonicalJSONError("JSON nesting exceeds the supported depth") from exc
    try:
        text = json.dumps(
            plain_value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError, RecursionError) as exc:
        raise CanonicalJSONError("value cannot be encoded as canonical JSON") from exc
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CanonicalJSONError("value cannot be encoded as canonical UTF-8 JSON") from exc


def canonical_json_sha256(value: object) -> str:
    """Return the lowercase SHA-256 digest of strict canonical JSON."""

    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CanonicalJSONError(f"duplicate object key: {key!r}")
        result[key] = value
    return result


def _reject_nonstandard_constant(constant: str) -> None:
    raise CanonicalJSONError(f"non-standard JSON constant: {constant}")


def loads_strict_json(text: str | bytes | bytearray) -> Any:
    """Load JSON while rejecting duplicate keys and non-standard values."""

    try:
        value = json.loads(
            text,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
    except CanonicalJSONError:
        raise
    except (TypeError, ValueError, RecursionError) as exc:
        raise CanonicalJSONError("invalid JSON document") from exc
    try:
        return _validated_plain_value(value)
    except RecursionError as exc:
        raise CanonicalJSONError("JSON nesting exceeds the supported depth") from exc
