"""Application entry point.

Boots the QApplication, configures logging + theme, constructs MainWindow,
and runs the event loop. Kept intentionally tiny — all real logic lives in
the `app.*` packages per the DRY anchors in CLAUDE.md.
"""

from __future__ import annotations

import sys
from importlib import resources

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app import __version__
from app.core.localization import LanguageManager
from app.core.logger import configure_logging, get_logger
from app.core.theme_manager import ThemeManager
from app.core.version_check import fetch_latest_release_version, is_newer_version
from app.database.db_manager import DBManager
from app.ui.main_window import MainWindow

logger = get_logger("main")


def main() -> int:
    """Create the QApplication, wire dependencies, run the event loop.

    Returns the Qt exit code.
    """
    configure_logging()
    logger.info("AI Exam Tutor v%s starting", __version__)

    latest_release = fetch_latest_release_version()
    if is_newer_version(__version__, latest_release):
        logger.warning(
            "A newer version is available on GitHub: %s (current: %s)",
            latest_release,
            __version__,
        )

    app = QApplication(sys.argv)
    app.setApplicationName("AI Exam Tutor")
    app.setOrganizationName("EDUIT")
    with resources.as_file(resources.files("resources").joinpath("eduit-favicon.ico")) as icon_path:
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

    db = DBManager("exam_tutor.db")
    language = LanguageManager(db)
    language.apply(app)
    theme = ThemeManager(db)
    theme.apply(app)

    window = MainWindow(db, theme)
    window.setWindowIcon(app.windowIcon())
    window.show()

    logger.info("Entering Qt event loop")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
