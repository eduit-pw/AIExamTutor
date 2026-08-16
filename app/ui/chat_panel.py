"""AI Tutor chat panel — right pane.

Displays chat history with the AI Tutor, sends user messages with workspace
auto-context, and stores everything in the messages table (per spec §0.2).
Supports image attachments from the PDF viewer's region snip.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core import config as cfg
from app.core.llm_client import LLMClient, LLMError
from app.core.localization import translate
from app.core.logger import get_logger
from app.database.db_manager import DBManager
from app.workspaces.base import BaseWorkspace

logger = get_logger("ui.chat_panel")


class _ChatWorker(QThread):
    """Background worker for LLM chat calls (keeps UI responsive)."""

    finished_ok = Signal(str)
    finished_err = Signal(str)

    def __init__(
        self,
        llm: LLMClient,
        settings: dict,
        messages: list[dict],
        images: list[bytes] | None = None,
    ) -> None:
        super().__init__()
        self._llm = llm
        self._settings = settings
        self._messages = messages
        self._images = images or []

    def run(self) -> None:
        try:
            reply = self._llm.chat_with_settings(
                self._settings.get("provider"),
                self._settings.get("model"),
                self._settings.get("api_key", ""),
                self._settings.get("base_url"),
                self._messages,
                self._images,
            )
            self.finished_ok.emit(reply)
        except LLMError as exc:
            self.finished_err.emit(str(exc))
        except Exception as exc:  # noqa: BLE001
            self.finished_err.emit(f"Unexpected error: {exc}")


class ChatPanel(QWidget):
    """Scrollable chat history + input box + send button."""

    def __init__(self, db: DBManager, llm: LLMClient, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._llm = llm
        self._active_attempt_id: int | None = None
        self._active_workspace: BaseWorkspace | None = None
        self._pending_images: list[bytes] = []

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header
        header = QLabel(translate("ChatPanel", "AI Tutor (Socratic)"))
        header.setStyleSheet("font-weight: bold; padding: 4px;")
        layout.addWidget(header)

        # Chat history (scrollable)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)

        self._history_widget = QWidget()
        self._history_layout = QVBoxLayout(self._history_widget)
        self._history_layout.setAlignment(self._history_layout.alignment() | 0x0080)  # AlignTop
        self._scroll.setWidget(self._history_widget)
        layout.addWidget(self._scroll, 1)

        # Input area
        input_layout = QVBoxLayout()
        self._attachment_label = QLabel("")
        input_layout.addWidget(self._attachment_label)

        text_row = QHBoxLayout()
        self._input = QPlainTextEdit()
        self._input.setPlaceholderText(translate("ChatPanel", "Ask the AI Tutor..."))
        self._input.setMaximumHeight(80)
        text_row.addWidget(self._input, 1)

        self._send_btn = QPushButton(translate("ChatPanel", "Send (Ctrl+Enter)"))
        self._send_btn.clicked.connect(self._send)
        text_row.addWidget(self._send_btn)
        input_layout.addLayout(text_row)

        layout.addLayout(input_layout)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self._send)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_active_attempt(self, attempt_id: int) -> None:
        """Bind the chat panel to an attempt and reload its history."""
        self._active_attempt_id = attempt_id
        self._reload_history()

    def set_active_workspace(self, workspace: BaseWorkspace | None) -> None:
        """Bind the workspace used for automatic tutor context injection."""
        self._active_workspace = workspace

    def attach_image(self, png_bytes: bytes) -> None:
        """Queue an image to be sent with the next message."""
        self._pending_images.append(png_bytes)
        self._attachment_label.setText(
            translate("ChatPanel", "📎 %1 image(s) attached — click Send").replace(
                "%1", str(len(self._pending_images))
            )
        )

    # ------------------------------------------------------------------
    # Send / receive
    # ------------------------------------------------------------------
    def _send(self) -> None:
        text = self._input.toPlainText().strip()
        if not text and not self._pending_images:
            return
        if self._active_attempt_id is None:
            self._append_message("system", "No active attempt. Open a workspace first.")
            return

        attempt_id = self._active_attempt_id

        # Save user message
        self._db.add_message(attempt_id, "user", text)
        self._append_message("user", text)
        self._input.clear()

        # Build messages with workspace context
        messages = self._build_context_messages(attempt_id, text)
        images = list(self._pending_images)
        self._pending_images.clear()
        self._attachment_label.setText("")

        # Disable send button while waiting
        self._send_btn.setEnabled(False)
        self._send_btn.setText(translate("ChatPanel", "Thinking..."))

        # Spin up background worker
        self._worker = _ChatWorker(self._llm, self._llm.connection_settings(), messages, images)
        self._worker.finished_ok.connect(self._on_reply)
        self._worker.finished_err.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_reply(self, reply: str) -> None:
        if self._active_attempt_id is not None:
            self._db.add_message(self._active_attempt_id, "assistant", reply)
        self._append_message("assistant", reply)

    def _on_error(self, error: str) -> None:
        self._append_message("system", f"[Error] {error}")

    def _on_worker_done(self) -> None:
        self._send_btn.setEnabled(True)
        self._send_btn.setText(translate("ChatPanel", "Send (Ctrl+Enter)"))
        self._worker = None

    # ------------------------------------------------------------------
    # History rendering
    # ------------------------------------------------------------------
    def _reload_history(self) -> None:
        # Clear existing
        while self._history_layout.count():
            item = self._history_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if self._active_attempt_id is None:
            return

        rows = self._db.list_messages(self._active_attempt_id)
        for row in rows:
            self._append_message(row["role"], row["content"])

    def _append_message(self, role: str, content: str) -> None:
        label = QLabel()
        if role == "user":
            label.setText(f"🙋 <b>You:</b><br>{content}")
            label.setStyleSheet(
                "background-color: #007aff; color: white; padding: 8px; "
                "border-radius: 8px; margin: 4px;"
            )
        elif role == "assistant":
            label.setText(f"🤖 <b>Tutor:</b><br>{content}")
            label.setStyleSheet(
                "background-color: #34c759; color: white; padding: 8px; "
                "border-radius: 8px; margin: 4px;"
            )
        else:
            label.setText(f"ℹ️ {content}")
            label.setStyleSheet(
                "background-color: #8e8e93; color: white; padding: 8px; "
                "border-radius: 8px; margin: 4px;"
            )
        label.setWordWrap(True)
        label.setTextFormat(Qt.TextFormat.RichText)
        self._history_layout.addWidget(label)
        # Auto-scroll to bottom
        self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum())

    # ------------------------------------------------------------------
    # Context injection
    # ------------------------------------------------------------------
    def _build_context_messages(self, attempt_id: int, user_text: str) -> list[dict]:
        """Build the full message list sent to the LLM, including history + system prompt.

        The system prompt comes from the active workspace (if any).
        """
        history = self._db.list_messages(attempt_id)
        messages = []
        if self._active_workspace is not None:
            prompt = self._active_workspace.tutor_system_prompt()
            context = self._active_workspace.build_context_payload()
            context.setdefault("exam_pdf", self._db.get_config(cfg.LAST_PDF, "") or "")
            answer_key_path = self._db.get_config(cfg.ANSWER_KEY_PDF, "") or ""
            context.setdefault("answer_key_pdf", answer_key_path)
            context.setdefault("answer_key_text", self._read_pdf_text(answer_key_path))
            messages.append({"role": "system", "content": prompt})
            messages.append(
                {
                    "role": "system",
                    "content": "Current workspace context:\n"
                    + json.dumps(context, ensure_ascii=False),
                }
            )
        for row in history:
            messages.append({"role": row["role"], "content": row["content"]})

        # The user_text is already the last entry in history (added in _send).
        # We don't need to re-add it — the LLM will see it as the last turn.
        return messages

    @staticmethod
    def _read_pdf_text(path: str) -> str:
        """Extract bounded answer-key text for the tutor when PyMuPDF is available."""
        if not path or not Path(path).exists():
            return ""
        try:
            import fitz

            with fitz.open(path) as document:
                text = "\n".join(page.get_text() for page in document)
            return text[:30000]
        except Exception:  # noqa: BLE001
            return ""
