"""Minimal smoke test so `python -m unittest discover` passes in CI.

Full AAA + Gherkin suite is task #6. This is just a placeholder that exercises
the scaffold imports and DBManager on :memory:.
"""

import unittest

from app.core.config import is_vision_capable
from app.database.db_manager import DBManager
from app.workspaces.factory import WorkspaceFactory
from app.workspaces.inf03 import INF03Workspace


class SmokeTests(unittest.TestCase):
    """One-method sanity check for every core component."""

    def test_db_manager_roundtrip(self) -> None:
        """DBManager can write and read config on an in-memory database."""
        # --- ARRANGE ---
        db = DBManager(":memory:")
        # --- ACT ---
        db.set_config("api_key_openai", "sk-test-123")
        # --- ASSERT ---
        self.assertEqual(db.get_config("api_key_openai"), "sk-test-123")

    def test_config_vision_registry(self) -> None:
        """is_vision_capable recognises registered models."""
        self.assertTrue(is_vision_capable("gpt-4o"))
        self.assertTrue(is_vision_capable("gemini-1.5-flash"))
        self.assertTrue(is_vision_capable("llama-3.2-11b-vision"))
        self.assertFalse(is_vision_capable("gpt-3.5-turbo"))
        self.assertFalse(is_vision_capable(""))

    def test_workspace_factory_registers_inf03(self) -> None:
        """INF03Workspace registers itself at import time."""
        self.assertIn("inf03", WorkspaceFactory.available())
        self.assertEqual(
            WorkspaceFactory.display_name_for("inf03"),
            "INF.03 — SQL & PHP/HTML",
        )

    def test_inf03_workspace_instantiates(self) -> None:
        """INF03Workspace constructor runs without Qt widget build."""
        # We don't call build_widget() — that would need a QApplication.
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        from app.core.llm_client import LLMClient

        llm = LLMClient(db)
        ws = INF03Workspace(attempt_id, db, llm)
        self.assertEqual(ws.workspace_id, "inf03")
