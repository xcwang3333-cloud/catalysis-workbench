"""Chinese-first presentation localization for the v1.2 product desktop.

The localization layer changes only user-facing Qt text. Scientific identifiers,
serialized values, user-entered names, FigureSpec values, and package semantics
remain unchanged.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QStatusBar,
    QWidget,
)

_TEXT = {
    # Shell and menus.
    "Home": "首页",
    "Data & Analysis": "数据与分析",
    "Figure": "图形",
    "Export": "导出",
    "File": "文件",
    "Edit": "编辑",
    "&View": "视图",
    "View": "视图",
    "Theme": "主题",
    "Navigation": "导航",
    "System": "跟随系统",
    "Light": "浅色",
    "Dark": "深色",
    "Toggle Navigation": "切换导航栏",
    "Open Project…": "打开项目…",
    "Save Project": "保存项目",
    "Add Data Files…": "添加数据文件…",
    "Exit": "退出",
    "Undo": "撤销",
    "Redo": "重做",
    "Save": "保存",
    "Modified": "已修改",
    "Ready": "就绪",
    "Unsaved changes": "有未保存修改",
    "Not saved yet": "尚未保存",
    "Saved": "已保存",
    "Unsaved analysis": "分析尚未保存",
    "Analysis current": "分析结果为最新",
    "Analysis needs valid processing state": "分析需要有效的处理参数",
    "Waiting for data": "等待数据",
    "Modified — save to update the project baseline": "已修改 — 保存以更新项目基线",
    # Home and New Analysis.
    "Start your analysis": "开始分析",
    (
        "Start a new scientific workflow or continue a recent project. "
        "A project directory is created only when you save."
    ): "开始新的科研分析，或继续最近的项目。只有保存时才会创建项目目录。",
    "New Analysis": "新建分析",
    "Recent Projects": "最近项目",
    "Your recently opened projects will appear here.": "最近打开的项目会显示在这里。",
    "Unavailable project": "项目不可用",
    "Unavailable": "不可用",
    "Open": "打开",
    "Remove": "移除",
    "Choose an analysis type": "选择分析类型",
    (
        "Select the scientific workflow that matches your data. "
        "You can add files after the analysis opens."
    ): "选择与数据匹配的科研工作流。进入分析后再添加数据文件。",
    "Start Analysis": "开始分析",
    (
        "LSV / Polarization\n"
        "Analyze polarization curves and electrochemical LSV data."
    ): "LSV / 极化曲线\n分析极化曲线和电化学 LSV 数据。",
    (
        "FE & Partial Current\n"
        "Analyze Faradaic efficiency and product partial-current data."
    ): "FE 与分电流\n分析法拉第效率（FE）与产物分电流数据。",
    (
        "Generic XY Plot\n"
        "Start a general two-column or multi-series XY analysis."
    ): "通用 XY 绘图\n用于通用双列或多序列 XY 数据分析。",
    "LSV / Polarization": "LSV / 极化曲线",
    "FE & Partial Current": "FE 与分电流",
    "Generic XY Plot": "通用 XY 绘图",
    # Data intake.
    "Import Data": "导入数据",
    "Edit data mapping": "编辑数据映射",
    "Review source data and mapping": "检查源数据与映射",
    (
        "Preview parser settings first, then explicitly map X and Y scientific "
        "meanings. Import never transforms the scientific values."
    ): "先检查解析设置，再明确映射 X 和 Y 的科学含义。导入过程不会修改科学数值。",
    "FILES": "文件",
    "PREVIEW": "预览",
    "MAPPING": "映射",
    (
        "Select a file to review. ✓ confirmed · ⚠ needs review · ✕ invalid"
    ): "选择文件进行检查。✓ 已确认 · ⚠ 待检查 · ✕ 无效",
    "Parser": "解析设置",
    "Excel sheet": "Excel 工作表",
    "Text delimiter": "文本分隔符",
    "Header row": "表头行",
    "Skip first rows": "跳过前几行",
    "Text encoding": "文本编码",
    "Reload Preview": "重新加载预览",
    "Scientific mapping": "科学映射",
    "Series name": "序列名称",
    "X column": "X 列",
    "X meaning": "X 物理量",
    "X unit": "X 单位",
    "X reference": "X 参比",
    "Y column": "Y 列",
    "Y meaning": "Y 物理量",
    "Y unit": "Y 单位",
    "Confirm this mapping": "确认当前映射",
    "Apply to compatible files": "应用到兼容文件",
    "Save mapping": "保存映射",
    "Add data": "添加数据",
    "Detected delimiter": "自动识别分隔符",
    "Optional, e.g. RHE": "可选，例如 RHE",
    "Preview unavailable": "预览不可用",
    (
        "Parser settings changed. Reload Preview before confirming this mapping."
    ): "解析设置已更改。请重新加载预览后再确认映射。",
    (
        "parser settings changed; reload preview before confirming"
    ): "解析设置已更改；请重新加载预览后再确认",
    "preview unavailable": "预览不可用",
    "Mapping confirmed": "映射已确认",
    "✓ Mapping confirmed": "✓ 映射已确认",
    "Review and confirm this mapping": "检查并确认此映射",
    "Review and confirm this mapping.": "请检查并确认此映射。",
    "choose a valid X column": "请选择有效的 X 列",
    "choose a valid Y column": "请选择有效的 Y 列",
    "X and Y columns must be different": "X 与 Y 列不能相同",
    # Analysis workspace.
    "Analysis title": "分析标题",
    "No analysis": "未打开分析",
    "DATA NAVIGATOR": "数据导航",
    "+ Add files": "+ 添加文件",
    (
        "Mapped scientific inputs. Rename or drag to reorder; mapping changes "
        "remain explicit."
    ): "已映射的科研数据。可重命名或拖动排序；映射修改始终需要明确确认。",
    "No mapped data yet": "尚未添加映射数据",
    "Edit mapping": "编辑映射",
    "Preview data": "预览数据",
    "Remove selected": "移除选中项",
    "No data selected.": "未选择数据。",
    "Mapped input": "已映射数据",
    "SCIENTIFIC CANVAS": "科学画布",
    "Raw": "原始数据",
    "Processed": "处理后",
    "Partial current density": "分电流密度",
    "Add mapped data to begin live scientific analysis.": "添加映射数据后开始实时科学分析。",
    "Continue to Figure": "进入图形编辑",
    "PROCESSING INSPECTOR": "处理参数",
    "Previous valid result": "上一份有效结果",
    "Needs input": "需要输入",
    "Analysis error": "分析错误",
    "analysis is incomplete": "分析尚不完整",
    "live analysis failed": "实时分析失败",
    "Add and map at least one data series to run the analysis.":
        "请添加并映射至少一个数据序列后再运行分析。",
    "Add at least one explicit current ↔ FE pair.": "请至少添加一组明确的电流 ↔ FE 配对。",
    (
        "Mapped raw values · display sampling only for large series; "
        "scientific data are unchanged."
    ): "已映射原始数据 · 大数据序列仅对显示进行抽样；科学数据保持不变。",
    (
        "Live scientific result · FE and partial current use separate "
        "views and no interpolation."
    ): "实时科学结果 · FE 与分电流使用独立视图，不进行插值。",
    (
        "Live scientific result · committed processing settings are current."
    ): "实时科学结果 · 当前已应用的处理参数为最新。",
    # Processing inspector. Scientific abbreviations and units remain unchanged.
    (
        "Scientific settings commit only after validation. Invalid fields stay "
        "outside the document and preserve the previous valid result."
    ): "科学参数仅在验证通过后应用。无效输入不会写入项目，并会保留上一份有效结果。",
    "Apply to": "应用范围",
    "Override selected series": "覆盖选中序列",
    "Common settings": "通用设置",
    "Selected-series override": "选中序列独立设置",
    "Potential": "电位",
    "No RHE conversion": "不进行 RHE 转换",
    "Direct RHE offset": "直接设置 RHE 偏移",
    "Reference vs SHE + pH": "参比电位 vs SHE + pH",
    "Convert to RHE": "转换为 RHE",
    "RHE offset (V)": "RHE 偏移 (V)",
    "Reference vs SHE (V)": "参比电位 vs SHE (V)",
    "Temperature (K)": "温度 (K)",
    "iR correction": "iR 校正",
    "Resistance (Ω)": "电阻 (Ω)",
    "Correction fraction": "校正比例",
    "Current density": "电流密度",
    "Normalize total current by electrode area": "按电极面积归一化总电流",
    "Electrode area (cm²)": "电极面积 (cm²)",
    "Output unit": "输出单位",
    "FE ↔ current pairs": "FE ↔ 电流配对",
    "Current series": "电流序列",
    "FE series": "FE 序列",
    "Add explicit pair": "添加明确配对",
    "Remove selected pair": "移除选中配对",
    "Analysis range": "分析范围",
    "From": "起始",
    "To": "终止",
    "blank = off": "留空 = 关闭",
    "blank = no lower bound": "留空 = 无下限",
    "blank = no upper bound": "留空 = 无上限",
    "Settings valid": "参数有效",
    "Ready · live analysis is current": "就绪 · 实时分析结果为最新",
    "<none>": "<无>",
    # Figure Workbench.
    "CONTENT": "内容",
    "PUBLICATION CANVAS": "出版画布",
    "PUBLICATION PREVIEW": "出版预览",
    "PROPERTIES": "属性",
    "Result": "结果",
    "Preset": "预设",
    "Create figure from this result": "从当前结果创建图形",
    "Refresh from Analysis": "从分析结果刷新",
    "Reset styling": "重置样式",
    "Traces": "曲线",
    "Presentation preview": "图形预览",
    "Create a figure": "创建图形",
    "Create a figure from the current analysis result.": "从当前分析结果创建图形。",
    "Analysis changed": "分析结果已变化",
    "Current · unsaved changes": "当前 · 有未保存修改",
    "Figure current": "图形为最新",
    "Preview needs attention": "预览需要处理",
    "Continue to Export": "进入导出",
    "Axis / display range": "坐标轴 / 显示范围",
    "Title": "标题",
    "Width (in)": "宽度 (in)",
    "Height (in)": "高度 (in)",
    "X label": "X 轴标签",
    "Y label": "Y 轴标签",
    "X display": "X 显示范围",
    "Y display": "Y 显示范围",
    "X scale": "X 轴尺度",
    "Y scale": "Y 轴尺度",
    "Unit style": "单位格式",
    "Label (unit)": "标签 (单位)",
    "Label / unit": "标签 / 单位",
    "Label only": "仅标签",
    "Legend": "图例",
    "Visibility": "显示状态",
    "Location": "位置",
    "Show": "显示",
    "Hide": "隐藏",
    "Typography": "字体",
    "Font family": "字体",
    "Axis label size": "轴标题字号",
    "Tick size": "刻度字号",
    "Legend size": "图例字号",
    "Selected trace": "选中曲线",
    "Label": "标签",
    "Color": "颜色",
    "Choose…": "选择…",
    "Line style": "线型",
    "Line width": "线宽",
    "Marker": "标记",
    "Marker size": "标记大小",
    "Auto": "自动",
    "Trace color": "曲线颜色",
    "No figure draft for this result": "当前结果尚未创建图形",
    "Analysis changed — refresh this figure": "分析结果已变化 — 请刷新图形",
    (
        "Publication preview · display range and styling do not modify scientific arrays."
    ): "出版预览 · 显示范围和样式不会修改科学数据。",
    # Export.
    "Export Figure Package": "导出图包",
    (
        "Validate the current publication figure, choose package contents, "
        "and export to a new directory."
    ): "检查当前出版图形，选择导出内容，并导出到新的目录。",
    "Waiting for export preflight": "等待导出检查",
    "Ready to export": "可以导出",
    "Exporting package…": "正在导出图包…",
    "Package exported": "图包已导出",
    "Export needs attention": "导出需要处理",
    "SUMMARY": "摘要",
    "CONTENTS": "内容",
    "FIGURE FILES": "图形文件",
    "SOURCE DATA": "源数据",
    "DESTINATION": "目标位置",
    "PREFLIGHT": "导出前检查",
    "RESULT": "结果",
    "Status": "状态",
    "No figure": "尚无图形",
    "Not ready": "未就绪",
    "Up to date": "已是最新",
    "Needs attention": "需要处理",
    "Package location": "图包位置",
    "Choose a new package directory": "选择新的图包目录",
    "Browse…": "浏览…",
    "○ Project saved": "○ 项目已保存",
    "✓ Project saved and clean": "✓ 项目已保存且无未保存修改",
    "✕ Save the project before export": "✕ 导出前请先保存项目",
    "○ Figure current": "○ 图形为最新",
    "✓ Figure current": "✓ 图形为最新",
    "✕ Refresh the Figure from Analysis": "✕ 请从分析结果刷新图形",
    "○ Font available": "○ 字体可用",
    "✓ Font available": "✓ 字体可用",
    "✕ Figure font unavailable": "✕ 图形字体不可用",
    "○ Visible traces": "○ 可见曲线",
    "✕ At least one visible trace is required": "✕ 至少需要一条可见曲线",
    "○ Destination available": "○ 目标位置可用",
    "✓ Destination available": "✓ 目标位置可用",
    (
        "✕ Destination must be a new directory with an existing parent"
    ): "✕ 目标位置必须是位于现有父目录下的新目录",
    "Export Package": "导出图包",
    "Open Folder": "打开文件夹",
    "Export Another": "继续导出",
    "Resolve preflight checks": "请先通过导出前检查",
    "Choose at least one figure format": "至少选择一种图形格式",
    "Choose at least one source-data format": "至少选择一种源数据格式",
    "Choose a destination": "请选择目标位置",
    "Choose a new available destination": "请选择新的可用目标位置",
    "Export is waiting for preflight": "等待导出前检查",
    "Export ready": "可以导出",
    "Exporting Figure Package…": "正在导出图包…",
    "Figure Package exported": "图包已导出",
    # Common dialog decisions.
    "Save changes?": "保存修改？",
    "Save changes before leaving this analysis?": "离开当前分析前是否保存修改？",
    (
        "Save keeps the current edits. Discard closes without saving. "
        "Cancel keeps the current analysis open."
    ): "保存会保留当前修改；放弃将不保存并关闭；取消则继续保留当前分析。",
    "Discard unapplied settings?": "放弃未应用的参数？",
    (
        "Current processing fields are invalid and have not been applied."
    ): "当前处理参数无效，因此尚未应用。",
    (
        "Discard removes only the unapplied field values. "
        "Cancel keeps them for editing."
    ): "放弃仅移除尚未应用的输入；取消可继续编辑这些参数。",
    "Remove data?": "移除数据？",
    "The original raw file is not modified.": "原始数据文件不会被修改。",
    "Discard": "放弃",
    "Cancel": "取消",
    "OK": "确定",
    "Ok": "确定",
    "Show Details...": "显示技术详情…",
    "Hide Details...": "隐藏技术详情…",
    # Cross-page status language.
    "Create a publication figure": "创建出版图形",
    "Figure needs refresh from Analysis": "图形需要从分析结果刷新",
    "Figure preview needs attention": "图形预览需要处理",
}

_PREFIXES = (
    ("Not applied: ", "未应用："),
    ("Needs input: ", "需要输入："),
    ("Error: ", "错误："),
    ("Analysis error: ", "分析错误："),
    ("Invalid presentation value: ", "无效的图形参数："),
    ("Package exported successfully:\n", "图包已成功导出：\n"),
    (
        "Previous valid result — current settings are not applied",
        "上一份有效结果 — 当前参数尚未应用",
    ),
)

_TRACE_RE = re.compile(r"^✓ (\d+) visible trace\(s\)$")
_REMOVE_RE = re.compile(r"^Remove (.+) from this analysis\?$")
_SERIES_STATUS_RE = re.compile(
    r"^(\d+) mapped series(?: · (Unsaved changes|Not saved yet|Saved))?$"
)
_PREVIEW_ROWS_RE = re.compile(
    r"^(\d+) preview rows · (\d+) columns(?: · (preview truncated))?$"
)
_MAPPING_COUNT_RE = re.compile(
    r"^(\d+) of (\d+) mappings confirmed(?: · (\d+) require attention)?$"
)


def translate_ui_text(text: str) -> str:
    """Translate one app-owned presentation string without touching symbols/IDs."""

    if not text:
        return text
    translated = _TEXT.get(text)
    if translated is not None:
        return translated

    match = _SERIES_STATUS_RE.match(text)
    if match is not None:
        count, storage = match.groups()
        result = f"已映射 {count} 个序列"
        if storage:
            result += f" · {_TEXT[storage]}"
        return result

    match = _TRACE_RE.match(text)
    if match is not None:
        return f"✓ 可见曲线：{match.group(1)} 条"

    match = _PREVIEW_ROWS_RE.match(text)
    if match is not None:
        rows, columns, truncated = match.groups()
        result = f"预览 {rows} 行 · {columns} 列"
        if truncated:
            result += " · 预览已截断"
        return result

    match = _MAPPING_COUNT_RE.match(text)
    if match is not None:
        confirmed, total, attention = match.groups()
        result = f"已确认 {confirmed}/{total} 个映射"
        if attention:
            result += f" · {attention} 个需要处理"
        return result

    match = _REMOVE_RE.match(text)
    if match is not None:
        return f"从当前分析中移除 {match.group(1)}？"

    if text in {"Figure up to date", "Figure up to date · Unsaved changes"}:
        return (
            "图形为最新 · 有未保存修改"
            if "Unsaved changes" in text
            else "图形为最新"
        )

    if "\nX: column " in text and "\nY: column " in text:
        result = re.sub(r"\nX: column (\d+) →", r"\nX：第 \1 列 →", text)
        result = re.sub(r"\nY: column (\d+) →", r"\nY：第 \1 列 →", result)
        return result.replace(" · ref ", " · 参比 ")

    for english, chinese in _PREFIXES:
        if text.startswith(english):
            suffix = text[len(english) :]
            translated_suffix = _TEXT.get(suffix, suffix)
            return chinese + translated_suffix
    return text


class ChineseUiLocalizer(QObject):
    """Apply Chinese-first text only after the v1.2 window becomes visible."""

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        if not isinstance(window, QMainWindow):
            raise TypeError("window must be a QMainWindow")
        self.window = window
        self._active = False
        self._refresh_pending = False
        application = QApplication.instance()
        if application is None:
            raise RuntimeError("ChineseUiLocalizer requires QApplication")
        self.application = application
        application.installEventFilter(self)

    @property
    def active(self) -> bool:
        return self._active

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        event_type = event.type()
        if watched is self.window and event_type is QEvent.Type.Show:
            self._active = True
            self.request_refresh()
        elif self._active and event_type in {
            QEvent.Type.Show,
            QEvent.Type.LayoutRequest,
        }:
            if isinstance(watched, QWidget) and self._belongs_to_product(watched):
                self.request_refresh()
        return super().eventFilter(watched, event)

    def _belongs_to_product(self, widget: QWidget) -> bool:
        current: QWidget | None = widget
        while current is not None:
            if current is self.window:
                return True
            current = current.parentWidget()
        return False

    def request_refresh(self) -> None:
        if not self._active or self._refresh_pending:
            return
        self._refresh_pending = True
        QTimer.singleShot(0, self._run_scheduled_refresh)

    def _run_scheduled_refresh(self) -> None:
        self._refresh_pending = False
        self.refresh()

    def refresh(self) -> None:
        """Translate all currently materialized v1.2 presentation widgets."""

        if not self._active:
            return
        self._localize_shell_identity()
        self._localize_widget(self.window)
        for widget in self.window.findChildren(QWidget):
            self._localize_widget(widget)
        for action in self.window.findChildren(QAction):
            self._set_action_text(action)
        self._localize_special_controls()

        shell = getattr(self.window, "app_shell", None)
        status_bar = getattr(shell, "status_bar", None)
        if isinstance(status_bar, QStatusBar):
            message = status_bar.currentMessage()
            translated = translate_ui_text(message)
            if translated != message:
                status_bar.showMessage(translated)

    def _localize_shell_identity(self) -> None:
        shell = getattr(self.window, "app_shell", None)
        if shell is None:
            return
        sidebar = shell.sidebar
        labels = {
            "home": "首页",
            "analysis": "数据与分析",
            "figure": "图形",
            "export": "导出",
        }
        for page_id, label in labels.items():
            if page_id not in sidebar._labels:
                continue
            sidebar._labels[page_id] = label
            button = sidebar._buttons[page_id]
            if sidebar.is_compact:
                button.setToolTip(label)
            else:
                if button.text() != label:
                    button.setText(label)
                button.setToolTip("")

        command = shell.command_bar
        document = self.window.session.state.document
        if document is None and command.project_title.text() in {"Home", "首页"}:
            command.project_title.setText("首页")
        command.task_pill.setText(translate_ui_text(command.task_pill.text()))
        command.dirty_pill.setText("已修改")

    def _localize_widget(self, widget: QWidget) -> None:
        if isinstance(widget, QMenu):
            title = widget.title()
            translated = translate_ui_text(title)
            if translated != title:
                widget.setTitle(translated)

        if widget.isWindow():
            title = widget.windowTitle()
            translated = translate_ui_text(title)
            if translated != title:
                widget.setWindowTitle(translated)

        if isinstance(widget, QGroupBox):
            title = widget.title()
            translated = translate_ui_text(title)
            if translated != title:
                widget.setTitle(translated)

        if isinstance(widget, QAbstractButton):
            text = widget.text()
            translated = translate_ui_text(text)
            if translated != text:
                widget.setText(translated)

        if isinstance(widget, QLabel):
            excluded = {"cwProjectTitle", "cwRecentProjectTitle", "cwPathText"}
            if widget.objectName() not in excluded:
                text = widget.text()
                translated = translate_ui_text(text)
                if translated != text:
                    widget.setText(translated)

        if isinstance(widget, QLineEdit):
            placeholder = widget.placeholderText()
            translated = translate_ui_text(placeholder)
            if translated != placeholder:
                widget.setPlaceholderText(translated)

        if isinstance(widget, QComboBox):
            # Only localize labels backed by stable itemData. Some combos use
            # currentText() as a scientific/serialized value and must stay English.
            for index in range(widget.count()):
                if widget.itemData(index) is None:
                    continue
                text = widget.itemText(index)
                translated = translate_ui_text(text)
                if translated != text:
                    widget.setItemText(index, translated)

        tooltip = widget.toolTip()
        translated_tooltip = translate_ui_text(tooltip)
        if translated_tooltip != tooltip:
            widget.setToolTip(translated_tooltip)

    def _localize_special_controls(self) -> None:
        figure = getattr(self.window, "figure_page", None)
        if figure is not None:
            # Legend visibility is semantically backed by currentData(), including
            # the automatic None value, so all three display labels are safe to localize.
            legend_combo = getattr(figure, "legend_combo", None)
            if isinstance(legend_combo, QComboBox):
                for index in range(legend_combo.count()):
                    text = legend_combo.itemText(index)
                    translated = translate_ui_text(text)
                    if translated != text:
                        legend_combo.setItemText(index, translated)

            # The empty Figure canvas is Matplotlib-rendered rather than a Qt label.
            # Re-render only when the retained draft is absent and the placeholder
            # itself has an exact presentation translation.
            if getattr(figure, "draft", None) is None:
                note = figure.preview_note.text()
                translated_note = translate_ui_text(note)
                if translated_note != note:
                    figure.set_preview_message(translated_note)

    @staticmethod
    def _set_action_text(action: QAction) -> None:
        text = action.text()
        translated = translate_ui_text(text)
        if translated != text:
            action.setText(translated)
        status_tip = action.statusTip()
        translated_tip = translate_ui_text(status_tip)
        if translated_tip != status_tip:
            action.setStatusTip(translated_tip)


def install_chinese_localization(window: QMainWindow) -> ChineseUiLocalizer:
    """Install Chinese-first localization on the v1.2 product window only."""

    return ChineseUiLocalizer(window)


__all__ = ["ChineseUiLocalizer", "install_chinese_localization", "translate_ui_text"]
