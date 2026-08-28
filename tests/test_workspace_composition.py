from __future__ import annotations

import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from catalysis_workbench.workflow import RecipeStep, WorkflowRecipe, WorkflowRecipeError
from catalysis_workbench.workspace import create_workspace, open_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.composition import (
    FigureComposition,
    RecipeComposition,
    WorkspaceComposition,
    bind_recipe_assets,
    create_workspace_composition,
    figure_spec_sha256,
    insert_recipe_step,
    load_figure_spec_asset,
    load_preset_bundle_asset,
    load_recipe_asset,
    move_recipe_step,
    open_workspace_composition,
    record_figure_export,
    remove_recipe_step,
    replace_recipe_step,
    save_figure_spec_asset,
    save_preset_bundle_asset,
    save_recipe_asset,
    save_workspace_composition,
)
from catalysis_workbench.workspace.evidence import (
    EvidenceRecord,
    append_evidence,
    create_evidence_ledger,
)
from catalysis_workbench.workspace.manifest import WorkspaceError


def _recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("raw",),
        steps=(
            RecipeStep(
                step_id="step-a",
                operation_id="example.identity",
                inputs={"series": "raw"},
                outputs={"series": "processed"},
                parameters={"scale": 1.0},
            ),
        ),
        outputs={"result": "processed"},
    )


def _independent_recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
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


def _dependent_recipe() -> WorkflowRecipe:
    return WorkflowRecipe(
        schema_version=1,
        inputs=("raw",),
        steps=(
            RecipeStep(
                step_id="producer",
                operation_id="example.producer",
                inputs={"value": "raw"},
                outputs={"value": "middle"},
                parameters={},
            ),
            RecipeStep(
                step_id="consumer",
                operation_id="example.consumer",
                inputs={"value": "middle"},
                outputs={"value": "final"},
                parameters={},
            ),
        ),
        outputs={"result": "final"},
    )


def _copy_asset(
    root: Path,
    source_dir: Path,
    *,
    asset_id: str,
    destination: str,
    content: bytes,
    asset_type: str = "data",
) -> None:
    source = source_dir / f"{asset_id}.bin"
    source.write_bytes(content)
    import_asset(
        root,
        source,
        asset_id=asset_id,
        asset_type=asset_type,
        policy="copy",
        destination=destination,
    )


def test_recipe_snapshot_reuses_reviewed_serialization_and_catalog(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    recipe = _recipe()

    asset = save_recipe_asset(
        root,
        recipe,
        asset_id="recipe-main",
        destination="recipes/main.json",
    )

    assert asset.asset_type == "workflow_recipe"
    assert asset.policy == "copy"
    assert asset.content_sha256 is not None
    loaded = load_recipe_asset(root, "recipe-main")
    assert loaded.recipe_sha256 == recipe.recipe_sha256
    assert loaded.steps == recipe.steps


def test_recipe_snapshot_collision_fails_before_new_destination_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    recipe = _recipe()
    save_recipe_asset(
        root,
        recipe,
        asset_id="recipe-main",
        destination="recipes/main.json",
    )
    before = open_workspace(root)

    with pytest.raises(WorkspaceError, match="asset_id collision"):
        save_recipe_asset(
            root,
            recipe,
            asset_id="recipe-main",
            destination="recipes/other.json",
        )

    assert open_workspace(root).manifest_sha256 == before.manifest_sha256
    assert not (root / "recipes" / "other.json").exists()


def test_recipe_asset_detects_byte_tampering(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _recipe(),
        asset_id="recipe-main",
        destination="recipes/main.json",
    )
    (root / "recipes" / "main.json").write_text("{}", encoding="utf-8")

    with pytest.raises(WorkspaceError, match="content digest"):
        load_recipe_asset(root, "recipe-main")


def test_figure_spec_snapshot_round_trips_complete_reviewed_state(
    tmp_path: Path,
) -> None:
    from catalysis_workbench.visualization import FigureSpec

    root = tmp_path / "workspace"
    create_workspace(root)
    spec = FigureSpec(
        xlabel="Potential",
        ylabel="Current",
        xlim=(-1.0, 0.5),
        show_legend=True,
    )

    save_figure_spec_asset(
        root,
        spec,
        asset_id="figure-spec",
        destination="figures/spec.json",
    )
    loaded = load_figure_spec_asset(root, "figure-spec")

    assert loaded.to_dict() == spec.to_dict()
    assert figure_spec_sha256(loaded) == figure_spec_sha256(spec)


def test_preset_bundle_snapshot_uses_reviewed_bundle_contract(tmp_path: Path) -> None:
    from catalysis_workbench.visualization import (
        FigurePresetBundle,
        FigurePresetEntry,
        FigureSpec,
    )

    root = tmp_path / "workspace"
    create_workspace(root)
    bundle = FigurePresetBundle(
        schema_version=1,
        entries=(FigurePresetEntry(name="paper", spec=FigureSpec(title="A")),),
    )

    save_preset_bundle_asset(
        root,
        bundle,
        asset_id="preset-main",
        destination="figures/presets.json",
    )
    loaded = load_preset_bundle_asset(root, "preset-main")

    assert loaded.bundle_sha256 == bundle.bundle_sha256


def test_recipe_binding_persists_exact_recipe_order_and_asset_associations(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    recipe = _recipe()
    save_recipe_asset(
        root,
        recipe,
        asset_id="recipe-main",
        destination="recipes/main.json",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="raw-data",
        destination="data/raw.bin",
        content=b"raw",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="result-data",
        destination="data/result.bin",
        content=b"result",
    )
    create_workspace_composition(root)

    updated = bind_recipe_assets(
        root,
        composition_id="analysis-main",
        recipe_asset_id="recipe-main",
        input_assets={"raw": "raw-data"},
        output_assets={"result": "result-data"},
    )

    assert len(updated.recipes) == 1
    record = updated.recipes[0]
    assert record.recipe_sha256 == recipe.recipe_sha256
    assert tuple(record.input_assets) == ("raw",)
    assert tuple(record.output_assets) == ("result",)
    assert open_workspace_composition(root).composition_sha256 == updated.composition_sha256


def test_recipe_binding_rejects_unknown_asset_without_persistent_mutation(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _recipe(),
        asset_id="recipe-main",
        destination="recipes/main.json",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="result-data",
        destination="data/result.bin",
        content=b"result",
    )
    create_workspace_composition(root)
    path = root / "workspace-composition.json"
    before = path.read_bytes()

    with pytest.raises(WorkspaceError, match="unknown workspace asset_id"):
        bind_recipe_assets(
            root,
            composition_id="analysis-main",
            recipe_asset_id="recipe-main",
            input_assets={"raw": "missing"},
            output_assets={"result": "result-data"},
        )

    assert path.read_bytes() == before


def test_figure_export_association_records_exact_presentation_export_and_evidence(
    tmp_path: Path,
) -> None:
    from catalysis_workbench.visualization import (
        FigurePresetBundle,
        FigurePresetEntry,
        FigureSpec,
    )

    root = tmp_path / "workspace"
    create_workspace(root)
    spec = FigureSpec(title="Result")
    save_figure_spec_asset(
        root,
        spec,
        asset_id="figure-spec",
        destination="figures/spec.json",
    )
    bundle = FigurePresetBundle(
        schema_version=1,
        entries=(FigurePresetEntry(name="paper", spec=spec),),
    )
    save_preset_bundle_asset(
        root,
        bundle,
        asset_id="preset-main",
        destination="figures/preset.json",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="figure-export",
        destination="exports/result.png",
        content=b"fake-png-bytes",
        asset_type="exported_figure",
    )
    create_evidence_ledger(root)
    append_evidence(
        root,
        EvidenceRecord(
            record_id="run-evidence",
            kind="artifact",
            evidence_sha256="a" * 64,
        ),
    )
    create_workspace_composition(root)

    updated = record_figure_export(
        root,
        composition_id="figure-main",
        figure_spec_asset_id="figure-spec",
        exported_figure_asset_id="figure-export",
        preset_bundle_asset_id="preset-main",
        evidence_record_ids=("run-evidence",),
    )

    record = updated.figures[0]
    assert record.figure_spec_sha256 == figure_spec_sha256(spec)
    assert record.preset_bundle_sha256 == bundle.bundle_sha256
    assert record.evidence_record_ids == ("run-evidence",)
    assert record.exported_figure_sha256 == open_workspace(root).assets[-1].content_sha256


def test_unknown_figure_evidence_fails_without_composition_mutation(
    tmp_path: Path,
) -> None:
    from catalysis_workbench.visualization import FigureSpec

    root = tmp_path / "workspace"
    create_workspace(root)
    save_figure_spec_asset(
        root,
        FigureSpec(),
        asset_id="figure-spec",
        destination="figures/spec.json",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="figure-export",
        destination="exports/result.svg",
        content=b"<svg/>",
        asset_type="exported_figure",
    )
    create_workspace_composition(root)
    before = (root / "workspace-composition.json").read_bytes()

    with pytest.raises(WorkspaceError, match="unknown evidence records"):
        record_figure_export(
            root,
            composition_id="figure-main",
            figure_spec_asset_id="figure-spec",
            exported_figure_asset_id="figure-export",
            evidence_record_ids=("missing",),
        )

    assert (root / "workspace-composition.json").read_bytes() == before


@pytest.mark.parametrize(
    "destination",
    ["workspace-composition.json", "WORKSPACE-COMPOSITION.JSON"],
)
def test_composition_metadata_path_is_reserved_from_asset_catalog(
    tmp_path: Path,
    destination: str,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    source = tmp_path / "payload.bin"
    source.write_bytes(b"payload")
    before = open_workspace(root)

    with pytest.raises(WorkspaceError, match="reserved workspace metadata"):
        import_asset(
            root,
            source,
            asset_id="forbidden",
            asset_type="data",
            policy="copy",
            destination=destination,
        )

    assert open_workspace(root).manifest_sha256 == before.manifest_sha256
    assert not (root / destination).exists()


def test_composition_identity_is_independent_of_workspace_root(tmp_path: Path) -> None:
    identities: list[str] = []
    for name in ("one", "two"):
        root = tmp_path / name
        create_workspace(root)
        save_recipe_asset(
            root,
            _recipe(),
            asset_id="recipe-main",
            destination="recipes/main.json",
        )
        _copy_asset(
            root,
            tmp_path,
            asset_id="raw-data",
            destination="data/raw.bin",
            content=b"same-raw",
        )
        _copy_asset(
            root,
            tmp_path,
            asset_id="result-data",
            destination="data/result.bin",
            content=b"same-result",
        )
        create_workspace_composition(root)
        value = bind_recipe_assets(
            root,
            composition_id="analysis-main",
            recipe_asset_id="recipe-main",
            input_assets={"raw": "raw-data"},
            output_assets={"result": "result-data"},
        )
        identities.append(value.composition_sha256)

    assert identities[0] == identities[1]


def test_strict_composition_loader_rejects_duplicate_and_unknown_fields(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    create_workspace_composition(root)
    path = root / "workspace-composition.json"

    path.write_text(
        '{"schema_version":1,"schema_version":1,"recipes":[],"figures":[]}',
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceError, match="cannot load workspace composition"):
        open_workspace_composition(root)

    path.write_text(
        '{"schema_version":1,"recipes":[],"figures":[],"unknown":1}',
        encoding="utf-8",
    )
    with pytest.raises(WorkspaceError, match="invalid workspace composition fields"):
        open_workspace_composition(root)


def test_composition_symlink_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    create_workspace_composition(root)
    path = root / "workspace-composition.json"
    external = tmp_path / "external.json"
    external.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(external)

    with pytest.raises(WorkspaceError, match="must not be a symbolic link"):
        open_workspace_composition(root)


def test_composition_overwrite_replaces_hardlink_without_mutating_external_target(
    tmp_path: Path,
) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    save_recipe_asset(
        root,
        _recipe(),
        asset_id="recipe-main",
        destination="recipes/main.json",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="raw-data",
        destination="data/raw.bin",
        content=b"raw",
    )
    _copy_asset(
        root,
        tmp_path,
        asset_id="result-data",
        destination="data/result.bin",
        content=b"result",
    )
    create_workspace_composition(root)
    path = root / "workspace-composition.json"
    external = tmp_path / "external-link.json"
    os.link(path, external)
    original_external = external.read_bytes()

    bind_recipe_assets(
        root,
        composition_id="analysis-main",
        recipe_asset_id="recipe-main",
        input_assets={"raw": "raw-data"},
        output_assets={"result": "result-data"},
    )

    assert external.read_bytes() == original_external
    assert path.read_bytes() != original_external


def test_composition_values_are_immutable() -> None:
    item = RecipeComposition(
        composition_id="r",
        recipe_asset_id="recipe",
        recipe_sha256="a" * 64,
        input_assets={"raw": "input"},
        output_assets={"result": "output"},
        input_asset_sha256={"raw": "b" * 64},
        output_asset_sha256={"result": "c" * 64},
    )
    value = WorkspaceComposition(schema_version=1, recipes=(item,), figures=())

    with pytest.raises(FrozenInstanceError):
        value.schema_version = 2  # type: ignore[misc]
    with pytest.raises(TypeError):
        item.input_assets["raw"] = "other"  # type: ignore[index]


def test_ordered_recipe_editing_moves_independent_steps_literally() -> None:
    recipe = _independent_recipe()

    moved = move_recipe_step(recipe, "right", 0)

    assert tuple(step.step_id for step in moved.steps) == ("right", "left")
    assert recipe.steps[0].step_id == "left"


def test_ordered_recipe_editing_does_not_topologically_repair_dependencies() -> None:
    recipe = _dependent_recipe()

    with pytest.raises(WorkflowRecipeError, match="unavailable bindings"):
        move_recipe_step(recipe, "consumer", 0)
    with pytest.raises(WorkflowRecipeError, match="unavailable bindings"):
        remove_recipe_step(recipe, "producer")


def test_ordered_recipe_editing_uses_literal_operations_without_discovery() -> None:
    recipe = _independent_recipe()
    inserted = RecipeStep(
        step_id="third",
        operation_id="not.registered.anywhere",
        inputs={"value": "a"},
        outputs={"value": "third_out"},
        parameters={"explicit": True},
    )
    updated = insert_recipe_step(recipe, 1, inserted)
    replacement = RecipeStep(
        step_id="third",
        operation_id="also.not.registered",
        inputs={"value": "a"},
        outputs={"value": "third_out"},
        parameters={"explicit": False},
    )
    updated = replace_recipe_step(updated, "third", replacement)

    assert updated.steps[1].operation_id == "also.not.registered"
    assert updated.steps[1].parameters["explicit"] is False


def test_composition_dataclasses_reject_duplicate_global_ids() -> None:
    recipe = RecipeComposition(
        composition_id="same",
        recipe_asset_id="recipe",
        recipe_sha256="a" * 64,
        input_assets={},
        output_assets={},
        input_asset_sha256={},
        output_asset_sha256={},
    )
    figure = FigureComposition(
        composition_id="same",
        figure_spec_asset_id="spec",
        figure_spec_sha256="b" * 64,
        exported_figure_asset_id="export",
        exported_figure_sha256="c" * 64,
    )

    with pytest.raises(WorkspaceError, match="composition_id values must be unique"):
        WorkspaceComposition(schema_version=1, recipes=(recipe,), figures=(figure,))


def test_save_workspace_composition_is_no_clobber_by_default(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    create_workspace(root)
    value = create_workspace_composition(root)

    with pytest.raises(FileExistsError):
        save_workspace_composition(value, root)
