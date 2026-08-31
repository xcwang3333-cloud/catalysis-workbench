"""Task-specific v1.2 Desktop processing inspector over retained semantics."""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from catalysis_workbench.application import (
    AnalysisRange,
    AnalysisSessionState,
    DataSeriesSpec,
    FEPartialCurrentAnalysisSpec,
    GenericXYAnalysisSpec,
    LSVAnalysisSpec,
    LSVProcessingSpec,
    PartialCurrentPair,
)

from .ui_foundation import SPACING, refresh_widget_style


class ProcessingPanel(QWidget):
    """Edit scientific settings while invalid drafts stay outside the document."""

    analysis_spec_changed = Signal(object)
    draft_state_changed = Signal(bool, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._loading = False
        self._selected_data_id: str | None = None
        self._analysis = None
        self._data_series: tuple[DataSeriesSpec, ...] = ()
        self._has_unapplied_draft = False
        self._draft_message = ""
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._apply_draft_now)
        self.setObjectName("cwProcessingPanel")
        self._build_ui()

    @property
    def has_unapplied_draft(self) -> bool:
        return self._has_unapplied_draft

    @property
    def draft_message(self) -> str:
        return self._draft_message

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(
            SPACING.compact,
            SPACING.compact,
            SPACING.compact,
            SPACING.compact,
        )
        root.setSpacing(SPACING.compact)
        helper = QLabel(
            "Scientific settings commit only after validation. Invalid fields "
            "stay outside the document and preserve the previous valid result."
        )
        helper.setObjectName("cwInspectorHelp")
        helper.setWordWrap(True)
        root.addWidget(helper)

        self.override_box = QGroupBox("Apply to")
        self.override_box.setObjectName("cwInspectorSection")
        override_layout = QVBoxLayout(self.override_box)
        self.override_check = QCheckBox("Override selected series")
        self.override_check.toggled.connect(self._override_toggled)
        override_layout.addWidget(self.override_check)
        self.override_target_label = QLabel("Common settings")
        self.override_target_label.setObjectName("cwInspectorTarget")
        override_layout.addWidget(self.override_target_label)
        root.addWidget(self.override_box)

        self.potential_box = QGroupBox("Potential")
        self.potential_box.setObjectName("cwInspectorSection")
        potential_form = QFormLayout(self.potential_box)
        self.rhe_mode_combo = QComboBox()
        self.rhe_mode_combo.addItem("No RHE conversion", "none")
        self.rhe_mode_combo.addItem("Direct RHE offset", "direct")
        self.rhe_mode_combo.addItem("Reference vs SHE + pH", "she_ph")
        potential_form.addRow("Convert to RHE", self.rhe_mode_combo)
        self.rhe_offset_edit = QLineEdit()
        self.rhe_offset_edit.setPlaceholderText("V")
        potential_form.addRow("RHE offset (V)", self.rhe_offset_edit)
        self.reference_she_edit = QLineEdit()
        self.reference_she_edit.setPlaceholderText("V vs SHE")
        potential_form.addRow("Reference vs SHE (V)", self.reference_she_edit)
        self.ph_edit = QLineEdit()
        potential_form.addRow("pH", self.ph_edit)
        self.temperature_edit = QLineEdit("298.15")
        potential_form.addRow("Temperature (K)", self.temperature_edit)
        root.addWidget(self.potential_box)

        self.ir_box = QGroupBox("iR correction")
        self.ir_box.setObjectName("cwInspectorSection")
        ir_form = QFormLayout(self.ir_box)
        self.resistance_edit = QLineEdit()
        self.resistance_edit.setPlaceholderText("blank = off")
        ir_form.addRow("Resistance (Ω)", self.resistance_edit)
        self.fraction_edit = QLineEdit("1.0")
        ir_form.addRow("Correction fraction", self.fraction_edit)
        root.addWidget(self.ir_box)

        self.current_box = QGroupBox("Current density")
        self.current_box.setObjectName("cwInspectorSection")
        current_form = QFormLayout(self.current_box)
        self.normalize_check = QCheckBox("Normalize total current by electrode area")
        current_form.addRow(self.normalize_check)
        self.area_edit = QLineEdit()
        self.area_edit.setPlaceholderText("cm²")
        current_form.addRow("Electrode area (cm²)", self.area_edit)
        self.current_density_unit_combo = QComboBox()
        self.current_density_unit_combo.addItems(["mA/cm^2", "A/cm^2", "uA/cm^2"])
        current_form.addRow("Output unit", self.current_density_unit_combo)
        root.addWidget(self.current_box)

        self.pair_box = QGroupBox("FE ↔ current pairs")
        self.pair_box.setObjectName("cwInspectorSection")
        pair_layout = QVBoxLayout(self.pair_box)
        pair_form = QFormLayout()
        self.current_pair_combo = QComboBox()
        pair_form.addRow("Current series", self.current_pair_combo)
        self.fe_pair_combo = QComboBox()
        pair_form.addRow("FE series", self.fe_pair_combo)
        pair_layout.addLayout(pair_form)
        self.add_pair_button = QPushButton("Add explicit pair")
        self.add_pair_button.setObjectName("cwSecondaryButton")
        self.add_pair_button.clicked.connect(self._add_pair)
        pair_layout.addWidget(self.add_pair_button)
        self.pair_list = QListWidget()
        self.pair_list.setObjectName("cwInspectorPairList")
        pair_layout.addWidget(self.pair_list)
        self.remove_pair_button = QPushButton("Remove selected pair")
        self.remove_pair_button.setObjectName("cwTertiaryButton")
        self.remove_pair_button.clicked.connect(self._remove_pair)
        pair_layout.addWidget(self.remove_pair_button)
        root.addWidget(self.pair_box)

        self.range_box = QGroupBox("Analysis range")
        self.range_box.setObjectName("cwInspectorSection")
        range_form = QFormLayout(self.range_box)
        self.range_min_edit = QLineEdit()
        self.range_min_edit.setPlaceholderText("blank = no lower bound")
        range_form.addRow("From", self.range_min_edit)
        self.range_max_edit = QLineEdit()
        self.range_max_edit.setPlaceholderText("blank = no upper bound")
        range_form.addRow("To", self.range_max_edit)
        root.addWidget(self.range_box)

        self.processing_status = QLabel("No analysis")
        self.processing_status.setObjectName("cwProcessingStatus")
        self.processing_status.setProperty("state", "empty")
        self.processing_status.setWordWrap(True)
        root.addWidget(self.processing_status)
        root.addStretch(1)

        for editor in (
            self.rhe_offset_edit,
            self.reference_she_edit,
            self.ph_edit,
            self.temperature_edit,
            self.resistance_edit,
            self.fraction_edit,
            self.area_edit,
            self.range_min_edit,
            self.range_max_edit,
        ):
            editor.textEdited.connect(self._schedule_apply)
        self.rhe_mode_combo.currentIndexChanged.connect(self._schedule_apply)
        self.rhe_mode_combo.currentIndexChanged.connect(self._update_rhe_visibility)
        self.normalize_check.toggled.connect(self._schedule_apply)
        self.current_density_unit_combo.currentIndexChanged.connect(self._schedule_apply)
        self._update_rhe_visibility()

    def _set_status(self, text: str, state: str) -> None:
        self.processing_status.setProperty("state", state)
        self.processing_status.setText(text)
        refresh_widget_style(self.processing_status)

    def _set_draft_state(self, invalid: bool, message: str = "") -> None:
        changed = invalid != self._has_unapplied_draft or message != self._draft_message
        self._has_unapplied_draft = invalid
        self._draft_message = message
        if changed:
            self.draft_state_changed.emit(invalid, message)

    def _schedule_apply(self, *_args: object) -> None:
        if self._loading or self._analysis is None:
            return
        self._timer.start()

    @staticmethod
    def _optional_float(text: str, *, label: str) -> float | None:
        value = text.strip()
        if not value:
            return None
        try:
            return float(value)
        except ValueError as exc:
            raise ValueError(f"{label} must be a real number") from exc

    @staticmethod
    def _required_float(text: str, *, label: str) -> float:
        value = ProcessingPanel._optional_float(text, label=label)
        if value is None:
            raise ValueError(f"{label} is required")
        return value

    def _read_lsv_processing(self) -> LSVProcessingSpec:
        mode = self.rhe_mode_combo.currentData()
        if mode == "direct":
            offset = self._required_float(self.rhe_offset_edit.text(), label="RHE offset")
            reference = None
            ph = None
        elif mode == "she_ph":
            offset = None
            reference = self._required_float(
                self.reference_she_edit.text(), label="reference vs SHE"
            )
            ph = self._required_float(self.ph_edit.text(), label="pH")
        else:
            mode = "none"
            offset = None
            reference = None
            ph = None
        return LSVProcessingSpec(
            rhe_mode=mode,
            rhe_offset_v=offset,
            reference_potential_vs_she_v=reference,
            ph=ph,
            temperature_k=self._required_float(
                self.temperature_edit.text(), label="temperature"
            ),
            resistance_ohm=self._optional_float(
                self.resistance_edit.text(), label="resistance"
            ),
            ir_correction_fraction=self._required_float(
                self.fraction_edit.text(), label="iR correction fraction"
            ),
            electrode_area_cm2=self._optional_float(
                self.area_edit.text(), label="electrode area"
            ),
            normalize_to_current_density=self.normalize_check.isChecked(),
            current_density_unit=self.current_density_unit_combo.currentText(),
        )

    def _read_range(self) -> AnalysisRange:
        return AnalysisRange(
            x_min=self._optional_float(
                self.range_min_edit.text(), label="analysis range start"
            ),
            x_max=self._optional_float(
                self.range_max_edit.text(), label="analysis range end"
            ),
        )

    def _selected_supports_current_override(self) -> bool:
        if self._selected_data_id is None:
            return False
        for spec in self._data_series:
            if spec.data_id == self._selected_data_id:
                return spec.mapping.y_role.casefold() in {"current", "current_density"}
        return False

    def _build_analysis_spec(self):
        if isinstance(self._analysis, LSVAnalysisSpec):
            config = self._read_lsv_processing()
            overrides = dict(self._analysis.overrides)
            selected = self._selected_data_id
            if self.override_check.isChecked() and selected is not None:
                overrides[selected] = config
                common = self._analysis.common
            else:
                common = config
                if selected is not None:
                    overrides.pop(selected, None)
            return LSVAnalysisSpec(
                common=common,
                overrides=overrides,
                analysis_range=self._read_range(),
            )
        if isinstance(self._analysis, FEPartialCurrentAnalysisSpec):
            config = self._read_lsv_processing()
            overrides = dict(self._analysis.current_overrides)
            selected = self._selected_data_id
            if (
                self.override_check.isChecked()
                and selected is not None
                and self._selected_supports_current_override()
            ):
                overrides[selected] = config
                common = self._analysis.current_common
            else:
                common = config
                if selected is not None:
                    overrides.pop(selected, None)
            return FEPartialCurrentAnalysisSpec(
                current_common=common,
                current_overrides=overrides,
                pairs=self._analysis.pairs,
                analysis_range=self._read_range(),
            )
        if isinstance(self._analysis, GenericXYAnalysisSpec):
            return GenericXYAnalysisSpec(analysis_range=self._read_range())
        raise RuntimeError("no supported processing state is loaded")

    def _apply_draft_now(self) -> None:
        if self._loading or self._analysis is None:
            return
        try:
            candidate = self._build_analysis_spec()
        except (TypeError, ValueError) as exc:
            message = str(exc)
            self._set_draft_state(True, message)
            self._set_status(f"Not applied: {message}", "draft")
            return
        self._set_draft_state(False)
        if candidate == self._analysis:
            self._set_status("Settings valid", "success")
            return
        self.analysis_spec_changed.emit(candidate)

    def mark_commit_error(self, message: str) -> None:
        self._set_draft_state(True, message)
        self._set_status(f"Not applied: {message}", "error")

    def discard_draft(self) -> None:
        self._timer.stop()
        self._set_draft_state(False)
        self._load_controls()

    def _override_toggled(self, checked: bool) -> None:
        if self._loading:
            return
        if checked and not self._selected_supports_current_override():
            self._loading = True
            self.override_check.setChecked(False)
            self._loading = False
            return
        self._load_processing_fields_for_target()
        self._schedule_apply()

    def _current_processing_for_target(self) -> LSVProcessingSpec:
        selected = self._selected_data_id
        if isinstance(self._analysis, LSVAnalysisSpec):
            if self.override_check.isChecked() and selected is not None:
                return self._analysis.overrides.get(selected, self._analysis.common)
            return self._analysis.common
        if isinstance(self._analysis, FEPartialCurrentAnalysisSpec):
            if self.override_check.isChecked() and selected is not None:
                return self._analysis.current_overrides.get(
                    selected, self._analysis.current_common
                )
            return self._analysis.current_common
        return LSVProcessingSpec()

    @staticmethod
    def _set_text(widget: QLineEdit, value: float | None) -> None:
        widget.setText("" if value is None else f"{value:g}")

    def _load_processing_fields_for_target(self) -> None:
        if not isinstance(self._analysis, (LSVAnalysisSpec, FEPartialCurrentAnalysisSpec)):
            return
        previous_loading = self._loading
        self._loading = True
        try:
            config = self._current_processing_for_target()
            index = self.rhe_mode_combo.findData(config.rhe_mode)
            self.rhe_mode_combo.setCurrentIndex(max(0, index))
            self._set_text(self.rhe_offset_edit, config.rhe_offset_v)
            self._set_text(
                self.reference_she_edit,
                config.reference_potential_vs_she_v,
            )
            self._set_text(self.ph_edit, config.ph)
            self._set_text(self.temperature_edit, config.temperature_k)
            self._set_text(self.resistance_edit, config.resistance_ohm)
            self._set_text(self.fraction_edit, config.ir_correction_fraction)
            self._set_text(self.area_edit, config.electrode_area_cm2)
            self.normalize_check.setChecked(config.normalize_to_current_density)
            unit_index = self.current_density_unit_combo.findText(
                config.current_density_unit
            )
            self.current_density_unit_combo.setCurrentIndex(max(0, unit_index))
            self._update_rhe_visibility()
        finally:
            self._loading = previous_loading

    def _load_range(self) -> None:
        if self._analysis is None:
            return
        analysis_range = self._analysis.analysis_range
        self._set_text(self.range_min_edit, analysis_range.x_min)
        self._set_text(self.range_max_edit, analysis_range.x_max)

    def _update_rhe_visibility(self, *_args: object) -> None:
        mode = self.rhe_mode_combo.currentData()
        direct = mode == "direct"
        she_ph = mode == "she_ph"
        self.rhe_offset_edit.setEnabled(direct)
        self.reference_she_edit.setEnabled(she_ph)
        self.ph_edit.setEnabled(she_ph)
        self.temperature_edit.setEnabled(she_ph)

    def _refresh_pair_controls(self) -> None:
        self.current_pair_combo.clear()
        self.fe_pair_combo.clear()
        by_id = {spec.data_id: spec for spec in self._data_series}
        for spec in self._data_series:
            role = spec.mapping.y_role.casefold()
            if role in {"current", "current_density"}:
                self.current_pair_combo.addItem(spec.display_name, spec.data_id)
            if role == "faradaic_efficiency":
                self.fe_pair_combo.addItem(spec.display_name, spec.data_id)
        self.pair_list.clear()
        if not isinstance(self._analysis, FEPartialCurrentAnalysisSpec):
            return
        for pair in self._analysis.pairs:
            current = by_id.get(pair.current_data_id)
            fe = by_id.get(pair.fe_data_id)
            current_name = (
                current.display_name if current is not None else pair.current_data_id
            )
            fe_name = fe.display_name if fe is not None else pair.fe_data_id
            self.pair_list.addItem(f"{current_name} ↔ {fe_name}")
        self.add_pair_button.setEnabled(
            self.current_pair_combo.count() > 0 and self.fe_pair_combo.count() > 0
        )
        self.remove_pair_button.setEnabled(self.pair_list.count() > 0)

    def _add_pair(self) -> None:
        if not isinstance(self._analysis, FEPartialCurrentAnalysisSpec):
            return
        self._timer.stop()
        self._apply_draft_now()
        if self._has_unapplied_draft:
            return
        current_id = self.current_pair_combo.currentData()
        fe_id = self.fe_pair_combo.currentData()
        if not isinstance(current_id, str) or not isinstance(fe_id, str):
            return
        try:
            pair = PartialCurrentPair(current_id, fe_id)
            candidate = replace(self._analysis, pairs=(*self._analysis.pairs, pair))
        except (TypeError, ValueError) as exc:
            self.mark_commit_error(str(exc))
            return
        self.analysis_spec_changed.emit(candidate)

    def _remove_pair(self) -> None:
        if not isinstance(self._analysis, FEPartialCurrentAnalysisSpec):
            return
        row = self.pair_list.currentRow()
        if row < 0 or row >= len(self._analysis.pairs):
            return
        pairs = list(self._analysis.pairs)
        del pairs[row]
        self.analysis_spec_changed.emit(replace(self._analysis, pairs=tuple(pairs)))

    def set_selected_data_id(self, data_id: str | None) -> None:
        if data_id == self._selected_data_id:
            return
        self._selected_data_id = data_id
        self._timer.stop()
        self._set_draft_state(False)
        self._load_controls()

    def apply_state(self, state: AnalysisSessionState) -> None:
        document = state.document
        if document is None:
            self._analysis = None
            self._data_series = ()
            self._set_draft_state(False)
            self.setEnabled(False)
            self._set_status("No analysis", "empty")
            return
        previous_analysis = self._analysis
        self._analysis = document.analysis
        self._data_series = tuple(document.data_series)
        self.setEnabled(True)
        if not self._has_unapplied_draft or previous_analysis != self._analysis:
            self._load_controls()
        else:
            self._refresh_pair_controls()

    def _load_controls(self) -> None:
        if self._analysis is None:
            return
        self._loading = True
        try:
            scientific_current = isinstance(
                self._analysis,
                (LSVAnalysisSpec, FEPartialCurrentAnalysisSpec),
            )
            self.override_box.setVisible(scientific_current)
            self.potential_box.setVisible(scientific_current)
            self.ir_box.setVisible(scientific_current)
            self.current_box.setVisible(scientific_current)
            self.pair_box.setVisible(
                isinstance(self._analysis, FEPartialCurrentAnalysisSpec)
            )
            selected = self._selected_data_id
            override_present = False
            if isinstance(self._analysis, LSVAnalysisSpec) and selected is not None:
                override_present = selected in self._analysis.overrides
            elif (
                isinstance(self._analysis, FEPartialCurrentAnalysisSpec)
                and selected is not None
            ):
                override_present = selected in self._analysis.current_overrides
            enabled = self._selected_supports_current_override()
            self.override_check.setEnabled(enabled)
            self.override_check.setChecked(enabled and override_present)
            self.override_target_label.setText(
                "Selected-series override"
                if enabled and override_present
                else "Common settings"
            )
            self._load_processing_fields_for_target()
            self._load_range()
            self._refresh_pair_controls()
        finally:
            self._loading = False

    def set_evaluation_status(
        self,
        status: str,
        message: str | None = None,
        *,
        stale: bool = False,
    ) -> None:
        if self._has_unapplied_draft:
            return
        if stale:
            text = "Previous valid result — current settings are not applied"
            if message:
                text += f": {message}"
            self._set_status(text, "stale")
            return
        if status == "success":
            self._set_status("Ready · live analysis is current", "success")
        elif status == "incomplete":
            self._set_status(
                f"Needs input: {message or 'analysis is incomplete'}",
                "incomplete",
            )
        else:
            self._set_status(f"Error: {message or 'analysis failed'}", "error")


__all__ = ["ProcessingPanel"]
