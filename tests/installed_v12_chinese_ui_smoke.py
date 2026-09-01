"""Fresh-wheel smoke for the Chinese-first v1.2 presentation layer."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path


def main() -> None:
    desktop_app = importlib.import_module("catalysis_workbench.desktop.app")
    localization = importlib.import_module(
        "catalysis_workbench.desktop.desktop_localization"
    )
    recent_module = importlib.import_module("catalysis_workbench.desktop.recent_projects")
    ui_module = importlib.import_module("catalysis_workbench.desktop.ui_foundation")
    qtcore = importlib.import_module("PySide6.QtCore")

    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        settings = qtcore.QSettings(
            str(base / "settings.ini"),
            qtcore.QSettings.Format.IniFormat,
        )
        handle = desktop_app.create_workbench_desktop(
            argv=("cw-v12-chinese-ui-smoke",),
            recent_store=recent_module.RecentProjectsStore(settings),
            ui_settings=ui_module.DesktopUiSettings(settings),
        )
        window = handle.window
        app = handle.application
        localizer = window.v12_localizer
        assert isinstance(localizer, localization.ChineseUiLocalizer)
        assert not localizer.active

        # Compatibility constructors and pre-show tests keep the retained English
        # widget source text. Chinese is a v1.2 visible presentation overlay.
        assert window.home_page.headline_label.text() == "Start your analysis"
        window.show()
        app.processEvents()
        app.processEvents()
        assert localizer.active

        shell = window.app_shell
        home = window.home_page
        assert shell.sidebar._buttons["home"].text() == "首页"
        assert shell.sidebar._buttons["analysis"].text() == "数据与分析"
        assert shell.sidebar._buttons["figure"].text() == "图形"
        assert shell.sidebar._buttons["export"].text() == "导出"
        assert home.headline_label.text() == "开始分析"
        assert home.new_analysis_button.text() == "新建分析"
        assert home.open_project_button.text() == "打开项目…"
        assert home.empty_state_label is not None
        assert home.empty_state_label.text() == "最近打开的项目会显示在这里。"

        dialog = home.new_analysis_dialog
        dialog.show()
        app.processEvents()
        app.processEvents()
        assert dialog.windowTitle() == "新建分析"
        assert "LSV / 极化曲线" in home.task_buttons["lsv"].text()
        fe_text = home.task_buttons["fe_partial_current"].text()
        assert "FE 与分电流" in fe_text
        assert "&" not in fe_text
        assert "通用 XY 绘图" in home.task_buttons["generic_xy"].text()
        dialog.hide()

        window.start_analysis("lsv")
        app.processEvents()
        app.processEvents()
        analysis = window.analysis_page
        assert analysis.title_edit.text() == "Untitled LSV analysis"
        assert analysis.add_files_button.text() == "+ 添加文件"
        assert analysis.processing_panel.potential_box.title() == "电位"
        assert analysis.processing_panel.ir_box.title() == "iR 校正"
        assert analysis.processing_panel.current_box.title() == "电流密度"
        assert analysis.processing_panel.range_box.title() == "分析范围"
        assert analysis.processing_panel.rhe_mode_combo.itemText(0) == "不进行 RHE 转换"
        assert analysis.processing_panel.rhe_mode_combo.itemData(0) == "none"
        assert analysis.processing_panel.current_density_unit_combo.itemText(0) == "mA/cm^2"
        assert analysis.processing_panel.ph_edit.parent() is not None

        # User-owned titles are never translated.
        window.rename_analysis("Home")
        app.processEvents()
        app.processEvents()
        assert window.session.state.document is not None
        assert window.session.state.document.title == "Home"
        assert shell.command_bar.project_title.text() == "Home"

        # Hidden Figure/Export pages are localized too, but semantic combo values
        # used by FigureSpec remain unchanged.
        localizer.refresh()
        figure = window.figure_page
        export = window.export_page
        assert figure.create_button.text() == "从当前结果创建图形"
        assert figure.preset_combo.itemText(0) == "publication"
        assert export.title_label.text() == "导出图包"
        assert export.svg_check.text() == "SVG"
        assert export.pdf_check.text() == "PDF"
        assert export.png_check.text() == "PNG"
        assert export.xlsx_check.text() == "XLSX"
        assert export.txt_check.text() == "TXT"

        # Scientific symbols and common units are intentionally not localized.
        assert localization.translate_ui_text("RHE") == "RHE"
        assert localization.translate_ui_text("SHE") == "SHE"
        assert localization.translate_ui_text("pH") == "pH"
        assert localization.translate_ui_text("mA/cm^2") == "mA/cm^2"
        assert localization.translate_ui_text("Ω") == "Ω"

        # Accessibility metadata stays stable in this focused presentation change.
        assert shell.accessibleName() == "CatalysisWorkbench application shell"
        assert shell.sidebar.accessibleName() == "Primary navigation"

        window.go_home(discard_changes=True)
        window.close()
        app.processEvents()

    print("installed v1.2 Chinese UI smoke: ok")


if __name__ == "__main__":
    main()
