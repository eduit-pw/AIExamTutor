"""Polish language & History essay workspace. [v1.1+ stub]"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from app.core.llm_client import LLMClient
from app.database.db_manager import DBManager
from app.workspaces.base import BaseWorkspace
from app.workspaces.factory import WorkspaceFactory


class HumanitiesWorkspace(BaseWorkspace):
    """Essay composition + literary canon dictionary. NOT IMPLEMENTED in v1.0."""

    workspace_id = "humanities"
    display_name = "Polish & History — Essay [v1.1+]"

    def __init__(self, attempt_id: int, db: DBManager, llm_client: LLMClient) -> None:
        super().__init__(attempt_id, db, llm_client)

    def build_widget(self) -> QWidget:
        raise NotImplementedError(
            "HumanitiesWorkspace lands in v1.1. See spec §1.2 (subject #3)."
        )

    def build_context_payload(self) -> dict[str, Any]:
        raise NotImplementedError

    def grade(self) -> dict[str, Any]:
        raise NotImplementedError


WorkspaceFactory.register(HumanitiesWorkspace.workspace_id, HumanitiesWorkspace)