"""MainWindow controller — 3-pane split view (PDF / Workspace / AI Tutor).

This module is the ONLY place that touches the MainWindow.ui file via QUiLoader.
All other logic lives in the workspace classes and core modules.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core import config as cfg
from app.core.llm_client import LLMClient
from app.core.logger import get_logger
from app.core.localization import translate
from app.core.theme_manager import ThemeManager
from app.database.db_manager import DBManager
from app.workspaces.factory import WorkspaceFactory, WorkspaceNotFoundError
from app.workspaces.base import BaseWorkspace

logger = get_logger("ui.main_window")


class MainWindow(QMainWindow):
    """Top-level window controller."""

    def __init__(self, db: DBManager, theme: ThemeManager) -> None:
        super().__init__()
        self._db = db
        self._theme = theme
        self._llm = LLMClient(db)
        self._active_workspace: BaseWorkspace | None = None
        self._active_workspace_widget: QWidget | None = None
        self._attempt_id: int | None = None
        self._pdf_path: str | None = None
        self._answer_key_path: str | None = None
        self._status_indicators: dict[str, QLabel] = {}

        self._load_ui()
        self._build_status_indicators()
        self._wire_actions()
        self._restore_last_state()
        self._update_vision_banner()

    # ------------------------------------------------------------------
    # UI loading
    # ------------------------------------------------------------------
    def _load_ui(self) -> None:
        """Load MainWindow.ui via QUiLoader and capture widget refs."""
        loader = QUiLoader()
        from importlib import resources

        with resources.as_file(
            resources.files("app.ui.views").joinpath("MainWindow.ui")
        ) as ui_path:
            widget = loader.load(str(ui_path))
        if widget is None:
            raise RuntimeError("QUiLoader returned None for MainWindow.ui")

        self.setCentralWidget(widget)

        # Capture the three panes
        self._main_splitter = widget.findChild(QWidget, "mainSplitter")
        self._left_pane = widget.findChild(QWidget, "leftPane")
        self._center_stack = widget.findChild(QStackedWidget, "centerStack")
        self._right_pane = widget.findChild(QWidget, "rightPane")

        if not all(
            [
                self._main_splitter,
                self._left_pane,
                self._center_stack,
                self._right_pane,
            ]
        ):
            raise LookupError("MainWindow.ui missing expected objectNames")

        # Build the left pane (PDF viewer placeholder) now.
        self._build_left_pane()
        # Build the right pane (AI Tutor chat placeholder) now.
        self._build_right_pane()

    def _build_left_pane(self) -> None:
        """Add a real PDF viewer widget to the left pane."""
        from app.ui.pdf_viewer import PDFViewer

        layout = QVBoxLayout(self._left_pane)
        layout.setContentsMargins(0, 0, 0, 0)
        self._pdf_viewer = PDFViewer()
        self._pdf_viewer.region_snipped.connect(self._on_region_snipped)
        layout.addWidget(self._pdf_viewer)
        # Keep a backwards-compatible reference
        self._pdf_label = self._pdf_viewer

    def _build_status_indicators(self) -> None:
        """Add persistent PDF/key/LLM/MySQL state indicators to the status bar."""
        for key, label in (
            ("pdf", translate("MainWindow", "PDF")),
            ("answer_key", translate("MainWindow", "Answer key")),
            ("llm", translate("MainWindow", "LLM")),
            ("mysql", translate("MainWindow", "MySQL")),
        ):
            indicator = QLabel()
            indicator.setObjectName("statusIndicator")
            indicator.setProperty("statusIndicator", True)
            indicator.setMinimumWidth(90 if key == "answer_key" else 65)
            indicator.setToolTip(
                translate("MainWindow", "%1 connection or file status").replace("%1", label)
            )
            indicator.setProperty("status_label", label)
            self.statusBar().addPermanentWidget(indicator)
            self._status_indicators[key] = indicator
            self._set_status_indicator(key, False)

    def _set_status_indicator(self, key: str, ready: bool) -> None:
        indicator = self._status_indicators.get(key)
        if indicator is not None:
            indicator.setText(f"{indicator.property('status_label') or key}: {'✅' if ready else '❌'}")
            indicator.setProperty("ready", ready)
            style = indicator.style()
            style.unpolish(indicator)
            style.polish(indicator)
            indicator.update()

    def _mark_status_indicator(self, key: str, label: str, ready: bool = True) -> None:
        indicator = self._status_indicators.get(key)
        if indicator is not None:
            indicator.setProperty("status_label", label)
            self._set_status_indicator(key, ready)

    def _build_right_pane(self) -> None:
        """Add the AI Tutor chat panel to the right pane."""
        from app.ui.chat_panel import ChatPanel

        layout = QVBoxLayout(self._right_pane)
        layout.setContentsMargins(0, 0, 0, 0)
        self._chat_panel = ChatPanel(self._db, self._llm, parent=self._right_pane)
        layout.addWidget(self._chat_panel)
        # Keep a backwards-compatible reference
        self._chat_display = self._chat_panel

    def _on_region_snipped(self, png_bytes: bytes) -> None:
        """Send a snipped PDF region to the chat as an image attachment."""
        if hasattr(self, "_chat_panel"):
            self._chat_panel.attach_image(png_bytes)

    # ------------------------------------------------------------------
    # Keyboard / menu wiring
    # ------------------------------------------------------------------
    def _wire_actions(self) -> None:
        file_menu = self.menuBar().addMenu(translate("MainWindow", "File"))

        # File → Open PDF (Ctrl+O)
        open_act = QAction(translate("MainWindow", "Open PDF"), self)
        open_act.setShortcut(QKeySequence("Ctrl+O"))
        open_act.triggered.connect(self._open_pdf)
        file_menu.addAction(open_act)

        answer_key_act = QAction(translate("MainWindow", "Open answer key PDF"), self)
        answer_key_act.triggered.connect(self._open_answer_key_pdf)
        file_menu.addAction(answer_key_act)

        # Settings (Ctrl+,)
        settings_act = QAction(translate("MainWindow", "Settings"), self)
        settings_act.setShortcut(QKeySequence("Ctrl+,"))
        settings_act.triggered.connect(self._open_settings)
        file_menu.addAction(settings_act)

        # Theme toggle (Ctrl+T)
        theme_act = QAction(translate("MainWindow", "Toggle Theme"), self)
        theme_act.setShortcut(QKeySequence("Ctrl+T"))
        theme_act.triggered.connect(self._toggle_theme)
        file_menu.addAction(theme_act)

        help_menu = self.menuBar().addMenu(translate("MainWindow", "Help"))
        about_act = QAction(translate("MainWindow", "About AI Exam Tutor"), self)
        about_act.triggered.connect(self._open_about)
        help_menu.addAction(about_act)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------
    def _restore_last_state(self) -> None:
        """Reopen last PDF + workspace from app_config."""
        last_pdf = self._db.get_config(cfg.LAST_PDF)
        if last_pdf and Path(last_pdf).exists():
            self._load_pdf(last_pdf)
        answer_key = self._db.get_config(cfg.ANSWER_KEY_PDF)
        if answer_key and Path(answer_key).exists():
            self._answer_key_path = answer_key
            self._mark_status_indicator(
                "answer_key", translate("MainWindow", "Answer key")
            )
            self.statusBar().showMessage(
                translate("MainWindow", "Answer key loaded: %1").replace(
                    "%1", Path(answer_key).name
                )
            )
        last_ws = self._db.get_config(cfg.ACTIVE_WORKSPACE)
        if last_ws in WorkspaceFactory.available():
            self._switch_workspace(last_ws)
        elif "inf03" in WorkspaceFactory.available():
            self._switch_workspace("inf03")

    # ------------------------------------------------------------------
    # PDF handling
    # ------------------------------------------------------------------
    def _open_pdf(self) -> None:
        start_dir = os.path.dirname(self._pdf_path) if self._pdf_path else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CKE Exam PDF", start_dir, "PDF Files (*.pdf)"
        )
        if path:
            self._load_pdf(path)

    def _open_answer_key_pdf(self) -> None:
        """Select the PDF answer key used as tutor context."""
        start_dir = os.path.dirname(self._answer_key_path) if self._answer_key_path else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open answer key PDF", start_dir, "PDF Files (*.pdf)"
        )
        if path:
            self._answer_key_path = path
            self._db.set_config(cfg.ANSWER_KEY_PDF, path)
            self._mark_status_indicator("answer_key", translate("MainWindow", "Answer key"))
            self.statusBar().showMessage(
                translate("MainWindow", "Answer key loaded: %1").replace("%1", Path(path).name)
            )

    def _load_pdf(self, path: str) -> None:
        """Load a PDF into the left pane using PyMuPDF (fitz)."""
        self._pdf_path = path
        if hasattr(self, "_pdf_viewer") and self._pdf_viewer.load_pdf(path):
            self._db.set_config(cfg.LAST_PDF, path)
            self.statusBar().showMessage(
                translate("MainWindow", "PDF loaded: %1").replace("%1", Path(path).name)
            )
            self._mark_status_indicator("pdf", translate("MainWindow", "PDF"))

    # ------------------------------------------------------------------
    # Workspace switching
    # ------------------------------------------------------------------
    def _switch_workspace(self, workspace_id: str) -> None:
        """Create the workspace widget and push it into the centre stack."""
        # Clean up previous workspace
        if self._active_workspace is not None:
            deactivate = getattr(self._active_workspace, "deactivate", None)
            if callable(deactivate):
                deactivate()
            if self._active_workspace_widget is not None:
                self._center_stack.removeWidget(self._active_workspace_widget)
                self._active_workspace_widget.deleteLater()
            self._active_workspace = None
            self._active_workspace_widget = None

        # If no attempt yet, create one
        if self._attempt_id is None:
            self._attempt_id = self._db.create_attempt(workspace_id, self._pdf_path)

        try:
            ws = WorkspaceFactory.create(
                workspace_id, self._attempt_id, self._db, self._llm
            )
        except WorkspaceNotFoundError:
            QMessageBox.warning(
                self,
                translate("MainWindow", "Workspace not available"),
                f"{workspace_id!r} is not implemented yet.",
            )
            return

        set_status_callback = getattr(ws, "set_status_callback", None)
        if callable(set_status_callback):
            set_status_callback(self._on_mysql_connection_succeeded)
        widget = ws.build_widget()
        self._center_stack.addWidget(widget)
        self._center_stack.setCurrentWidget(widget)
        self._active_workspace = ws
        self._active_workspace_widget = widget
        self._db.set_config(cfg.ACTIVE_WORKSPACE, workspace_id)

        # Bind chat panel to this attempt so it reloads history.
        if hasattr(self, "_chat_panel") and self._attempt_id is not None:
            self._chat_panel.set_active_attempt(self._attempt_id)
            self._chat_panel.set_active_workspace(ws)

        self._update_vision_banner()

    # ------------------------------------------------------------------
    # Settings / Theme
    # ------------------------------------------------------------------
    def _open_settings(self) -> None:
        """Open the settings dialog (placeholder for now)."""
        # Real dialog loads SettingsDialog.ui via QUiLoader — task #4.
        from app.ui.settings_dialog import SettingsDialog

        dlg = SettingsDialog(self._db, self._llm, self)
        dlg.connection_succeeded.connect(
            lambda provider: self._on_llm_connection_succeeded(provider)
        )
        if dlg.exec():
            self._update_vision_banner()

    def _open_about(self) -> None:
        """Open application information and the compact student manual."""
        from app.ui.about_dialog import AboutDialog

        workspace_id = (
            self._active_workspace.workspace_id
            if self._active_workspace is not None
            else self._db.get_config(cfg.ACTIVE_WORKSPACE, "inf03")
        )
        language = self._db.get_config(cfg.LANGUAGE, "pl") or "pl"
        AboutDialog(
            workspace_id=workspace_id or "inf03",
            language=language,
            parent=self,
        ).exec()

    def _on_llm_connection_succeeded(self, provider: str) -> None:
        self._mark_status_indicator("llm", translate("MainWindow", "LLM"))
        self.statusBar().showMessage(
            translate("MainWindow", "LLM connection successful: %1").replace(
                "%1", provider
            )
        )

    def _on_mysql_connection_succeeded(self, message: str) -> None:
        self._mark_status_indicator("mysql", translate("MainWindow", "MySQL"))
        self.statusBar().showMessage(message)

    def _toggle_theme(self) -> None:
        """Flip Light/Dark and reapply."""
        self._theme.toggle(QApplication.instance())

    def _update_vision_banner(self) -> None:
        """Show/hide the vision-warning banner based on active model."""
        if not self._llm.is_vision_capable():
            self.statusBar().showMessage(
                translate(
                    "MainWindow",
                    "Vision disabled — STEM workspaces won't work. Configure a vision model in Settings.",
                )
            )
        else:
            self.statusBar().clearMessage()