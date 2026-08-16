"""Cross-cutting modules: config, logger, theme, LLM client."""

from app.core import config as cfg
from app.core.llm_client import LLMClient, LLMError
from app.core.logger import configure_logging, get_logger
from app.core.theme_manager import ThemeManager

__all__ = [
    "LLMClient",
    "LLMError",
    "ThemeManager",
    "cfg",
    "configure_logging",
    "get_logger",
]
