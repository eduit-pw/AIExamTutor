"""About dialog with a compact student manual."""

from __future__ import annotations

from importlib import resources
from io import BytesIO

import qrcode
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTextBrowser,
    QVBoxLayout,
)

from app.core.localization import LANGUAGE_ENGLISH, translate

SUPPORT_URL = "https://eduit.net.pl/"


MANUAL_HTML_BY_LANGUAGE: dict[str, dict[str, str]] = {
    "pl": {
        "inf03": """
        <h2>Skrócona instrukcja ucznia: INF.03</h2>
        <h3>Zanim zaczniesz</h3>
        <p>Przygotuj arkusz INF.03 w PDF oraz, jeśli chcesz korzystać z oceniania,
        osobny klucz odpowiedzi. Do pracy z SQL potrzebujesz uruchomionego MySQL,
        na przykład przez XAMPP. Skonfiguruj lokalnego lub chmurowego dostawcę AI.</p>
        <h3>Pierwsze uruchomienie</h3>
        <ol>
            <li>Otwórz <b>Plik -&gt; Ustawienia</b> i wybierz dostawcę, model oraz język.</li>
            <li>Otwórz arkusz przez <b>Plik -&gt; Otwórz PDF</b>.</li>
            <li>Opcjonalnie otwórz <b>Plik -&gt; Otwórz PDF z kluczem odpowiedzi</b>.</li>
            <li>Wyślij krótkie pytanie testowe do tutora AI.</li>
        </ol>
        <h3>Środowisko INF.03</h3>
        <p>W środkowym panelu znajdziesz SQL, wynik zapytania oraz zakładki
        <b>index.php</b>, <b>index.html</b> i <b>style.css</b>. Szkice są automatycznie
        zapisywane. <b>Zapisz bieżący plik</b> zapisuje plik na dysku, a
        <b>Uruchom w przeglądarce</b> pokazuje podgląd HTML/CSS. SQL uruchomisz przez
        <b>Uruchom SQL</b> lub <b>Ctrl+Enter</b>.</p>
        <h3>PDF i tutor</h3>
        <p>Lewy panel pokazuje arkusz. Użyj <b>Zaznacz fragment</b>, aby wysłać tutorowi
        fragment strony. Tutor AI pomaga rozumować i sprawdzać wymagania, zamiast
        automatycznie podawać całe rozwiązanie.</p>
        <h3>Bezpieczeństwo</h3>
        <p>Nie wysyłaj klucza API tutorowi ani nie publikuj go na zrzutach ekranu.
        Dostawcy chmurowi mogą naliczać opłaty za zapytania i obrazy.</p>
        """,
        "default": """
        <h2>Skrócona instrukcja ucznia</h2>
        <p>Wybierz workspace, aby wyświetlić instrukcję dopasowaną do jego zadań.</p>
        <h3>Podstawowy workflow</h3>
        <ol>
            <li>Otwórz arkusz PDF.</li>
            <li>Skonfiguruj dostawcę AI w ustawieniach.</li>
            <li>Pracuj w aktywnym workspace.</li>
            <li>Użyj tutora do sprawdzania rozumowania i wymagań zadania.</li>
        </ol>
        <h3>Bezpieczeństwo</h3>
        <p>Nie publikuj klucza API i sprawdź koszty dostawcy chmurowego przed użyciem.</p>
        """,
    },
    LANGUAGE_ENGLISH: {
        "inf03": """
        <h2>Compact student guide: INF.03</h2>
        <h3>Before you start</h3>
        <p>Prepare the INF.03 exam sheet as a PDF and, if you want to use grading,
        a separate answer key. SQL work requires a running MySQL server, for example
        through XAMPP. Configure a local or cloud AI provider.</p>
        <h3>First launch</h3>
        <ol>
            <li>Open <b>File -&gt; Settings</b> and choose the provider, model, and language.</li>
            <li>Open the exam sheet through <b>File -&gt; Open PDF</b>.</li>
            <li>Optionally open the answer-key PDF.</li>
            <li>Send the tutor a short test question.</li>
        </ol>
        <h3>INF.03 workspace</h3>
        <p>The center panel contains SQL, query results, and the <b>index.php</b>,
        <b>index.html</b>, and <b>style.css</b> tabs. Drafts are saved automatically.
        <b>Save current file</b> writes a file to disk, while <b>Run in browser</b>
        previews HTML/CSS. Run SQL with <b>Run SQL</b> or <b>Ctrl+Enter</b>.</p>
        <h3>PDF and tutor</h3>
        <p>The left panel displays the exam sheet. Use <b>Snip Region</b> to send
        a page fragment to the tutor. The tutor supports reasoning and requirement
        checking instead of automatically giving the complete solution.</p>
        <h3>Security</h3>
        <p>Do not send your API key to the tutor or publish it in screenshots.
        Cloud providers may charge for requests and images.</p>
        """,
        "default": """
        <h2>Compact student guide</h2>
        <p>Select a workspace to display instructions tailored to its tasks.</p>
        <h3>Basic workflow</h3>
        <ol>
            <li>Open the exam sheet PDF.</li>
            <li>Configure an AI provider in Settings.</li>
            <li>Work in the active workspace.</li>
            <li>Use the tutor to check your reasoning and task requirements.</li>
        </ol>
        <h3>Security</h3>
        <p>Do not publish your API key and check cloud-provider costs before use.</p>
        """,
    },
}


class AboutDialog(QDialog):
    """Show application information and the compact student manual."""

    def __init__(self, workspace_id: str = "inf03", language: str = "pl", parent=None) -> None:
        super().__init__(parent)
        self._workspace_id = workspace_id
        self._language = language
        self._load_ui()

    def _load_ui(self) -> None:
        loader = QUiLoader()
        with resources.as_file(resources.files("app.ui.views").joinpath("AboutDialog.ui")) as path:
            widget = loader.load(str(path), self)
        if widget is None:
            raise RuntimeError("QUiLoader returned None for AboutDialog.ui")

        button_box = widget.findChild(QDialogButtonBox, "buttonBox")
        manual_browser = widget.findChild(QTextBrowser, "manualBrowser")
        title_label = widget.findChild(QLabel, "titleLabel")
        support_label = widget.findChild(QLabel, "supportLabel")
        qr_code_label = widget.findChild(QLabel, "qrCodeLabel")
        support_link_label = widget.findChild(QLabel, "supportLinkLabel")
        if (
            button_box is None
            or manual_browser is None
            or support_label is None
            or qr_code_label is None
            or support_link_label is None
        ):
            raise LookupError("AboutDialog.ui is missing required widgets")
        button_box.rejected.connect(self.reject)
        button_box.accepted.connect(self.accept)
        close_button = button_box.button(QDialogButtonBox.StandardButton.Close)
        if close_button is not None:
            close_button.setText(translate("AboutDialog", "Close"))
        if title_label is not None:
            title_label.setText(translate("AboutDialog", "<b>AI Exam Tutor</b><br/>Version 1.2.0"))
        support_label.setText(
            translate(
                "AboutDialog",
                "<b>Support the project</b><br/>"
                "If the app helps you learn, you can support its development.",
            )
        )
        support_link_label.setText(f'<a href="{SUPPORT_URL}">{SUPPORT_URL}</a>')
        qr_image = qrcode.make(SUPPORT_URL)
        qr_bytes = BytesIO()
        qr_image.save(qr_bytes, format="PNG")
        image = QImage()
        image.loadFromData(qr_bytes.getvalue(), "PNG")
        qr_code_label.setPixmap(
            QPixmap.fromImage(image).scaled(
                220,
                220,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        manual_browser.setHtml(
            MANUAL_HTML_BY_LANGUAGE.get(self._language, MANUAL_HTML_BY_LANGUAGE["pl"]).get(
                self._workspace_id,
                MANUAL_HTML_BY_LANGUAGE[
                    self._language if self._language in MANUAL_HTML_BY_LANGUAGE else "pl"
                ]["default"],
            )
        )

        self.setWindowTitle(translate("AboutDialog", "About AI Exam Tutor"))
        layout = QVBoxLayout(self)
        layout.addWidget(widget)
        self.resize(720, 620)
