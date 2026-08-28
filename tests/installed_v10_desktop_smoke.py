from __future__ import annotations

import importlib
import sys
import tempfile
from pathlib import Path

import numpy as np

import catalysis_workbench
from catalysis_workbench.application import ApplicationSession
from catalysis_workbench.core import Series
from catalysis_workbench.visualization import FigureSpec
from catalysis_workbench.workflow import RecipeStep, WorkflowRecipe, check_digest
from catalysis_workbench.workspace import create_workspace
from catalysis_workbench.workspace.assets import import_asset
from catalysis_workbench.workspace.composition import (
    save_figure_spec_asset,
    save_recipe_asset,
)
from catalysis_workbench.workspace.evidence import (
    append_evidence,
    create_evidence_ledger,
    record_evidence,
)

EXPECTED_VERSION = "1.0.0.dev0"

assert catalysis_workbench.__version__ == EXPECTED_VERSION
assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)

desktop = importlib.import_module("catalysis_workbench.desktop")
assert not any(name == "PySide6" or name.startswith("PySide6.") for name in sys.modules)
assert desktop.desktop_available() is True

create_desktop = importlib.import_module(
    "catalysis_workbench.desktop.app"
).create_desktop
QCloseEvent = importlib.import_module("PySide6.QtGui").QCloseEvent

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

    raw = base / "raw.dat"
    raw.write_bytes(b"raw")
    import_asset(
        root,
        raw,
        asset_id="raw",
        asset_type="source_file",
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
        FigureSpec(title="Desktop figure"),
        asset_id="figure",
        destination="figures/spec.json",
    )
    create_evidence_ledger(root)
    append_evidence(
        root,
        record_evidence(
            "recipe-evidence",
            recipe,
            asset_ids=("recipe",),
        ),
    )

    handle = create_desktop(root, session=ApplicationSession(), argv=("cw-desktop-smoke",))
    window = handle.window
    application = handle.application

    assert type(window).__module__ == "catalysis_workbench.desktop.window"
    assert window.asset_tree.topLevelItemCount() == 3
    assert window.evidence_tree.topLevelItemCount() == 1

    extra = base / "extra.dat"
    extra.write_bytes(b"extra")
    window.import_asset_path(
        extra,
        asset_id="extra",
        asset_type="source_file",
        policy="reference",
    )
    assert window.asset_tree.topLevelItemCount() == 4

    window.session.select_recipe("recipe")
    window.refresh_views()
    assert window.recipe_list.count() == 1
    assert "recipe" in window.recipe_label.text()

    source = Series(
        x=np.array([0.0, 1.0, 2.0]),
        y=np.array([1.0, 2.0, 3.0]),
        key="source",
        label="source",
    )
    run = window.execute_recipe(
        {"source": source},
        input_identities={"source": "desktop-smoke-source-v1"},
    )
    assert np.allclose(run.outputs["result"].y, np.array([2.0, 3.0, 4.0]))
    assert window.run_table.rowCount() >= 4

    report = window.run_qa(
        (check_digest(run.record_sha256, run.record_sha256, subject="run"),)
    )
    assert report.status.value == "pass"
    assert window.qa_table.rowCount() == 1

    window.session.select_figure_spec("figure")
    window.refresh_views()
    window.figure_title.setText("Desktop edited")
    window.figure_width.setValue(4.25)
    window.figure_dpi.setValue(450)
    window._apply_figure_controls()
    edited = window.session.state.figure_spec
    assert edited is not None
    assert edited.title == "Desktop edited"
    assert edited.layout.figure_width_in == 4.25
    assert edited.export.dpi == 450
    assert window.session.state.figure_spec_dirty is True

    window._confirm_discard_edits = lambda: False
    rejected_close = QCloseEvent()
    window.closeEvent(rejected_close)
    assert rejected_close.isAccepted() is False
    assert window.session.state.figure_spec_dirty is True

    window._confirm_discard_edits = lambda: True
    accepted_close = QCloseEvent()
    window.closeEvent(accepted_close)
    assert accepted_close.isAccepted() is True

    window.set_figure_editor_data(source)
    assert window._figure_editor_button.isEnabled()

    window.session.save_figure_spec(
        asset_id="figure-edited",
        destination="figures/edited.json",
    )
    window.refresh_views()
    assert window.asset_tree.topLevelItemCount() == 5

    new_root = base / "new-workspace"
    window.create_workspace_path(new_root)
    assert window.asset_tree.topLevelItemCount() == 0
    assert window.session.state.workspace_root == new_root.resolve()

    window.open_workspace_path(root)
    assert window.asset_tree.topLevelItemCount() == 5

    window.close_workspace_path()
    assert window.session.state.workspace_root is None

    window.close()
    application.processEvents()

print("installed v1.0 Block 6 PySide6 desktop smoke: ok")
