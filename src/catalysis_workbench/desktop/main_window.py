"""Qt Widgets presentation shell bound to the GUI-neutral application layer."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from catalysis_workbench.application import (
    ApplicationError,
    ApplicationSession,
    MoveRecipeStepCommand,
    create_workspace_in_session,
    import_asset_in_session,
    workspace_snapshot,
)
from catalysis_workbench.core import Dataset, Series
from catalysis_workbench.visualization import FigureSpec, VisualizationError
from catalysis_workbench.workflow import QAFinding, QAReport, WorkflowRun
from catalysis_workbench.workspace.manifest import WorkspaceError


class ImportAssetDialog(QDialog):
    """Collect explicit catalog metadata for one user-selected source file."""

    def __init__(self, source: str | Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import asset")
        self._source = Path(source)

        form = QFormLayout(self)
        source_label = QLabel(str(self._source))
        source_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("Source", source_label)

        self.asset_id = QLineEdit(self._source.stem)
        self.asset_type = QLineEdit("source_file")
        self.policy = QComboBox()
        self.policy.addItems(("reference", "copy"))
        self.destination = QLineEdit(f"assets/{self._source.name}")
        self.destination.setEnabled(False)
        self.policy.currentTextChanged.connect(
            lambda value: self.destination.setEnabled(value == "copy")
        )

        form.addRow("Asset ID", self.asset_id)
        form.addRow("Asset type", self.asset_type)
        form.addRow("Policy", self.policy)
        form.addRow("Copy destination", self.destination)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def import_values(self) -> dict[str, str | None]:
        """Return exactly the user-visible import values."""

        policy = self.policy.currentText()
        destination = self.destination.text().strip() if policy == "copy" else None
        return {
            "asset_id": self.asset_id.text().strip(),
            "asset_type": self.asset_type.text().strip(),
            "policy": policy,
            "destination": destination,
        }


class CatalysisWorkbenchMainWindow(QMainWindow):
    """Thin desktop presentation shell over :class:`ApplicationSession`."""

    def __init__(
        self,
        *,
        session: ApplicationSession | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if session is not None and not isinstance(session, ApplicationSession):
            raise TypeError("session must be an ApplicationSession or None")
        self.session = ApplicationSession() if session is None else session
        self._figure_editor_data: Series | Dataset | None = None
        self._figure_editor_controller: Any | None = None

        self.setWindowTitle("CatalysisWorkbench")
        self.resize(1180, 760)
        self._build_actions()
        self._build_ui()
        self.refresh_views()

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        new_action = QAction("New Workspace…", self)
        open_action = QAction("Open Workspace…", self)
        import_action = QAction("Import Asset…", self)
        refresh_action = QAction("Refresh Workspace", self)
        close_action = QAction("Close Workspace", self)
        exit_action = QAction("Exit", self)

        new_action.triggered.connect(self._choose_create_workspace)
        open_action.triggered.connect(self._choose_open_workspace)
        import_action.triggered.connect(self._choose_import_asset)
        refresh_action.triggered.connect(self._refresh_workspace_action)
        close_action.triggered.connect(self._close_workspace_action)
        exit_action.triggered.connect(self.close)

        file_menu.addActions((new_action, open_action, import_action))
        file_menu.addSeparator()
        file_menu.addActions((refresh_action, close_action))
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        self._import_action = import_action
        self._refresh_action = refresh_action
        self._close_action = close_action

    def _build_ui(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        asset_panel = QWidget()
        asset_layout = QVBoxLayout(asset_panel)
        asset_layout.addWidget(QLabel("Workspace assets"))
        self.asset_tree = QTreeWidget()
        self.asset_tree.setColumnCount(5)
        self.asset_tree.setHeaderLabels(("ID", "Type", "Policy", "Path", "SHA-256"))
        self.asset_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.asset_tree.itemSelectionChanged.connect(self._asset_selection_changed)
        self.asset_tree.itemDoubleClicked.connect(self._activate_asset)
        asset_layout.addWidget(self.asset_tree)
        splitter.addWidget(asset_panel)

        self.tabs = QTabWidget()
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 5)

        self._build_project_tab()
        self._build_recipe_tab()
        self._build_evidence_tab()
        self._build_figure_tab()

    def _build_project_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.workspace_label = QLabel("No workspace open")
        self.workspace_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.manifest_label = QLabel("")
        self.manifest_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.selection_label = QLabel("Selected assets: none")
        layout.addWidget(self.workspace_label)
        layout.addWidget(self.manifest_label)
        layout.addWidget(self.selection_label)
        layout.addStretch(1)
        self.tabs.addTab(page, "Project")

    def _build_recipe_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.recipe_label = QLabel("No recipe selected")
        self.recipe_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.recipe_label)

        self.recipe_list = QListWidget()
        self.recipe_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.recipe_list)

        buttons = QHBoxLayout()
        up = QPushButton("Move up")
        down = QPushButton("Move down")
        save = QPushButton("Save recipe snapshot…")
        up.clicked.connect(lambda: self._move_recipe_step(-1))
        down.clicked.connect(lambda: self._move_recipe_step(1))
        save.clicked.connect(self._save_recipe_action)
        buttons.addWidget(up)
        buttons.addWidget(down)
        buttons.addStretch(1)
        buttons.addWidget(save)
        layout.addLayout(buttons)

        self._recipe_up = up
        self._recipe_down = down
        self._recipe_save = save
        self.tabs.addTab(page, "Recipe")

    def _build_evidence_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Persistent evidence ledger"))
        self.evidence_tree = QTreeWidget()
        self.evidence_tree.setColumnCount(5)
        self.evidence_tree.setHeaderLabels(
            ("Record ID", "Kind", "Record SHA-256", "Assets", "Related records")
        )
        layout.addWidget(self.evidence_tree, 2)

        layout.addWidget(QLabel("Last workflow run"))
        self.run_table = QTableWidget(0, 2)
        self.run_table.setHorizontalHeaderLabels(("Field", "Value"))
        self.run_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.run_table, 1)

        layout.addWidget(QLabel("Last QA report"))
        self.qa_table = QTableWidget(0, 4)
        self.qa_table.setHorizontalHeaderLabels(("Check", "Status", "Code", "Finding SHA-256"))
        self.qa_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.qa_table, 1)
        self.tabs.addTab(page, "Evidence / QA")

    def _build_figure_tab(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.figure_label = QLabel("No FigureSpec selected")
        self.figure_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.figure_label)

        form = QFormLayout()
        self.figure_title = QLineEdit()
        self.figure_xlabel = QLineEdit()
        self.figure_ylabel = QLineEdit()
        self.figure_xscale = QComboBox()
        self.figure_xscale.addItems(("linear", "log", "symlog", "logit"))
        self.figure_yscale = QComboBox()
        self.figure_yscale.addItems(("linear", "log", "symlog", "logit"))

        self.figure_width = QDoubleSpinBox()
        self.figure_width.setRange(0.1, 100.0)
        self.figure_width.setDecimals(4)
        self.figure_height = QDoubleSpinBox()
        self.figure_height.setRange(0.1, 100.0)
        self.figure_height.setDecimals(4)

        self.figure_dpi = QSpinBox()
        self.figure_dpi.setRange(1, 10000)
        self.figure_transparent = QCheckBox()

        form.addRow("Title", self.figure_title)
        form.addRow("X label", self.figure_xlabel)
        form.addRow("Y label", self.figure_ylabel)
        form.addRow("X scale", self.figure_xscale)
        form.addRow("Y scale", self.figure_yscale)
        form.addRow("Figure width (in)", self.figure_width)
        form.addRow("Figure height (in)", self.figure_height)
        form.addRow("Export DPI", self.figure_dpi)
        form.addRow("Transparent export", self.figure_transparent)
        layout.addLayout(form)

        controls = QHBoxLayout()
        apply_button = QPushButton("Apply presentation")
        save_button = QPushButton("Save FigureSpec snapshot…")
        editor_button = QPushButton("Open Matplotlib editor")
        sync_button = QPushButton("Apply Matplotlib editor state")
        apply_button.clicked.connect(self._apply_figure_controls)
        save_button.clicked.connect(self._save_figure_spec_action)
        editor_button.clicked.connect(self._open_matplotlib_editor)
        sync_button.clicked.connect(self._apply_matplotlib_editor)
        controls.addWidget(apply_button)
        controls.addWidget(save_button)
        controls.addStretch(1)
        controls.addWidget(editor_button)
        controls.addWidget(sync_button)
        layout.addLayout(controls)

        self._figure_controls = (
            self.figure_title,
            self.figure_xlabel,
            self.figure_ylabel,
            self.figure_xscale,
            self.figure_yscale,
            self.figure_width,
            self.figure_height,
            self.figure_dpi,
            self.figure_transparent,
            apply_button,
            save_button,
        )
        self._figure_editor_button = editor_button
        self._figure_sync_button = sync_button
        self.tabs.addTab(page, "Figure")

    def _show_error(self, title: str, exc: BaseException) -> None:
        QMessageBox.critical(self, title, str(exc))
        self.statusBar().showMessage(str(exc), 8000)

    def _run_ui_action(self, title: str, action) -> None:
        try:
            action()
        except (
            ApplicationError,
            WorkspaceError,
            VisualizationError,
            FileNotFoundError,
            FileExistsError,
            NotADirectoryError,
            OSError,
            TypeError,
            ValueError,
        ) as exc:
            self._show_error(title, exc)

    def create_workspace_path(self, root: str | Path) -> None:
        """Create and select an explicit workspace without opening a chooser."""

        create_workspace_in_session(self.session, root)
        self.refresh_views()

    def open_workspace_path(self, root: str | Path) -> None:
        """Open an explicit workspace without opening a chooser."""

        self.session.open_workspace(root)
        self.refresh_views()

    def import_asset_path(
        self,
        source: str | Path,
        *,
        asset_id: str,
        asset_type: str,
        policy: str,
        destination: str | None = None,
    ) -> None:
        """Import an explicit source/catalog mapping without parser inference."""

        import_asset_in_session(
            self.session,
            source,
            asset_id=asset_id,
            asset_type=asset_type,
            policy=policy,
            destination=destination,
        )
        self.refresh_views()

    def execute_recipe(
        self,
        inputs: Mapping[str, object],
        *,
        input_identities: Mapping[str, str],
    ) -> WorkflowRun:
        """Delegate explicit workflow execution to the application controller."""

        result = self.session.execute_recipe(inputs, input_identities=input_identities)
        self.refresh_views()
        return result

    def run_qa(self, findings: Iterable[QAFinding]) -> QAReport:
        """Delegate explicitly selected QA findings to the application controller."""

        report = self.session.run_qa(findings)
        self.refresh_views()
        return report

    def set_figure_editor_data(self, data: Series | Dataset | None) -> None:
        """Supply explicit scientific data for the existing Matplotlib FigureSpec editor."""

        if data is not None and not isinstance(data, (Series, Dataset)):
            raise TypeError("figure editor data must be Series, Dataset, or None")
        self._figure_editor_data = data
        self._sync_figure_editor_buttons()

    def _choose_create_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Choose parent directory for new workspace",
        )
        if not path:
            return
        name, accepted = QInputDialog.getText(self, "New workspace", "Directory name")
        if not accepted or not name.strip():
            return
        target = Path(path) / name.strip()
        self._run_ui_action("Create workspace failed", lambda: self.create_workspace_path(target))

    def _choose_open_workspace(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Open workspace")
        if path:
            self._run_ui_action("Open workspace failed", lambda: self.open_workspace_path(path))

    def _choose_import_asset(self) -> None:
        if self.session.state.workspace_root is None:
            self._show_error("Import asset failed", ApplicationError("no workspace is open"))
            return
        source, _ = QFileDialog.getOpenFileName(self, "Select asset source")
        if not source:
            return
        dialog = ImportAssetDialog(source, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        values = dialog.import_values()
        self._run_ui_action(
            "Import asset failed",
            lambda: self.import_asset_path(
                source,
                asset_id=str(values["asset_id"]),
                asset_type=str(values["asset_type"]),
                policy=str(values["policy"]),
                destination=values["destination"],
            ),
        )

    def _refresh_workspace_action(self) -> None:
        self._run_ui_action(
            "Refresh workspace failed",
            lambda: (self.session.refresh_workspace(), self.refresh_views()),
        )

    def _close_workspace_action(self) -> None:
        self._run_ui_action(
            "Close workspace failed",
            lambda: (self.session.close_workspace(), self.refresh_views()),
        )

    def refresh_views(self) -> None:
        """Refresh all presentation widgets from current application/workspace state."""

        state = self.session.state
        open_state = state.workspace_root is not None
        self._import_action.setEnabled(open_state)
        self._refresh_action.setEnabled(open_state)
        self._close_action.setEnabled(open_state)

        if not open_state:
            self.workspace_label.setText("No workspace open")
            self.manifest_label.clear()
            self.selection_label.setText("Selected assets: none")
            self.asset_tree.clear()
            self.evidence_tree.clear()
        else:
            snapshot = workspace_snapshot(self.session)
            self.workspace_label.setText(f"Workspace: {state.workspace_root}")
            self.manifest_label.setText(
                f"Manifest SHA-256: {snapshot.manifest.manifest_sha256}"
            )
            selected = ", ".join(state.selected_asset_ids) or "none"
            self.selection_label.setText(f"Selected assets: {selected}")
            self._populate_assets(snapshot.manifest.assets)
            self._populate_evidence(
                () if snapshot.evidence is None else snapshot.evidence.records
            )

        self._populate_recipe()
        self._populate_run()
        self._populate_qa()
        self._populate_figure()
        self.statusBar().showMessage(f"Application revision {self.session.state.revision}")

    def _populate_assets(self, assets) -> None:
        selected = set(self.session.state.selected_asset_ids)
        self.asset_tree.blockSignals(True)
        try:
            self.asset_tree.clear()
            for asset in assets:
                item = QTreeWidgetItem(
                    (
                        asset.asset_id,
                        asset.asset_type,
                        asset.policy,
                        asset.path,
                        asset.content_sha256 or "",
                    )
                )
                item.setData(0, Qt.ItemDataRole.UserRole, asset.asset_id)
                item.setData(1, Qt.ItemDataRole.UserRole, asset.asset_type)
                self.asset_tree.addTopLevelItem(item)
                item.setSelected(asset.asset_id in selected)
            for column in range(self.asset_tree.columnCount()):
                self.asset_tree.resizeColumnToContents(column)
        finally:
            self.asset_tree.blockSignals(False)

    def _asset_selection_changed(self) -> None:
        if self.session.state.workspace_root is None:
            return
        asset_ids = tuple(
            str(item.data(0, Qt.ItemDataRole.UserRole))
            for item in self.asset_tree.selectedItems()
        )
        self._run_ui_action(
            "Asset selection failed",
            lambda: (self.session.select_assets(asset_ids), self.refresh_views()),
        )

    def _activate_asset(self, item: QTreeWidgetItem) -> None:
        asset_id = str(item.data(0, Qt.ItemDataRole.UserRole))
        asset_type = str(item.data(1, Qt.ItemDataRole.UserRole))
        if asset_type == "workflow_recipe":
            self._run_ui_action(
                "Recipe selection failed",
                lambda: (self.session.select_recipe(asset_id), self.refresh_views()),
            )
        elif asset_type == "figure_spec":
            self._run_ui_action(
                "FigureSpec selection failed",
                lambda: (self.session.select_figure_spec(asset_id), self.refresh_views()),
            )

    def _populate_recipe(self) -> None:
        state = self.session.state
        recipe = state.recipe
        self.recipe_list.clear()
        enabled = recipe is not None
        self._recipe_up.setEnabled(enabled)
        self._recipe_down.setEnabled(enabled)
        self._recipe_save.setEnabled(enabled)
        if recipe is None:
            self.recipe_label.setText("No recipe selected")
            return
        suffix = " (dirty)" if state.recipe_dirty else ""
        self.recipe_label.setText(
            f"{state.selected_recipe_asset_id} · {recipe.recipe_sha256}{suffix}"
        )
        for step in recipe.steps:
            self.recipe_list.addItem(f"{step.step_id} · {step.operation_id}")

    def _move_recipe_step(self, delta: int) -> None:
        recipe = self.session.state.recipe
        row = self.recipe_list.currentRow()
        if recipe is None or row < 0:
            return
        target = row + delta
        if target < 0 or target >= len(recipe.steps):
            return
        step_id = recipe.steps[row].step_id

        def action() -> None:
            self.session.edit_recipe(
                MoveRecipeStepCommand(step_id=step_id, new_index=target)
            )
            self.refresh_views()
            self.recipe_list.setCurrentRow(target)

        self._run_ui_action("Recipe edit failed", action)

    def _save_recipe_action(self) -> None:
        state = self.session.state
        if state.recipe is None:
            return
        asset_id, accepted = QInputDialog.getText(
            self,
            "Save recipe snapshot",
            "New asset ID",
        )
        if not accepted or not asset_id.strip():
            return
        default = f"recipes/{asset_id.strip()}.json"
        destination, accepted = QInputDialog.getText(
            self,
            "Save recipe snapshot",
            "Workspace destination",
            text=default,
        )
        if not accepted or not destination.strip():
            return
        self._run_ui_action(
            "Save recipe failed",
            lambda: (
                self.session.save_recipe(
                    asset_id=asset_id.strip(),
                    destination=destination.strip(),
                ),
                self.refresh_views(),
            ),
        )

    def _populate_evidence(self, records) -> None:
        self.evidence_tree.clear()
        for record in records:
            item = QTreeWidgetItem(
                (
                    record.record_id,
                    record.kind,
                    record.record_sha256,
                    ", ".join(record.asset_ids),
                    ", ".join(record.related_record_ids),
                )
            )
            self.evidence_tree.addTopLevelItem(item)
        for column in range(self.evidence_tree.columnCount()):
            self.evidence_tree.resizeColumnToContents(column)

    def _set_table_rows(self, table: QTableWidget, rows: list[tuple[str, ...]]) -> None:
        table.setRowCount(len(rows))
        for row, values in enumerate(rows):
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))
        table.resizeColumnsToContents()

    def _populate_run(self) -> None:
        run = self.session.state.last_workflow_run
        if run is None:
            self._set_table_rows(self.run_table, [])
            return
        rows = [
            ("record_sha256", run.record_sha256),
            ("recipe_sha256", run.recipe_sha256),
            ("content_sha256", run.content_sha256),
            ("steps", ", ".join(step.step_id for step in run.steps)),
            ("outputs", ", ".join(run.output_identities)),
        ]
        self._set_table_rows(self.run_table, rows)

    def _populate_qa(self) -> None:
        report = self.session.state.last_qa_report
        if report is None:
            self._set_table_rows(self.qa_table, [])
            return
        rows = [
            (
                finding.check_id,
                finding.status.value,
                finding.code,
                finding.finding_sha256,
            )
            for finding in report.findings
        ]
        self._set_table_rows(self.qa_table, rows)

    def _populate_figure(self) -> None:
        state = self.session.state
        spec = state.figure_spec
        enabled = spec is not None
        for control in self._figure_controls:
            control.setEnabled(enabled)
        if spec is None:
            self.figure_label.setText("No FigureSpec selected")
            self._sync_figure_editor_buttons()
            return

        suffix = " (dirty)" if state.figure_spec_dirty else ""
        self.figure_label.setText(f"{state.selected_figure_spec_asset_id}{suffix}")
        controls = (
            (self.figure_title, spec.title or ""),
            (self.figure_xlabel, spec.xlabel or ""),
            (self.figure_ylabel, spec.ylabel or ""),
        )
        for widget, value in controls:
            widget.blockSignals(True)
            widget.setText(value)
            widget.blockSignals(False)

        for combo, value in (
            (self.figure_xscale, spec.xscale),
            (self.figure_yscale, spec.yscale),
        ):
            combo.blockSignals(True)
            combo.setCurrentText(value)
            combo.blockSignals(False)

        for widget, value in (
            (self.figure_width, spec.layout.figure_width_in),
            (self.figure_height, spec.layout.figure_height_in),
            (self.figure_dpi, spec.export.dpi),
        ):
            widget.blockSignals(True)
            widget.setValue(value)
            widget.blockSignals(False)

        self.figure_transparent.blockSignals(True)
        self.figure_transparent.setChecked(spec.export.transparent)
        self.figure_transparent.blockSignals(False)
        self._sync_figure_editor_buttons()

    def _apply_figure_controls(self) -> None:
        spec = self.session.state.figure_spec
        if spec is None:
            return

        def action() -> None:
            layout = spec.layout.updated(
                figure_width_in=self.figure_width.value(),
                figure_height_in=self.figure_height.value(),
            )
            export = spec.export.updated(
                dpi=self.figure_dpi.value(),
                transparent=self.figure_transparent.isChecked(),
            )
            self.session.update_figure_spec(
                layout=layout,
                export=export,
                title=self.figure_title.text() or None,
                xlabel=self.figure_xlabel.text() or None,
                ylabel=self.figure_ylabel.text() or None,
                xscale=self.figure_xscale.currentText(),
                yscale=self.figure_yscale.currentText(),
            )
            self.refresh_views()

        self._run_ui_action("Figure presentation update failed", action)

    def _save_figure_spec_action(self) -> None:
        if self.session.state.figure_spec is None:
            return
        asset_id, accepted = QInputDialog.getText(
            self,
            "Save FigureSpec snapshot",
            "New asset ID",
        )
        if not accepted or not asset_id.strip():
            return
        default = f"figures/{asset_id.strip()}.json"
        destination, accepted = QInputDialog.getText(
            self,
            "Save FigureSpec snapshot",
            "Workspace destination",
            text=default,
        )
        if not accepted or not destination.strip():
            return
        self._run_ui_action(
            "Save FigureSpec failed",
            lambda: (
                self.session.save_figure_spec(
                    asset_id=asset_id.strip(),
                    destination=destination.strip(),
                ),
                self.refresh_views(),
            ),
        )

    def _sync_figure_editor_buttons(self) -> None:
        selected = self.session.state.figure_spec is not None
        self._figure_editor_button.setEnabled(
            selected and self._figure_editor_data is not None
        )
        self._figure_sync_button.setEnabled(
            selected and self._figure_editor_controller is not None
        )

    def _open_matplotlib_editor(self) -> None:
        spec = self.session.state.figure_spec
        data = self._figure_editor_data
        if spec is None or data is None:
            return

        def action() -> None:
            from catalysis_workbench.visualization import open_figure_spec_editor

            self._figure_editor_controller = open_figure_spec_editor(
                data,
                spec,
                show=True,
            )
            self._sync_figure_editor_buttons()

        self._run_ui_action("Open FigureSpec editor failed", action)

    def _apply_matplotlib_editor(self) -> None:
        controller = self._figure_editor_controller
        if controller is None or self.session.state.figure_spec is None:
            return

        def action() -> None:
            editor_spec: FigureSpec = controller.spec
            self.session.update_figure_spec(
                layout=editor_spec.layout,
                style=editor_spec.style,
                export=editor_spec.export,
                xlabel=editor_spec.xlabel,
                ylabel=editor_spec.ylabel,
                title=editor_spec.title,
                xlim=editor_spec.xlim,
                ylim=editor_spec.ylim,
                xscale=editor_spec.xscale,
                yscale=editor_spec.yscale,
                show_legend=editor_spec.show_legend,
                annotations=editor_spec.annotations,
                series_styles=dict(editor_spec.series_styles),
                category_styles=dict(editor_spec.category_styles),
            )
            self.refresh_views()

        self._run_ui_action("Apply FigureSpec editor state failed", action)


__all__ = ["CatalysisWorkbenchMainWindow", "ImportAssetDialog"]
