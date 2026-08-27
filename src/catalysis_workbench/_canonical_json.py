"""Strict canonical JSON primitives used by reproducible artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping
from typing import Any


class CanonicalJSONError(ValueError):
    """Raised when a value is not strict canonical JSON."""


def _validated_plain_value(value: object, *, location: str = "$") -> Any:
    if value is None or type(value) in {bool, str}:
        return value
    if type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise CanonicalJSONError(f"non-finite float at {location}")
        return value
    if isinstance(value, list):
        return [
            _validated_plain_value(item, location=f"{location}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise CanonicalJSONError(f"non-string object key at {location}")
            result[key] = _validated_plain_value(item, location=f"{location}.{key}")
        return result
    raise CanonicalJSONError(
        f"unsupported value type at {location}: {type(value).__name__}"
    )


def canonical_json_bytes(value: object) -> bytes:
    """Return strict canonical JSON encoded as UTF-8."""

    plain_value = _validated_plain_value(value)
    try:
        text = json.dumps(
            plain_value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
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
    except (TypeError, ValueError) as exc:
        raise CanonicalJSONError("invalid JSON document") from exc
    return _validated_plain_value(value)
