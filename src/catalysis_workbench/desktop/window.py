"""Public desktop window with explicit dirty-state close protection."""

from __future__ import annotations

from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMessageBox

from .main_window import CatalysisWorkbenchMainWindow as _PresentationMainWindow


class CatalysisWorkbenchMainWindow(_PresentationMainWindow):
    """Presentation shell that cannot silently discard dirty application edits."""

    def _confirm_discard_edits(self) -> bool:
        state = self.session.state
        if not (state.recipe_dirty or state.figure_spec_dirty):
            return True
        result = QMessageBox.question(
            self,
            "Discard unsaved edits?",
            "Recipe or FigureSpec edits are unsaved. Exit and discard them?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt override
        """Require an explicit discard decision before closing dirty state."""

        if not self._confirm_discard_edits():
            event.ignore()
            return
        super().closeEvent(event)


__all__ = ["CatalysisWorkbenchMainWindow"]
