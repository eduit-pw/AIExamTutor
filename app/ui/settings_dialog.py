"""Provider and model settings dialog."""

from __future__ import annotations

from importlib import resources

from PySide6.QtCore import QThread, Signal
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.core import config as cfg
from app.core.llm_client import LLMClient
from app.core.localization import LANGUAGE_OPTIONS, translate
from app.database.db_manager import DBManager

PROVIDERS: tuple[tuple[str, str], ...] = (
    (cfg.PROVIDER_OPENAI, "OpenAI"),
    (cfg.PROVIDER_GEMINI, "Google Gemini"),
    (cfg.PROVIDER_OPENROUTER, "OpenRouter"),
    (cfg.PROVIDER_GROQ, "Groq"),
    (cfg.PROVIDER_LMSTUDIO, "LM Studio"),
    (cfg.PROVIDER_OLLAMA, "Ollama"),
    (cfg.PROVIDER_OMNIROUTE, "OmniRoute"),
    (cfg.PROVIDER_CUSTOM, "Custom OpenAI-compatible"),
)

MODELS: dict[str, tuple[str, ...]] = {
    cfg.PROVIDER_OPENAI: ("gpt-4o", "gpt-4o-mini"),
    cfg.PROVIDER_GEMINI: ("gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.5-flash-8b"),
    cfg.PROVIDER_OPENROUTER: ("openai/gpt-4o-mini", "openai/gpt-4o"),
    cfg.PROVIDER_GROQ: ("llama-3.2-11b-vision", "llama-3.1-70b-versatile"),
    cfg.PROVIDER_LMSTUDIO: ("local-model",),
    cfg.PROVIDER_OLLAMA: ("llava", "llama3.2"),
    cfg.PROVIDER_OMNIROUTE: ("local-model",),
    cfg.PROVIDER_CUSTOM: ("local-model",),
}


class _ConnectionTestWorker(QThread):
    """Send a minimal request without blocking the settings dialog."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(
        self, llm: LLMClient, provider: str, model: str, api_key: str, base_url: str
    ) -> None:
        super().__init__()
        self._llm = llm
        self._provider = provider
        self._model = model
        self._api_key = api_key
        self._base_url = base_url

    def run(self) -> None:
        try:
            reply = self._llm.test_connection(
                self._provider,
                self._model,
                self._api_key,
                self._base_url,
            )
            self.succeeded.emit(reply)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class SettingsDialog(QDialog):
    """Edit the active provider and its persisted connection settings."""

    connection_succeeded = Signal(str)

    def __init__(self, db: DBManager, llm: LLMClient, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._llm = llm
        self._test_worker: _ConnectionTestWorker | None = None
        self._load_ui()
        self._provider_combo.currentIndexChanged.connect(self._provider_changed)
        self._test_connection_button.clicked.connect(self._test_connection)
        self._button_box.accepted.connect(self._save)
        self._button_box.rejected.connect(self.reject)
        self._load_values()

    def _load_ui(self) -> None:
        loader = QUiLoader()
        with resources.as_file(
            resources.files("app.ui.views").joinpath("SettingsDialog.ui")
        ) as path:
            widget = loader.load(str(path), self)
        if widget is None:
            raise RuntimeError("QUiLoader returned None for SettingsDialog.ui")
        self.setWindowTitle(translate("SettingsDialog", "AI Tutor Settings"))
        self._provider_combo = widget.findChild(QComboBox, "providerComboBox")
        self._model_combo = widget.findChild(QComboBox, "modelComboBox")
        self._api_key = widget.findChild(QLineEdit, "apiKeyLineEdit")
        self._base_url = widget.findChild(QLineEdit, "baseUrlLineEdit")
        self._language_combo = widget.findChild(QComboBox, "languageComboBox")
        self._test_connection_button = widget.findChild(QPushButton, "testConnectionButton")
        self._button_box = widget.findChild(QDialogButtonBox, "buttonBox")
        if any(
            value is None
            for value in (
                self._provider_combo,
                self._model_combo,
                self._api_key,
                self._base_url,
                self._language_combo,
                self._test_connection_button,
                self._button_box,
            )
        ):
            raise LookupError("SettingsDialog.ui is missing required widgets")
        self._apply_translations(widget)
        layout = QVBoxLayout(self)
        layout.addWidget(widget)

    def _apply_translations(self, widget) -> None:
        """Apply translations to UI-loaded controls and standard buttons."""
        self.setWindowTitle(translate("SettingsDialog", "AI Tutor Settings"))
        for object_name, source_text in (
            ("providerLabel", "Provider"),
            ("modelLabel", "Model"),
            ("apiKeyLabel", "API key"),
            ("baseUrlLabel", "Base URL"),
            ("languageLabel", "Language"),
        ):
            label = widget.findChild(QLabel, object_name)
            if label is not None:
                label.setText(translate("SettingsDialog", source_text))
        save_button = self._button_box.button(QDialogButtonBox.StandardButton.Save)
        cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if save_button is not None:
            save_button.setText(translate("SettingsDialog", "Save"))
        if cancel_button is not None:
            cancel_button.setText(translate("SettingsDialog", "Cancel"))
        self._test_connection_button.setText(translate("SettingsDialog", "Test connection"))

    def _load_values(self) -> None:
        self._provider_combo.clear()
        for provider_id, label in PROVIDERS:
            self._provider_combo.addItem(translate("SettingsDialog", label), provider_id)
        self._language_combo.clear()
        for language_id, label in LANGUAGE_OPTIONS:
            self._language_combo.addItem(label, language_id)
        language = self._db.get_config(cfg.LANGUAGE, "pl")
        language_index = self._language_combo.findData(language)
        self._language_combo.setCurrentIndex(max(language_index, 0))
        self._initial_language = self._language_combo.currentData()
        provider = self._db.get_config(cfg.ACTIVE_PROVIDER, cfg.PROVIDER_OPENAI)
        index = self._provider_combo.findData(provider)
        self._provider_combo.setCurrentIndex(max(index, 0))

    def _provider_changed(self) -> None:
        provider = self._provider_combo.currentData()
        self._model_combo.clear()
        self._model_combo.addItems(MODELS.get(provider, ()))
        saved_model = self._db.get_config(cfg.model_key(provider), "")
        if saved_model and self._model_combo.findText(saved_model) < 0:
            self._model_combo.addItem(saved_model)
        if saved_model:
            self._model_combo.setCurrentText(saved_model)
        self._api_key.setText(self._db.get_config(cfg.api_key_key(provider), "") or "")
        self._base_url.setText(
            self._db.get_config(
                cfg.base_url_key(provider), LLMClient.DEFAULT_BASE_URLS.get(provider, "")
            )
            or ""
        )

    def _save(self) -> None:
        provider = self._provider_combo.currentData()
        model = self._model_combo.currentText().strip()
        base_url = self._base_url.text().strip()
        if not model or (provider == cfg.PROVIDER_CUSTOM and not base_url):
            QMessageBox.warning(
                self,
                translate("SettingsDialog", "Incomplete settings"),
                translate(
                    "SettingsDialog",
                    "Select a model and provide a base URL for a custom provider.",
                ),
            )
            return
        self._save_provider_settings(provider, model, base_url)
        selected_language = self._language_combo.currentData()
        self._db.set_config(cfg.LANGUAGE, selected_language)
        if selected_language != self._initial_language:
            QMessageBox.information(
                self,
                translate("SettingsDialog", "Language changed"),
                translate(
                    "SettingsDialog",
                    "Restart the application to apply the new language.",
                ),
            )
        self.accept()

    def _save_provider_settings(self, provider: str, model: str, base_url: str) -> None:
        """Persist the exact provider fields currently shown in the dialog."""
        self._db.set_config(cfg.ACTIVE_PROVIDER, provider)
        self._db.set_config(cfg.model_key(provider), model)
        self._db.set_config(cfg.api_key_key(provider), self._api_key.text())
        self._db.set_config(cfg.base_url_key(provider), base_url)

    def _test_connection(self) -> None:
        """Send a minimal request using the current, unsaved form values."""
        if self._test_worker is not None:
            return
        provider = self._provider_combo.currentData()
        model = self._model_combo.currentText().strip()
        base_url = self._base_url.text().strip()
        if not model or (provider == cfg.PROVIDER_CUSTOM and not base_url):
            QMessageBox.warning(
                self,
                translate("SettingsDialog", "Incomplete settings"),
                translate(
                    "SettingsDialog",
                    "Select a model and provide a base URL for a custom provider.",
                ),
            )
            return
        self._test_connection_button.setEnabled(False)
        self._test_connection_button.setText(translate("SettingsDialog", "Testing..."))
        self._test_worker = _ConnectionTestWorker(
            self._llm,
            provider,
            model,
            self._api_key.text(),
            base_url,
        )
        self._test_worker.succeeded.connect(self._test_succeeded)
        self._test_worker.failed.connect(self._test_failed)
        self._test_worker.finished.connect(self._test_finished)
        self._test_worker.start()

    def _test_succeeded(self, reply: str) -> None:
        self.connection_succeeded.emit(self._provider_combo.currentText())
        preview = " ".join(reply.strip().split())[:120]
        QMessageBox.information(
            self,
            translate("SettingsDialog", "Connection successful"),
            translate("SettingsDialog", "The API responded successfully.")
            + (f"\n\n{preview}" if preview else ""),
        )

    def _test_failed(self, error: str) -> None:
        QMessageBox.warning(
            self,
            translate("SettingsDialog", "Connection failed"),
            translate("SettingsDialog", "The API did not respond: %1").replace("%1", error),
        )

    def _test_finished(self) -> None:
        self._test_worker = None
        self._test_connection_button.setEnabled(True)
        self._test_connection_button.setText(translate("SettingsDialog", "Test connection"))
