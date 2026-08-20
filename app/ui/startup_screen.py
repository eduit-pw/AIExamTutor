"""Startup exam selector loaded from a Qt Designer .ui file."""

from __future__ import annotations

from importlib import resources

from PySide6.QtCore import Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QFrame, QMenu, QPushButton, QSizePolicy, QWidget

from app.core.exam_catalog import EXAM_ENTRIES, ExamEntry
from app.core.localization import translate


class StartupScreen(QWidget):
    """Let the student choose an available exam subject."""

    exam_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._root = self._load_ui()
        self._wire_exam_buttons()

    def _load_ui(self) -> QWidget:
        loader = QUiLoader()
        with resources.as_file(
            resources.files("app.ui.views").joinpath("StartupScreen.ui")
        ) as ui_path:
            root = loader.load(str(ui_path), self)
        if root is None:
            raise RuntimeError("QUiLoader returned None for StartupScreen.ui")
        for card_name in ("e8Card", "maturaCard", "vocationalCard"):
            card = root.findChild(QFrame, card_name)
            if card is not None:
                card.setFixedHeight(440)
                card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = self.layout()
        if layout is None:
            from PySide6.QtWidgets import QVBoxLayout

            layout = QVBoxLayout(self)
        layout.addWidget(root)
        return root

    def _wire_exam_buttons(self) -> None:
        entries_by_button: dict[str, list[ExamEntry]] = {}
        for entry in EXAM_ENTRIES:
            entries_by_button.setdefault(self.button_name(entry), []).append(entry)

        for button_name, entries in entries_by_button.items():
            button = self._root.findChild(QPushButton, button_name)
            if button is None:
                raise LookupError(f"StartupScreen.ui missing {button_name!r}")
            available_entries = [entry for entry in entries if entry.is_available]
            button.setEnabled(bool(available_entries))
            button.setToolTip(
                translate(
                    "StartupScreen",
                    "Choose an exam level" if len(available_entries) > 1 else "Open this exam",
                )
                if available_entries
                else translate(
                    "StartupScreen",
                    "This subject will be available in a future version.",
                )
            )
            if len(available_entries) == 1:
                button.clicked.connect(
                    lambda _checked=False, item=available_entries[0]: self._select(item)
                )
            elif len(available_entries) > 1:
                button.clicked.connect(
                    lambda _checked=False, target=button, items=available_entries:
                    self._choose_level(target, items)
                )

    @staticmethod
    def button_name(entry: ExamEntry) -> str:
        """Return the objectName convention used by StartupScreen.ui."""
        if entry.category_id == "matura":
            subject_id = entry.entry_id.rsplit("_", maxsplit=1)[0]
            return f"examButton_{subject_id}"
        return f"examButton_{entry.entry_id}"

    @staticmethod
    def _level_text(entry: ExamEntry) -> str:
        if entry.level_label == "Matura podstawowa":
            return translate("StartupScreen", "Basic level")
        if entry.level_label == "Matura rozszerzona":
            return translate("StartupScreen", "Extended level")
        return entry.level_label

    def _choose_level(self, button: QPushButton, entries: list[ExamEntry]) -> None:
        menu = QMenu(button)
        for entry in entries:
            action = menu.addAction(self._level_text(entry))
            action.triggered.connect(lambda _checked=False, item=entry: self._select(item))
        menu.exec(button.mapToGlobal(button.rect().bottomLeft()))

    def _select(self, entry: ExamEntry) -> None:
        self.exam_selected.emit(entry.workspace_id)