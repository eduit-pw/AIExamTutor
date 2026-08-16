"""BYOK multi-provider LLM client — DRY anchor per CLAUDE.md §2.

Design notes:
  * Pure stdlib networking (urllib) — avoids pinning the OpenAI SDK, keeps the
    PyInstaller bundle small, and matches the LGPLv3 + minimal-deps philosophy.
  * All provider routing is config-driven; switching providers means changing
    `app_config` rows, never touching code.
  * Only the chat-completions shape is implemented. Vision payloads are
    base64-inlined into the user message (OpenAI-style multi-content array).
  * `is_vision_capable()` reads the registry from `app.core.config` so the
    MainWindow banner can warn when the active model lacks vision.

"""

from __future__ import annotations

import base64
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core import config as cfg
from app.core.logger import get_logger
from app.database.db_manager import DBManager

logger = get_logger("llm_client")


class LLMError(RuntimeError):
    """Raised for any LLM-layer failure (network, auth, schema)."""


class LLMClient:
    """Stateless facade over multiple OpenAI-compatible Vision providers.

    Public surface:
      - chat(messages, images=None) -> str
      - active_provider() -> str | None
      - active_model() -> str | None
      - is_vision_capable() -> bool

    The constructor only stores the DB handle; no I/O happens until chat() is
    called. That keeps tests simple: build a DBManager with `:memory:` and a
    custom `HttpPoster` and you can assert routing decisions without a network.
    """

    # OpenAI-compatible default base URLs. Overridden by `base_url_<provider>`.
    DEFAULT_BASE_URLS: dict[str, str] = {
        cfg.PROVIDER_OPENAI: "https://api.openai.com/v1",
        cfg.PROVIDER_GEMINI: "https://generativelanguage.googleapis.com/v1beta",
        cfg.PROVIDER_OPENROUTER: "https://openrouter.ai/api/v1",
        cfg.PROVIDER_GROQ: "https://api.groq.com/openai/v1",
        cfg.PROVIDER_LMSTUDIO: "http://localhost:1234/v1",
        cfg.PROVIDER_OLLAMA: "http://localhost:11434/v1",
        cfg.PROVIDER_OMNIROUTE: "http://localhost:20128/v1",
        cfg.PROVIDER_CUSTOM: "",  # user must supply base_url_custom
    }

    def __init__(self, db: DBManager, http_poster: Any | None = None) -> None:
        """Store db + optional http_poster (overridable for tests)."""
        self._db = db
        # Default poster is the module-level _post_json below; tests inject
        # a stub that returns canned responses without touching the network.
        self._http_poster = http_poster or _post_json

    # ------------------------------------------------------------------
    # Provider routing helpers
    # ------------------------------------------------------------------
    def active_provider(self) -> str | None:
        """Return the configured provider id, or None if unset."""
        return self._db.get_config(cfg.ACTIVE_PROVIDER)

    def active_model(self) -> str | None:
        """Return the configured model for the active provider, or None."""
        provider = self.active_provider()
        if provider is None:
            return None
        return self._db.get_config(cfg.model_key(provider))

    def is_vision_capable(self) -> bool:
        """True iff the currently active model is registered as vision-capable."""
        return cfg.is_vision_capable(self.active_model())

    # ------------------------------------------------------------------
    # Chat history helper
    # ------------------------------------------------------------------
    def get_chat_history(self, attempt_id: int) -> list[dict[str, Any]]:
        """Return the full chat transcript for an attempt as LLM-ready messages.

        Returns a list of {"role": ..., "content": ...} suitable for passing
        directly to `chat()`. Does NOT include images — those must be supplied
        separately by the caller based on current workspace state.
        """
        rows = self._db.list_messages(attempt_id)
        return [{"role": row["role"], "content": row["content"]} for row in rows]

    # ------------------------------------------------------------------
    # Public chat entry point
    # ------------------------------------------------------------------
    def chat(
        self,
        messages: list[dict[str, Any]],
        images: list[bytes] | None = None,
    ) -> str:
        """Send `messages` (optionally with image attachments) to the active provider.

        Args:
            messages: list of {"role": "system"|"user"|"assistant", "content": ...}.
                      May already contain a Socratic system prompt.
            images:   optional list of PNG/JPEG bytes attached to the LAST user
                      message (or a new user message if the last one is assistant).

        Returns:
            The assistant's textual reply.

        Raises:
            LLMError: for any provider / network / schema problem.
        """
        settings = self.connection_settings()
        return self.chat_with_settings(
            settings["provider"],
            settings["model"],
            settings["api_key"],
            settings["base_url"],
            messages,
            images,
        )

    def connection_settings(self) -> dict[str, str | None]:
        """Read provider settings once, in the caller's thread."""
        provider = self.active_provider()
        if provider is None:
            return {"provider": None, "model": None, "api_key": "", "base_url": ""}
        return {
            "provider": provider,
            "model": self.active_model() or self._default_model_for(provider),
            "api_key": self._db.get_config(cfg.api_key_key(provider), "") or "",
            "base_url": self._base_url_for(provider),
        }

    def chat_with_settings(
        self,
        provider: str | None,
        model: str | None,
        api_key: str,
        base_url: str | None,
        messages: list[dict[str, Any]],
        images: list[bytes] | None = None,
    ) -> str:
        """Send chat using settings already read by the caller's thread."""
        if provider is None:
            raise LLMError("No active provider configured. Open Settings (Ctrl+,).")
        if not base_url:
            raise LLMError(f"No base URL configured for provider {provider!r}.")
        if not model:
            raise LLMError("No model configured.")
        # Route to provider-specific implementation
        if provider == cfg.PROVIDER_GEMINI:
            return self._chat_gemini(base_url, api_key, model, messages, images)
        else:
            return self._chat_openai_compatible(base_url, api_key, model, messages, images)

    def test_connection(
        self,
        provider: str,
        model: str,
        api_key: str,
        base_url: str,
    ) -> str:
        """Send a minimal request using explicit settings, without DB access."""
        messages = [{"role": "user", "content": "Reply with exactly: OK"}]
        return self.chat_with_settings(provider, model, api_key, base_url, messages, None)

    def _chat_openai_compatible(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, Any]],
        images: list[bytes] | None,
    ) -> str:
        """Handle OpenAI-compatible endpoints (OpenAI, Groq, OpenRouter, local)."""
        payload_messages = self._maybe_attach_images(messages, images)
        body = {
            "model": model,
            "messages": payload_messages,
            "temperature": 0.4,
        }

        url = f"{base_url.rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            response = self._http_poster(url, headers, body)
        except (HTTPError, URLError, TimeoutError) as exc:
            logger.exception("LLM request failed")
            raise LLMError(f"Network error talking to provider: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"Invalid JSON from provider: {exc}") from exc

        try:
            return self._extract_assistant_text(response)
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected response schema: {exc}") from exc

    def _chat_gemini(
        self,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, Any]],
        images: list[bytes] | None,
    ) -> str:
        """Handle Google Gemini native API format.

        Endpoint: {base_url}/models/{model}:generateContent?key={API_KEY}
        Request format: {"contents": [...], "generationConfig": {...}}
        Response format: {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}
        """
        contents = self._convert_to_gemini_contents(messages, images)
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 4096,
            },
        }

        url = f"{base_url.rstrip('/')}/models/{model}:generateContent"
        if api_key:
            url += f"?key={api_key}"
        headers = {"Content-Type": "application/json"}

        try:
            response = self._http_poster(url, headers, body)
        except (HTTPError, URLError, TimeoutError) as exc:
            logger.exception("Gemini request failed")
            raise LLMError(f"Network error talking to Gemini: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise LLMError(f"Invalid JSON from Gemini: {exc}") from exc

        try:
            return self._extract_gemini_text(response)
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected Gemini response schema: {exc}") from exc

    @staticmethod
    def _convert_to_gemini_contents(
        messages: list[dict[str, Any]],
        images: list[bytes] | None,
    ) -> list[dict[str, Any]]:
        """Convert OpenAI-style messages to Gemini contents format.

        Gemini uses:
          - role: "user" or "model" (not "system" or "assistant")
          - parts: array of {"text": "..."} or {"inlineData": {"mimeType": "...", "data": "..."}}
        System prompt is prepended to the first user message.
        """
        contents = []
        system_prompt = None

        # Extract system prompt if present
        for msg in messages:
            if msg.get("role") == "system":
                system_prompt = msg.get("content", "")
                break

        for msg in messages:
            role = msg.get("role")
            if role == "system":
                continue  # already extracted
            content = msg.get("content", "")

            # Handle OpenAI multi-content format (list of parts)
            if isinstance(content, list):
                parts = []
                for part in content:
                    if part.get("type") == "text":
                        parts.append({"text": part.get("text", "")})
                    elif part.get("type") == "image_url":
                        # Extract base64 from data URL
                        url = part.get("image_url", {}).get("url", "")
                        if url.startswith("data:image/"):
                            header, b64 = url.split(",", 1)
                            mime_type = header.split(";")[0].split(":")[1]
                            parts.append({"inlineData": {"mimeType": mime_type, "data": b64}})
                if parts:
                    gemini_role = "user" if role == "user" else "model"
                    contents.append({"role": gemini_role, "parts": parts})
            else:
                # Simple string content
                parts = [{"text": content}]
                if role == "user" and system_prompt:
                    parts.insert(0, {"text": system_prompt + "\n\n"})
                    system_prompt = None  # only prepend once
                gemini_role = "user" if role == "user" else "model"
                contents.append({"role": gemini_role, "parts": parts})

        # If we still have a system prompt but no user message, add a dummy user message
        if system_prompt and not contents:
            contents.append({"role": "user", "parts": [{"text": system_prompt}]})

        # Attach additional images to the last user message
        if images:
            # Find last user message
            for idx in range(len(contents) - 1, -1, -1):
                if contents[idx].get("role") == "user":
                    for image_bytes in images:
                        b64 = base64.b64encode(image_bytes).decode("ascii")
                        contents[idx]["parts"].append(
                            {"inlineData": {"mimeType": "image/png", "data": b64}}
                        )
                    break

        return contents

    @staticmethod
    def _extract_gemini_text(response: dict[str, Any]) -> str:
        """Extract text from Gemini native response."""
        candidates = response.get("candidates", [])
        if not candidates:
            raise KeyError("No candidates in response")
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            raise KeyError("No parts in candidate content")
        return parts[0].get("text", "")

    # ------------------------------------------------------------------
    # Internal helpers (kept private; not part of the public contract)
    # ------------------------------------------------------------------
    def _base_url_for(self, provider: str) -> str:
        override = self._db.get_config(cfg.base_url_key(provider), "") or ""
        return override or self.DEFAULT_BASE_URLS.get(provider, "")

    @staticmethod
    def _default_model_for(provider: str) -> str:
        """Fallback model when none configured. Local providers usually omit keys."""
        defaults: dict[str, str] = {
            cfg.PROVIDER_OPENAI: "gpt-4o-mini",
            cfg.PROVIDER_GEMINI: "gemini-1.5-flash",
            cfg.PROVIDER_OPENROUTER: "openai/gpt-4o-mini",
            cfg.PROVIDER_GROQ: "llama-3.1-70b-versatile",
            cfg.PROVIDER_LMSTUDIO: "local-model",
            cfg.PROVIDER_OLLAMA: "llama3.2",
            cfg.PROVIDER_OMNIROUTE: "local-model",
            cfg.PROVIDER_CUSTOM: "local-model",
        }
        return defaults.get(provider, "gpt-4o-mini")

    @staticmethod
    def _maybe_attach_images(
        messages: list[dict[str, Any]],
        images: list[bytes] | None,
    ) -> list[dict[str, Any]]:
        """Inline base64-encoded images into the last user message (OpenAI style).

        Returns a NEW list; never mutates the caller's messages.
        """
        if not images:
            return list(messages)

        new_messages = [dict(m) for m in messages]
        # Find the last user-role message; create one if none exists.
        target_index: int | None = None
        for idx in range(len(new_messages) - 1, -1, -1):
            if new_messages[idx].get("role") == "user":
                target_index = idx
                break
        if target_index is None:
            new_messages.append({"role": "user", "content": ""})
            target_index = len(new_messages) - 1

        original_content = new_messages[target_index].get("content") or ""
        content_parts: list[dict[str, Any]] = [
            {"type": "text", "text": original_content},
        ]
        for image_bytes in images:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{b64}"},
                }
            )
        new_messages[target_index]["content"] = content_parts
        return new_messages

    @staticmethod
    def _extract_assistant_text(response: dict[str, Any]) -> str:
        """Pull the assistant text out of an OpenAI-shaped completion."""
        choices = response["choices"]
        first = choices[0]
        message = first["message"]
        content = message.get("content") or ""
        if content.strip():
            return content
        reasoning = message.get("reasoning_content") or ""
        if reasoning.strip():
            return reasoning
        raise KeyError("Assistant response contains no text")


# ----------------------------------------------------------------------
# Module-level networking — overridable via LLMClient(http_poster=...)
# ----------------------------------------------------------------------
def _post_json(url: str, headers: dict[str, str], body: dict[str, Any]) -> dict[str, Any]:
    """POST `body` (JSON) to `url` with `headers`, return the parsed JSON dict.

    Kept module-level so tests can monkeypatch it instead of constructing a
    subclass. The generous timeout accommodates slower local models.
    """
    data = json.dumps(body).encode("utf-8")
    request = Request(url, data=data, headers=headers, method="POST")
    with urlopen(request, timeout=120) as response:  # noqa: S310 — URL is provider-config
        raw = response.read().decode("utf-8")
    return json.loads(raw)
