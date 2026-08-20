"""Regression tests for chat input and prompt sanitization."""

import unittest
from unittest import mock

from PySide6.QtWidgets import QApplication

from app.core import config as cfg
from app.core.llm_client import LLMClient
from app.database.db_manager import DBManager
from app.ui.chat_panel import ChatPanel
from app.workspaces.inf03 import INF03Workspace

QAPP = QApplication.instance() or QApplication([])


class ChatPanelKeyboardAndSecurityTests(unittest.TestCase):
    def test_fetch_available_models_returns_model_ids(self) -> None:
        """
        Scenario: provider model list can be fetched from the API
        Given: an OpenAI-compatible endpoint that returns a model list
        When:  fetch_available_models() is called
        Then:  the configured model names are returned without the models/ prefix
        """
        db = DBManager(":memory:")
        client = LLMClient(
            db,
            http_poster=lambda url, headers, body: {
                "data": [
                    {"id": "models/gpt-4o-mini"},
                    {"id": "models/gpt-4o"},
                ]
            },
        )

        result = client.fetch_available_models(cfg.PROVIDER_OPENAI, "sk-key", "https://example.test/v1")

        self.assertEqual(result, ["gpt-4o-mini", "gpt-4o"])

    def test_sanitize_prompt_text_removes_html_and_script_payloads(self) -> None:
        """
        Scenario: prompt text is sanitized before being sent to the model
        Given: user input containing HTML and script content
        When:  sanitize_prompt_text() is called
        Then:  only clean plain text remains
        """
        raw = '<script>alert("x")</script><div onclick="alert(1)">hello</div>'

        cleaned = LLMClient.sanitize_prompt_text(raw)

        self.assertNotIn("<script", cleaned.lower())
        self.assertNotIn("onclick", cleaned.lower())
        self.assertIn("hello", cleaned.lower())

    def test_save_path_is_reused_without_prompting_again(self) -> None:
        """
        Scenario: the same file keeps its chosen save path inside one session
        Given: an attempt whose selected HTML save path is already persisted
        When:  _resolve_save_path("index.html") is called again
        Then:  the saved path is reused and no save dialog opens
        """
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        db.set_config(cfg.code_file_key(attempt_id, "index.html"), "C:/tmp/index.html")
        workspace = INF03Workspace.__new__(INF03Workspace)
        workspace.attempt_id = attempt_id
        workspace.db = db

        with mock.patch("app.workspaces.inf03.QFileDialog.getSaveFileName") as get_save:
            path = workspace._resolve_save_path("index.html", "HTML files (*.html)", "index.html")

        self.assertEqual(path, "C:/tmp/index.html")
        get_save.assert_not_called()

    def test_chat_context_includes_loaded_exam_sheet_text(self) -> None:
        """
        Scenario: the tutor can guide from the actual exam requirements
        Given: an active workspace and a loaded exam sheet
        When: the chat context is built
        Then: the exam sheet text is sent alongside the student's code
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        db.set_config(cfg.LAST_PDF, "C:/exam.pdf")
        db.add_message(attempt_id, "user", "tak")
        workspace = mock.Mock()
        workspace.tutor_system_prompt.return_value = "Tutor prompt"
        workspace.build_context_payload.return_value = {"sql_query": "select * from city;"}
        panel = ChatPanel(db, LLMClient(db))
        panel.set_active_workspace(workspace)

        # --- ACT ---
        with mock.patch.object(
            ChatPanel,
            "_read_pdf_text",
            return_value="Wybierz tylko rekordy wymagane przez polecenie.",
        ):
            messages = panel._build_context_messages(attempt_id, "tak")

        # --- ASSERT ---
        context_message = messages[1]
        self.assertIn("exam_sheet_text", context_message["content"])
        self.assertIn("Wybierz tylko rekordy wymagane przez polecenie.", context_message["content"])


if __name__ == "__main__":
    unittest.main()
