"""UI contract tests for the INF.03 workspace and AI assistant panel."""

import os
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import (
    QApplication,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolButton,
)

from app.core.llm_client import LLMClient
from app.core.theme_manager import ThemeManager
from app.database.db_manager import DBManager
from app.ui.chat_panel import ChatPanel
from app.ui.main_window import MainWindow
from app.ui.monaco_editor import MonacoEditor
from app.ui.pdf_viewer import PDFViewer
from app.workspaces.inf03 import INF03Workspace


class INF03UiTests(unittest.TestCase):
    """Verify the student-facing INF.03 layout contract."""

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        cls.application = QApplication.instance() or QApplication([])

    def _build_workspace(self) -> tuple[INF03Workspace, object, DBManager]:
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        workspace = INF03Workspace(attempt_id, db, LLMClient(db))
        return workspace, workspace.build_widget(), db

    def test_inf03_uses_full_height_tabs_and_sql_splitter(self) -> None:
        """
        Scenario: INF.03 gives the active editor the available height
        Given: a constructed INF.03 workspace
        When: the workspace layout is inspected
        Then: SQL and web work use top-level tabs and SQL favors the editor
        """
        # --- ARRANGE ---
        workspace, root, _db = self._build_workspace()
        root.resize(760, 700)
        root.show()
        self.application.processEvents()
        # --- ACT ---
        workspace_tabs = root.findChild(QTabWidget, "workspaceTabs")
        sql_splitter = root.findChild(QSplitter, "sqlSplitter")
        editors = root.findChildren(QPlainTextEdit)
        # --- ASSERT ---
        self.assertIsNotNone(workspace_tabs)
        assert workspace_tabs is not None
        self.assertEqual(
            [workspace_tabs.tabText(index) for index in range(workspace_tabs.count())],
            ["Database (SQL)", "index.php", "index.html", "style.css", "script.js"],
        )
        self.assertEqual(len(root.findChildren(QTabWidget)), 1)
        self.assertIsNotNone(sql_splitter)
        assert sql_splitter is not None
        self.assertGreater(sql_splitter.sizes()[0], sql_splitter.sizes()[1])
        self.assertEqual(len(editors), 5)
        javascript_editor = root.findChild(MonacoEditor, "jsEditor")
        self.assertIsNotNone(javascript_editor)
        assert javascript_editor is not None
        javascript_editor.setPlainText("const answer = 42;")
        self.assertEqual(javascript_editor.toPlainText(), "const answer = 42;")
        javascript_editor.set_theme("dark")
        self.assertEqual(javascript_editor._theme, "vs-dark")
        javascript_editor.set_theme("light")
        self.assertEqual(javascript_editor._theme, "vs")
        root.close()
        workspace.deactivate()

    def test_connection_settings_are_collapsed_and_actions_are_hierarchical(self) -> None:
        """
        Scenario: INF.03 keeps secondary tools out of the main editor area
        Given: a constructed INF.03 workspace
        When: the toolbar and connection settings are inspected
        Then: connection settings start collapsed and only checking is primary
        """
        # --- ARRANGE ---
        workspace, root, _db = self._build_workspace()
        # --- ACT ---
        toggle = root.findChild(QToolButton, "connectionSettingsToggle")
        primary = root.findChildren(QPushButton, "checkTaskButton")
        secondary = root.findChildren(QPushButton)
        # --- ASSERT ---
        self.assertIsNotNone(toggle)
        assert toggle is not None
        self.assertFalse(toggle.isChecked())
        self.assertFalse(root.findChild(QPushButton, "saveConnectionButton").isVisible())
        self.assertEqual(len(primary), 1)
        self.assertTrue(primary[0].property("primaryAction"))
        self.assertTrue(
            all(button.property("secondaryAction") for button in secondary if button != primary[0])
        )
        root.close()
        workspace.deactivate()

    def test_chat_panel_has_guided_empty_state_and_wide_input(self) -> None:
        """
        Scenario: AI Assistant is useful before the first question
        Given: a new ChatPanel without an active attempt
        When: the panel is shown
        Then: a helpful empty state and usable input controls are visible
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        panel = ChatPanel(db, LLMClient(db))
        panel.show()
        self.application.processEvents()
        # --- ACT ---
        empty_state = panel.findChild(type(panel._empty_state), "emptyState")
        # --- ASSERT ---
        self.assertIsNotNone(empty_state)
        assert empty_state is not None
        self.assertTrue(empty_state.isVisible())
        self.assertGreaterEqual(panel._input.minimumHeight(), 56)
        self.assertGreaterEqual(panel._input.minimumWidth(), 180)
        self.assertEqual(panel._send_btn.sizePolicy().horizontalPolicy().name, "Expanding")
        panel.close()

    def test_pdf_toolbar_is_compact_and_polish_empty_state_is_used(self) -> None:
        """
        Scenario: PDF controls remain usable in the narrow left pane
        Given: a new PDF viewer without a loaded document
        When: the toolbar and empty state are inspected
        Then: the snip action is compact and the empty state is Polish
        """
        # --- ARRANGE ---
        viewer = PDFViewer()
        # --- ACT ---
        snip_button = viewer.findChild(QToolButton, "snipButton")
        empty_text = viewer._image_label.text()
        # --- ASSERT ---
        self.assertIsNotNone(snip_button)
        assert snip_button is not None
        self.assertLessEqual(snip_button.width(), 30)
        self.assertNotIn("\n", empty_text)
        self.assertIn("Choose an exam sheet", empty_text)
        viewer.close()

    def test_main_window_keeps_pdf_pane_wide_enough_for_controls(self) -> None:
        """
        Scenario: the PDF pane has enough room for its own toolbar
        Given: a newly constructed main window
        When: the splitter panes are inspected
        Then: the PDF pane has a 300 pixel minimum width
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        window = MainWindow(db, ThemeManager(db))
        # --- ACT ---
        minimum_width = window._left_pane.minimumWidth()
        # --- ASSERT ---
        self.assertGreaterEqual(minimum_width, 300)
        window.close()

    def test_viewer_pdf_load_updates_persisted_path_and_file_status(self) -> None:
        """
        Scenario: loading a PDF through the viewer updates the shared file state
        Given: a MainWindow and a valid PDF loaded directly by its PDFViewer
        When:  the viewer finishes loading the PDF
        Then:  LAST_PDF is persisted and the File indicator is ready
        """
        # --- ARRANGE ---
        import fitz

        db = DBManager(":memory:")
        window = MainWindow(db, ThemeManager(db))
        handle, path = tempfile.mkstemp(suffix=".pdf")
        os.close(handle)
        document = fitz.open()
        document.new_page()
        document.save(path)
        document.close()
        try:
            # --- ACT ---
            loaded = window._pdf_viewer.load_pdf(path)
            self.application.processEvents()

            # --- ASSERT ---
            self.assertTrue(loaded)
            self.assertEqual(db.get_config("last_pdf"), path)
            self.assertTrue(window._status_indicators["file"].property("ready"))
        finally:
            if window._pdf_viewer._doc is not None:
                window._pdf_viewer._doc.close()
            os.unlink(path)
            window.close()

    def test_startup_hides_status_bar_but_keeps_four_status_segments(self) -> None:
        """
        Scenario: Status information is consolidated without wasting startup space
        Given: a newly constructed main window
        When: the startup selector is displayed
        Then: the status bar is hidden and has file, database and AI segments
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        window = MainWindow(db, ThemeManager(db))
        window.show()
        self.application.processEvents()
        # --- ACT ---
        segment_keys = set(window._status_indicators)
        # --- ASSERT ---
        self.assertEqual(segment_keys, {"file", "answer_key", "database", "ai"})
        self.assertFalse(window.statusBar().isVisible())
        window.close()

    def test_startup_button_opens_inf03_workspace(self) -> None:
        """
        Scenario: the INF.03 starter opens the actual workspace
        Given: the exam selector is visible
        When: the student clicks the INF.03 button
        Then: MainWindow creates INF03Workspace and shows its tabs
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        window = MainWindow(db, ThemeManager(db))
        button = window._startup_screen.findChild(
            QPushButton, "examButton_vocational_inf03"
        )
        self.assertIsNotNone(button)

        # --- ACT ---
        with patch.object(INF03Workspace, "_load_schemas"):
            assert button is not None
            button.click()
            self.application.processEvents()

        # --- ASSERT ---
        self.assertIsNotNone(window._active_workspace)
        self.assertEqual(window._active_workspace.workspace_id, "inf03")
        self.assertIsNotNone(
            window._active_workspace_widget.findChild(QTabWidget, "workspaceTabs")
        )
        window.close()


if __name__ == "__main__":
    unittest.main()
