"""Tests for WorkspaceFactory and base workspace contract."""

import unittest
from unittest.mock import Mock, patch

from app.core.llm_client import LLMClient
from app.database.db_manager import DBManager
from app.workspaces.factory import WorkspaceFactory, WorkspaceNotFoundError
from app.workspaces.inf03 import INF03Workspace


class WorkspaceFactoryTests(unittest.TestCase):
    """Tests for WorkspaceFactory registration and creation."""

    def setUp(self) -> None:
        # Reset registry before each test
        WorkspaceFactory._registry.clear()
        # Re-import to re-register
        from app.workspaces import (  # noqa: F401
            foreign_language,
            humanities,
            inf03,
            inf04,
            science,
            stem,
        )

    def tearDown(self) -> None:
        WorkspaceFactory.reset()

    def test_inf03_registered(self) -> None:
        """
        Scenario: INF03Workspace registers itself at import
        Given: fresh WorkspaceFactory registry
        When:  available() is called
        Then:  'inf03' is in the list
        """
        # --- ARRANGE / ACT ---
        available = WorkspaceFactory.available()
        # --- ASSERT ---
        self.assertIn("inf03", available)

    def test_all_stubs_registered(self) -> None:
        """
        Scenario: v1.1+ stubs also register (greyed out in UI)
        Given: fresh WorkspaceFactory registry
        When:  available() is called
        Then:  all six other workspace_ids are present
        """
        # --- ARRANGE / ACT ---
        available = WorkspaceFactory.available()
        # --- ASSERT ---
        expected = {"inf03", "foreign_language", "humanities", "stem", "science", "inf04"}
        self.assertEqual(set(available), expected)

    def test_display_name_for_inf03(self) -> None:
        """
        Scenario: display_name_for returns the human-readable label
        Given: WorkspaceFactory with INF03 registered
        When:  display_name_for('inf03') is called
        Then:  returns 'INF.03 — SQL & PHP/HTML'
        """
        # --- ARRANGE / ACT ---
        name = WorkspaceFactory.display_name_for("inf03")
        # --- ASSERT ---
        self.assertEqual(name, "INF.03 — SQL & PHP/HTML")

    def test_create_inf03_returns_workspace(self) -> None:
        """
        Scenario: create('inf03') returns an INF03Workspace instance
        Given: a DBManager and LLMClient
        When:  create('inf03', attempt_id, db, llm) is called
        Then:  the returned object is an INF03Workspace
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        llm = LLMClient(db)
        # --- ACT ---
        ws = WorkspaceFactory.create("inf03", attempt_id, db, llm)
        # --- ASSERT ---
        self.assertIsInstance(ws, INF03Workspace)
        self.assertEqual(ws.workspace_id, "inf03")

    def test_create_unknown_raises(self) -> None:
        """
        Scenario: create() raises WorkspaceNotFoundError for unknown id
        Given: WorkspaceFactory with no 'nonexistent' registered
        When:  create('nonexistent', ...) is called
        Then:  WorkspaceNotFoundError is raised
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        llm = LLMClient(db)
        # --- ACT / ASSERT ---
        with self.assertRaises(WorkspaceNotFoundError):
            WorkspaceFactory.create("nonexistent", attempt_id, db, llm)

    def test_unregister_removes_binding(self) -> None:
        """
        Scenario: unregister removes a workspace from the registry
        Given: 'inf03' registered
        When:  unregister('inf03') then available()
        Then:  'inf03' not in available()
        """
        # --- ARRANGE ---
        # --- ACT ---
        WorkspaceFactory.unregister("inf03")
        # --- ASSERT ---
        self.assertNotIn("inf03", WorkspaceFactory.available())


class INF03WorkspaceTests(unittest.TestCase):
    """Tests for INF03Workspace construction (without Qt widget build)."""

    def setUp(self) -> None:
        self.db = DBManager(":memory:")
        self.attempt_id = self.db.create_attempt("inf03")
        self.llm = LLMClient(self.db)

    def test_workspace_id_and_display_name(self) -> None:
        """
        Scenario: workspace_id and display_name class attributes are correct
        Given: INF03Workspace class
        When:  I inspect workspace_id and display_name
        Then:  they equal 'inf03' and 'INF.03 — SQL & PHP/HTML'
        """
        # --- ARRANGE / ACT / ASSERT ---
        self.assertEqual(INF03Workspace.workspace_id, "inf03")
        self.assertEqual(INF03Workspace.display_name, "INF.03 — SQL & PHP/HTML")

    def test_constructor_stores_dependencies(self) -> None:
        """
        Scenario: __init__ stores attempt_id, db, llm_client
        Given: INF03Workspace(attempt_id, db, llm)
        When:  I inspect the instance attributes
        Then:  they match the constructor arguments
        """
        # --- ARRANGE / ACT ---
        ws = INF03Workspace(self.attempt_id, self.db, self.llm)
        # --- ASSERT ---
        self.assertEqual(ws.attempt_id, self.attempt_id)
        self.assertIs(ws.db, self.db)
        self.assertIs(ws.llm_client, self.llm)

    def test_build_context_payload_returns_dict(self) -> None:
        """
        Scenario: build_context_payload returns a JSON-serializable dict
        Given: an INF03Workspace instance
        When:  build_context_payload() is called
        Then:  returns dict with expected keys (may be empty strings)
        """
        # --- ARRANGE ---
        ws = INF03Workspace(self.attempt_id, self.db, self.llm)
        # --- ACT ---
        payload = ws.build_context_payload()
        # --- ASSERT ---
        self.assertIsInstance(payload, dict)
        expected_keys = {"sql_query", "php_source", "html_source", "css_source", "schema"}
        self.assertEqual(set(payload.keys()), expected_keys)

    def test_default_files_include_css(self) -> None:
        """
        Scenario: INF.03 exposes a stylesheet draft
        Given: the INF03Workspace default file list
        When:  I inspect the supported editor files
        Then:  'style.css' is included
        """
        # --- ARRANGE ---
        # --- ACT ---
        files = INF03Workspace.DEFAULT_FILES
        # --- ASSERT ---
        self.assertIn("style.css", files)

    def test_build_context_payload_includes_css_content(self) -> None:
        """
        Scenario: tutor context includes the stylesheet source
        Given: an INF03Workspace with CSS editor content
        When:  build_context_payload() is called
        Then:  css_source contains the current stylesheet
        """
        # --- ARRANGE ---
        ws = INF03Workspace(self.attempt_id, self.db, self.llm)
        ws._css_editor = Mock(toPlainText=Mock(return_value="body { color: red; }"))
        # --- ACT ---
        payload = ws.build_context_payload()
        # --- ASSERT ---
        self.assertEqual(payload["css_source"], "body { color: red; }")

    def test_grade_without_answer_key_returns_empty_dict(self) -> None:
        """
        Scenario: grade() skips evaluation without an answer key
        Given: an INF03Workspace instance
        When:  grade() is called without an answer-key PDF
        Then:  returns {} without calling the LLM
        """
        # --- ARRANGE ---
        ws = INF03Workspace(self.attempt_id, self.db, self.llm)
        # --- ACT ---
        result = ws.grade()
        # --- ASSERT ---
        self.assertEqual(result, {})

    def test_grade_builds_payload_and_persists_score(self) -> None:
        """
        Scenario: grade evaluates the solution against the answer key
        Given: an answer-key PDF path and a valid evaluator JSON response
        When:  grade() is called
        Then:  the complete payload is sent and the score is persisted
        """
        # --- ARRANGE ---
        self.db.set_config("answer_key_pdf", "answer-key.pdf")
        response = (
            '{"total_score": 8, "max_score": 10, "percentage": 80, '
            '"criteria": [], "missing_requirements": [], "summary": "Dobrze"}'
        )
        ws = INF03Workspace(self.attempt_id, self.db, self.llm)
        with (
            patch.object(self.llm, "chat", return_value=response) as chat,
            patch.object(INF03Workspace, "_extract_pdf_text", return_value="answer key"),
        ):
            # --- ACT ---
            result = ws.grade()

        # --- ASSERT ---
        self.assertEqual(result["percentage"], 80)
        chat.assert_called_once()
        messages = chat.call_args.args[0]
        self.assertIn("answer key", messages[1]["content"])
        saved = self.db.get_attempt(self.attempt_id)
        self.assertIn('"total_score": 8', saved["score_json"])

    def test_parse_grade_response_rejects_missing_score(self) -> None:
        """
        Scenario: malformed evaluator output is rejected
        Given: JSON without total_score
        When:  the evaluator response is parsed
        Then:  ValueError is raised
        """
        # --- ARRANGE ---
        response = '{"summary": "incomplete"}'
        # --- ACT / ASSERT ---
        with self.assertRaises(ValueError):
            INF03Workspace._parse_grade_response(response)


if __name__ == "__main__":
    unittest.main()
