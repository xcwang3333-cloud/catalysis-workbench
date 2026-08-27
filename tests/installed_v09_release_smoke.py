"""Installed-wheel smoke for the cumulative v0.9 public release surface."""

from __future__ import annotations

import importlib.metadata
import string
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import catalysis_workbench
import catalysis_workbench.workflow as workflow

EXPECTED_VERSION = "0.9.0.dev0"
EXPECTED_WORKFLOW_ALL = {
    "RecipeStep",
    "WorkflowRecipe",
    "WorkflowRecipeError",
    "dump_recipe",
    "load_recipe",
    "recipe_from_dict",
    "recipe_to_dict",
}
SOURCE_TREE = Path(__file__).resolve().parents[1] / "src"


def _step(
    step_id: str,
    operation_id: str,
    output_binding: str,
    *,
    parameters: dict[str, object] | None = None,
) -> workflow.RecipeStep:
    return workflow.RecipeStep(
        step_id=step_id,
        operation_id=operation_id,
        inputs={"series": "source"},
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

    first = _step(
        "crop",
        "catalysis.processing.crop.v1",
        "cropped",
        parameters={"upper": 0.8, "lower": 0.2},
    )
    recipe = workflow.WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(first,),
        outputs={"result": "cropped"},
    )
    assert len(recipe.recipe_sha256) == 64
    assert all(character in string.hexdigits.lower() for character in recipe.recipe_sha256)
    restored = workflow.recipe_from_dict(workflow.recipe_to_dict(recipe))
    assert restored.recipe_sha256 == recipe.recipe_sha256

    reordered = _step(
        "crop",
        "catalysis.processing.crop.v1",
        "cropped",
        parameters={"lower": 0.2, "upper": 0.8},
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

    for optional_name in ("pymatgen", "pyvista", "vtk"):
        assert optional_name not in sys.modules
    print("installed v0.9 release smoke passed")


if __name__ == "__main__":
    main()
