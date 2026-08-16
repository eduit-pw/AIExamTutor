"""SQLite access layer — single source of truth for all persistence.

DRY anchor per CLAUDE.md §2. Every module that needs a database connection or
a config value must go through this class. Never open `sqlite3.connect(...)`
anywhere else in the codebase.

Designed to support both production (file-backed) and test (`:memory:`) usage.
The schema is loaded once per connection via `schema.sql` shipped as a package
data file (see pyproject.toml [tool.setuptools.package-data]).
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path
from typing import Any


class DBManager:
    """Thin wrapper around sqlite3 with config/attempt/message/draft helpers.

    Public surface (all methods are instance methods so tests can mock easily):
      - config:     get_config, set_config, all_config
      - attempts:   create_attempt, finish_attempt, get_attempt, list_attempts
      - messages:   add_message, list_messages
      - drafts:     save_draft, load_draft, delete_draft

    Every method is small, single-purpose, and free of business logic — the
    workspace modules own the rules; DBManager owns the SQL.
    """

    def __init__(self, path: str | Path) -> None:
        """Open (or create) the SQLite database and apply the schema.

        Args:
            path: filesystem path or the special token ":memory:" for tests.
        """
        self._path = str(path)
        self._conn = sqlite3.connect(self._path, detect_types=sqlite3.PARSE_DECLTYPES)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._apply_schema()
        self._conn.commit()

    # ------------------------------------------------------------------
    # Schema bootstrap
    # ------------------------------------------------------------------
    def _apply_schema(self) -> None:
        schema_text = (
            resources.files("app.database").joinpath("schema.sql").read_text(encoding="utf-8")
        )
        self._conn.executescript(schema_text)

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    def close(self) -> None:
        """Close the underlying connection. Safe to call multiple times."""
        self._conn.close()

    @staticmethod
    def _utcnow_iso() -> str:
        return datetime.now(tz=UTC).isoformat(timespec="seconds")

    # ------------------------------------------------------------------
    # app_config
    # ------------------------------------------------------------------
    def get_config(self, key: str, default: str | None = None) -> str | None:
        """Return the value for `key`, or `default` if absent."""
        row = self._conn.execute(
            "SELECT value FROM app_config WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row is not None else default

    def set_config(self, key: str, value: str) -> None:
        """Insert or update a single config key. Commits immediately."""
        self._conn.execute(
            """
            INSERT INTO app_config (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self._conn.commit()

    def all_config(self) -> dict[str, str]:
        """Return a snapshot of every config key/value pair."""
        rows = self._conn.execute("SELECT key, value FROM app_config").fetchall()
        return {row["key"]: row["value"] for row in rows}

    # ------------------------------------------------------------------
    # attempts
    # ------------------------------------------------------------------
    def create_attempt(self, subject: str, exam_pdf: str | None = None) -> int:
        """Start a new attempt and return its primary key."""
        cursor = self._conn.execute(
            "INSERT INTO attempts (subject, exam_pdf, started_at) VALUES (?, ?, ?)",
            (subject, exam_pdf, self._utcnow_iso()),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def finish_attempt(self, attempt_id: int, score: dict[str, Any]) -> None:
        """Mark an attempt as finished and persist the score JSON.

        Args:
            attempt_id: primary key of the attempt to close.
            score: per-rubric mapping, e.g. {"correctness": 0.8, "readability": 1.0}.
        """
        self._conn.execute(
            "UPDATE attempts SET finished_at = ?, score_json = ? WHERE id = ?",
            (self._utcnow_iso(), json.dumps(score), attempt_id),
        )
        self._conn.commit()

    def get_attempt(self, attempt_id: int) -> dict[str, Any] | None:
        """Return one attempt as a dict, or None if not found."""
        row = self._conn.execute(
            "SELECT * FROM attempts WHERE id = ?", (attempt_id,)
        ).fetchone()
        return dict(row) if row is not None else None

    def list_attempts(self, subject: str | None = None) -> list[dict[str, Any]]:
        """Return all attempts, newest first. Optionally filtered by subject."""
        if subject is None:
            rows = self._conn.execute(
                "SELECT * FROM attempts ORDER BY started_at DESC, id DESC"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM attempts WHERE subject = ? ORDER BY started_at DESC, id DESC",
                (subject,),
            ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # messages (chat history)
    # ------------------------------------------------------------------
    def add_message(self, attempt_id: int, role: str, content: str) -> int:
        """Append a chat message and return its primary key."""
        if role not in {"user", "assistant", "system"}:
            raise ValueError(f"invalid role: {role!r}")
        cursor = self._conn.execute(
            "INSERT INTO messages (attempt_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (attempt_id, role, content, self._utcnow_iso()),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def list_messages(self, attempt_id: int) -> list[dict[str, Any]]:
        """Return the full chat transcript for an attempt, oldest first."""
        rows = self._conn.execute(
            "SELECT * FROM messages WHERE attempt_id = ? ORDER BY created_at ASC",
            (attempt_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    # ------------------------------------------------------------------
    # drafts (editor auto-save)
    # ------------------------------------------------------------------
    def save_draft(self, attempt_id: int, file_name: str, content: str) -> None:
        """Upsert an editor draft. Called by the 500 ms debounce timer."""
        self._conn.execute(
            """
            INSERT INTO drafts (attempt_id, file_name, content, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(attempt_id, file_name) DO UPDATE
                SET content = excluded.content, updated_at = excluded.updated_at
            """,
            (attempt_id, file_name, content, self._utcnow_iso()),
        )
        self._conn.commit()

    def load_draft(self, attempt_id: int, file_name: str) -> str | None:
        """Return the saved draft content, or None if no draft exists."""
        row = self._conn.execute(
            "SELECT content FROM drafts WHERE attempt_id = ? AND file_name = ?",
            (attempt_id, file_name),
        ).fetchone()
        return row["content"] if row is not None else None

    def delete_draft(self, attempt_id: int, file_name: str) -> None:
        """Remove a draft explicitly (e.g. on workspace switch)."""
        self._conn.execute(
            "DELETE FROM drafts WHERE attempt_id = ? AND file_name = ?",
            (attempt_id, file_name),
        )
        self._conn.commit()