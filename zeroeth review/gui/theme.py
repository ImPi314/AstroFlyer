"""
AstroFlyer HEO Studio - Native Desktop GUI Theme & Styling Configuration
AstroFlyer HEO Dark Operations Theme:
- Dark Aerospace Canvas (#1e1e1e Window, #161616 Cards & Docks, #252526 Toolbars)
- High-Efficiency VCR Execution Strip (Run F5, Pause F6, Stop Shift+F5, Step F10)
- 48px Left Activity Rail & Collapsible Object Browser Tree
- Dynamic Watch Window with Flight Regime Badges (Lime, Red, Purple, Amber)
- Consistent Aerospace Cyan & Sky Blue Highlights (#00e5ff / #0284c7)
"""

THEME_DARK = """
/* Global Reset & Consistent High-Contrast Aerospace Selection */
* {
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

QWidget {
    background-color: #1e1e1e;
    color: #e4e4e7;
    font-family: 'Roboto', 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 11px;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

QMainWindow {
    background-color: #1e1e1e;
}

/* Top Menu Bar */
QMenuBar {
    background-color: #252526;
    color: #e4e4e7;
    border-bottom: 1px solid #3f3f46;
    padding: 2px 6px;
    font-weight: 500;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    border-radius: 3px;
    color: #d4d4d8;
}

QMenuBar::item:selected {
    background-color: #3f3f46;
    color: #ffffff;
}

QMenu {
    background-color: #252526;
    color: #e4e4e7;
    border: 1px solid #3f3f46;
    padding: 4px;
    border-radius: 4px;
}

QMenu::item {
    padding: 5px 22px 5px 12px;
    border-radius: 3px;
    color: #d4d4d8;
}

QMenu::item:selected {
    background-color: #0284c7;
    color: #ffffff;
}

QMenu::separator {
    height: 1px;
    background-color: #3f3f46;
    margin: 4px 2px;
}

/* VCR Toolbar & Execution Console */
QToolBar {
    background-color: #161616;
    border-bottom: 1px solid #3f3f46;
    padding: 3px 8px;
    spacing: 5px;
}

QToolButton {
    background-color: #262626;
    color: #ffffff;
    border: 1px solid #3f3f46;
    border-radius: 3px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 11px;
}

QToolButton:hover {
    background-color: #333333;
    border-color: #00e5ff;
    color: #00e5ff;
}

QToolButton:pressed {
    background-color: #0369a1;
    border-color: #00e5ff;
    color: #ffffff;
}

/* Dock Widgets (Object Browser & Watch Window) */
QDockWidget {
    color: #ffffff;
    font-weight: 700;
    font-size: 11px;
}

QDockWidget::title {
    background-color: #161616;
    padding: 6px 10px;
    border: 1px solid #3f3f46;
    border-bottom: 2px solid #00e5ff;
    font-size: 11px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 0.5px;
}

/* Cards & Group Boxes (Surface Panels) */
QGroupBox {
    background-color: #262626;
    border: 1px solid #3f3f46;
    border-radius: 4px;
    margin-top: 12px;
    padding-top: 12px;
    padding-bottom: 8px;
    padding-left: 8px;
    padding-right: 8px;
    font-weight: 700;
    color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 1px 6px;
    background-color: #262626;
    color: #00e5ff;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.5px;
    border: 1px solid #3f3f46;
    border-radius: 3px;
}

/* Form Controls: LineEdits, ComboBoxes, SpinBoxes */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {
    background-color: #18181b;
    color: #ffffff;
    border: 1px solid #3f3f46;
    border-radius: 3px;
    padding: 4px 6px;
    font-family: 'Cascadia Code', Consolas, monospace;
    font-size: 11px;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border: 1px solid #00e5ff;
    background-color: #141416;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 18px;
    border-left: 1px solid #3f3f46;
}

/* Dynamic Watch Window Table & Tree */
QTreeWidget, QTableWidget, QTableView, QTreeView {
    background-color: #161616;
    alternate-background-color: #1e1e1e;
    color: #e4e4e7;
    border: 1px solid #3f3f46;
    gridline-color: #2e2e2e;
    font-family: 'Cascadia Code', Consolas, monospace;
    font-size: 11px;
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

QHeaderView::section {
    background-color: #1a1a1a;
    color: #a1a1aa;
    font-weight: 700;
    font-size: 10px;
    padding: 5px;
    border: 1px solid #2e2e2e;
    text-transform: uppercase;
}

/* Status Bar */
QStatusBar {
    background-color: #161616;
    color: #a1a1aa;
    border-top: 1px solid #3f3f46;
    font-family: 'Cascadia Code', Consolas, monospace;
    font-size: 10px;
    padding: 2px 8px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 4px;
    background: #3f3f46;
    border-radius: 2px;
}

QSlider::sub-page:horizontal {
    background: #00e5ff;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background: #ffffff;
    border: 1px solid #00e5ff;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}

QSlider::handle:horizontal:hover {
    background: #00e5ff;
}

/* Tab Bar */
QTabWidget::pane {
    border: 1px solid #3f3f46;
    background-color: #1e1e1e;
}

QTabBar::tab {
    background-color: #161616;
    color: #a1a1aa;
    border: 1px solid #3f3f46;
    border-bottom: none;
    padding: 5px 12px;
    font-weight: 600;
    font-size: 11px;
    border-top-left-radius: 3px;
    border-top-right-radius: 3px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #1e1e1e;
    color: #00e5ff;
    border-top: 2px solid #00e5ff;
}

QTabBar::tab:hover {
    background-color: #262626;
    color: #ffffff;
}

/* Custom Scrollbars */
QScrollBar:vertical {
    border: none;
    background-color: #161616;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background-color: #3f3f46;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00e5ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background-color: #161616;
    height: 8px;
    margin: 0px;
}

QScrollBar::handle:horizontal {
    background-color: #3f3f46;
    border-radius: 4px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #00e5ff;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""

THEME_LIGHT = """
/* Light Mode Theme */
* {
    selection-background-color: #0284c7;
    selection-color: #ffffff;
}

QWidget {
    background-color: #f1f5f9;
    color: #0f172a;
    font-family: 'Roboto', 'Segoe UI', -apple-system, sans-serif;
    font-size: 11px;
}

QMainWindow {
    background-color: #f8fafc;
}

QMenuBar {
    background-color: #cbd5e1;
    color: #0f172a;
    border-bottom: 1px solid #94a3b8;
}

QMenuBar::item:selected {
    background-color: #94a3b8;
}

QToolBar {
    background-color: #e2e8f0;
    border-bottom: 1px solid #cbd5e1;
}

QToolButton {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
}

QDockWidget::title {
    background-color: #e2e8f0;
    color: #0f172a;
    border-bottom: 2px solid #0284c7;
}

QTreeWidget, QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f8fafc;
    color: #0f172a;
    gridline-color: #e2e8f0;
}

QStatusBar {
    background-color: #e2e8f0;
    color: #475569;
}
"""

ASTROFLYER_STYLESHEET = THEME_DARK
