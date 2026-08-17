"""Light/Dark QSS theme manager — DRY anchor per CLAUDE.md §2.

The two style sheets are intentionally short. Per CLAUDE.md, no fancy
templating — just well-named constants. Adding a theme = adding a constant
and an entry in the toggle.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from app.core.config import THEME
from app.database.db_manager import DBManager

LIGHT_QSS: str = """
QWidget { background-color: #f5f5f7; color: #1d1d1f; font-size: 10pt; }
QPlainTextEdit, QTextEdit, QLineEdit, QTextBrowser {
    background-color: #ffffff; color: #1d1d1f; border: 1px solid #d1d1d6;
    border-radius: 4px; padding: 4px;
}
QPushButton {
    background-color: #007aff; color: white; border: none;
    padding: 6px 12px; border-radius: 4px;
}
QPushButton:hover { background-color: #0a84ff; }
QPushButton:disabled { background-color: #a1c8ff; }
QPushButton[secondaryAction="true"] {
    background-color: transparent; color: #174a82; border: 1px solid #6f8bab;
    padding: 5px 8px;
}
QPushButton[secondaryAction="true"]:hover {
    background-color: #e0edff; border-color: #005fcc;
}
QPushButton[primaryAction="true"] {
    background-color: #005fcc; color: #ffffff; border: 2px solid #004a99;
    font-weight: 700;
}
QPushButton[primaryAction="true"]:hover { background-color: #004a99; }
QToolButton {
    background-color: transparent; color: #174a82; border: none;
    text-align: left; padding: 5px 2px; font-weight: 600;
}
QToolButton:hover { color: #005fcc; }
QTabWidget::pane { border: 1px solid #c1c8d2; background-color: #ffffff; }
QTabBar::tab {
    background-color: #e5eaf1; color: #24354a; padding: 7px 14px;
    border: 1px solid #c1c8d2; border-bottom: none;
}
QTabBar::tab:selected { background-color: #ffffff; color: #174a82; font-weight: 700; }
QTabBar::tab:selected { margin-bottom: -1px; }
MonacoEditor { border: none; background-color: #ffffff; }
QTableView {
    background-color: #ffffff; alternate-background-color: #f0f0f3;
    gridline-color: #d1d1d6;
}
QHeaderView::section { background-color: #e5e5ea; padding: 4px; border: none; }
QSplitter::handle { background-color: #d1d1d6; }
QScrollArea#pdfScroll { background-color: #e7edf5; border: 1px solid #c1c8d2; }
QLabel#pdfEmptyState {
    color: #31445d; background-color: transparent; font-weight: 600; padding: 24px;
}
QLabel[chatEmptyState="true"] { color: #4a5d73; background-color: transparent; }
QStatusBar { background-color: #e5e5ea; min-height: 24px; max-height: 28px; padding: 0 4px; }
QStatusBar::item { border: none; }
QMenuBar {
    background-color: #ffffff; color: #1d1d1f; padding: 6px 10px; spacing: 4px;
    border-bottom: 1px solid #d1d1d6;
}
QMenuBar::item { padding: 5px 10px; border-radius: 5px; }
QMenuBar::item:selected { background-color: #e5e5ea; }
QMenu {
    background-color: #ffffff; color: #1d1d1f; border: 1px solid #d1d1d6;
    padding: 4px;
}
QMenu::item { padding: 6px 24px 6px 10px; border-radius: 4px; }
QMenu::item:selected { background-color: #e5e5ea; }
QWidget#StartupScreen {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f5f5f7, stop:1 #e9eef8);
}
QScrollArea#categoriesScroll { background: transparent; border: none; }
QWidget#categoriesContainer { background: transparent; }
QLabel#titleLabel, QLabel#subtitleLabel { background: transparent; }
QScrollBar:vertical {
    background: transparent; width: 10px; margin: 2px;
}
QScrollBar::handle:vertical {
    background: #8296b0; min-height: 28px; border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal { height: 0px; }
QFrame[categoryCard="true"] {
    background-color: #ffffff; border: 2px solid #526b8a; border-radius: 14px;
}
QLabel[levelBadge="true"] { color: #173f78; background-color: #d6e6ff; border-radius: 10px; }
QPushButton[examEntry="true"] {
    background-color: #ffffff; color: #162234; border: 2px solid #5f7592;
    border-radius: 8px; text-align: left; padding: 4px 10px;
    min-height: 32px; font-weight: 600;
}
QPushButton[examEntry="true"]:hover { background-color: #d9e9ff; border-color: #005fcc; }
QPushButton[examEntry="true"]:focus { border: 3px solid #004ea8; }
QPushButton[examEntry="true"]:pressed { background-color: #bed8ff; }
QPushButton[examEntry="true"]:disabled {
    background-color: #e2e6ec; color: #626b78; border-color: #8793a3;
}
QLabel[statusIndicator="true"] {
    background-color: transparent; padding: 1px 6px; margin: 0;
    border-left: 1px solid #c1c8d2;
}
QLabel[statusIndicator="true"][ready="true"] {
    color: #176b3a;
}
QLabel[statusIndicator="true"][ready="false"] {
    color: #6e6e73;
}
QLabel#banner { background-color: #ffd60a; color: #1d1d1f; padding: 6px; }
"""

DARK_QSS: str = """
QWidget { background-color: #1e1e22; color: #f5f5f7; font-size: 10pt; }
QPlainTextEdit, QTextEdit, QLineEdit, QTextBrowser {
    background-color: #2c2c30; color: #f5f5f7; border: 1px solid #3a3a3e;
    border-radius: 4px; padding: 4px;
}
QPushButton {
    background-color: #0a84ff; color: white; border: none;
    padding: 6px 12px; border-radius: 4px;
}
QPushButton:hover { background-color: #409cff; }
QPushButton:disabled { background-color: #2c5e9c; }
QPushButton[secondaryAction="true"] {
    background-color: transparent; color: #c1d9f4; border: 1px solid #8ca8c8;
    padding: 5px 8px;
}
QPushButton[secondaryAction="true"]:hover {
    background-color: #3b4e63; border-color: #d0e5ff;
}
QPushButton[primaryAction="true"] {
    background-color: #0a84ff; color: #ffffff; border: 2px solid #77baff;
    font-weight: 700;
}
QPushButton[primaryAction="true"]:hover { background-color: #409cff; }
QToolButton {
    background-color: transparent; color: #c1d9f4; border: none;
    text-align: left; padding: 5px 2px; font-weight: 600;
}
QToolButton:hover { color: #ffffff; }
QTabWidget::pane { border: 1px solid #68788b; background-color: #303b4a; }
QTabBar::tab {
    background-color: #252e3a; color: #d0e5ff; padding: 7px 14px;
    border: 1px solid #68788b; border-bottom: none;
}
QTabBar::tab:selected { background-color: #303b4a; color: #ffffff; font-weight: 700; }
QTabBar::tab:selected { margin-bottom: -1px; }
MonacoEditor { border: none; background-color: #2c2c30; }
QTableView {
    background-color: #2c2c30; alternate-background-color: #252529;
    gridline-color: #3a3a3e;
}
QHeaderView::section { background-color: #2c2c30; color: #f5f5f7; padding: 4px; border: none; }
QSplitter::handle { background-color: #3a3a3e; }
QScrollArea#pdfScroll { background-color: #252e3a; border: 1px solid #68788b; }
QLabel#pdfEmptyState {
    color: #d7e2ef; background-color: transparent; font-weight: 600; padding: 24px;
}
QLabel[chatEmptyState="true"] { color: #d7e2ef; background-color: transparent; }
QStatusBar {
    background-color: #2c2c30; color: #f5f5f7; min-height: 24px;
    max-height: 28px; padding: 0 4px;
}
QStatusBar::item { border: none; }
QMenuBar {
    background-color: #2c2c30; color: #f5f5f7; padding: 6px 10px; spacing: 4px;
    border-bottom: 1px solid #54545a;
}
QMenuBar::item { padding: 5px 10px; border-radius: 5px; }
QMenuBar::item:selected { background-color: #3a3a3e; }
QMenu {
    background-color: #2c2c30; color: #f5f5f7; border: 1px solid #54545a;
    padding: 4px;
}
QMenu::item { padding: 6px 24px 6px 10px; border-radius: 4px; }
QMenu::item:selected { background-color: #3a3a3e; }
QWidget#StartupScreen {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1e1e22, stop:1 #242d3a);
}
QScrollArea#categoriesScroll { background: transparent; border: none; }
QWidget#categoriesContainer { background: transparent; }
QLabel#titleLabel, QLabel#subtitleLabel { background: transparent; }
QScrollBar:vertical {
    background: transparent; width: 10px; margin: 2px;
}
QScrollBar::handle:vertical {
    background: #6f8299; min-height: 28px; border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal { height: 0px; }
QFrame[categoryCard="true"] {
    background-color: #303b4a; border: 2px solid #a8c8ed; border-radius: 14px;
}
QLabel[levelBadge="true"] { color: #e5f1ff; background-color: #35587f; border-radius: 10px; }
QPushButton[examEntry="true"] {
    background-color: #465a70; color: #ffffff; border: 2px solid #c1d9f4;
    border-radius: 8px; text-align: left; padding: 4px 10px;
    min-height: 32px; font-weight: 600;
}
QPushButton[examEntry="true"]:hover { background-color: #52647a; border-color: #d0e5ff; }
QPushButton[examEntry="true"]:focus { border: 3px solid #d0e5ff; }
QPushButton[examEntry="true"]:pressed { background-color: #60758f; }
QPushButton[examEntry="true"]:disabled {
    background-color: #303945; color: #aeb9c7; border-color: #68788b;
}
QLabel[statusIndicator="true"] {
    background-color: transparent; padding: 1px 6px; margin: 0;
    border-left: 1px solid #54545a;
}
QLabel[statusIndicator="true"][ready="true"] {
    color: #b8f0c9;
}
QLabel[statusIndicator="true"][ready="false"] {
    color: #a1a1a6;
}
QLabel#banner { background-color: #ffd60a; color: #1d1d1f; padding: 6px; }
"""


class ThemeManager:
    """Apply and toggle the Light/Dark QSS theme; persist via DBManager."""

    LIGHT = "light"
    DARK = "dark"

    def __init__(self, db: DBManager) -> None:
        self._db = db

    def current(self) -> str:
        """Return the persisted theme id; defaults to LIGHT."""
        return self._db.get_config(THEME, self.LIGHT) or self.LIGHT

    def apply(self, app: QApplication) -> None:
        """Apply the current theme to a QApplication."""
        theme = self.current()
        qss = LIGHT_QSS if theme == self.LIGHT else DARK_QSS
        app.setProperty("ai_exam_tutor_theme", theme)
        app.setStyleSheet(qss)

    def toggle(self, app: QApplication) -> str:
        """Flip Light↔Dark, persist, reapply. Returns the new theme id."""
        new_theme = self.DARK if self.current() == self.LIGHT else self.LIGHT
        self._db.set_config(THEME, new_theme)
        self.apply(app)
        return new_theme
