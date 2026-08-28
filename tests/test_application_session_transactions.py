from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import catalysis_workbench.application.session as session_module
from catalysis_workbench.application import ApplicationError, ApplicationSession
from catalysis_workbench.core import Series
from catalysis_workbench.workflow import RecipeStep, WorkflowRecipe
from catalysis_workbench.workspace import create_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.composition import save_recipe_asset


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


def _series() -> Series:
    return Series(
        x=np.array([0.0, 1.0]),
        y=np.array([1.0, 2.0]),
        key="source",
        label="source",
    )


def _add_asset(root: Path, source_dir: Path, asset_id: str) -> None:
    source = source_dir / f"{asset_id}.bin"
    source.write_bytes(asset_id.encode("utf-8"))
    import_asset(
        root,
        source,
        asset_id=asset_id,
        asset_type="data",
        policy="copy",
        destination=f"data/{asset_id}.bin",
    )


def test_execution_rejects_manifest_change_before_state_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _recipe(),
        asset_id="recipe",
        destination="recipes/main.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_recipe("recipe")
    before = session.state

    real_execute = session_module.execute_recipe

    def execute_then_mutate(*args, **kwargs):
        run = real_execute(*args, **kwargs)
        _add_asset(root, tmp_path, "concurrent")
        return run

    monkeypatch.setattr(session_module, "execute_recipe", execute_then_mutate)

    with pytest.raises(ApplicationError, match="changed during the application command"):
        session.execute_recipe(
            {"source": _series()},
            input_identities={"source": "source-v1"},
        )

    assert session.state is before


def test_recipe_save_rejects_unexpected_concurrent_manifest_transition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _recipe(),
        asset_id="recipe",
        destination="recipes/main.json",
    )
    session = ApplicationSession()
    session.open_workspace(root)
    session.select_recipe("recipe")
    before = session.state

    real_save = session_module.save_recipe_asset

    def save_then_mutate(*args, **kwargs):
        asset = real_save(*args, **kwargs)
        _add_asset(root, tmp_path, "concurrent")
        return asset

    monkeypatch.setattr(session_module, "save_recipe_asset", save_then_mutate)

    with pytest.raises(ApplicationError, match="changed concurrently with recipe save"):
        session.save_recipe(
            asset_id="recipe-copy",
            destination="recipes/copy.json",
        )

    assert session.state is before
