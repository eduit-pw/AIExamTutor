"""Rotating file logger — DRY anchor per CLAUDE.md §2.

Exposes a single `get_logger(name)` that returns a configured logger. Logs go
to BOTH stderr (for dev) and a rotating file under %LOCALAPPDATA%/AIExamTutor/
so support tickets can include `app.log` without leaking user data.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "ai_exam_tutor"
_INITIALISED = False


def _default_log_path() -> Path:
    """Resolve %LOCALAPPDATA%/AIExamTutor/app.log, creating dirs as needed."""
    base = Path.home() / "AppData" / "Local" / "AIExamTutor"
    base.mkdir(parents=True, exist_ok=True)
    return base / "app.log"


def configure_logging(log_path: Path | None = None) -> None:
    """Idempotently set up the root logger. Called from main() at startup."""
    global _INITIALISED
    if _INITIALISED:
        return

    log_path = log_path or _default_log_path()
    log_path.parent.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(log_path, maxBytes=512_000, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(formatter)

    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)

    root = logging.getLogger(_LOGGER_NAME)
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(stderr_handler)
    root.propagate = False

    _INITIALISED = True


def get_logger(child_name: str | None = None) -> logging.Logger:
    """Return a logger namespaced under `ai_exam_tutor`.

    Call `configure_logging()` once at startup before logging anything.
    """
    if not _INITIALISED:
        configure_logging()
    suffix = f".{child_name}" if child_name else ""
    return logging.getLogger(f"{_LOGGER_NAME}{suffix}")
