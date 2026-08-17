"""Qt wrapper for the local Monaco bundle provided by Rocher."""

from __future__ import annotations

import json
import os
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtWidgets import QApplication, QPlainTextEdit, QVBoxLayout, QWidget

try:
    from PySide6.QtWebChannel import QWebChannel
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError:  # pragma: no cover - exercised only without Qt WebEngine
    QWebChannel = None  # type: ignore[assignment,misc]
    QWebEngineView = None  # type: ignore[assignment,misc]

try:
    import rocher
except ImportError:  # pragma: no cover - dependency is required in production
    rocher = None  # type: ignore[assignment]


class _MonacoBridge(QObject):
    """Receive Monaco model changes through Qt WebChannel."""

    def __init__(self, owner: MonacoEditor) -> None:
        super().__init__(owner)
        self._owner = owner

    @Slot(str)
    def reportContent(self, content: str) -> None:  # noqa: N802
        self._owner._receive_content(content)


class MonacoEditor(QWidget):
    """A QPlainTextEdit-compatible editor backed by Monaco when available."""

    textChanged = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = ""
        self._language = "javascript"
        self._theme = self._current_theme()
        self._web_view: QWebEngineView | None = None
        self._fallback_editor: QPlainTextEdit | None = None
        self._bridge: _MonacoBridge | None = None
        self._channel: QWebChannel | None = None
        self._layout: QVBoxLayout | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._layout = layout
        if self._can_use_web_engine():
            self._build_monaco(layout)
        else:
            self._build_fallback(layout)

    def _can_use_web_engine(self) -> bool:
        """Keep offscreen tests and environments without WebEngine deterministic."""
        return (
            os.environ.get("QT_QPA_PLATFORM") != "offscreen"
            and rocher is not None
            and QWebEngineView is not None
            and QWebChannel is not None
        )

    def _build_fallback(self, layout: QVBoxLayout) -> None:
        self._fallback_editor = QPlainTextEdit(self)
        self._fallback_editor.setStyleSheet("border: none; border-radius: 0; padding: 0;")
        self._fallback_editor.textChanged.connect(self._on_fallback_changed)
        layout.addWidget(self._fallback_editor)

    def _build_monaco(self, layout: QVBoxLayout) -> None:
        assert rocher is not None
        assert QWebEngineView is not None
        assert QWebChannel is not None
        self._web_view = QWebEngineView(self)
        self._web_view.setVisible(False)
        self._web_view.setStyleSheet("border: none; background: transparent;")
        self._bridge = _MonacoBridge(self)
        self._channel = QWebChannel(self._web_view.page())
        self._channel.registerObject("bridge", self._bridge)
        self._web_view.page().setWebChannel(self._channel)
        self._web_view.loadFinished.connect(self._on_page_loaded)
        self._web_view.setHtml(self._build_html(), self._base_url())
        layout.addWidget(self._web_view)

    @staticmethod
    def _current_theme() -> str:
        application = QApplication.instance()
        theme = application.property("ai_exam_tutor_theme") if application else None
        return "vs" if theme != "dark" else "vs-dark"

    def _base_url(self) -> QUrl:
        assert rocher is not None
        package_root = Path(rocher.path()).parent
        return QUrl.fromLocalFile(str(package_root) + os.sep)

    def _build_html(self) -> str:
        assert rocher is not None
        editor_html = rocher.editor_html(
            "vs",
            "monaco-container",
            self._language,
            self._value,
            theme=self._theme,
            automaticLayout=True,
            minimap={"enabled": False},
        ).replace("/static/vs", "vs")
        return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<style>
html, body, #monaco-container {{ width: 100%; height: 100%; margin: 0; overflow: hidden; }}
</style>
</head>
<body>
<div id="monaco-container"></div>
<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
{editor_html}
<script>
(function connectBridge() {{
    if (!window.monaco || !monaco.editor || !monaco.editor.getModels().length) {{
        window.setTimeout(connectBridge, 25);
        return;
    }}
    new QWebChannel(qt.webChannelTransport, function(channel) {{
        const bridge = channel.objects.bridge;
        const model = monaco.editor.getModels()[0];
        model.onDidChangeContent(function() {{ bridge.reportContent(model.getValue()); }});
        bridge.reportContent(model.getValue());
        window.__aiExamTutorModel = model;
    }});
}})();
</script>
</body>
</html>"""

    def _on_page_loaded(self, loaded: bool) -> None:
        if not loaded or self._web_view is None:
            failed_view = self._web_view
            self._web_view = None
            if failed_view is not None:
                failed_view.deleteLater()
            if self._fallback_editor is None and self._layout is not None:
                self._build_fallback(self._layout)
            return
        self._web_view.setVisible(True)
        self.set_language(self._language)

    def _on_fallback_changed(self) -> None:
        assert self._fallback_editor is not None
        self._value = self._fallback_editor.toPlainText()
        self.textChanged.emit()

    def _receive_content(self, content: str) -> None:
        if content == self._value:
            return
        self._value = content
        self.textChanged.emit()

    def set_language(self, language: str) -> None:
        self._language = language
        if self._web_view is not None:
            language_json = json.dumps(language)
            self._web_view.page().runJavaScript(
                f"window.__aiExamTutorModel && monaco.editor.setModelLanguage("
                f"window.__aiExamTutorModel, {language_json});"
            )

    def set_theme(self, theme: str) -> None:
        """Switch Monaco's palette without changing the current document."""
        self._theme = "vs-dark" if theme == "dark" else "vs"
        if self._web_view is not None:
            theme_json = json.dumps(self._theme)
            self._web_view.page().runJavaScript(f"monaco.editor.setTheme({theme_json});")

    def toPlainText(self) -> str:  # noqa: N802
        if self._fallback_editor is not None:
            return self._fallback_editor.toPlainText()
        return self._value

    def setPlainText(self, text: str) -> None:  # noqa: N802
        self._value = text
        if self._fallback_editor is not None:
            self._fallback_editor.setPlainText(text)
            return
        if self._web_view is not None:
            text_json = json.dumps(text)
            self._web_view.page().runJavaScript(
                f"window.__aiExamTutorModel && window.__aiExamTutorModel.setValue({text_json});"
            )

    def document(self):
        """Return the fallback document for compatibility with old callers."""
        if self._fallback_editor is not None:
            return self._fallback_editor.document()
        return None

    def setPlaceholderText(self, text: str) -> None:  # noqa: N802
        if self._fallback_editor is not None:
            self._fallback_editor.setPlaceholderText(text)

    def setMinimumHeight(self, height: int) -> None:  # noqa: N802
        super().setMinimumHeight(height)
        if self._fallback_editor is not None:
            self._fallback_editor.setMinimumHeight(height)

    def setMaximumHeight(self, height: int) -> None:  # noqa: N802
        super().setMaximumHeight(height)
        if self._fallback_editor is not None:
            self._fallback_editor.setMaximumHeight(height)
