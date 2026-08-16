"""Regression tests for background workers and SQLite thread isolation."""

import unittest
from typing import Any

from app.ui.chat_panel import _ChatWorker
from app.ui.settings_dialog import _ConnectionTestWorker
from app.workspaces.inf03_grading import GradeWorker


class _WorkerLLMStub:
    """LLM double that rejects the old DB-backed worker API."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def chat(self, *args: Any, **kwargs: Any) -> str:
        raise AssertionError("Worker must not call DB-backed LLMClient.chat()")

    def chat_with_settings(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("chat_with_settings", args))
        return '{"total_score": 1}'

    def test_connection(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("test_connection", args))
        return "OK"


class WorkerThreadIsolationTests(unittest.TestCase):
    """Ensure background workers receive configuration snapshots."""

    def test_chat_worker_uses_settings_snapshot(self) -> None:
        """
        Scenario: Chat worker does not access SQLite from its background thread
        Given: an LLM stub that rejects DB-backed chat()
        When:  the worker runs with a settings snapshot
        Then:  chat_with_settings() receives the snapshot and message payload
        """
        # --- ARRANGE ---
        llm = _WorkerLLMStub()
        settings = {
            "provider": "lmstudio",
            "model": "local-model",
            "api_key": "",
            "base_url": "http://localhost:1234/v1",
        }
        worker = _ChatWorker(llm, settings, [{"role": "user", "content": "Hello"}])
        result: list[str] = []
        worker.finished_ok.connect(result.append)
        # --- ACT ---
        worker.run()
        # --- ASSERT ---
        self.assertEqual(result, ['{"total_score": 1}'])
        self.assertEqual(llm.calls[0][0], "chat_with_settings")
        self.assertEqual(llm.calls[0][1][0], "lmstudio")

    def test_connection_worker_uses_explicit_settings(self) -> None:
        """
        Scenario: Connection worker does not read SQLite settings
        Given: an LLM stub with explicit connection-test support
        When:  the worker runs with provider settings
        Then:  test_connection() receives those settings
        """
        # --- ARRANGE ---
        llm = _WorkerLLMStub()
        worker = _ConnectionTestWorker(
            llm, "lmstudio", "local-model", "", "http://localhost:1234/v1"
        )
        result: list[str] = []
        worker.succeeded.connect(result.append)
        # --- ACT ---
        worker.run()
        # --- ASSERT ---
        self.assertEqual(result, ["OK"])
        self.assertEqual(llm.calls[0][0], "test_connection")
        self.assertEqual(
            llm.calls[0][1], ("lmstudio", "local-model", "", "http://localhost:1234/v1")
        )

    def test_grade_worker_uses_settings_snapshot(self) -> None:
        """
        Scenario: Grade worker does not access SQLite from its background thread
        Given: an LLM stub that rejects DB-backed chat()
        When:  the grading worker runs with a settings snapshot
        Then:  chat_with_settings() is used for evaluation
        """
        # --- ARRANGE ---
        llm = _WorkerLLMStub()
        settings = {
            "provider": "lmstudio",
            "model": "local-model",
            "api_key": "",
            "base_url": "http://localhost:1234/v1",
        }
        worker = GradeWorker(llm, settings, [{"role": "user", "content": "grade"}])
        result: list[str] = []
        worker.succeeded.connect(result.append)
        # --- ACT ---
        worker.run()
        # --- ASSERT ---
        self.assertEqual(result, ['{"total_score": 1}'])
        self.assertEqual(llm.calls[0][0], "chat_with_settings")


if __name__ == "__main__":
    unittest.main()
