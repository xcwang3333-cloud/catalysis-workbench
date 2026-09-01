"""Chinese presentation overlay for app-owned Figure Workbench canvas text."""

from __future__ import annotations

from matplotlib.font_manager import FontProperties, findfont
from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget


_CANVAS_TEXT = {
    "Create a figure from the current analysis result.": "从当前分析结果创建图形。",
}
_CJK_FONT_CANDIDATES = (
    "Microsoft YaHei",
    "PingFang SC",
    "Heiti SC",
    "Noto Sans CJK SC",
    "Noto Sans CJK JP",
    "SimHei",
    "Arial Unicode MS",
)


def _system_cjk_font() -> FontProperties | None:
    """Return an installed CJK-capable system font without shipping font files."""

    for family in _CJK_FONT_CANDIDATES:
        try:
            path = findfont(FontProperties(family=family), fallback_to_default=False)
        except ValueError:
            continue
        return FontProperties(fname=path)
    return None


class FigureCanvasLocalizer(QObject):
    """Translate only known app-owned Matplotlib placeholder text in v1.2."""

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        if not isinstance(window, QMainWindow):
            raise TypeError("window must be a QMainWindow")
        application = QApplication.instance()
        if application is None:
            raise RuntimeError("FigureCanvasLocalizer requires QApplication")
        self.window = window
        self.figure_page = window.figure_page
        self.application = application
        self.placeholder_font = _system_cjk_font()
        application.installEventFilter(self)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        if event.type() in {
            QEvent.Type.Paint,
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
        }:
            canvas = getattr(self.figure_page, "_canvas", None)
            if watched is canvas:
                self.refresh()
            elif watched is self.window and event.type() is QEvent.Type.Show:
                self.refresh()
        return super().eventFilter(watched, event)

    def refresh(self) -> None:
        """Translate known placeholder artists without changing scientific labels."""

        canvas = getattr(self.figure_page, "_canvas", None)
        if not isinstance(canvas, QWidget):
            return
        figure = getattr(canvas, "figure", None)
        if figure is None:
            return
        for axes in figure.axes:
            for artist in axes.texts:
                text = artist.get_text()
                translated = _CANVAS_TEXT.get(text)
                if translated is None:
                    continue
                artist.set_text(translated)
                if self.placeholder_font is not None:
                    artist.set_fontproperties(self.placeholder_font)


def install_figure_canvas_localization(window: QMainWindow) -> FigureCanvasLocalizer:
    """Install the v1.2-only Figure canvas localization overlay."""

    return FigureCanvasLocalizer(window)


__all__ = ["FigureCanvasLocalizer", "install_figure_canvas_localization"]
