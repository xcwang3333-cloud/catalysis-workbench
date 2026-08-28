from __future__ import annotations

import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import numpy as np
import pytest

from catalysis_workbench.application import (
    ApplicationError,
    ApplicationSession,
    ApplicationState,
    InsertRecipeStepCommand,
    MoveRecipeStepCommand,
    RemoveRecipeStepCommand,
    ReplaceRecipeStepCommand,
)
from catalysis_workbench.core import Series
from catalysis_workbench.workflow import (
    RecipeStep,
    WorkflowRecipe,
    WorkflowRecipeError,
    check_digest,
)
from catalysis_workbench.workspace import create_workspace, open_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.composition import (
    save_figure_spec_asset,
    save_recipe_asset,
)


def _registered_recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="offset",
                operation_id="catalysis.processing.offset.v1",
                inputs={"series": "source"},
                outputs={"series": "shifted"},
                parameters={"value": 1.0},
            ),
        ),
        outputs={"result": "shifted"},
    )


def _independent_recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("left_in", "right_in"),
        steps=(
            RecipeStep(
                step_id="left",
                operation_id="not.discovered.left",
                inputs={"value": "left_in"},
                outputs={"value": "left_out"},
                parameters={},
            ),
            RecipeStep(
                step_id="right",
                operation_id="not.discovered.right",
                inputs={"value": "right_in"},
                outputs={"value": "right_out"},
                parameters={},
            ),
        ),
        outputs={"left": "left_out", "right": "right_out"},
    )


def _dependent_recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("source",),
        steps=(
            RecipeStep(
                step_id="producer",
                operation_id="not.discovered.producer",
                inputs={"value": "source"},
                outputs={"value": "middle"},
                parameters={},
            ),
            RecipeStep(
                step_id="consumer",
                operation_id="not.discovered.consumer",
                inputs={"value": "middle"},
                outputs={"value": "result"},
                parameters={},
            ),
        ),
        outputs={"result": "result"},
    )


def _series() -> Series:
    return Series(
        x=np.array([0.0, 1.0, 2.0]),
        y=np.array([1.0, 2.0, 3.0]),
        key="source",
        label="source",
    )


def _copy_asset(
    root: Path,
    tmp_path: Path,
    *,
    asset_id: str,
    content: bytes = b"payload",
) -> None:
    source = tmp_path / f"{asset_id}.bin"
    source.write_bytes(content)
    import_asset(
        root,
        source,
        asset_id=asset_id,
        asset_type="data",
        policy="copy",
        destination=f"data/{asset_id}.bin",
    )


def test_application_import_is_headless_and_does_not_load_desktop_toolkits() -> None:
    code = """
import sys
import catalysis_workbench.application
assert "matplotlib.pyplot" not in sys.modules
assert "PySide6" not in sys.modules
assert "PyQt6" not in sys.modules
"""
    subprocess.run([sys.executable, "-c", code], check=True)


def test_session_open_close_uses_immutable_revisioned_state(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    manifest = create_workspace(root)
    session = ApplicationSession()

    opened = session.open_workspace(root)

    assert opened.workspace_root == root.resolve()
    assert opened.workspace_manifest_sha256 == manifest.manifest_sha256
    assert opened.revision == 1
    with pytest.raises(FrozenInstanceError):
        opened.revision = 99  # type: ignore[misc]

    closed = session.close_workspace()
    assert closed.workspace_root is None
    assert closed.workspace_manifest_sha256 is None
    assert closed.selected_asset_ids == ()
    assert closed.revision == 2


def test_invalid_asset_selection_does_not_mutate_application_state(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    session = ApplicationSession()
    session.open_workspace(root)
    before = session.state

    with pytest.raises(ApplicationError, match="unknown workspace asset IDs"):
        session.select_assets(("missing",))

    assert session.state is before


def test_external_workspace_change_requires_explicit_refresh(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    session = ApplicationSession()
    session.open_workspace(root)
    before = session.state
    _copy_asset(root, tmp_path, asset_id="raw")

    with pytest.raises(ApplicationError, match="changed outside"):
        session.select_assets(("raw",))

    assert session.state is before
    refreshed = session.refresh_workspace()
    assert refreshed.workspace_manifest_sha256 == open_workspace(root).manifest_sha256
    selected = session.select_assets(("raw",))
    assert selected.selected_asset_ids == ("raw",)


def test_refresh_refuses_to_discard_dirty_recipe_without_explicit_flag(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _independent_recipe(),
        asset_id="recipe",
        destination="recipes/main.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_recipe("recipe")
    session.edit_recipe(MoveRecipeStepCommand("right", 0))
    dirty = session.state
    _copy_asset(root, tmp_path, asset_id="new")

    with pytest.raises(ApplicationError, match="discard dirty"):
        session.refresh_workspace()

    assert session.state is dirty
    refreshed = session.refresh_workspace(discard_edits=True)
    assert refreshed.recipe_dirty is False
    assert tuple(step.step_id for step in refreshed.recipe.steps) == ("left", "right")


def test_recipe_editing_is_literal_closed_set_and_transaction_safe(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _independent_recipe(),
        asset_id="recipe",
        destination="recipes/main.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_recipe("recipe")

    moved = session.edit_recipe(MoveRecipeStepCommand("right", 0))
    assert moved.recipe_dirty is True
    assert tuple(step.step_id for step in moved.recipe.steps) == ("right", "left")

    replacement = RecipeStep(
        step_id="right",
        operation_id="still.not.discovered",
        inputs={"value": "right_in"},
        outputs={"value": "right_out"},
        parameters={"explicit": True},
    )
    replaced = session.edit_recipe(
        ReplaceRecipeStepCommand("right", replacement)
    )
    assert replaced.recipe.steps[0].operation_id == "still.not.discovered"

    inserted = RecipeStep(
        step_id="third",
        operation_id="also.not.discovered",
        inputs={"value": "left_in"},
        outputs={"value": "third_out"},
        parameters={},
    )
    inserted_state = session.edit_recipe(InsertRecipeStepCommand(1, inserted))
    assert tuple(step.step_id for step in inserted_state.recipe.steps) == (
        "right",
        "third",
        "left",
    )

    removed = session.edit_recipe(RemoveRecipeStepCommand("third"))
    assert tuple(step.step_id for step in removed.recipe.steps) == ("right", "left")

    before = session.state
    with pytest.raises(TypeError, match="supported recipe edit command"):
        session.edit_recipe(object())  # type: ignore[arg-type]
    assert session.state is before


def test_invalid_dependent_recipe_move_does_not_mutate_state(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _dependent_recipe(),
        asset_id="recipe",
        destination="recipes/main.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_recipe("recipe")
    before = session.state

    with pytest.raises(WorkflowRecipeError, match="unavailable bindings"):
        session.edit_recipe(MoveRecipeStepCommand("consumer", 0))

    assert session.state is before


def test_recipe_save_updates_manifest_identity_only_after_success(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _independent_recipe(),
        asset_id="recipe",
        destination="recipes/main.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_recipe("recipe")
    session.edit_recipe(MoveRecipeStepCommand("right", 0))
    old_digest = session.state.workspace_manifest_sha256

    saved = session.save_recipe(
        asset_id="recipe-edited",
        destination="recipes/edited.json",
    )

    assert saved.selected_recipe_asset_id == "recipe-edited"
    assert saved.recipe_dirty is False
    assert saved.workspace_manifest_sha256 != old_digest
    assert saved.workspace_manifest_sha256 == open_workspace(root).manifest_sha256


def test_execution_delegates_to_reviewed_workflow_and_commits_only_success(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    recipe = _registered_recipe()
    save_recipe_asset(
        root,
        recipe,
        asset_id="recipe",
        destination="recipes/main.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_recipe("recipe")
    before = session.state

    with pytest.raises(ValueError, match="inputs"):
        session.execute_recipe(
            {"wrong": _series()},
            input_identities={"wrong": "source-v1"},
        )

    assert session.state is before
    run = session.execute_recipe(
        {"source": _series()},
        input_identities={"source": "source-v1"},
    )
    assert run.recipe_sha256 == recipe.recipe_sha256
    assert session.state.last_workflow_run is run
    assert np.allclose(run.outputs["result"].y, np.array([2.0, 3.0, 4.0]))


def test_qa_aggregates_only_explicit_findings_and_is_transaction_safe(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    session = ApplicationSession()
    session.open_workspace(root)
    finding = check_digest("a" * 64, "a" * 64)

    report = session.run_qa((finding,))
    assert report.findings == (finding,)
    assert session.state.last_qa_report is report
    before = session.state

    with pytest.raises(ValueError, match="at least one finding"):
        session.run_qa(())

    assert session.state is before


def test_figure_selection_edit_and_save_use_reviewed_figure_spec_api(
    tmp_path: Path,
) -> None:
    from catalysis_workbench.visualization import FigureSpec

    root = tmp_path / "workspace"
    create_workspace(root)
    save_figure_spec_asset(
        root,
        FigureSpec(title="Initial"),
        asset_id="spec",
        destination="figures/spec.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    selected = session.select_figure_spec("spec")
    assert selected.figure_spec.title == "Initial"
    assert selected.figure_spec_dirty is False

    edited = session.update_figure_spec(title="Edited", show_legend=True)
    assert edited.figure_spec.title == "Edited"
    assert edited.figure_spec.show_legend is True
    assert edited.figure_spec_dirty is True

    styled = session.update_figure_style(line_width=2.5)
    assert styled.figure_spec.style.line_width == pytest.approx(2.5)

    saved = session.save_figure_spec(
        asset_id="spec-edited",
        destination="figures/edited.json",
    )
    assert saved.selected_figure_spec_asset_id == "spec-edited"
    assert saved.figure_spec_dirty is False
    assert saved.workspace_manifest_sha256 == open_workspace(root).manifest_sha256


def test_invalid_figure_edit_does_not_mutate_state(tmp_path: Path) -> None:
    from catalysis_workbench.visualization import FigureSpec, VisualizationError

    root = tmp_path / "workspace"
    create_workspace(root)
    save_figure_spec_asset(
        root,
        FigureSpec(),
        asset_id="spec",
        destination="figures/spec.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_figure_spec("spec")
    before = session.state

    with pytest.raises((TypeError, ValueError, VisualizationError)):
        session.update_figure_style(line_width=-1.0)

    assert session.state is before


def test_public_application_state_rejects_closed_workspace_payload() -> None:
    with pytest.raises(ApplicationError, match="closed application state"):
        ApplicationState(selected_asset_ids=("asset",))
