"""Explicit, source-controlled operation registry for reproducible recipes."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from catalysis_workbench._canonical_json import CanonicalJSONError, canonical_json_bytes


@dataclass(frozen=True, slots=True)
class OperationDescriptor:
    """Immutable execution contract for one reviewed workflow operation."""

    operation_id: str
    contract_version: int
    input_ports: tuple[str, ...]
    output_ports: tuple[str, ...]
    required_parameters: tuple[str, ...] = ()
    parameter_defaults: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        operation_id = self.operation_id
        if (
            not isinstance(operation_id, str)
            or not operation_id
            or operation_id.strip() != operation_id
        ):
            raise ValueError(
                "operation_id must be a non-empty string without surrounding whitespace"
            )
        if type(self.contract_version) is not int or self.contract_version < 1:
            raise ValueError("contract_version must be a positive integer")
        if not operation_id.endswith(f".v{self.contract_version}"):
            raise ValueError("operation_id version suffix must match contract_version")

        input_ports = _validate_names(self.input_ports, field_name="input_ports")
        output_ports = _validate_names(self.output_ports, field_name="output_ports")
        required_parameters = _validate_names(
            self.required_parameters,
            field_name="required_parameters",
        )
        defaults = dict(self.parameter_defaults)
        _validate_names(tuple(defaults), field_name="parameter_defaults")
        overlap = set(required_parameters).intersection(defaults)
        if overlap:
            joined = ", ".join(sorted(overlap))
            raise ValueError(
                f"required parameters cannot also define defaults: {joined}"
            )
        try:
            canonical_json_bytes(defaults)
        except CanonicalJSONError as exc:
            raise ValueError(
                "parameter_defaults must contain strict JSON values"
            ) from exc

        object.__setattr__(self, "input_ports", input_ports)
        object.__setattr__(self, "output_ports", output_ports)
        object.__setattr__(self, "required_parameters", required_parameters)
        object.__setattr__(
            self,
            "parameter_defaults",
            _freeze_json_value(defaults),
        )

    @property
    def parameter_names(self) -> tuple[str, ...]:
        """Return all accepted parameter names in deterministic contract order."""
        return (*self.required_parameters, *self.parameter_defaults.keys())


def _validate_names(
    values: tuple[str, ...],
    *,
    field_name: str,
) -> tuple[str, ...]:
    names = tuple(values)
    if any(
        not isinstance(name, str) or not name or name.strip() != name
        for name in names
    ):
        raise ValueError(
            f"{field_name} must contain non-empty strings without surrounding whitespace"
        )
    if len(names) != len(set(names)):
        raise ValueError(f"{field_name} must contain unique names")
    return names


def _freeze_json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze_json_value(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_freeze_json_value(item) for item in value)
    return value


_OPERATIONS = (
    OperationDescriptor(
        operation_id="catalysis.processing.crop.v1",
        contract_version=1,
        input_ports=("series",),
        output_ports=("series",),
        parameter_defaults={"x_min": None, "x_max": None, "inclusive": True},
    ),
    OperationDescriptor(
        operation_id="catalysis.processing.offset.v1",
        contract_version=1,
        input_ports=("series",),
        output_ports=("series",),
        required_parameters=("value",),
    ),
    OperationDescriptor(
        operation_id="catalysis.processing.normalize.v1",
        contract_version=1,
        input_ports=("series",),
        output_ports=("series",),
        parameter_defaults={
            "method": "max",
            "target": 1.0,
            "area_mode": "absolute",
        },
    ),
)

_OPERATION_BY_ID = MappingProxyType(
    {item.operation_id: item for item in _OPERATIONS}
)


def list_recipe_operations() -> tuple[OperationDescriptor, ...]:
    """Return reviewed recipe operations in source-controlled registry order."""
    return _OPERATIONS


def get_operation_descriptor(operation_id: str) -> OperationDescriptor:
    """Return the exact reviewed descriptor for an operation ID."""
    if not isinstance(operation_id, str):
        raise TypeError("operation_id must be a string")
    try:
        return _OPERATION_BY_ID[operation_id]
    except KeyError:
        raise KeyError(
            f"unknown workflow operation_id: {operation_id!r}"
        ) from None
