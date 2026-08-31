from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

import catalysis_workbench
from catalysis_workbench.application import (
    ApplicationSession,
    MoveRecipeStepCommand,
)
from catalysis_workbench.core import Series
from catalysis_workbench.visualization import FigureSpec
from catalysis_workbench.workflow import RecipeStep, WorkflowRecipe, check_digest
from catalysis_workbench.workspace import create_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.composition import (
    save_figure_spec_asset,
    save_recipe_asset,
)

EXPECTED_VERSION = "1.1.0"

assert catalysis_workbench.__version__ == EXPECTED_VERSION
assert "PySide6" not in sys.modules
assert "PyQt6" not in sys.modules

recipe = WorkflowRecipe(
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

with tempfile.TemporaryDirectory() as directory:
    base = Path(directory)
    root = base / "workspace"
    create_workspace(root)

    raw_source = base / "raw.dat"
    raw_source.write_bytes(b"raw")
    import_asset(
        root,
        raw_source,
        asset_id="raw",
        asset_type="data",
        policy="copy",
        destination="data/raw.dat",
    )
    save_recipe_asset(
        root,
        recipe,
        asset_id="recipe",
        destination="recipes/main.json",
    )
    save_figure_spec_asset(
        root,
        FigureSpec(title="Block 5"),
        asset_id="figure-spec",
        destination="figures/spec.json",
    )

    session = ApplicationSession()
    session.open_workspace(root)
    session.select_assets(("raw",))
    session.select_recipe("recipe")

    source = Series(
        x=np.array([0.0, 1.0, 2.0]),
        y=np.array([1.0, 2.0, 3.0]),
        key="source",
        label="source",
    )
    run = session.execute_recipe(
        {"source": source},
        input_identities={"source": "installed-source-v1"},
    )
    assert np.allclose(run.outputs["result"].y, np.array([2.0, 3.0, 4.0]))
    assert session.state.last_workflow_run is run

    report = session.run_qa(
        (check_digest(run.record_sha256, run.record_sha256, subject="run"),)
    )
    assert report.status.value == "pass"
    assert session.state.last_qa_report is report

    session.select_figure_spec("figure-spec")
    edited = session.update_figure_spec(title="Edited Block 5")
    assert edited.figure_spec.title == "Edited Block 5"
    assert edited.figure_spec_dirty is True

independent = WorkflowRecipe(
    schema_version=1,
    inputs=("a", "b"),
    steps=(
        RecipeStep(
            step_id="left",
            operation_id="not.discovered.left",
            inputs={"value": "a"},
            outputs={"value": "left_out"},
            parameters={},
        ),
        RecipeStep(
            step_id="right",
            operation_id="not.discovered.right",
            inputs={"value": "b"},
            outputs={"value": "right_out"},
            parameters={},
        ),
    ),
    outputs={"left": "left_out", "right": "right_out"},
)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory) / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        independent,
        asset_id="recipe",
        destination="recipes/independent.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_recipe("recipe")
    state = session.edit_recipe(MoveRecipeStepCommand("right", 0))
    assert tuple(step.step_id for step in state.recipe.steps) == ("right", "left")
    assert state.recipe_dirty is True

print("installed v1.0 Block 5 application/session smoke: ok")