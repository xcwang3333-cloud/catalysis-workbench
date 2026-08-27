from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from catalysis_workbench._canonical_json import (
    CanonicalJSONError,
    canonical_json_bytes,
    canonical_json_sha256,
    loads_strict_json,
)


def test_mapping_insertion_order_is_canonical() -> None:
    assert canonical_json_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    assert canonical_json_bytes({"a": 1, "b": 2}) == b'{"a":1,"b":2}'


def test_nested_mapping_keys_are_canonicalized() -> None:
    left = {"outer": {"z": 1, "a": 2}, "tail": True}
    right = {"tail": True, "outer": {"a": 2, "z": 1}}
    assert canonical_json_bytes(left) == canonical_json_bytes(right)


def test_list_order_is_literal() -> None:
    assert canonical_json_bytes({"values": [1, 2]}) != canonical_json_bytes(
        {"values": [2, 1]}
    )


def test_unicode_is_deterministic_utf8() -> None:
    assert canonical_json_bytes({"label": "催化"}) == '{"label":"催化"}'.encode()


def test_sha256_is_deterministic() -> None:
    assert canonical_json_sha256({"b": 2, "a": 1}) == (
        "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777"
    )


@dataclass
class _ExampleDataclass:
    value: int


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        (1, 2),
        {1, 2},
        frozenset({1, 2}),
        b"bytes",
        Path("recipe.json"),
        np.int64(1),
        np.float64(1.5),
        np.str_("numpy string"),
        np.array([1, 2]),
        {1: "non-string key"},
        _ExampleDataclass(1),
        object(),
    ],
)
def test_unsupported_python_values_are_rejected(value: object) -> None:
    with pytest.raises(CanonicalJSONError):
        canonical_json_bytes(value)


@pytest.mark.parametrize(
    "text",
    [
        '{"key":1,"key":2}',
        '{"outer":{"key":1,"key":2}}',
    ],
)
def test_duplicate_json_keys_are_rejected(text: str) -> None:
    with pytest.raises(CanonicalJSONError, match="duplicate object key"):
        loads_strict_json(text)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_nonstandard_json_constants_are_rejected(constant: str) -> None:
    with pytest.raises(CanonicalJSONError, match="non-standard JSON constant"):
        loads_strict_json(f'{{"value":{constant}}}')


def test_float_overflow_from_json_is_rejected() -> None:
    with pytest.raises(CanonicalJSONError, match="non-finite float"):
        loads_strict_json('{"value":1e999}')


def test_valid_strict_json_loads_as_plain_values() -> None:
    assert loads_strict_json('{"items":[null,true,1,1.5,"x"]}') == {
        "items": [None, True, 1, 1.5, "x"]
    }


def test_invalid_json_has_controlled_error() -> None:
    with pytest.raises(CanonicalJSONError, match="invalid JSON document"):
        loads_strict_json("{")


def test_cyclic_list_is_rejected_with_controlled_error() -> None:
    value: list[object] = []
    value.append(value)
    with pytest.raises(CanonicalJSONError, match="cyclic JSON container"):
        canonical_json_bytes(value)


def test_cyclic_mapping_is_rejected_with_controlled_error() -> None:
    value: dict[str, object] = {}
    value["self"] = value
    with pytest.raises(CanonicalJSONError, match="cyclic JSON container"):
        canonical_json_bytes(value)


def test_indirect_container_cycle_is_rejected() -> None:
    first: dict[str, object] = {}
    second = {"first": first}
    first["second"] = second
    with pytest.raises(CanonicalJSONError, match="cyclic JSON container"):
        canonical_json_bytes(first)


def test_acyclic_shared_reference_is_serialized_by_value() -> None:
    shared = [1, 2]
    value = {"left": shared, "right": shared}
    assert canonical_json_bytes(value) == (
        b'{"left":[1,2],"right":[1,2]}'
    )


@pytest.mark.parametrize(
    "value",
    [
        "\ud800",
        "\udfff",
        {"\ud800": "value"},
        {"outer": [{"bad": "\udfff"}]},
    ],
)
def test_lone_surrogates_are_rejected(value: object) -> None:
    with pytest.raises(CanonicalJSONError, match="valid UTF-8"):
        canonical_json_bytes(value)


@pytest.mark.parametrize(
    "text",
    [
        '"\\ud800"',
        '"\\udfff"',
        '{"\\ud800":"value"}',
    ],
)
def test_strict_loader_rejects_lone_surrogates(text: str) -> None:
    with pytest.raises(CanonicalJSONError, match="valid UTF-8"):
        loads_strict_json(text)


def test_valid_non_bmp_unicode_round_trips() -> None:
    value = {"emoji": "😀", "label": "催化"}
    encoded = canonical_json_bytes(value)
    assert encoded == '{"emoji":"😀","label":"催化"}'.encode()
    assert loads_strict_json(encoded) == value


def test_valid_escaped_surrogate_pair_decodes_to_unicode_scalar() -> None:
    value = loads_strict_json('"\\ud83d\\ude00"')
    assert value == "😀"
    assert canonical_json_bytes(value) == '"😀"'.encode()


@pytest.mark.parametrize(
    "text",
    [
        "null",
        "true",
        "1",
        "1.0",
        '"catalysis"',
        '["催化",{"emoji":"😀"}]',
        '{"nested":{"values":[1,2,3]}}',
    ],
)
def test_successful_strict_load_is_immediately_canonicalizable(text: str) -> None:
    canonical_json_bytes(loads_strict_json(text))


def test_numeric_identity_remains_literal() -> None:
    assert canonical_json_bytes(0.0) == b"0.0"
    assert canonical_json_bytes(-0.0) == b"-0.0"
    assert canonical_json_bytes(1) == b"1"
    assert canonical_json_bytes(1.0) == b"1.0"
