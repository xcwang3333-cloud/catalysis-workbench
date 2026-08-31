"""Installed-wheel smoke for the cumulative v0.9 public API surface."""

from __future__ import annotations

import importlib.metadata
import string
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

import catalysis_workbench
import catalysis_workbench.workflow as workflow
from catalysis_workbench.core import Axis, Dataset, Series

EXPECTED_VERSION = "1.1.0"
EXPECTED_WORKFLOW_ALL = {
    "BatchItem",
    "BatchItemRecord",
    "BatchRunRecord",
    "OperationDescriptor",
    "QAFinding",
    "QAReport",
    "QAStatus",
    "RecipeStep",
    "StepExecutionRecord",
    "WorkflowRecipe",
    "WorkflowRecipeError",
    "WorkflowRun",
    "check_digest",
    "check_finite_values",
    "check_stable_keys",
    "check_units",
    "dump_recipe",
    "execute_recipe",
    "get_operation_descriptor",
    "list_recipe_operations",
    "load_recipe",
    "recipe_from_dict",
    "recipe_to_dict",
    "run_batch",
    "run_qa",
}
EXPECTED_OPERATION_IDS = (
    "catalysis.processing.crop.v1",
    "catalysis.processing.offset.v1",
    "catalysis.processing.normalize.v1",
)
SOURCE_TREE = Path(__file__).resolve().parents[1] / "src"


def _step(
    step_id: str,
    operation_id: str,
    output_binding: str,
    *,
    input_binding: str = "source",
    parameters: dict[str, object] | None = None,
) -> workflow.RecipeStep:
    return workflow.RecipeStep(
        step_id=step_id,
        operation_id=operation_id,
        inputs={"series": input_binding},
        outputs={"series": output_binding},
        parameters={} if parameters is None else parameters,
    )


def main() -> None:
    assert importlib.metadata.version("catalysis-workbench") == EXPECTED_VERSION
    assert catalysis_workbench.__version__ == EXPECTED_VERSION
    package_path = Path(catalysis_workbench.__file__).resolve()
    workflow_path = Path(workflow.__file__).resolve()
    assert not package_path.is_relative_to(SOURCE_TREE)
    assert not workflow_path.is_relative_to(SOURCE_TREE)
    assert "site-packages" in {part.lower() for part in workflow_path.parts}
    assert set(workflow.__all__) == EXPECTED_WORKFLOW_ALL
    assert len(workflow.__all__) == len(EXPECTED_WORKFLOW_ALL)
    assert all(hasattr(workflow, name) for name in workflow.__all__)
    assert "catalysis_workbench.processing" not in sys.modules

    first = _step(
        "crop",
        "catalysis.processing.crop.v1",
        "cropped",
        parameters={"x_min": 0.2, "x_max": 0.8},
    )
    recipe = workflow.WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(first,),
        outputs={"result": "cropped"},
    )
    assert len(recipe.recipe_sha256) == 64
    assert all(
        character in string.hexdigits.lower()
        for character in recipe.recipe_sha256
    )
    restored = workflow.recipe_from_dict(workflow.recipe_to_dict(recipe))
    assert restored.recipe_sha256 == recipe.recipe_sha256

    reordered = _step(
        "crop",
        "catalysis.processing.crop.v1",
        "cropped",
        parameters={"x_max": 0.8, "x_min": 0.2},
    )
    reordered_recipe = workflow.WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(reordered,),
        outputs={"result": "cropped"},
    )
    assert reordered_recipe.recipe_sha256 == recipe.recipe_sha256

    left = _step("left", "example.left.v1", "left_result")
    right = _step("right", "example.right.v1", "right_result")
    output_bindings = {"left": "left_result", "right": "right_result"}
    left_first = workflow.WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(left, right),
        outputs=output_bindings,
    )
    right_first = workflow.WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(right, left),
        outputs=output_bindings,
    )
    assert left_first.recipe_sha256 != right_first.recipe_sha256

    with TemporaryDirectory() as directory:
        path = Path(directory) / "recipe.json"
        workflow.dump_recipe(recipe, path)
        assert workflow.load_recipe(path).recipe_sha256 == recipe.recipe_sha256
        try:
            workflow.dump_recipe(recipe, path)
        except FileExistsError:
            pass
        else:
            raise AssertionError("dump_recipe silently overwrote an existing file")

    operations = workflow.list_recipe_operations()
    assert tuple(item.operation_id for item in operations) == EXPECTED_OPERATION_IDS
    assert all(isinstance(item, workflow.OperationDescriptor) for item in operations)
    try:
        workflow.get_operation_descriptor("catalysis.processing.savgol.v1")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown workflow operation was accepted")

    source = Series(
        x=np.array([0.0, 1.0, 2.0, 3.0]),
        y=np.array([1.0, 2.0, 4.0, 8.0]),
        label="source",
        key="source",
    )
    executable = workflow.WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            _step(
                "crop",
                "catalysis.processing.crop.v1",
                "cropped",
                parameters={"x_min": 1.0, "x_max": 3.0},
            ),
            _step(
                "offset",
                "catalysis.processing.offset.v1",
                "shifted",
                input_binding="cropped",
                parameters={"value": -1.0},
            ),
            _step(
                "normalize",
                "catalysis.processing.normalize.v1",
                "normalized",
                input_binding="shifted",
            ),
        ),
        outputs={"result": "normalized"},
    )
    run = workflow.execute_recipe(
        executable,
        {"source": source},
        input_identities={"source": "installed-wheel-source-v1"},
    )
    assert isinstance(run, workflow.WorkflowRun)
    assert len(run.steps) == 3
    assert all(
        isinstance(record, workflow.StepExecutionRecord)
        for record in run.steps
    )
    assert run.recipe_sha256 == executable.recipe_sha256
    assert len(run.content_sha256) == 64
    assert len(run.record_sha256) == 64
    np.testing.assert_allclose(
        run.outputs["result"].x,
        np.array([1.0, 2.0, 3.0]),
    )
    np.testing.assert_allclose(
        run.outputs["result"].y,
        np.array([1.0 / 7.0, 3.0 / 7.0, 1.0]),
    )
    assert run.steps[2].effective_parameters == {
        "method": "max",
        "target": 1.0,
        "area_mode": "absolute",
    }
    assert run.environment_evidence == {
        "catalysis_workbench_version": EXPECTED_VERSION
    }

    failing_source = Series(
        x=np.array([10.0, 11.0, 12.0, 13.0]),
        y=np.array([1.0, 2.0, 4.0, 8.0]),
        label="source",
        key="source",
    )
    batch = workflow.run_batch(
        executable,
        (
            workflow.BatchItem(
                key="good",
                inputs={"source": source},
                input_identities={"source": "installed-batch-good-v1"},
            ),
            workflow.BatchItem(
                key="bad",
                inputs={"source": failing_source},
                input_identities={"source": "installed-batch-bad-v1"},
            ),
        ),
        error_policy="record",
    )
    assert isinstance(batch, workflow.BatchRunRecord)
    assert tuple(item.key for item in batch.items) == ("good", "bad")
    assert tuple(item.status for item in batch.items) == ("success", "failure")
    assert isinstance(batch.items[0], workflow.BatchItemRecord)
    assert isinstance(batch.items[0].workflow_run, workflow.WorkflowRun)
    assert batch.items[1].workflow_run is None
    assert batch.items[1].failure_code is not None
    assert batch.items[1].failure_code.endswith(".ProcessingError")
    assert len(batch.items[0].record_sha256) == 64
    assert len(batch.items[1].record_sha256) == 64
    assert len(batch.record_sha256) == 64
    assert batch.environment_evidence == {
        "catalysis_workbench_version": EXPECTED_VERSION
    }

    qa_source = Series(
        x=np.array([0.0, 0.5, 1.0]),
        y=np.array([1.0, np.nan, 3.0]),
        label="qa-source",
        key="qa-source",
        x_axis=Axis("potential", unit="V"),
        y_axis=Axis("response"),
    )
    digest_finding = workflow.check_digest(
        run.record_sha256,
        run.record_sha256,
        subject="workflow-run",
    )
    finite_x = workflow.check_finite_values(
        qa_source,
        components=("x",),
        subject="qa-source",
    )
    finite_y = workflow.check_finite_values(
        qa_source,
        components=("y",),
        subject="qa-source",
    )
    unit_x = workflow.check_units(
        qa_source,
        expected={"x": "V"},
        subject="qa-source",
    )
    missing_unit = workflow.check_units(
        qa_source,
        expected={"y": None},
        subject="qa-source",
    )
    stable_keys = workflow.check_stable_keys(
        Dataset((qa_source,)),
        subject="qa-source",
    )
    qa_report = workflow.run_qa(
        (digest_finding, finite_x, unit_x, missing_unit, stable_keys)
    )
    assert isinstance(digest_finding, workflow.QAFinding)
    assert isinstance(qa_report, workflow.QAReport)
    assert qa_report.status is workflow.QAStatus.PASS
    assert finite_y.status is workflow.QAStatus.FAIL
    assert len(digest_finding.finding_sha256) == 64
    assert len(qa_report.report_sha256) == 64
    assert workflow.run_qa((finite_y,)).status is workflow.QAStatus.FAIL

    for optional_name in ("pymatgen", "pyvista", "vtk"):
        assert optional_name not in sys.modules

    cycle: list[object] = []
    cycle.append(cycle)
    try:
        _step(
            "cycle",
            "example.cycle.v1",
            "cycle_result",
            parameters={"x": cycle},
        )
    except workflow.WorkflowRecipeError:
        pass
    else:
        raise AssertionError("cyclic recipe parameters were accepted")

    invalid_identifier = chr(0xD800)
    try:
        _step(invalid_identifier, "example.invalid.v1", "invalid_result")
    except workflow.WorkflowRecipeError:
        pass
    else:
        raise AssertionError("lone-surrogate recipe identifier was accepted")
    print("installed v0.9 smoke passed")


if __name__ == "__main__":
    main()
