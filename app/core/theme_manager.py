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
QTableView {
    background-color: #ffffff; alternate-background-color: #f0f0f3;
    gridline-color: #d1d1d6;
}
QHeaderView::section { background-color: #e5e5ea; padding: 4px; border: none; }
QSplitter::handle { background-color: #d1d1d6; }
QStatusBar { background-color: #e5e5ea; }
QLabel#statusIndicator {
    background-color: #e5e5ea; color: #6e6e73; border: 1px solid #d1d1d6;
    border-radius: 4px; padding: 2px 6px; margin: 2px;
}
QLabel#statusIndicator[ready="true"] {
    background-color: #dff7e8; color: #176b3a; border-color: #a8dfba;
}
QLabel#statusIndicator[ready="false"] {
    background-color: #ffe5e5; color: #a12626; border-color: #f0b0b0;
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
QTableView {
    background-color: #2c2c30; alternate-background-color: #252529;
    gridline-color: #3a3a3e;
}
QHeaderView::section { background-color: #2c2c30; color: #f5f5f7; padding: 4px; border: none; }
QSplitter::handle { background-color: #3a3a3e; }
QStatusBar { background-color: #2c2c30; color: #f5f5f7; }
QLabel#statusIndicator {
    background-color: #3a3a3e; color: #d1d1d6; border: 1px solid #54545a;
    border-radius: 4px; padding: 2px 6px; margin: 2px;
}
QLabel#statusIndicator[ready="true"] {
    background-color: #214b35; color: #b8f0c9; border-color: #397755;
}
QLabel#statusIndicator[ready="false"] {
    background-color: #542b2b; color: #ffc1c1; border-color: #824545;
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
        qss = LIGHT_QSS if self.current() == self.LIGHT else DARK_QSS
        app.setStyleSheet(qss)

    def toggle(self, app: QApplication) -> str:
        """Flip Light↔Dark, persist, reapply. Returns the new theme id."""
        new_theme = self.DARK if self.current() == self.LIGHT else self.LIGHT
        self._db.set_config(THEME, new_theme)
        self.apply(app)
        return new_theme
