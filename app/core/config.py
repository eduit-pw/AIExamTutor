"""Centralized constants for `app_config` keys.

Centralizing avoids typo-driven bugs ("api_key_openai" vs "openai_api_key").
Every place in the code that reads/writes a config key should import the
constant from here, never inline the string literal.
"""

from __future__ import annotations

# --- Active provider routing ---
ACTIVE_PROVIDER = "active_provider"  # e.g. "openai", "gemini", "ollama"
ACTIVE_MODEL = "active_model"  # e.g. "gpt-4o", "llama3.2-vision"


# --- Per-provider credentials (suffix is the provider id) ---
def api_key_key(provider_id: str) -> str:
    """Return the config key that stores the API key for `provider_id`."""
    return f"api_key_{provider_id}"


def base_url_key(provider_id: str) -> str:
    """Return the config key that stores the base URL for `provider_id`."""
    return f"base_url_{provider_id}"


def model_key(provider_id: str) -> str:
    """Return the config key that stores the selected model for `provider_id`."""
    return f"model_{provider_id}"


# --- UI / UX preferences ---
THEME = "theme"  # "light" | "dark"
LANGUAGE = "language"  # "pl" | "en", Polish by default
LAST_PDF = "last_pdf"  # absolute path of last opened CKE PDF
ANSWER_KEY_PDF = "answer_key_pdf"  # absolute path of the answer key for AI context
ACTIVE_WORKSPACE = "active_workspace"  # e.g. "inf03" — drives WorkspaceFactory
MYSQL_CONNECTION = "mysql_connection"  # MySQL URL used by the INF.03 SQL runner


def code_file_key(attempt_id: int, file_name: str) -> str:
    """Return the persisted path key for a workspace code file."""
    return f"code_file_{attempt_id}_{file_name}"


# --- Provider identifiers (canonical lowercase ids) ---
PROVIDER_OPENAI = "openai"
PROVIDER_GEMINI = "gemini"
PROVIDER_OPENROUTER = "openrouter"
PROVIDER_GROQ = "groq"
PROVIDER_LMSTUDIO = "lmstudio"
PROVIDER_OLLAMA = "ollama"
PROVIDER_OMNIROUTE = "omniroute"
PROVIDER_CUSTOM = "custom"


# Vision-capability registry. Adding a new vision model? Add it here and the
# warning banner logic in MainWindow will stop nagging automatically.
VISION_CAPABLE_MODELS: frozenset[str] = frozenset(
    {
        # OpenAI
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-vision-preview",
        # Google Gemini
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash-8b",
        # Groq
        "llama-3.2-11b-vision",
        "llama-3.2-90b-vision",
        # Local vision models (frequently used via Ollama / LMStudio)
        "llava",
        "llava:13b",
        "qwen2-vl",
    }
)


def is_vision_capable(model_name: str | None) -> bool:
    """True iff the named model is in the vision-capability registry.

    Matching is exact on lowercase. If a user types a custom variant they
    can opt-in by adding it to VISION_CAPABLE_MODELS.
    """
    if not model_name:
        return False
    return model_name.strip().lower() in VISION_CAPABLE_MODELS
