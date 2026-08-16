"""Tests for core modules: config, logger, theme_manager."""

import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.core import config as cfg
from app.core.logger import configure_logging, get_logger
from app.core.localization import LanguageManager
from app.core.theme_manager import ThemeManager
from app.database.db_manager import DBManager


class ConfigTests(unittest.TestCase):
    """Tests for config constants and vision capability registry."""

    def test_vision_capable_recognises_openai_models(self) -> None:
        """
        Scenario: is_vision_capable returns True for registered OpenAI vision models
        Given: model names gpt-4o, gpt-4o-mini, gpt-4-vision-preview
        When:  is_vision_capable(model) is called
        Then:  returns True
        """
        for model in ("gpt-4o", "gpt-4o-mini", "gpt-4-vision-preview"):
            with self.subTest(model=model):
                self.assertTrue(cfg.is_vision_capable(model))

    def test_vision_capable_recognises_gemini_models(self) -> None:
        """
        Scenario: is_vision_capable returns True for registered Gemini vision models
        Given: model names gemini-1.5-flash, gemini-1.5-pro, gemini-1.5-flash-8b
        When:  is_vision_capable(model) is called
        Then:  returns True
        """
        for model in ("gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.5-flash-8b"):
            with self.subTest(model=model):
                self.assertTrue(cfg.is_vision_capable(model))

    def test_vision_capable_recognises_local_models(self) -> None:
        """
        Scenario: is_vision_capable returns True for local vision models
        Given: model names llava, llava:13b, qwen2-vl
        When:  is_vision_capable(model) is called
        Then:  returns True
        """
        for model in ("llava", "llava:13b", "qwen2-vl"):
            with self.subTest(model=model):
                self.assertTrue(cfg.is_vision_capable(model))

    def test_vision_capable_false_for_text_models(self) -> None:
        """
        Scenario: is_vision_capable returns False for text-only models
        Given: model names gpt-3.5-turbo, llama3.2, gemini-1.0-pro
        When:  is_vision_capable(model) is called
        Then:  returns False
        """
        for model in ("gpt-3.5-turbo", "llama3.2", "gemini-1.0-pro", "unknown-model"):
            with self.subTest(model=model):
                self.assertFalse(cfg.is_vision_capable(model))

    def test_vision_capable_false_for_none_or_empty(self) -> None:
        """
        Scenario: is_vision_capable returns False for None or empty string
        Given: model is None or ""
        When:  is_vision_capable(model) is called
        Then:  returns False
        """
        self.assertFalse(cfg.is_vision_capable(None))
        self.assertFalse(cfg.is_vision_capable(""))

    def test_config_key_generators(self) -> None:
        """
        Scenario: api_key_key, base_url_key, model_key generate correct prefixes
        Given: provider_id = 'openai'
        When:  calling the three helpers
        Then:  return 'api_key_openai', 'base_url_openai', 'model_openai'
        """
        self.assertEqual(cfg.api_key_key("openai"), "api_key_openai")
        self.assertEqual(cfg.base_url_key("openai"), "base_url_openai")
        self.assertEqual(cfg.model_key("openai"), "model_openai")


class LoggerTests(unittest.TestCase):
    """Tests for logger configuration."""

    def test_configure_logging_idempotent(self) -> None:
        """
        Scenario: configure_logging() can be called multiple times safely
        Given: fresh logger state
        When:  configure_logging() is called twice
        Then:  no exception, logger is configured
        """
        # --- ARRANGE / ACT ---
        configure_logging()
        configure_logging()  # second call
        # --- ASSERT ---
        logger = get_logger("test")
        self.assertIsInstance(logger, logging.Logger)

    def test_get_logger_returns_child(self) -> None:
        """
        Scenario: get_logger('child') returns a namespaced logger
        Given: configure_logging() called
        When:  get_logger('mymodule') is called
        Then:  logger name is 'ai_exam_tutor.mymodule'
        """
        # --- ARRANGE ---
        configure_logging()
        # --- ACT ---
        logger = get_logger("mymodule")
        # --- ASSERT ---
        self.assertEqual(logger.name, "ai_exam_tutor.mymodule")


class LocalizationTests(unittest.TestCase):
    """Tests for the persisted application language preference."""

    def setUp(self) -> None:
        self.db = DBManager(":memory:")
        self.languages = LanguageManager(self.db)

    def test_polish_is_the_default_language(self) -> None:
        """
        Scenario: Polish is used when no language was saved
        Given: a fresh configuration database
        When:  the current language is read
        Then:  it is 'pl'
        """
        # --- ARRANGE / ACT ---
        language = self.languages.current()
        # --- ASSERT ---
        self.assertEqual(language, "pl")

    def test_language_round_trip(self) -> None:
        """
        Scenario: selected language is persisted
        Given: a language manager and an empty configuration database
        When:  English is saved
        Then:  English is returned as the current language
        """
        # --- ARRANGE / ACT ---
        self.languages.save("en")
        # --- ASSERT ---
        self.assertEqual(self.languages.current(), "en")

    def test_unknown_language_is_rejected(self) -> None:
        """
        Scenario: unsupported language cannot be saved
        Given: a language manager
        When:  an unknown language is saved
        Then:  ValueError is raised
        """
        # --- ARRANGE / ACT / ASSERT ---
        with self.assertRaises(ValueError):
            self.languages.save("de")


class ThemeManagerTests(unittest.TestCase):
    """Tests for ThemeManager Light/Dark persistence and application."""

    def setUp(self) -> None:
        self.db = DBManager(":memory:")
        self.theme = ThemeManager(self.db)

    def test_current_returns_default_light(self) -> None:
        """
        Scenario: current() returns 'light' when no config stored
        Given: fresh DBManager with no theme config
        When:  current() is called
        Then:  returns 'light'
        """
        # --- ARRANGE / ACT ---
        result = self.theme.current()
        # --- ASSERT ---
        self.assertEqual(result, "light")

    def test_current_returns_persisted_dark(self) -> None:
        """
        Scenario: current() returns persisted theme
        Given: DBManager with theme=dark in app_config
        When:  current() is called
        Then:  returns 'dark'
        """
        # --- ARRANGE ---
        self.db.set_config("theme", "dark")
        # --- ACT ---
        result = self.theme.current()
        # --- ASSERT ---
        self.assertEqual(result, "dark")

    def test_toggle_flips_and_persists(self) -> None:
        """
        Scenario: toggle() flips light���dark and writes to app_config
        Given: fresh DBManager (defaults to light)
        When:  toggle(app) is called
        Then:  returns 'dark' and DB has theme=dark
        """
        # --- ARRANGE ---
        mock_app = MagicMock()
        # --- ACT ---
        new_theme = self.theme.toggle(mock_app)
        # --- ASSERT ---
        self.assertEqual(new_theme, "dark")
        self.assertEqual(self.db.get_config("theme"), "dark")

    def test_apply_sets_stylesheet(self) -> None:
        """
        Scenario: apply(app) calls app.setStyleSheet with correct QSS
        Given: ThemeManager with theme=dark
        When:  apply(mock_app) is called
        Then:  mock_app.setStyleSheet called with DARK_QSS
        """
        # --- ARRANGE ---
        self.db.set_config("theme", "dark")
        mock_app = MagicMock()
        # --- ACT ---
        self.theme.apply(mock_app)
        # --- ASSERT ---
        mock_app.setStyleSheet.assert_called_once()
        called_qss = mock_app.setStyleSheet.call_args[0][0]
        self.assertIn("background-color: #1e1e22", called_qss)  # DARK_QSS signature


if __name__ == "__main__":
    unittest.main()