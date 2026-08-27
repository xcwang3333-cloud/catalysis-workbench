from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import pytest

from catalysis_workbench.workflow import registry as workflow_registry


EXPECTED_OPERATION_IDS = (
    "catalysis.processing.crop.v1",
    "catalysis.processing.offset.v1",
    "catalysis.processing.normalize.v1",
)


def test_registry_contains_only_first_execution_slice_in_literal_order() -> None:
    operations = workflow_registry.list_recipe_operations()
    assert tuple(item.operation_id for item in operations) == EXPECTED_OPERATION_IDS


def test_registry_descriptors_are_frozen_and_defaults_are_read_only() -> None:
    crop = workflow_registry.get_operation_descriptor(
        "catalysis.processing.crop.v1"
    )
    with pytest.raises(FrozenInstanceError):
        crop.operation_id = "changed"  # type: ignore[misc]
    assert isinstance(crop.parameter_defaults, MappingProxyType)
    with pytest.raises(TypeError):
        crop.parameter_defaults["x_min"] = 1.0  # type: ignore[index]


def test_registry_contracts_are_explicit() -> None:
    crop, offset, normalize = workflow_registry.list_recipe_operations()
    assert crop.input_ports == ("series",)
    assert crop.output_ports == ("series",)
    assert crop.required_parameters == ()
    assert crop.parameter_defaults == {
        "x_min": None,
        "x_max": None,
        "inclusive": True,
    }
    assert offset.required_parameters == ("value",)
    assert offset.parameter_defaults == {}
    assert normalize.parameter_defaults == {
        "method": "max",
        "target": 1.0,
        "area_mode": "absolute",
    }


def test_parameter_names_preserve_contract_order() -> None:
    descriptor = workflow_registry.OperationDescriptor(
        operation_id="example.operation.v1",
        contract_version=1,
        input_ports=("source",),
        output_ports=("result",),
        required_parameters=("required",),
        parameter_defaults={"first": 1, "second": 2},
    )
    assert descriptor.parameter_names == ("required", "first", "second")


def test_unknown_operation_fails_closed() -> None:
    with pytest.raises(KeyError, match="unknown workflow operation_id"):
        workflow_registry.get_operation_descriptor(
            "catalysis.processing.savgol.v1"
        )
    with pytest.raises(KeyError):
        workflow_registry.get_operation_descriptor(
            " catalysis.processing.crop.v1"
        )


def test_non_string_operation_id_is_rejected() -> None:
    with pytest.raises(TypeError):
        workflow_registry.get_operation_descriptor(1)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "arguments",
    [
        {"operation_id": "example.operation.v2", "contract_version": 1},
        {"operation_id": " example.operation.v1"},
        {"input_ports": ("source", "source")},
        {"output_ports": ("",)},
        {"required_parameters": ("value", "value")},
        {"parameter_defaults": {"value": float("nan")}},
    ],
)
def test_invalid_descriptors_are_rejected(arguments: dict[str, object]) -> None:
    values: dict[str, object] = {
        "operation_id": "example.operation.v1",
        "contract_version": 1,
        "input_ports": ("source",),
        "output_ports": ("result",),
        "required_parameters": (),
        "parameter_defaults": {},
    }
    values.update(arguments)
    with pytest.raises(ValueError):
        workflow_registry.OperationDescriptor(**values)  # type: ignore[arg-type]


def test_required_parameter_cannot_also_have_default() -> None:
    with pytest.raises(ValueError, match="cannot also define defaults"):
        workflow_registry.OperationDescriptor(
            operation_id="example.operation.v1",
            contract_version=1,
            input_ports=("source",),
            output_ports=("result",),
            required_parameters=("value",),
            parameter_defaults={"value": 1},
        )


def test_registry_source_has_no_dynamic_discovery() -> None:
    path = (
        Path(__file__).parents[1]
        / "src"
        / "catalysis_workbench"
        / "workflow"
        / "registry.py"
    )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.add(node.func.id)
    assert "importlib" not in imported_roots
    assert {"eval", "exec"}.isdisjoint(called_names)
