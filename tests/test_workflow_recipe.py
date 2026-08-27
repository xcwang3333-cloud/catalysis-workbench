from __future__ import annotations

import ast
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import MappingProxyType

import numpy as np
import pytest

from catalysis_workbench._canonical_json import (
    canonical_json_bytes,
    loads_strict_json,
)
from catalysis_workbench.workflow import (
    RecipeStep,
    WorkflowRecipe,
    WorkflowRecipeError,
    dump_recipe,
    load_recipe,
    recipe_from_dict,
    recipe_to_dict,
)


def _step(
    *,
    step_id: str = "crop",
    operation_id: str = "catalysis.processing.crop.v1",
    input_binding: str = "source",
    output_binding: str = "cropped",
    parameters: object | None = None,
) -> RecipeStep:
    return RecipeStep(
        step_id=step_id,
        operation_id=operation_id,
        inputs={"series": input_binding},
        outputs={"series": output_binding},
        parameters={} if parameters is None else parameters,
    )


def _recipe(
    *,
    inputs: tuple[str, ...] = ("source",),
    steps: tuple[RecipeStep, ...] | None = None,
    outputs: object | None = None,
) -> WorkflowRecipe:
    selected_steps = (_step(),) if steps is None else steps
    selected_outputs = {"result": "cropped"} if outputs is None else outputs
    return WorkflowRecipe(
        schema_version=1,
        inputs=inputs,
        steps=selected_steps,
        outputs=selected_outputs,
    )


def test_valid_single_step_recipe() -> None:
    recipe = _recipe()
    assert recipe.inputs == ("source",)
    assert recipe.steps[0].step_id == "crop"
    assert recipe.outputs == {"result": "cropped"}


def test_valid_multiple_step_recipe() -> None:
    recipe = _recipe(
        steps=(
            _step(),
            _step(
                step_id="normalize",
                operation_id="catalysis.processing.normalize.v1",
                input_binding="cropped",
                output_binding="normalized",
            ),
        ),
        outputs={"result": "normalized"},
    )
    assert tuple(step.step_id for step in recipe.steps) == ("crop", "normalize")


def test_recipe_models_are_frozen() -> None:
    step = _step()
    recipe = _recipe(steps=(step,))
    with pytest.raises(FrozenInstanceError):
        step.step_id = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        recipe.inputs = ("changed",)  # type: ignore[misc]


def test_step_state_is_deeply_detached_and_frozen() -> None:
    inputs = {"series": "source"}
    outputs = {"series": "cropped"}
    nested = {"limits": [0.2, {"upper": 0.8}]}
    step = RecipeStep(
        step_id="crop",
        operation_id="catalysis.processing.crop.v1",
        inputs=inputs,
        outputs=outputs,
        parameters=nested,
    )
    inputs["series"] = "changed"
    outputs["series"] = "changed"
    nested["limits"][0] = 9.0
    nested["limits"][1]["upper"] = 9.0
    assert step.inputs == {"series": "source"}
    assert step.outputs == {"series": "cropped"}
    assert isinstance(step.parameters, MappingProxyType)
    assert step.parameters["limits"][0] == 0.2
    assert isinstance(step.parameters["limits"], tuple)
    assert isinstance(step.parameters["limits"][1], MappingProxyType)


def test_recipe_state_is_detached_from_caller_sequences_and_mappings() -> None:
    inputs = ["source"]
    steps = [_step()]
    outputs = {"result": "cropped"}
    recipe = WorkflowRecipe(
        schema_version=1, inputs=inputs, steps=steps, outputs=outputs
    )
    inputs[0] = "changed"
    steps.clear()
    outputs["result"] = "changed"
    assert recipe.inputs == ("source",)
    assert len(recipe.steps) == 1
    assert recipe.outputs == {"result": "cropped"}


def test_recipe_to_dict_returns_detached_mutable_plain_values() -> None:
    recipe = _recipe(steps=(_step(parameters={"values": [1, {"x": 2}]}),))
    serialized = recipe_to_dict(recipe)
    serialized["steps"][0]["parameters"]["values"][1]["x"] = 99
    assert recipe.steps[0].parameters["values"][1]["x"] == 2


@pytest.mark.parametrize("step_id", ["", " crop", "crop "])
def test_invalid_step_id_is_rejected(step_id: str) -> None:
    with pytest.raises(WorkflowRecipeError):
        _step(step_id=step_id)


@pytest.mark.parametrize("operation_id", ["", " operation", "operation "])
def test_invalid_operation_id_is_rejected(operation_id: str) -> None:
    with pytest.raises(WorkflowRecipeError):
        _step(operation_id=operation_id)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("inputs", {"": "source"}),
        ("inputs", {"series": ""}),
        ("inputs", {" series": "source"}),
        ("outputs", {"series": " cropped"}),
    ],
)
def test_invalid_port_or_binding_name_is_rejected(field: str, value: object) -> None:
    arguments = {
        "step_id": "crop",
        "operation_id": "catalysis.processing.crop.v1",
        "inputs": {"series": "source"},
        "outputs": {"series": "cropped"},
        "parameters": {},
    }
    arguments[field] = value
    with pytest.raises(WorkflowRecipeError):
        RecipeStep(**arguments)


def test_duplicate_step_id_is_rejected() -> None:
    with pytest.raises(WorkflowRecipeError, match="duplicate step_id"):
        _recipe(
            steps=(
                _step(output_binding="first"),
                _step(input_binding="first", output_binding="second"),
            ),
            outputs={"result": "second"},
        )


def test_duplicate_workflow_input_is_rejected() -> None:
    with pytest.raises(WorkflowRecipeError, match="must be unique"):
        _recipe(inputs=("source", "source"))


def test_undeclared_input_binding_is_rejected() -> None:
    with pytest.raises(WorkflowRecipeError, match="unavailable bindings"):
        _recipe(steps=(_step(input_binding="missing"),))


def test_forward_reference_is_rejected() -> None:
    with pytest.raises(WorkflowRecipeError, match="unavailable bindings"):
        _recipe(
            steps=(
                _step(input_binding="later", output_binding="first"),
                _step(
                    step_id="later",
                    input_binding="source",
                    output_binding="later",
                ),
            )
        )


def test_output_collision_with_external_input_is_rejected() -> None:
    with pytest.raises(WorkflowRecipeError, match="overwrites existing bindings"):
        _recipe(steps=(_step(output_binding="source"),))


def test_output_collision_with_earlier_output_is_rejected() -> None:
    with pytest.raises(WorkflowRecipeError, match="overwrites existing bindings"):
        _recipe(
            steps=(
                _step(output_binding="shared"),
                _step(step_id="again", input_binding="shared", output_binding="shared"),
            )
        )


def test_duplicate_output_binding_within_step_is_rejected() -> None:
    step = RecipeStep(
        step_id="split",
        operation_id="example.split.v1",
        inputs={"source": "source"},
        outputs={"left": "shared", "right": "shared"},
        parameters={},
    )
    with pytest.raises(WorkflowRecipeError, match="more than once"):
        _recipe(steps=(step,), outputs={"result": "shared"})


def test_recipe_output_must_reference_available_binding() -> None:
    with pytest.raises(WorkflowRecipeError, match="unavailable bindings"):
        _recipe(outputs={"result": "missing"})


@pytest.mark.parametrize("schema_version", [True, 0, -1, 2, "1"])
def test_unsupported_schema_is_rejected(schema_version: object) -> None:
    with pytest.raises(WorkflowRecipeError, match="integer 1"):
        WorkflowRecipe(
            schema_version=schema_version,
            inputs=("source",),
            steps=(_step(),),
            outputs={"result": "cropped"},
        )


def test_empty_steps_are_rejected() -> None:
    with pytest.raises(WorkflowRecipeError, match="at least one step"):
        _recipe(steps=())


def test_empty_recipe_outputs_are_rejected() -> None:
    with pytest.raises(WorkflowRecipeError, match="at least one output"):
        _recipe(outputs={})


@pytest.mark.parametrize("field", ["metadata", 1])
def test_unknown_serialized_recipe_field_is_rejected(field: object) -> None:
    serialized = recipe_to_dict(_recipe())
    serialized[field] = "unexpected"
    with pytest.raises(WorkflowRecipeError):
        recipe_from_dict(serialized)


def test_missing_serialized_recipe_field_is_rejected() -> None:
    serialized = recipe_to_dict(_recipe())
    del serialized["outputs"]
    with pytest.raises(WorkflowRecipeError, match="missing"):
        recipe_from_dict(serialized)


def test_unknown_serialized_step_field_is_rejected() -> None:
    serialized = recipe_to_dict(_recipe())
    serialized["steps"][0]["callable"] = "forbidden"
    with pytest.raises(WorkflowRecipeError, match="unknown"):
        recipe_from_dict(serialized)


def test_missing_serialized_step_field_is_rejected() -> None:
    serialized = recipe_to_dict(_recipe())
    del serialized["steps"][0]["parameters"]
    with pytest.raises(WorkflowRecipeError, match="missing"):
        recipe_from_dict(serialized)


@pytest.mark.parametrize(
    "parameters",
    [
        (1, 2),
        {1, 2},
        np.array([1, 2]),
        np.int64(1),
        np.str_("numpy string"),
        {"value": float("nan")},
        {"value": float("inf")},
        {1: "value"},
        {"value": object()},
    ],
)
def test_non_strict_parameters_are_rejected(parameters: object) -> None:
    with pytest.raises(WorkflowRecipeError, match="strict JSON"):
        _step(parameters=parameters)


def test_recipe_round_trip_retains_digest() -> None:
    recipe = _recipe(
        steps=(_step(parameters={"bounds": [0.2, 0.8], "label": "催化"}),)
    )
    encoded = canonical_json_bytes(recipe_to_dict(recipe))
    restored = recipe_from_dict(loads_strict_json(encoded))
    assert recipe_to_dict(restored) == recipe_to_dict(recipe)
    assert restored.recipe_sha256 == recipe.recipe_sha256


def test_digest_is_independent_of_mapping_insertion_order() -> None:
    left_step = RecipeStep(
        step_id="crop",
        operation_id="catalysis.processing.crop.v1",
        inputs={"series": "source", "mask": "mask"},
        outputs={"series": "cropped"},
        parameters={"upper": 0.8, "lower": 0.2},
    )
    right_step = RecipeStep(
        step_id="crop",
        operation_id="catalysis.processing.crop.v1",
        inputs={"mask": "mask", "series": "source"},
        outputs={"series": "cropped"},
        parameters={"lower": 0.2, "upper": 0.8},
    )
    left = _recipe(inputs=("source", "mask"), steps=(left_step,))
    right = _recipe(inputs=("source", "mask"), steps=(right_step,))
    assert left.recipe_sha256 == right.recipe_sha256


def _independent_steps() -> tuple[RecipeStep, RecipeStep]:
    return (
        _step(step_id="left", output_binding="left_result"),
        _step(
            step_id="right",
            operation_id="catalysis.processing.offset.v1",
            output_binding="right_result",
        ),
    )


def test_digest_is_sensitive_to_step_order() -> None:
    left, right = _independent_steps()
    outputs = {"left": "left_result", "right": "right_result"}
    first = _recipe(steps=(left, right), outputs=outputs)
    second = _recipe(steps=(right, left), outputs=outputs)
    assert first.recipe_sha256 != second.recipe_sha256


def test_digest_is_sensitive_to_workflow_input_order() -> None:
    first = _recipe(inputs=("source", "mask"))
    second = _recipe(inputs=("mask", "source"))
    assert first.recipe_sha256 != second.recipe_sha256


@pytest.mark.parametrize(
    "changed_step",
    [
        _step(step_id="different"),
        _step(operation_id="catalysis.processing.offset.v1"),
        _step(output_binding="transformed"),
        _step(parameters={"lower": 0.3}),
    ],
)
def test_digest_is_sensitive_to_step_semantics(changed_step: RecipeStep) -> None:
    original = _recipe()
    output_binding = next(iter(changed_step.outputs.values()))
    changed = _recipe(steps=(changed_step,), outputs={"result": output_binding})
    assert original.recipe_sha256 != changed.recipe_sha256


def test_dump_and_load_use_canonical_json_with_one_newline(tmp_path: Path) -> None:
    recipe = _recipe(steps=(_step(parameters={"upper": 0.8, "lower": 0.2}),))
    path = tmp_path / "recipe.json"
    dump_recipe(recipe, path)
    assert path.read_bytes() == canonical_json_bytes(recipe_to_dict(recipe)) + b"\n"
    restored = load_recipe(path)
    assert restored.recipe_sha256 == recipe.recipe_sha256


def test_dump_refuses_overwrite_by_default(tmp_path: Path) -> None:
    path = tmp_path / "recipe.json"
    dump_recipe(_recipe(), path)
    with pytest.raises(FileExistsError):
        dump_recipe(_recipe(), path)


def test_dump_allows_explicit_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "recipe.json"
    dump_recipe(_recipe(), path)
    changed = _recipe(steps=(_step(parameters={"value": 0.1}),))
    dump_recipe(changed, path, overwrite=True)
    assert load_recipe(path).recipe_sha256 == changed.recipe_sha256


def test_load_rejects_duplicate_json_keys(tmp_path: Path) -> None:
    path = tmp_path / "recipe.json"
    path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
    with pytest.raises(WorkflowRecipeError, match="cannot load recipe"):
        load_recipe(path)


def test_file_path_does_not_affect_digest(tmp_path: Path) -> None:
    recipe = _recipe()
    first = tmp_path / "first.json"
    second = tmp_path / "nested" / "second.json"
    second.parent.mkdir()
    dump_recipe(recipe, first)
    dump_recipe(recipe, second)
    assert load_recipe(first).recipe_sha256 == load_recipe(second).recipe_sha256


def test_recipe_has_no_later_block_identity_fields() -> None:
    recipe = _recipe()
    assert not hasattr(recipe, "content_sha256")
    assert not hasattr(recipe, "record_sha256")


def test_block_one_source_has_no_execution_or_dynamic_discovery() -> None:
    source = Path(__file__).parents[1] / "src" / "catalysis_workbench" / "workflow"
    trees = [ast.parse(path.read_text(encoding="utf-8")) for path in source.glob("*.py")]
    imported_roots: set[str] = set()
    called_names: set[str] = set()
    for tree in trees:
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                called_names.add(node.func.id)
    assert "importlib" not in imported_roots
    assert {"eval", "exec"}.isdisjoint(called_names)


def test_workflow_import_does_not_eagerly_load_processing_or_optional_backends() -> None:
    code = """
import sys
import catalysis_workbench.workflow
for name in ('catalysis_workbench.processing', 'pymatgen', 'pyvista', 'vtk'):
    assert name not in sys.modules, name
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
