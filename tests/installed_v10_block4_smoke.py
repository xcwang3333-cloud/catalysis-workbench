from __future__ import annotations

import tempfile
from pathlib import Path

import catalysis_workbench
from catalysis_workbench.visualization import FigureSpec
from catalysis_workbench.workflow import RecipeStep, WorkflowRecipe
from catalysis_workbench.workspace import create_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.composition import (
    bind_recipe_assets,
    create_workspace_composition,
    figure_spec_sha256,
    load_figure_spec_asset,
    load_recipe_asset,
    move_recipe_step,
    open_workspace_composition,
    record_figure_export,
    save_figure_spec_asset,
    save_recipe_asset,
)

EXPECTED_VERSION = "1.0.0.dev0"

assert catalysis_workbench.__version__ == EXPECTED_VERSION

recipe = WorkflowRecipe(
    schema_version=1,
    inputs=("raw",),
    steps=(
        RecipeStep(
            step_id="step-a",
            operation_id="example.unregistered",
            inputs={"value": "raw"},
            outputs={"value": "result"},
            parameters={"explicit": True},
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

    result_source = base / "result.dat"
    result_source.write_bytes(b"result")
    import_asset(
        root,
        result_source,
        asset_id="result",
        asset_type="data",
        policy="copy",
        destination="data/result.dat",
    )

    save_recipe_asset(
        root,
        recipe,
        asset_id="recipe",
        destination="recipes/main.json",
    )
    assert load_recipe_asset(root, "recipe").recipe_sha256 == recipe.recipe_sha256

    create_workspace_composition(root)
    composed = bind_recipe_assets(
        root,
        composition_id="analysis",
        recipe_asset_id="recipe",
        input_assets={"raw": "raw"},
        output_assets={"result": "result"},
    )
    assert composed.recipes[0].recipe_sha256 == recipe.recipe_sha256

    spec = FigureSpec(title="Installed Block 4")
    save_figure_spec_asset(
        root,
        spec,
        asset_id="figure-spec",
        destination="figures/spec.json",
    )
    loaded_spec = load_figure_spec_asset(root, "figure-spec")
    assert figure_spec_sha256(loaded_spec) == figure_spec_sha256(spec)

    export_source = base / "figure.svg"
    export_source.write_bytes(b"<svg/>")
    import_asset(
        root,
        export_source,
        asset_id="figure-export",
        asset_type="exported_figure",
        policy="copy",
        destination="exports/figure.svg",
    )
    composed = record_figure_export(
        root,
        composition_id="figure",
        figure_spec_asset_id="figure-spec",
        exported_figure_asset_id="figure-export",
    )
    assert composed.figures[0].figure_spec_sha256 == figure_spec_sha256(spec)
    assert open_workspace_composition(root).composition_sha256 == composed.composition_sha256

independent = WorkflowRecipe(
    schema_version=1,
    inputs=("a", "b"),
    steps=(
        RecipeStep(
            step_id="left",
            operation_id="example.left",
            inputs={"value": "a"},
            outputs={"value": "left_out"},
            parameters={},
        ),
        RecipeStep(
            step_id="right",
            operation_id="example.right",
            inputs={"value": "b"},
            outputs={"value": "right_out"},
            parameters={},
        ),
    ),
    outputs={"left": "left_out", "right": "right_out"},
)
moved = move_recipe_step(independent, "right", 0)
assert tuple(step.step_id for step in moved.steps) == ("right", "left")

print("installed v1.0 Block 4 workspace composition smoke: ok")
