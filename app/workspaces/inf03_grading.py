"""Background worker used by the INF.03 evaluator."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from app.core.llm_client import LLMClient


class GradeWorker(QThread):
    """Run one evaluator request without blocking the Qt event loop."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        llm_client: LLMClient,
        settings: dict[str, str | None],
        messages: list[dict[str, str]],
    ) -> None:
        super().__init__()
        self._llm_client = llm_client
        self._settings = settings
        self._messages = messages

    def run(self) -> None:
        try:
            self.succeeded.emit(
                self._llm_client.chat_with_settings(
                    self._settings.get("provider"),
                    self._settings.get("model"),
                    self._settings.get("api_key", "") or "",
                    self._settings.get("base_url"),
                    self._messages,
                )
            )
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
