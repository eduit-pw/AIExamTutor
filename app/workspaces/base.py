"""Abstract base class for every subject workspace.

Defined per spec §4.1. Concrete subclasses live in this same package
(inf03.py is the v1.0 reference; the others raise NotImplementedError until
v1.1+).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from PySide6.QtWidgets import QWidget

from app.core.llm_client import LLMClient
from app.database.db_manager import DBManager


class BaseWorkspace(ABC):
    """Every subject-specific workspace implements this contract.

    Subclasses are expected to:
      1. Set the class attributes `workspace_id` and `display_name`.
      2. Register themselves with WorkspaceFactory at import time.
      3. Load their .ui via QUiLoader in `build_widget()`.
      4. Snapshot their current state in `build_context_payload()` so the
         AI Tutor can answer with full context.
      5. Compute rubric scores in `grade()` when the student finishes.
    """

    workspace_id: str = ""
    display_name: str = ""

    def __init__(self, attempt_id: int, db: DBManager, llm_client: LLMClient) -> None:
        """Store construction inputs. Do NOT touch Qt here — use build_widget()."""
        self.attempt_id = attempt_id
        self.db = db
        self.llm_client = llm_client

    # ------------------------------------------------------------------
    # Contract
    # ------------------------------------------------------------------
    @abstractmethod
    def build_widget(self) -> QWidget:
        """Return the central widget loaded from a .ui via QUiLoader."""

    @abstractmethod
    def build_context_payload(self) -> dict[str, Any]:
        """Return the dict merged into every Tutor chat request.

        Must be JSON-serializable. Examples:
          inf03 -> {"sql_query": "...", "php_source": "...", "html_source": "..."}
        """

    def tutor_system_prompt(self) -> str:
        """Return the system prompt used for this workspace's tutor."""
        return (
            "You are a helpful exam tutor. Guide the student without giving away the final answer."
        )

    @abstractmethod
    def grade(self) -> dict[str, Any]:
        """Return the validated score report for the current attempt.

        The exact report shape belongs to the workspace. Implementations must
        return JSON-compatible data and must not expose provider-specific
        response objects to the UI.
        """
