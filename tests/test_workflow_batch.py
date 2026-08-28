from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import numpy as np
import pytest

from catalysis_workbench.core import Series
from catalysis_workbench.workflow import (
    BatchItem,
    BatchItemRecord,
    RecipeStep,
    WorkflowRecipe,
    register_operation,
    run_batch,
)


def _series(*, key: str = "source") -> Series:
    return Series(
        x=np.array([0.0, 1.0, 2.0]),
        y=np.array([1.0, 2.0, 3.0]),
        key=key,
        label=key,
    )


def _recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="offset",
                operation_id="catalysis.processing.offset.v1",
                inputs={"series": "source"},
                outputs={"series": "result"},
                parameters={"value": 1.0},
            ),
        ),
        outputs={"result": "result"},
    )


def _item(item_id: str, source_identity: str) -> BatchItem:
    return BatchItem(
        item_id=item_id,
        inputs={"source": _series(key=item_id)},
        input_identities={"source": source_identity},
    )


def test_batch_preserves_literal_item_order() -> None:
    batch = run_batch(
        _recipe(),
        (
            _item("second", "source-2"),
            _item("first", "source-1"),
        ),
    )
    assert tuple(item.item_id for item in batch.items) == ("second", "first")
    assert tuple(item.status for item in batch.items) == ("success", "success")


def test_batch_rejects_duplicate_item_ids() -> None:
    with pytest.raises(ValueError, match="batch item ids must be unique"):
        run_batch(
            _recipe(),
            (
                _item("same", "source-1"),
                _item("same", "source-2"),
            ),
        )


def test_batch_records_successful_outputs() -> None:
    batch = run_batch(_recipe(), (_item("one", "source-1"),))
    item = batch.items[0]
    assert item.status == "success"
    assert item.workflow_run is not None
    assert item.failure is None
    assert np.array_equal(item.workflow_run.outputs["result"].y, np.array([2.0, 3.0, 4.0]))


def test_batch_record_identity_changes_with_item_identity() -> None:
    first = run_batch(_recipe(), (_item("one", "source-1"),))
    second = run_batch(_recipe(), (_item("one", "source-2"),))
    assert first.record_sha256 != second.record_sha256


def test_batch_record_identity_changes_with_literal_item_order() -> None:
    recipe = _recipe()
    first = run_batch(
        recipe,
        (_item("one", "source-1"), _item("two", "source-2")),
    )
    second = run_batch(
        recipe,
        (_item("two", "source-2"), _item("one", "source-1")),
    )
    assert first.record_sha256 != second.record_sha256


def test_batch_failure_policy_raise_re_raises() -> None:
    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="unknown",
                operation_id="test.batch.unknown.raise",
                inputs={"series": "source"},
                outputs={"series": "result"},
                parameters={},
            ),
        ),
        outputs={"result": "result"},
    )
    with pytest.raises(ValueError, match="unknown workflow operation"):
        run_batch(recipe, (_item("one", "source-1"),), error_policy="raise")


def test_batch_failure_policy_record_is_deterministic() -> None:
    def explode(*, series: Series, label: str) -> dict[str, object]:
        del series
        raise RuntimeError(f"boom {label}")

    operation_id = "test.batch.explode.record"
    try:
        register_operation(operation_id, explode)
    except ValueError:
        pass

    recipe = WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="explode",
                operation_id=operation_id,
                inputs={"series": "source"},
                outputs={"series": "result"},
                parameters={"label": "batch"},
            ),
        ),
        outputs={"result": "result"},
    )

    first = run_batch(recipe, (_item("one", "source-1"),), error_policy="record")
    second = run_batch(recipe, (_item("one", "source-1"),), error_policy="record")
    item = first.items[0]
    assert item.status == "failed"
    assert item.workflow_run is None
    assert item.failure is not None
    assert item.failure.error_type == "RuntimeError"
    assert item.failure.message == "boom batch"
    assert "traceback" not in item.failure.to_dict()
    assert first.record_sha256 == second.record_sha256


def test_batch_failure_record_identity_changes_with_failure_message() -> None:
    def explode(*, series: Series, label: str) -> dict[str, object]:
        del series
        raise RuntimeError(f"boom {label}")

    operation_id = "test.batch.explode.identity"
    try:
        register_operation(operation_id, explode)
    except ValueError:
        pass

    def _failing_recipe(label: str) -> WorkflowRecipe:
        return WorkflowRecipe(
            schema_version=1,
            inputs=("source",),
            steps=(
                RecipeStep(
                    step_id="explode",
                    operation_id=operation_id,
                    inputs={"series": "source"},
                    outputs={"series": "result"},
                    parameters={"label": label},
                ),
            ),
            outputs={"result": "result"},
        )

    first = run_batch(
        _failing_recipe("first"),
        (_item("one", "source-1"),),
        error_policy="record",
    )
    second = run_batch(
        _failing_recipe("second"),
        (_item("one", "source-1"),),
        error_policy="record",
    )
    assert first.record_sha256 != second.record_sha256


def test_error_policy_is_part_of_batch_record_identity() -> None:
    recipe = _recipe()
    raised = run_batch(
        recipe,
        (_item("one", "source-1"),),
        error_policy="raise",
    )
    recorded = run_batch(
        recipe,
        (_item("one", "source-1"),),
        error_policy="record",
    )
    assert raised.items[0].record_sha256 == recorded.items[0].record_sha256
    assert raised.record_sha256 != recorded.record_sha256


def test_batch_run_record_is_frozen_and_deeply_read_only() -> None:
    result = run_batch(_recipe(), (_item("one", "source-1"),))
    item = result.items[0]

    assert isinstance(item, BatchItemRecord)
    assert isinstance(item.input_identities, MappingProxyType)
    assert isinstance(result.environment_evidence, MappingProxyType)
    assert result.environment_evidence == {
        "catalysis_workbench_version": "1.0.0"
    }
    with pytest.raises(FrozenInstanceError):
        result.error_policy = "record"  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.environment_evidence["host"] = "example"  # type: ignore[index]


def test_empty_batch_is_deterministic_and_valid() -> None:
    first = run_batch(_recipe(), ())
    second = run_batch(_recipe(), ())
    assert first.items == ()
    assert first.record_sha256 == second.record_sha256