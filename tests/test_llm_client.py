"""Tests for LLMClient — BYOK multi-provider engine.

Per ADR-005: built-in unittest, AAA pattern, Gherkin docstrings.
Uses a stubbed http_poster to avoid network I/O.
"""

import json
import unittest
from typing import Any
from unittest.mock import MagicMock

from app.core.llm_client import LLMClient, LLMError
from app.core import config as cfg
from app.database.db_manager import DBManager


def _make_client(db: DBManager, stub_response: dict[str, Any]) -> LLMClient:
    """Create an LLMClient with a stubbed http_poster that returns `stub_response`."""
    def _stub_poster(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
        # Verify auth header is passed for keyed providers
        if db.get_config(cfg.api_key_key("openai")):
            assert "Authorization" in headers
        return stub_response

    return LLMClient(db, http_poster=_stub_poster)


class LLMClientOpenAICompatTests(unittest.TestCase):
    """Tests for OpenAI-compatible provider routing (OpenAI, Groq, OpenRouter, Local)."""

    def test_connection_uses_explicit_settings(self) -> None:
        """
        Scenario: Connection test sends a minimal request without reading DB settings
        Given: explicit provider, model, API key, and base URL values
        When:  test_connection() is called
        Then:  the request uses those values and asks for exactly OK
        """
        # --- ARRANGE ---
        seen: dict[str, Any] = {}

        def _capture_poster(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
            seen.update(url=url, headers=headers, body=body)
            return {"choices": [{"message": {"content": "OK"}}]}

        client = LLMClient(DBManager(":memory:"), http_poster=_capture_poster)
        # --- ACT ---
        reply = client.test_connection(
            cfg.PROVIDER_OPENAI,
            "test-model",
            "test-key",
            "https://example.test/v1",
        )
        # --- ASSERT ---
        self.assertEqual(reply, "OK")
        self.assertEqual(seen["url"], "https://example.test/v1/chat/completions")
        self.assertEqual(seen["body"]["model"], "test-model")
        self.assertEqual(seen["body"]["messages"][0]["content"], "Reply with exactly: OK")
        self.assertEqual(seen["headers"]["Authorization"], "Bearer test-key")

    def test_connection_rejects_missing_model_or_base_url(self) -> None:
        """
        Scenario: Connection test validates required explicit settings
        Given: an empty model or base URL
        When:  test_connection() is called
        Then:  LLMError explains the missing setting
        """
        # --- ARRANGE ---
        client = LLMClient(DBManager(":memory:"))
        # --- ACT / ASSERT ---
        with self.assertRaisesRegex(LLMError, "No model"):
            client.test_connection(cfg.PROVIDER_OPENAI, "", "", "https://example.test/v1")
        with self.assertRaisesRegex(LLMError, "base URL"):
            client.test_connection(cfg.PROVIDER_OPENAI, "test-model", "", "")

    def test_chat_returns_assistant_text(self) -> None:
        """
        Scenario: chat() returns the assistant's message content
        Given: an LLMClient with active_provider=openai, model=gpt-4o-mini
        When:  I call chat([{"role": "user", "content": "hello"}])
        Then:  the return value equals the stubbed response content
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_OPENAI)
        db.set_config(cfg.model_key(cfg.PROVIDER_OPENAI), "gpt-4o-mini")
        db.set_config(cfg.api_key_key(cfg.PROVIDER_OPENAI), "sk-test")
        stub = {
            "choices": [{"message": {"content": "Hello back!"}}]
        }
        client = _make_client(db, stub)
        # --- ACT ---
        reply = client.chat([{"role": "user", "content": "hello"}])
        # --- ASSERT ---
        self.assertEqual(reply, "Hello back!")

    def test_chat_uses_reasoning_text_when_content_is_empty(self) -> None:
        """
        Scenario: Local OpenAI-compatible model puts its answer in reasoning_content
        Given: a response with empty content and non-empty reasoning_content
        When:  chat() is called
        Then:  the available reasoning text is returned instead of failing as empty
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_LMSTUDIO)
        db.set_config(cfg.model_key(cfg.PROVIDER_LMSTUDIO), "local-model")
        client = LLMClient(
            db,
            http_poster=lambda url, headers, body: {
                "choices": [{
                    "message": {
                        "content": "",
                        "reasoning_content": "Hello from local model",
                    }
                }]
            },
        )
        # --- ACT ---
        reply = client.chat([{"role": "user", "content": "Hello"}])
        # --- ASSERT ---
        self.assertEqual(reply, "Hello from local model")

    def test_chat_raises_on_no_active_provider(self) -> None:
        """
        Scenario: chat() raises LLMError when no provider configured
        Given: an LLMClient with no active_provider set
        When:  I call chat([...])
        Then:  LLMError is raised with a helpful message
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        client = LLMClient(db)
        # --- ACT / ASSERT ---
        with self.assertRaises(LLMError) as cm:
            client.chat([{"role": "user", "content": "x"}])
        self.assertIn("No active provider", str(cm.exception))

    def test_chat_raises_on_missing_base_url(self) -> None:
        """
        Scenario: chat() raises LLMError when base_url missing for provider
        Given: active_provider=custom with no base_url_custom configured
        When:  I call chat([...])
        Then:  LLMError mentions base URL
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_CUSTOM)
        client = LLMClient(db)
        # --- ACT / ASSERT ---
        with self.assertRaises(LLMError) as cm:
            client.chat([{"role": "user", "content": "x"}])
        self.assertIn("base URL", str(cm.exception))

    def test_chat_includes_bearer_token_when_key_present(self) -> None:
        """
        Scenario: Authorization header sent when API key configured
        Given: active_provider=openai with api_key_openai=sk-test
        When:  chat() is called
        Then:  the stubbed http_poster receives Authorization: Bearer sk-test
        """
        # --- ARRANGE ---
        seen_headers: dict[str, str] = {}
        def _capture_poster(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
            seen_headers.update(headers)
            return {"choices": [{"message": {"content": "ok"}}]}
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_OPENAI)
        db.set_config(cfg.api_key_key(cfg.PROVIDER_OPENAI), "sk-test")
        client = LLMClient(db, http_poster=_capture_poster)
        # --- ACT ---
        client.chat([{"role": "user", "content": "x"}])
        # --- ASSERT ---
        self.assertEqual(seen_headers.get("Authorization"), "Bearer sk-test")

    def test_chat_attaches_images_to_last_user_message(self) -> None:
        """
        Scenario: images are base64-inlined into the last user message
        Given: messages=[{"role": "user", "content": "see this"}], images=[b"png"]
        When:  chat() is called
        Then:  the posted body contains a content array with image_url part
        """
        # --- ARRANGE ---
        seen_body: dict[str, Any] = {}
        def _capture_poster(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
            seen_body.update(body)
            return {"choices": [{"message": {"content": "ok"}}]}
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_OPENAI)
        db.set_config(cfg.api_key_key(cfg.PROVIDER_OPENAI), "sk-test")
        client = LLMClient(db, http_poster=_capture_poster)
        png = b"\x89PNG\r\n\x1a\n"  # minimal PNG header
        # --- ACT ---
        client.chat([{"role": "user", "content": "look"}], images=[png])
        # --- ASSERT ---
        last_msg = seen_body["messages"][-1]
        self.assertIsInstance(last_msg["content"], list)
        parts = last_msg["content"]
        self.assertTrue(any(p.get("type") == "image_url" for p in parts))


class LLMClientGeminiTests(unittest.TestCase):
    """Tests for Google Gemini native API routing."""

    def test_chat_gemini_returns_text(self) -> None:
        """
        Scenario: chat() via Gemini returns candidate text
        Given: active_provider=gemini, model=gemini-1.5-flash
        When:  chat() is called
        Then:  the return value equals the stubbed candidate text
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_GEMINI)
        db.set_config(cfg.model_key(cfg.PROVIDER_GEMINI), "gemini-1.5-flash")
        db.set_config(cfg.api_key_key(cfg.PROVIDER_GEMINI), "gemini-key")
        stub = {
            "candidates": [{
                "content": {"parts": [{"text": "Gemini says hi"}]}
            }]
        }
        client = _make_client(db, stub)
        # --- ACT ---
        reply = client.chat([{"role": "user", "content": "hi"}])
        # --- ASSERT ---
        self.assertEqual(reply, "Gemini says hi")

    def test_chat_gemini_includes_api_key_in_url(self) -> None:
        """
        Scenario: Gemini request URL includes ?key=API_KEY
        Given: active_provider=gemini with api_key_gemini=mykey
        When:  chat() is called
        Then:  the stubbed http_poster receives a URL containing key=mykey
        """
        # --- ARRANGE ---
        seen_url: str = ""
        def _capture_poster(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
            nonlocal seen_url
            seen_url = url
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_GEMINI)
        db.set_config(cfg.model_key(cfg.PROVIDER_GEMINI), "gemini-1.5-flash")
        db.set_config(cfg.api_key_key(cfg.PROVIDER_GEMINI), "mykey")
        client = LLMClient(db, http_poster=_capture_poster)
        # --- ACT ---
        client.chat([{"role": "user", "content": "x"}])
        # --- ASSERT ---
        self.assertIn("key=mykey", seen_url)

    def test_chat_gemini_converts_system_prompt(self) -> None:
        """
        Scenario: OpenAI system prompt becomes prepended text in first user message
        Given: messages include a system role message
        When:  chat() is called via Gemini
        Then:  the posted contents[0] parts[0].text starts with the system prompt
        """
        # --- ARRANGE ---
        seen_body: dict[str, Any] = {}
        def _capture_poster(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
            seen_body.update(body)
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_GEMINI)
        db.set_config(cfg.model_key(cfg.PROVIDER_GEMINI), "gemini-1.5-flash")
        db.set_config(cfg.api_key_key(cfg.PROVIDER_GEMINI), "k")
        client = LLMClient(db, http_poster=_capture_poster)
        # --- ACT ---
        client.chat([
            {"role": "system", "content": "You are a tutor."},
            {"role": "user", "content": "Hello"},
        ])
        # --- ASSERT ---
        contents = seen_body["contents"]
        first_user = next(c for c in contents if c["role"] == "user")
        self.assertTrue(first_user["parts"][0]["text"].startswith("You are a tutor."))


class LLMClientHelpersTests(unittest.TestCase):
    """Tests for helper methods: vision detection, chat history."""

    def test_is_vision_capable_true_for_registered_models(self) -> None:
        """
        Scenario: is_vision_capable returns True for known vision models
        Given: active_model set to gpt-4o, gemini-1.5-flash, llama-3.2-11b-vision
        When:  is_vision_capable() is called
        Then:  returns True for each
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_OPENAI)
        for model in ("gpt-4o", "gemini-1.5-flash", "llama-3.2-11b-vision"):
            db.set_config(cfg.model_key(cfg.PROVIDER_OPENAI), model)
            client = LLMClient(db)
            # --- ACT ---
            result = client.is_vision_capable()
            # --- ASSERT ---
            self.assertTrue(result, f"Expected vision capable for {model}")

    def test_is_vision_capable_false_for_text_only_models(self) -> None:
        """
        Scenario: is_vision_capable returns False for text-only models
        Given: active_model set to gpt-3.5-turbo
        When:  is_vision_capable() is called
        Then:  returns False
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        db.set_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_OPENAI)
        db.set_config(cfg.model_key(cfg.PROVIDER_OPENAI), "gpt-3.5-turbo")
        client = LLMClient(db)
        # --- ACT ---
        result = client.is_vision_capable()
        # --- ASSERT ---
        self.assertFalse(result)

    def test_get_chat_history_returns_messages(self) -> None:
        """
        Scenario: get_chat_history returns attempt messages as role/content dicts
        Given: an attempt with three messages in DB
        When:  get_chat_history(attempt_id) is called
        Then:  list of {"role": ..., "content": ...} is returned
        """
        # --- ARRANGE ---
        db = DBManager(":memory:")
        attempt_id = db.create_attempt("inf03")
        db.add_message(attempt_id, "system", "sys")
        db.add_message(attempt_id, "user", "hi")
        db.add_message(attempt_id, "assistant", "hello")
        client = LLMClient(db)
        # --- ACT ---
        history = client.get_chat_history(attempt_id)
        # --- ASSERT ---
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]["role"], "system")
        self.assertEqual(history[1]["content"], "hi")


if __name__ == "__main__":
    unittest.main()