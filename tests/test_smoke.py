"""Minimal smoke test so `python -m unittest discover` passes in CI.

Full AAA + Gherkin suite is task #6. This is just a placeholder that exercises
the scaffold imports and DBManager on :memory:.
"""

import struct
import unittest
from pathlib import Path

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
            "INF.03 — SQL & PHP/HTML/CSS/JavaScript",
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

    def test_windows_icon_contains_square_taskbar_sizes(self) -> None:
        """
        Scenario: Windows can select a suitable application icon
        Given: the application icon resource
        When: its image directory is inspected
        Then: it contains square entries at standard taskbar sizes
        """
        # --- ARRANGE ---
        icon_path = Path(__file__).parents[1] / "resources" / "eduit-favicon.ico"
        icon_bytes = icon_path.read_bytes()
        image_count = struct.unpack_from("<H", icon_bytes, 4)[0]

        # --- ACT ---
        sizes = {
            (
                icon_bytes[6 + index * 16] or 256,
                icon_bytes[7 + index * 16] or 256,
            )
            for index in range(image_count)
        }

        # --- ASSERT ---
        self.assertTrue({(16, 16), (32, 32), (48, 48), (256, 256)} <= sizes)
        self.assertTrue(all(width == height for width, height in sizes))
