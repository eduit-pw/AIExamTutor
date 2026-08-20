"""MainWindow controller — 3-pane split view (PDF / Workspace / AI Tutor).

This module is the ONLY place that touches the MainWindow.ui file via QUiLoader.
All other logic lives in the workspace classes and core modules.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
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
from app.core.localization import translate
from app.core.logger import get_logger
from app.core.theme_manager import ThemeManager
from app.database.db_manager import DBManager
from app.ui.monaco_editor import MonacoEditor
from app.ui.startup_screen import StartupScreen
from app.workspaces.base import BaseWorkspace
from app.workspaces.factory import WorkspaceFactory

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
        self._close_retry_scheduled = False

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
        self.setMinimumSize(1080, 640)
        self.resize(1120, 720)

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

        self._main_splitter.setStretchFactor(0, 1)
        self._main_splitter.setStretchFactor(1, 2)
        self._main_splitter.setStretchFactor(2, 1)
        self._main_splitter.setChildrenCollapsible(False)
        self._left_pane.setMinimumWidth(300)
        self._center_stack.setMinimumWidth(400)
        self._right_pane.setMinimumWidth(300)
        self._splitter_timer = QTimer(self._main_splitter)
        self._splitter_timer.setSingleShot(True)
        self._splitter_timer.timeout.connect(self._set_initial_splitter_sizes)
        self._splitter_timer.start(0)

        # Build the left pane (PDF viewer placeholder) now.
        self._build_left_pane()
        # Build the right pane (AI Tutor chat placeholder) now.
        self._build_right_pane()

    def _set_initial_splitter_sizes(self) -> None:
        """Set useful pane proportions while preserving each pane's minimum width."""
        total_width = self._main_splitter.width()
        if total_width <= 0:
            return
        left_width = max(300, int(total_width * 0.27))
        right_width = max(300, int(total_width * 0.28))
        center_width = max(400, total_width - left_width - right_width)
        self._main_splitter.setSizes([left_width, center_width, right_width])

    def _build_left_pane(self) -> None:
        """Add a real PDF viewer widget to the left pane."""
        from app.ui.pdf_viewer import PDFViewer

        layout = QVBoxLayout(self._left_pane)
        layout.setContentsMargins(0, 0, 0, 0)
        self._pdf_viewer = PDFViewer()
        self._pdf_viewer.status_changed.connect(self._on_workspace_status)
        self._pdf_viewer.pdf_loaded.connect(self._on_pdf_loaded)
        self._pdf_viewer.region_snipped.connect(self._on_region_snipped)
        layout.addWidget(self._pdf_viewer)
        # Keep a backwards-compatible reference
        self._pdf_label = self._pdf_viewer

    def _build_status_indicators(self) -> None:
        """Add clear file, database and AI states to the shared status bar."""
        for key, title_source in (
            ("file", "File"),
            ("answer_key", "Answer key"),
            ("database", "Database"),
            ("ai", "AI"),
        ):
            title = translate("MainWindow", title_source)
            indicator = QLabel()
            indicator.setObjectName(f"status{key.title()}")
            indicator.setProperty("statusIndicator", True)
            indicator.setMinimumWidth(116)
            indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
            indicator.setToolTip(f"{title} status")
            self.statusBar().addPermanentWidget(indicator)
            self._status_indicators[key] = indicator
            self._set_status_indicator(key, False)

    def _set_status_indicator(self, key: str, ready: bool) -> None:
        key = {
            "connection": "database",
            "mysql": "database",
            "llm": "ai",
            "pdf": "file",
        }.get(key, key)
        indicator = self._status_indicators.get(key)
        if indicator is not None:
            title = translate(
                "MainWindow",
                {
                    "file": "File",
                    "answer_key": "Answer key",
                    "database": "Database",
                    "ai": "AI",
                }[key],
            )
            state_text = translate("MainWindow", "Connected" if ready else "Offline mode")
            indicator.setText(f"{title}: {state_text}")
            indicator.setToolTip(f"{title}: {state_text}")
            indicator.setVisible(True)
            indicator.setProperty("ready", ready)
            style = indicator.style()
            style.unpolish(indicator)
            style.polish(indicator)
            indicator.update()

    def _mark_status_indicator(self, key: str, label: str, ready: bool = True) -> None:
        del label
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

    def _send_chat_from_workspace(self, text: str) -> None:
        """Forward workspace content into the main AI chat input and send it."""
        if not hasattr(self, "_chat_panel"):
            return
        self._chat_panel._input.setPlainText(text)
        self._chat_panel._send()

    def _on_region_snipped(self, png_bytes: bytes) -> None:
        """Send a snipped PDF region to the chat as an image attachment."""
        if hasattr(self, "_chat_panel"):
            self._chat_panel.attach_image(png_bytes)

    # ------------------------------------------------------------------
    # Keyboard / menu wiring
    # ------------------------------------------------------------------
    def _wire_actions(self) -> None:
        file_menu = self.menuBar().addMenu(translate("MainWindow", "File"))

        choose_exam_act = QAction(translate("MainWindow", "Choose exam"), self)
        choose_exam_act.triggered.connect(self._show_startup_screen)
        file_menu.addAction(choose_exam_act)

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
        """Restore document context, then let the student choose a workspace."""
        last_pdf = self._db.get_config(cfg.LAST_PDF)
        if last_pdf and Path(last_pdf).exists():
            self._load_pdf(last_pdf)
        answer_key = self._db.get_config(cfg.ANSWER_KEY_PDF)
        if answer_key and Path(answer_key).exists():
            self._answer_key_path = answer_key
            self._mark_status_indicator("answer_key", translate("MainWindow", "Answer key"))
            self.statusBar().showMessage(
                translate("MainWindow", "Answer key loaded: %1").replace(
                    "%1", Path(answer_key).name
                )
            )
        self._show_startup_screen()

    def _show_startup_screen(self) -> None:
        """Show the exam selector without creating an attempt."""
        self._clear_active_workspace()
        self._attempt_id = None
        self._left_pane.setVisible(False)
        self._right_pane.setVisible(False)
        previous_selector = getattr(self, "_startup_screen", None)
        if previous_selector is not None:
            self._center_stack.removeWidget(previous_selector)
            previous_selector.deleteLater()
        selector = StartupScreen(self)
        selector.exam_selected.connect(self._switch_workspace)
        self._center_stack.addWidget(selector)
        self._center_stack.setCurrentWidget(selector)
        self._startup_screen = selector
        if hasattr(self, "_chat_panel"):
            self._chat_panel.set_active_workspace(None)
        self.statusBar().setVisible(False)
        self.statusBar().showMessage(translate("MainWindow", "Choose an exam to begin."))

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
        if hasattr(self, "_pdf_viewer") and self._pdf_viewer.load_pdf(path):
            return

    def _on_pdf_loaded(self, path: str) -> None:
        """Persist and display any PDF loaded by menu, restore, or drag-and-drop."""
        self._pdf_path = path
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
        logger.info("Opening workspace requested: workspace_id=%s", workspace_id)
        if workspace_id not in WorkspaceFactory.available():
            logger.error(
                "Workspace rejected: workspace_id=%s available=%s",
                workspace_id,
                WorkspaceFactory.available(),
            )
            QMessageBox.warning(
                self,
                translate("MainWindow", "Exam not available"),
                translate("MainWindow", "This exam is not available yet."),
            )
            return
        if workspace_id in {"stem", "science"} and not self._llm.is_vision_capable():
            QMessageBox.information(
                self,
                translate("MainWindow", "Image support required"),
                translate(
                    "MainWindow",
                    "Enable image support (Vision) in File > Settings > Model "
                    "to unlock this subject.",
                ),
            )
            return

        try:
            # Build the new widget before removing the selector. A construction
            # failure must leave the student with a usable screen and a log.
            attempt_id = self._attempt_id
            if attempt_id is None:
                attempt_id = self._db.create_attempt(workspace_id, self._pdf_path)
                logger.info(
                    "Created attempt: workspace_id=%s attempt_id=%s", workspace_id, attempt_id
                )

            ws = WorkspaceFactory.create(workspace_id, attempt_id, self._db, self._llm)
            logger.info("Workspace instance created: %s", type(ws).__name__)
            widget = ws.build_widget()
            logger.info("Workspace widget built: workspace_id=%s", workspace_id)
        except Exception as exc:  # noqa: BLE001 - keep the selector usable after UI failures
            logger.exception("Failed to open workspace: workspace_id=%s", workspace_id)
            self.statusBar().setVisible(True)
            self.statusBar().showMessage(
                translate("MainWindow", "Unable to open %1")
                .replace("%1", f"{workspace_id}: {exc}")
            )
            QMessageBox.critical(
                self,
                translate("MainWindow", "Workspace could not be opened"),
                translate("MainWindow", "The selected exam view could not be loaded. "
                          "See the application log for details."),
            )
            return

        self._attempt_id = attempt_id
        self.statusBar().setVisible(True)
        self._left_pane.setVisible(True)
        self._right_pane.setVisible(True)
        startup_screen = getattr(self, "_startup_screen", None)
        if startup_screen is not None:
            self._center_stack.removeWidget(startup_screen)
            startup_screen.deleteLater()
            self._startup_screen = None

        # Clean up previous workspace after the replacement was built.
        self._clear_active_workspace()

        set_status_callback = getattr(ws, "set_status_callback", None)
        if callable(set_status_callback):
            set_status_callback(self._on_workspace_status)
        set_connection_callback = getattr(ws, "set_connection_callback", None)
        if callable(set_connection_callback):
            set_connection_callback(self._on_mysql_connection_succeeded)
        self._center_stack.addWidget(widget)
        self._center_stack.setCurrentWidget(widget)
        self._active_workspace = ws
        self._active_workspace_widget = widget
        self._db.set_config(cfg.ACTIVE_WORKSPACE, workspace_id)

        # Bind chat panel to this attempt so it reloads history.
        if hasattr(self, "_chat_panel") and self._attempt_id is not None:
            logger.info("Binding chat panel: attempt_id=%s", self._attempt_id)
            self._chat_panel.set_active_attempt(self._attempt_id)
            self._chat_panel.set_active_workspace(ws)
        set_chat_callback = getattr(ws, "set_chat_callback", None)
        if callable(set_chat_callback):
            set_chat_callback(self._send_chat_from_workspace)

        self._update_vision_banner()
        logger.info("Workspace opened successfully: workspace_id=%s", workspace_id)

    def _clear_active_workspace(self) -> None:
        """Remove the current workspace widget while keeping persisted data."""
        if self._active_workspace is None:
            return
        deactivate = getattr(self._active_workspace, "deactivate", None)
        if callable(deactivate):
            deactivate()
        if self._active_workspace_widget is not None:
            self._center_stack.removeWidget(self._active_workspace_widget)
            self._active_workspace_widget.deleteLater()
        self._active_workspace = None
        self._active_workspace_widget = None

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
            translate("MainWindow", "LLM connection successful: %1").replace("%1", provider)
        )

    def _on_mysql_connection_succeeded(self, message: str) -> None:
        self._mark_status_indicator("mysql", translate("MainWindow", "MySQL"))
        self.statusBar().showMessage(message)

    def _on_workspace_status(self, message: str) -> None:
        self.statusBar().showMessage(message)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Wait for an active chat request before destroying the Qt widgets."""
        chat_panel = getattr(self, "_chat_panel", None)
        if chat_panel is not None and chat_panel.has_running_worker():
            event.ignore()
            if not self._close_retry_scheduled:
                self._close_retry_scheduled = True
                self.setEnabled(False)
            QTimer.singleShot(100, self._retry_close)
            return

        self._close_retry_scheduled = False
        event.accept()

    def _retry_close(self) -> None:
        self._close_retry_scheduled = False
        self.close()

    def _toggle_theme(self) -> None:
        """Flip Light/Dark and reapply."""
        new_theme = self._theme.toggle(QApplication.instance())
        for editor in self.findChildren(MonacoEditor):
            editor.set_theme(new_theme)

    def _update_vision_banner(self) -> None:
        """Show/hide the vision-warning banner based on active model."""
        active_workspace_id = (
            self._active_workspace.workspace_id if self._active_workspace is not None else None
        )
        if active_workspace_id in {"stem", "science"} and not self._llm.is_vision_capable():
            self.statusBar().showMessage(
                translate(
                    "MainWindow",
                    "Enable image support (Vision) in File > Settings > Model "
                    "to unlock this subject.",
                )
            )
        else:
            self.statusBar().clearMessage()
