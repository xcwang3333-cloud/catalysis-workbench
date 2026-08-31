from __future__ import annotations

from dataclasses import FrozenInstanceError
from types import MappingProxyType

import numpy as np
import pytest

from catalysis_workbench.core import Series
from catalysis_workbench.processing import ProcessingError
from catalysis_workbench.workflow import batch as batch_module
from catalysis_workbench.workflow.batch import (
    BatchItem,
    BatchItemRecord,
    BatchRunRecord,
    run_batch,
)
from catalysis_workbench.workflow.recipe import RecipeStep, WorkflowRecipe


def _recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="crop",
                operation_id="catalysis.processing.crop.v1",
                inputs={"series": "source"},
                outputs={"series": "result"},
                parameters={"x_min": 0.0, "x_max": 3.0},
            ),
        ),
        outputs={"result": "result"},
    )


def _series(*, shift: float = 0.0) -> Series:
    return Series(
        x=np.array([0.0, 1.0, 2.0, 3.0]) + shift,
        y=np.array([1.0, 2.0, 4.0, 8.0]),
        label="source",
        key="source",
    )


def _item(key: str, identity: str, *, shift: float = 0.0) -> BatchItem:
    return BatchItem(
        key=key,
        inputs={"source": _series(shift=shift)},
        input_identities={"source": identity},
    )


def test_batch_item_is_frozen_and_detached_from_input_mappings() -> None:
    inputs = {"source": _series()}
    identities = {"source": "source-v1"}
    item = BatchItem(
        key="item-1",
        inputs=inputs,
        input_identities=identities,
    )
    inputs["extra"] = _series()
    identities["source"] = "changed"

    assert isinstance(item.inputs, MappingProxyType)
    assert isinstance(item.input_identities, MappingProxyType)
    assert tuple(item.inputs) == ("source",)
    assert item.input_identities == {"source": "source-v1"}
    with pytest.raises(FrozenInstanceError):
        item.key = "changed"  # type: ignore[misc]
    with pytest.raises(TypeError):
        item.inputs["source"] = _series()  # type: ignore[index]


@pytest.mark.parametrize(
    ("inputs", "identities"),
    [
        ({"source": _series()}, {}),
        ({}, {"source": "source-v1"}),
        ({"source": _series()}, {"other": "source-v1"}),
    ],
)
def test_batch_item_requires_identity_for_every_named_input(
    inputs: dict[str, object],
    identities: dict[str, str],
) -> None:
    with pytest.raises(ValueError, match="same names"):
        BatchItem(
            key="item-1",
            inputs=inputs,
            input_identities=identities,
        )


@pytest.mark.parametrize("key", ["", " item", "item ", chr(0xD800)])
def test_batch_item_key_must_be_stable_utf8(key: str) -> None:
    with pytest.raises(ValueError):
        _item(key, "source-v1")


def test_run_batch_preserves_literal_caller_order() -> None:
    recipe = _recipe()
    result = run_batch(
        recipe,
        (
            _item("second", "source-2"),
            _item("first", "source-1"),
        ),
    )

    assert isinstance(result, BatchRunRecord)
    assert tuple(item.key for item in result.items) == ("second", "first")
    assert all(item.status == "success" for item in result.items)
    assert all(
        isinstance(item.workflow_run, batch_module.WorkflowRun)
        for item in result.items
    )


def test_run_batch_uses_same_recipe_for_every_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe = _recipe()
    original = batch_module.execute_recipe
    recipe_ids: list[int] = []

    def record_call(
        passed_recipe: WorkflowRecipe,
        inputs: object,
        *,
        input_identities: object,
    ) -> batch_module.WorkflowRun:
        recipe_ids.append(id(passed_recipe))
        return original(
            passed_recipe,
            inputs,  # type: ignore[arg-type]
            input_identities=input_identities,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(batch_module, "execute_recipe", record_call)
    run_batch(
        recipe,
        (
            _item("one", "source-1"),
            _item("two", "source-2"),
        ),
    )
    assert recipe_ids == [id(recipe), id(recipe)]


def test_duplicate_item_keys_fail_before_any_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fail_if_called(*args: object, **kwargs: object) -> object:
        calls.append("called")
        raise AssertionError("execute_recipe must not be called")

    monkeypatch.setattr(batch_module, "execute_recipe", fail_if_called)
    with pytest.raises(ValueError, match="keys must be unique"):
        run_batch(
            _recipe(),
            (
                _item("duplicate", "source-1"),
                _item("duplicate", "source-2"),
            ),
        )
    assert calls == []


def test_invalid_error_policy_fails_before_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fail_if_called(*args: object, **kwargs: object) -> object:
        calls.append("called")
        raise AssertionError("execute_recipe must not be called")

    monkeypatch.setattr(batch_module, "execute_recipe", fail_if_called)
    with pytest.raises(ValueError, match="error_policy"):
        run_batch(
            _recipe(),
            (_item("one", "source-1"),),
            error_policy="retry",
        )
    assert calls == []


def test_raise_policy_propagates_first_failure_and_stops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = batch_module.execute_recipe
    calls: list[str] = []

    def record_call(
        recipe: WorkflowRecipe,
        inputs: object,
        *,
        input_identities: object,
    ) -> batch_module.WorkflowRun:
        identities = input_identities  # type: ignore[assignment]
        calls.append(identities["source"])
        return original(
            recipe,
            inputs,  # type: ignore[arg-type]
            input_identities=identities,  # type: ignore[arg-type]
        )

    monkeypatch.setattr(batch_module, "execute_recipe", record_call)
    with pytest.raises(ProcessingError, match="selected no points"):
        run_batch(
            _recipe(),
            (
                _item("good", "good-v1"),
                _item("bad", "bad-v1", shift=10.0),
                _item("later", "later-v1"),
            ),
            error_policy="raise",
        )
    assert calls == ["good-v1", "bad-v1"]


def test_record_policy_retains_failure_code_and_continues() -> None:
    result = run_batch(
        _recipe(),
        (
            _item("good", "good-v1"),
            _item("bad", "bad-v1", shift=10.0),
            _item("later", "later-v1"),
        ),
        error_policy="record",
    )

    assert tuple(item.status for item in result.items) == (
        "success",
        "failure",
        "success",
    )
    failed = result.items[1]
    assert failed.workflow_run is None
    assert failed.failure_code is not None
    assert failed.failure_code.endswith(".ProcessingError")
    assert "selected no points" not in failed.failure_code


def test_batch_records_are_deterministic_for_same_order_and_identities() -> None:
    recipe = _recipe()
    first = run_batch(
        recipe,
        (
            _item("one", "source-1"),
            _item("two", "source-2"),
        ),
        error_policy="record",
    )
    second = run_batch(
        recipe,
        (
            _item("one", "source-1"),
            _item("two", "source-2"),
        ),
        error_policy="record",
    )

    assert tuple(item.record_sha256 for item in first.items) == tuple(
        item.record_sha256 for item in second.items
    )
    assert first.record_sha256 == second.record_sha256


def test_batch_record_identity_is_order_sensitive() -> None:
    recipe = _recipe()
    first = run_batch(
        recipe,
        (
            _item("one", "source-1"),
            _item("two", "source-2"),
        ),
    )
    second = run_batch(
        recipe,
        (
            _item("two", "source-2"),
            _item("one", "source-1"),
        ),
    )
    assert first.record_sha256 != second.record_sha256


def test_batch_item_record_identity_changes_with_input_identity() -> None:
    recipe = _recipe()
    first = run_batch(recipe, (_item("one", "source-A"),))
    second = run_batch(recipe, (_item("one", "source-B"),))

    assert first.items[0].record_sha256 != second.items[0].record_sha256
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
        "catalysis_workbench_version": "1.1.0"
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
