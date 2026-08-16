"""Application language selection and Qt translation loading."""

from __future__ import annotations

from importlib import resources

from PySide6.QtCore import QCoreApplication, QTranslator
from PySide6.QtWidgets import QApplication

from app.core import config as cfg
from app.database.db_manager import DBManager

LANGUAGE_POLISH = "pl"
LANGUAGE_ENGLISH = "en"
DEFAULT_LANGUAGE = LANGUAGE_POLISH

LANGUAGE_OPTIONS: tuple[tuple[str, str], ...] = (
    (LANGUAGE_POLISH, "Polski"),
    (LANGUAGE_ENGLISH, "English"),
)


def translate(context: str, text: str) -> str:
    """Translate a runtime-created GUI string through the active Qt catalog."""
    return QCoreApplication.translate(context, text)


class LanguageManager:
    """Persist and apply the selected Qt translation."""

    def __init__(self, db: DBManager) -> None:
        self._db = db
        self._translator: QTranslator | None = None

    def current(self) -> str:
        """Return a supported language code, defaulting to Polish."""
        value = self._db.get_config(cfg.LANGUAGE, DEFAULT_LANGUAGE)
        return value if value in {LANGUAGE_POLISH, LANGUAGE_ENGLISH} else DEFAULT_LANGUAGE

    def apply(self, app: QApplication, language: str | None = None) -> str:
        """Install the selected translation before creating application widgets."""
        selected = language or self.current()
        if selected not in {LANGUAGE_POLISH, LANGUAGE_ENGLISH}:
            selected = DEFAULT_LANGUAGE
        if self._translator is not None:
            app.removeTranslator(self._translator)
            self._translator = None
        if selected == LANGUAGE_POLISH:
            translator = QTranslator(app)
            with resources.as_file(
                resources.files("translations").joinpath("ai_exam_tutor_pl.qm")
            ) as path:
                if translator.load(str(path)):
                    app.installTranslator(translator)
                    self._translator = translator
        return selected

    def save(self, language: str) -> None:
        """Persist a supported language for the next application start."""
        if language not in {LANGUAGE_POLISH, LANGUAGE_ENGLISH}:
            raise ValueError(f"Unsupported language: {language!r}")
        self._db.set_config(cfg.LANGUAGE, language)
