from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import numpy as np
import pytest

from catalysis_workbench.core import Series
from catalysis_workbench.processing import ProcessingError, crop, normalize, offset
from catalysis_workbench.workflow.execution import (
    StepExecutionRecord,
    WorkflowRun,
    execute_recipe,
)
from catalysis_workbench.workflow.recipe import RecipeStep, WorkflowRecipe


def _series() -> Series:
    return Series(
        x=np.array([0.0, 1.0, 2.0, 3.0]),
        y=np.array([1.0, 2.0, 4.0, 8.0]),
        label="source",
        key="source",
    )


def _chain_recipe(*, offset_value: float = -1.0) -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="crop",
                operation_id="catalysis.processing.crop.v1",
                inputs={"series": "source"},
                outputs={"series": "cropped"},
                parameters={"x_min": 1.0, "x_max": 3.0},
            ),
            RecipeStep(
                step_id="offset",
                operation_id="catalysis.processing.offset.v1",
                inputs={"series": "cropped"},
                outputs={"series": "shifted"},
                parameters={"value": offset_value},
            ),
            RecipeStep(
                step_id="normalize",
                operation_id="catalysis.processing.normalize.v1",
                inputs={"series": "shifted"},
                outputs={"series": "normalized"},
                parameters={},
            ),
        ),
        outputs={"result": "normalized"},
    )


def test_execute_recipe_matches_direct_processing_chain() -> None:
    source = _series()
    recipe = _chain_recipe()

    run = execute_recipe(
        recipe,
        {"source": source},
        input_identities={"source": "source-fixture-v1"},
    )

    expected = normalize(
        offset(crop(source, x_min=1.0, x_max=3.0), -1.0),
        method="max",
        target=1.0,
        area_mode="absolute",
    )
    assert run.outputs["result"].equals(expected)
    assert source.equals(_series())
    assert tuple(record.step_id for record in run.steps) == (
        "crop",
        "offset",
        "normalize",
    )
    assert run.steps[0].effective_parameters == {
        "x_min": 1.0,
        "x_max": 3.0,
        "inclusive": True,
    }
    assert run.steps[2].effective_parameters == {
        "method": "max",
        "target": 1.0,
        "area_mode": "absolute",
    }


def test_execution_records_are_frozen_and_deeply_read_only() -> None:
    run = execute_recipe(
        _chain_recipe(),
        {"source": _series()},
        input_identities={"source": "source-fixture-v1"},
    )
    assert isinstance(run, WorkflowRun)
    assert isinstance(run.outputs, MappingProxyType)
    assert isinstance(run.output_identities, MappingProxyType)
    assert isinstance(run.steps[0], StepExecutionRecord)
    assert isinstance(run.steps[0].effective_parameters, MappingProxyType)
    with pytest.raises(FrozenInstanceError):
        run.content_sha256 = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        run.output_identities["result"] = "changed"  # type: ignore[index]


def test_execution_identity_is_deterministic() -> None:
    recipe = _chain_recipe()
    source = _series()
    first = execute_recipe(
        recipe,
        {"source": source},
        input_identities={"source": "source-fixture-v1"},
    )
    second = execute_recipe(
        recipe,
        {"source": source.copy()},
        input_identities={"source": "source-fixture-v1"},
    )
    assert first.recipe_sha256 == second.recipe_sha256
    assert first.output_identities == second.output_identities
    assert first.content_sha256 == second.content_sha256
    assert first.record_sha256 == second.record_sha256


def test_execution_identity_changes_with_explicit_input_identity() -> None:
    recipe = _chain_recipe()
    first = execute_recipe(
        recipe,
        {"source": _series()},
        input_identities={"source": "source-A"},
    )
    second = execute_recipe(
        recipe,
        {"source": _series()},
        input_identities={"source": "source-B"},
    )
    assert first.output_identities != second.output_identities
    assert first.content_sha256 != second.content_sha256
    assert first.record_sha256 != second.record_sha256


def test_execution_identity_changes_with_recipe_semantics() -> None:
    first = execute_recipe(
        _chain_recipe(offset_value=-1.0),
        {"source": _series()},
        input_identities={"source": "source-fixture-v1"},
    )
    second = execute_recipe(
        _chain_recipe(offset_value=-2.0),
        {"source": _series()},
        input_identities={"source": "source-fixture-v1"},
    )
    assert first.recipe_sha256 != second.recipe_sha256
    assert first.content_sha256 != second.content_sha256


def test_full_preflight_rejects_invalid_later_parameters_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from catalysis_workbench.workflow import _adapters

    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="crop",
                operation_id="catalysis.processing.crop.v1",
                inputs={"series": "source"},
                outputs={"series": "cropped"},
                parameters={"x_min": 0.0},
            ),
            RecipeStep(
                step_id="normalize",
                operation_id="catalysis.processing.normalize.v1",
                inputs={"series": "cropped"},
                outputs={"series": "normalized"},
                parameters={"method": "invented"},
            ),
        ),
        outputs={"result": "normalized"},
    )
    calls: list[str] = []

    def fail_if_called(*args: object, **kwargs: object) -> dict[str, Series]:
        calls.append("called")
        return {"series": _series()}

    monkeypatch.setattr(_adapters, "execute_operation", fail_if_called)
    with pytest.raises(ValueError, match="normalize method"):
        execute_recipe(
            recipe,
            {"source": _series()},
            input_identities={"source": "source-fixture-v1"},
        )
    assert calls == []


def test_full_preflight_rejects_later_external_type_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from catalysis_workbench.workflow import _adapters

    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=("left", "right"),
        steps=(
            RecipeStep(
                step_id="left",
                operation_id="catalysis.processing.crop.v1",
                inputs={"series": "left"},
                outputs={"series": "left_result"},
                parameters={"x_min": 0.0},
            ),
            RecipeStep(
                step_id="right",
                operation_id="catalysis.processing.crop.v1",
                inputs={"series": "right"},
                outputs={"series": "right_result"},
                parameters={"x_min": 0.0},
            ),
        ),
        outputs={"left": "left_result", "right": "right_result"},
    )
    calls: list[str] = []

    def fail_if_called(*args: object, **kwargs: object) -> dict[str, Series]:
        calls.append("called")
        return {"series": _series()}

    monkeypatch.setattr(_adapters, "execute_operation", fail_if_called)
    with pytest.raises(TypeError, match="requires a Series"):
        execute_recipe(
            recipe,
            {"left": _series(), "right": object()},
            input_identities={"left": "left-v1", "right": "right-v1"},
        )
    assert calls == []


def test_literal_recipe_order_is_authoritative(monkeypatch: pytest.MonkeyPatch) -> None:
    from catalysis_workbench.workflow import _adapters

    recipe = _chain_recipe()
    calls: list[str] = []
    original = _adapters.execute_operation

    def record_call(
        operation_id: str,
        inputs: object,
        parameters: object,
    ) -> dict[str, Series]:
        calls.append(operation_id)
        return original(operation_id, inputs, parameters)  # type: ignore[arg-type]

    monkeypatch.setattr(_adapters, "execute_operation", record_call)
    execute_recipe(
        recipe,
        {"source": _series()},
        input_identities={"source": "source-fixture-v1"},
    )
    assert calls == [
        "catalysis.processing.crop.v1",
        "catalysis.processing.offset.v1",
        "catalysis.processing.normalize.v1",
    ]


def test_unknown_operation_fails_closed_before_execution() -> None:
    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="unknown",
                operation_id="example.dynamic.v1",
                inputs={"series": "source"},
                outputs={"series": "result"},
                parameters={},
            ),
        ),
        outputs={"result": "result"},
    )
    with pytest.raises(KeyError, match="unknown workflow operation_id"):
        execute_recipe(
            recipe,
            {"source": _series()},
            input_identities={"source": "source-fixture-v1"},
        )


def test_step_ports_must_match_reviewed_contract() -> None:
    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="crop",
                operation_id="catalysis.processing.crop.v1",
                inputs={"data": "source"},
                outputs={"series": "result"},
                parameters={"x_min": 0.0},
            ),
        ),
        outputs={"result": "result"},
    )
    with pytest.raises(ValueError, match="ports do not match"):
        execute_recipe(
            recipe,
            {"source": _series()},
            input_identities={"source": "source-fixture-v1"},
        )


@pytest.mark.parametrize(
    ("inputs", "identities", "match"),
    [
        ({}, {"source": "source-v1"}, "inputs must match"),
        ({"source": _series(), "extra": _series()}, {"source": "source-v1"}, "inputs must match"),
        ({"source": _series()}, {}, "input_identities must match"),
        (
            {"source": _series()},
            {"source": "source-v1", "extra": "extra-v1"},
            "input_identities must match",
        ),
    ],
)
def test_external_bindings_must_match_recipe_exactly(
    inputs: dict[str, object],
    identities: dict[str, str],
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        execute_recipe(_chain_recipe(), inputs, input_identities=identities)


@pytest.mark.parametrize("identity", ["", " source", "source ", "\ud800"])
def test_input_identity_must_be_explicit_valid_utf8(identity: str) -> None:
    with pytest.raises(ValueError):
        execute_recipe(
            _chain_recipe(),
            {"source": _series()},
            input_identities={"source": identity},
        )


def test_existing_processing_failure_propagates_unchanged() -> None:
    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="crop",
                operation_id="catalysis.processing.crop.v1",
                inputs={"series": "source"},
                outputs={"series": "result"},
                parameters={"x_min": 100.0},
            ),
        ),
        outputs={"result": "result"},
    )
    with pytest.raises(ProcessingError, match="selected no points"):
        execute_recipe(
            recipe,
            {"source": _series()},
            input_identities={"source": "source-fixture-v1"},
        )


def test_run_records_only_deterministic_environment_evidence() -> None:
    run = execute_recipe(
        _chain_recipe(),
        {"source": _series()},
        input_identities={"source": "source-fixture-v1"},
    )
    assert run.environment_evidence == {"catalysis_workbench_version": "1.0.0"}
    assert all(
        forbidden not in run.environment_evidence
        for forbidden in ("timestamp", "duration", "host", "user", "pid", "path")
    )
