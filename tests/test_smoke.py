"""Minimal smoke test so `python -m unittest discover` passes in CI.

Full AAA + Gherkin suite is task #6. This is just a placeholder that exercises
the scaffold imports and DBManager on :memory:.
"""

import json
import struct
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication

from app.core.config import is_vision_capable
from app.core.version_check import fetch_latest_release_version, is_newer_version
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

    def test_main_window_uses_application_icon_from_resources(self) -> None:
        """
        Scenario: the taskbar icon uses the branded application icon
        Given: a MainWindow instance created by the app
        When: the window icon is inspected
        Then: it comes from the packaged eduit-favicon.ico resource
        """
        # --- ARRANGE ---
        QApplication.instance() or QApplication([])
        from app.core.theme_manager import ThemeManager
        from app.database.db_manager import DBManager
        from app.ui.main_window import MainWindow

        db = DBManager(":memory:")
        theme = ThemeManager(db)
        # --- ACT ---
        window = MainWindow(db, theme)

        # --- ASSERT ---
        self.assertFalse(window.windowIcon().isNull())
        self.assertTrue(window.windowIcon().availableSizes())
        self.assertFalse(window.windowIcon().pixmap(64, 64).isNull())
        window.close()

    def test_update_checker_reads_github_latest_release(self) -> None:
        """
        Scenario: the app checks the GitHub latest release on startup
        Given: a GitHub response with tag_name=v1.3.0
        When: the release metadata is fetched
        Then: the app can detect that the local version is outdated
        """
        # --- ARRANGE ---
        response = MagicMock()
        response.__enter__.return_value = response
        response.read.return_value = json.dumps({"tag_name": "v1.3.0"}).encode("utf-8")

        # --- ACT ---
        with patch("app.core.version_check.urlopen", return_value=response):
            latest = fetch_latest_release_version()

        # --- ASSERT ---
        self.assertEqual(latest, "v1.3.0")
        self.assertTrue(is_newer_version("1.2.2", latest))

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
