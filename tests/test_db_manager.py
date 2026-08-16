"""Tests for DBManager — SQLite persistence layer.

Per ADR-005: built-in unittest, AAA pattern, Gherkin docstrings,
:memory: database for isolation.
"""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.database.db_manager import DBManager


class DBManagerConfigTests(unittest.TestCase):
    """Tests for DBManager app_config key/value persistence."""

    def test_new_file_database_is_created_with_schema(self) -> None:
        """
        Scenario: First application start creates the SQLite database
        Given: a path that does not contain a database file
        When:  I construct DBManager for that path
        Then:  the file and all application tables exist
        """
        # --- ARRANGE ---
        with TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "new_exam_tutor.db"
            self.assertFalse(database_path.exists())
            # --- ACT ---
            db = DBManager(database_path)
            tables = {
                row[0]
                for row in db._conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            # --- ASSERT ---
            self.assertTrue(database_path.is_file())
            self.assertTrue({"app_config", "attempts", "messages", "drafts"}.issubset(tables))
            db.close()

    def test_set_and_get_round_trip(self) -> None:
        """
        Scenario: Round-trip a config value through DBManager
        Given: an in-memory DBManager with an empty app_config table
        When:  I set 'api_key_openai' to 'sk-test-1234'
        Then:  get('api_key_openai') returns 'sk-test-1234'
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        # --- ACT ---
        db.set_config("api_key_openai", "sk-test-1234")
        # --- ASSERT ---
        self.assertEqual(db.get_config("api_key_openai"), "sk-test-1234")

    def test_get_missing_returns_default(self) -> None:
        """
        Scenario: Missing config key returns provided default
        Given: an in-memory DBManager with no config rows
        When:  I call get_config('missing_key', 'default-value')
        Then:  the result is 'default-value'
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        # --- ACT ---
        result = db.get_config("missing_key", "default-value")
        # --- ASSERT ---
        self.assertEqual(result, "default-value")

    def test_overwrite_existing_key(self) -> None:
        """
        Scenario: set_config overwrites an existing key
        Given: an in-memory DBManager with 'theme' set to 'light'
        When:  I set 'theme' to 'dark'
        Then:  get_config('theme') returns 'dark'
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        db.set_config("theme", "light")
        # --- ACT ---
        db.set_config("theme", "dark")
        # --- ASSERT ---
        self.assertEqual(db.get_config("theme"), "dark")

    def test_all_config_returns_snapshot(self) -> None:
        """
        Scenario: all_config returns every key/value pair
        Given: an in-memory DBManager with three config rows
        When:  I call all_config()
        Then:  the dict contains exactly those three pairs
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        db.set_config("a", "1")
        db.set_config("b", "2")
        db.set_config("c", "3")
        # --- ACT ---
        snapshot = db.all_config()
        # --- ASSERT ---
        self.assertEqual(snapshot, {"a": "1", "b": "2", "c": "3"})


class DBManagerAttemptsTests(unittest.TestCase):
    """Tests for attempt lifecycle (create, finish, list)."""

    def test_create_attempt_returns_id(self) -> None:
        """
        Scenario: create_attempt inserts a row and returns its PK
        Given: an in-memory DBManager
        When:  I call create_attempt('inf03', 'path.pdf')
        Then:  the return value is an integer > 0
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        # --- ACT ---
        attempt_id = db.create_attempt("inf03", "path.pdf")
        # --- ASSERT ---
        self.assertIsInstance(attempt_id, int)
        self.assertGreater(attempt_id, 0)

    def test_finish_attempt_persists_score(self) -> None:
        """
        Scenario: finish_attempt writes finished_at and score_json
        Given: an attempt created with create_attempt
        When:  I call finish_attempt with a score dict
        Then:  the attempt row has finished_at and score_json populated
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        score = {"correctness": 0.8, "readability": 1.0}
        # --- ACT ---
        db.finish_attempt(attempt_id, score)
        # --- ASSERT ---
        row = db.get_attempt(attempt_id)
        self.assertIsNotNone(row["finished_at"])
        self.assertIn("correctness", row["score_json"])

    def test_list_attempts_orders_by_started_desc(self) -> None:
        """
        Scenario: list_attempts returns newest first
        Given: two attempts created in sequence
        When:  I call list_attempts()
        Then:  the first element is the second attempt
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        id1 = db.create_attempt("inf03")
        id2 = db.create_attempt("inf03")
        # --- ACT ---
        attempts = db.list_attempts()
        # --- ASSERT ---
        self.assertEqual(attempts[0]["id"], id2)
        self.assertEqual(attempts[1]["id"], id1)

    def test_list_attempts_filters_by_subject(self) -> None:
        """
        Scenario: list_attempts(subject=...) filters correctly
        Given: one 'inf03' attempt and one 'foreign_language' attempt
        When:  I call list_attempts('inf03')
        Then:  only the inf03 attempt is returned
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        db.create_attempt("inf03")
        db.create_attempt("foreign_language")
        # --- ACT ---
        inf03_only = db.list_attempts("inf03")
        # --- ASSERT ---
        self.assertEqual(len(inf03_only), 1)
        self.assertEqual(inf03_only[0]["subject"], "inf03")


class DBManagerMessagesTests(unittest.TestCase):
    """Tests for chat message persistence."""

    def test_add_and_list_messages_preserves_order(self) -> None:
        """
        Scenario: messages are returned in creation order
        Given: an attempt with three messages added sequentially
        When:  I call list_messages(attempt_id)
        Then:  the roles are ['user', 'assistant', 'user'] in that order
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        # --- ACT ---
        db.add_message(attempt_id, "user", "Hello")
        db.add_message(attempt_id, "assistant", "Hi there")
        db.add_message(attempt_id, "user", "How are you?")
        # --- ASSERT ---
        msgs = db.list_messages(attempt_id)
        self.assertEqual([m["role"] for m in msgs], ["user", "assistant", "user"])
        self.assertEqual([m["content"] for m in msgs], ["Hello", "Hi there", "How are you?"])

    def test_add_message_rejects_invalid_role(self) -> None:
        """
        Scenario: add_message raises ValueError for unknown role
        Given: an in-memory DBManager and a valid attempt_id
        When:  I call add_message with role='invalid'
        Then:  ValueError is raised
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        # --- ACT / ASSERT ---
        with self.assertRaises(ValueError):
            db.add_message(attempt_id, "invalid", "oops")

    def test_messages_cascaded_on_attempt_delete(self) -> None:
        """
        Scenario: deleting an attempt removes its messages (FK cascade)
        Given: an attempt with two messages, then the attempt is deleted via SQL
        When:  I list messages for that attempt_id
        Then:  the result is empty
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        db.add_message(attempt_id, "user", "x")
        db.add_message(attempt_id, "assistant", "y")
        # --- ACT ---
        db._conn.execute("DELETE FROM attempts WHERE id = ?", (attempt_id,))
        db._conn.commit()
        # --- ASSERT ---
        self.assertEqual(db.list_messages(attempt_id), [])


class DBManagerDraftsTests(unittest.TestCase):
    """Tests for editor auto-save drafts."""

    def test_save_and_load_draft_round_trip(self) -> None:
        """
        Scenario: save_draft + load_draft preserves content
        Given: an attempt with no prior drafts
        When:  I save 'query.sql' = 'SELECT 1', then load it
        Then:  load_draft returns 'SELECT 1'
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        # --- ACT ---
        db.save_draft(attempt_id, "query.sql", "SELECT 1")
        # --- ASSERT ---
        self.assertEqual(db.load_draft(attempt_id, "query.sql"), "SELECT 1")

    def test_save_draft_overwrites_existing(self) -> None:
        """
        Scenario: saving same file_name twice overwrites
        Given: a draft 'index.php' with content 'old'
        When:  I save 'index.php' with content 'new'
        Then:  load_draft returns 'new'
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        db.save_draft(attempt_id, "index.php", "old")
        # --- ACT ---
        db.save_draft(attempt_id, "index.php", "new")
        # --- ASSERT ---
        self.assertEqual(db.load_draft(attempt_id, "index.php"), "new")

    def test_delete_draft_removes_row(self) -> None:
        """
        Scenario: delete_draft removes the draft row
        Given: a draft exists for 'query.sql'
        When:  I call delete_draft(attempt_id, 'query.sql')
        Then:  load_draft returns None
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        db.save_draft(attempt_id, "query.sql", "SELECT 1")
        # --- ACT ---
        db.delete_draft(attempt_id, "query.sql")
        # --- ASSERT ---
        self.assertIsNone(db.load_draft(attempt_id, "query.sql"))


if __name__ == "__main__":
    unittest.main()
