"""INF.03 reference workspace — SQL Runner + PHP/HTML/CSS/JavaScript editor.

This is the only fully-implemented workspace in v1.0. It exercises every
piece of the architecture: QUiLoader for the widget tree, the 500 ms debounce
timer for auto-save, the Socratic prompt, and the auto-context payload.

Widget loading: see `build_widget()`. When the .ui file is missing (early
development / CI smoke test), we fall back to a programmatically-built widget
tree that uses the same objectNames the .ui would set. Once `INF03Workspace.ui`
is dropped into `app/ui/views/workspaces/`, the QUiLoader path takes over and
the fallback is bypassed.

Register with WorkspaceFactory at import time.
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableView,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.core import config as cfg
from app.core.llm_client import LLMClient, LLMError
from app.core.localization import translate
from app.core.logger import get_logger
from app.database.db_manager import DBManager
from app.ui.monaco_editor import MonacoEditor
from app.workspaces.base import BaseWorkspace
from app.workspaces.factory import WorkspaceFactory
from app.workspaces.inf03_grading import GradeWorker
from app.workspaces.inf03_highlighters import SqlHighlighter

logger = get_logger("workspace.inf03")

# Auto-save debounce interval per spec §0.2 / §1.2.
AUTOSAVE_DEBOUNCE_MS = 500
MAX_PDF_CONTEXT_CHARS = 30_000
DEFAULT_CONNECTION_STRING = "mysql://root:@localhost:3306/"


# ----------------------------------------------------------------------
# Workspace
# ----------------------------------------------------------------------
class INF03Workspace(BaseWorkspace):
    """SQL Runner plus PHP/HTML/CSS/JavaScript editor, per spec §0.2."""

    workspace_id = "inf03"
    display_name = "INF.03 — SQL & PHP/HTML/CSS/JavaScript"

    DEFAULT_FILES: tuple[str, ...] = (
        "query.sql",
        "index.php",
        "index.html",
        "style.css",
        "script.js",
    )

    def __init__(self, attempt_id: int, db: DBManager, llm_client: LLMClient) -> None:
        super().__init__(attempt_id, db, llm_client)
        self._root: QWidget | None = None
        self._sql_editor: QPlainTextEdit | None = None
        self._php_editor: MonacoEditor | None = None
        self._html_editor: MonacoEditor | None = None
        self._css_editor: MonacoEditor | None = None
        self._js_editor: MonacoEditor | None = None
        self._results_view: QTableView | None = None
        self._schema_combo: QComboBox | None = None
        self._status: QLabel | None = None
        self._autosave_timer: QTimer | None = None
        self._connection_input: QLineEdit | None = None
        self._code_tabs: QTabWidget | None = None
        self._splitter_timer: QTimer | None = None
        self._grade_worker: GradeWorker | None = None
        self._check_button: QPushButton | None = None
        self._active = True
        self._status_callback = None
        self._connection_callback = None

    def set_status_callback(self, callback) -> None:
        """Send workspace feedback messages to the main status bar."""
        self._status_callback = callback

    def set_connection_callback(self, callback) -> None:
        """Notify the main window when the database connection succeeds."""
        self._connection_callback = callback

    def deactivate(self) -> None:
        """Ignore late worker results when this workspace leaves the UI."""
        self._active = False

    # ------------------------------------------------------------------
    # BaseWorkspace contract
    # ------------------------------------------------------------------
    def build_widget(self) -> QWidget:
        """Load INF03Workspace.ui if present, else build the tree programmatically.

        Both code paths produce widgets with the SAME objectNames so the
        rest of this class doesn't care which path was taken.
        """
        logger.info("Building INF.03 widget")
        try:
            widget = self._load_from_ui()
        except (FileNotFoundError, LookupError):
            logger.warning("INF03Workspace.ui not found; building programmatically")
            widget = self._build_programmatic()

        logger.info("Wiring INF.03 widget signals")
        self._wire_signals(widget)
        logger.info("Restoring INF.03 drafts")
        self._restore_drafts(widget)
        self._configure_splitter(widget)
        logger.info("INF.03 widget ready")
        return widget

    def build_context_payload(self) -> dict[str, Any]:
        """Snapshot the current editor state for the AI Tutor."""
        return {
            "sql_query": self._current_sql(),
            "php_source": self._current_php(),
            "html_source": self._current_html(),
            "css_source": self._current_css(),
            "javascript_source": self._current_javascript(),
            "schema": self._current_schema(),
        }

    def grade(self) -> dict[str, Any]:
        """Evaluate the current solution against the exam and answer key."""
        if not self.db.get_config(cfg.ANSWER_KEY_PDF, ""):
            return {}
        response = self.llm_client.chat(self._build_grade_messages())
        score = self._parse_grade_response(response)
        self.db.finish_attempt(self.attempt_id, score)
        return score

    def tutor_system_prompt(self) -> str:
        """Return the INF.03 Socratic prompt used for every chat request."""
        return self._socratic_prompt()

    # ------------------------------------------------------------------
    # .ui loading + fallback builder
    # ------------------------------------------------------------------
    def _load_from_ui(self) -> QWidget:
        loader = QUiLoader()
        loader.registerCustomWidget(MonacoEditor)
        from importlib import resources

        with resources.as_file(
            resources.files("app.ui.views.workspaces").joinpath("INF03Workspace.ui")
        ) as ui_path:
            if not ui_path.exists():
                raise FileNotFoundError(str(ui_path))
            logger.info("Loading INF.03 declarative view: %s", ui_path)
            widget = loader.load(str(ui_path))  # type: ignore[arg-type]
        if widget is None:
            raise FileNotFoundError("QUiLoader returned None")
        self._capture_widget_refs(widget)
        logger.info("INF.03 declarative view loaded and references captured")
        return widget

    def _build_programmatic(self) -> QWidget:
        """Construct the same widget tree by hand when the .ui is missing.

        Object names must match the .ui that Qt Designer will eventually
        produce (see spec §3.1).
        """
        root = QWidget()
        root.setObjectName("INF03Root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(8, 8, 8, 8)

        workspace_tabs = QTabWidget()
        workspace_tabs.setObjectName("workspaceTabs")

        # --- SQL tab ---
        sql_tab = QWidget()
        sql_layout = QVBoxLayout(sql_tab)
        top_row = QHBoxLayout()
        self._schema_combo = QComboBox()
        self._schema_combo.setObjectName("schemaComboBox")
        self._schema_combo.addItem("(no schema)")
        run_btn = QPushButton(translate("INF03Workspace", "Run SQL"))
        run_btn.setObjectName("runSqlButton")
        top_row.addWidget(QLabel(translate("INF03Workspace", "Schema")))
        top_row.addWidget(self._schema_combo, 1)
        top_row.addWidget(run_btn)
        sql_layout.addLayout(top_row)

        connection_toggle = QToolButton()
        connection_toggle.setObjectName("connectionSettingsToggle")
        connection_toggle.setText(translate("INF03Workspace", "Database connection settings"))
        connection_toggle.setCheckable(True)
        connection_toggle.setChecked(False)
        connection_toggle.setArrowType(Qt.ArrowType.RightArrow)
        sql_layout.addWidget(connection_toggle)

        connection_panel = QWidget()
        connection_panel.setObjectName("connectionSettingsPanel")
        connection_panel.setVisible(False)
        connection_row = QHBoxLayout(connection_panel)
        connection_row.addWidget(QLabel(translate("INF03Workspace", "Connection")))
        self._connection_input = QLineEdit(
            self.db.get_config(cfg.MYSQL_CONNECTION, DEFAULT_CONNECTION_STRING)
        )
        self._connection_input.setObjectName("connectionStringLineEdit")
        self._connection_input.setPlaceholderText("mysql://user:password@host:3306/database")
        connection_row.addWidget(self._connection_input, 1)
        save_connection = QPushButton(translate("INF03Workspace", "Save"))
        save_connection.setObjectName("saveConnectionButton")
        connection_row.addWidget(save_connection)
        test_connection = QPushButton(translate("INF03Workspace", "Test"))
        test_connection.setObjectName("testConnectionButton")
        connection_row.addWidget(test_connection)
        sql_layout.addWidget(connection_panel)

        sql_splitter = QSplitter(Qt.Orientation.Vertical)
        sql_splitter.setObjectName("sqlSplitter")

        self._sql_editor = QPlainTextEdit()
        self._sql_editor.setObjectName("sqlEditor")
        self._sql_editor.setPlaceholderText("SELECT * FROM ...")
        SqlHighlighter(self._sql_editor.document())
        sql_splitter.addWidget(self._sql_editor)

        self._results_view = QTableView()
        self._results_view.setObjectName("resultsTable")
        self._results_view.setAlternatingRowColors(True)
        self._results_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        sql_splitter.addWidget(self._results_view)
        sql_layout.addWidget(sql_splitter, 1)
        workspace_tabs.addTab(sql_tab, translate("INF03Workspace", "Database (SQL)"))

        # --- Source tabs ---
        self._php_editor = MonacoEditor()
        self._php_editor.setObjectName("phpEditor")
        self._php_editor.set_language("php")
        self._html_editor = MonacoEditor()
        self._html_editor.setObjectName("htmlEditor")
        self._html_editor.set_language("html")
        self._css_editor = MonacoEditor()
        self._css_editor.setObjectName("cssEditor")
        self._css_editor.set_language("css")
        self._js_editor = MonacoEditor()
        self._js_editor.setObjectName("jsEditor")
        self._js_editor.set_language("javascript")
        workspace_tabs.addTab(self._php_editor, "index.php")
        workspace_tabs.addTab(self._html_editor, "index.html")
        workspace_tabs.addTab(self._css_editor, "style.css")
        workspace_tabs.addTab(self._js_editor, "script.js")
        self._code_tabs = workspace_tabs
        outer.addWidget(workspace_tabs, 1)

        code_actions = QHBoxLayout()
        code_actions.addStretch()
        save_code = QPushButton(translate("INF03Workspace", "Save file"))
        save_code.setObjectName("saveCodeButton")
        check_task = QPushButton(translate("INF03Workspace", "Check task"))
        check_task.setObjectName("checkTaskButton")
        browser_btn = QPushButton(translate("INF03Workspace", "Preview"))
        browser_btn.setToolTip(translate("INF03Workspace", "Preview in browser"))
        browser_btn.setObjectName("runBrowserButton")
        send_chat = QPushButton(translate("INF03Workspace", "Send to chat"))
        send_chat.setObjectName("sendToChatButton")
        for button in (save_code, browser_btn, send_chat, check_task):
            code_actions.addWidget(button)
        outer.addLayout(code_actions)

        self._root = root
        return root

    def _configure_splitter(self, widget: QWidget) -> None:
        """Give the active editor most of the SQL tab and keep it adjustable."""
        splitter = widget.findChild(QSplitter, "sqlSplitter")
        if splitter is None:
            return
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        def set_initial_sizes() -> None:
            total = splitter.height()
            if total > 0:
                splitter.setSizes([int(total * 0.72), int(total * 0.28)])

        self._splitter_timer = QTimer(splitter)
        self._splitter_timer.setSingleShot(True)
        self._splitter_timer.timeout.connect(set_initial_sizes)
        self._splitter_timer.start(0)

    def _capture_widget_refs(self, widget: QWidget) -> None:
        """After QUiLoader, locate child widgets by their objectName."""
        self._root = widget
        self._sql_editor = widget.findChild(QPlainTextEdit, "sqlEditor")
        self._php_editor = widget.findChild(MonacoEditor, "phpEditor")
        self._html_editor = widget.findChild(MonacoEditor, "htmlEditor")
        self._css_editor = widget.findChild(MonacoEditor, "cssEditor")
        self._results_view = widget.findChild(QTableView, "resultsTable")
        self._schema_combo = widget.findChild(QComboBox, "schemaComboBox")
        self._status = widget.findChild(QLabel, "statusLabel")
        self._connection_input = widget.findChild(QLineEdit, "connectionStringLineEdit")
        self._code_tabs = widget.findChild(QTabWidget, "workspaceTabs")
        self._js_editor = widget.findChild(MonacoEditor, "jsEditor")
        # Fail loudly if any expected widget is missing — that means the .ui
        # was edited and forgot to rename something.
        for name, ref in (
            ("sqlEditor", self._sql_editor),
            ("phpEditor", self._php_editor),
            ("htmlEditor", self._html_editor),
            ("cssEditor", self._css_editor),
            ("resultsTable", self._results_view),
            ("schemaComboBox", self._schema_combo),
            ("connectionStringLineEdit", self._connection_input),
            ("workspaceTabs", self._code_tabs),
            ("jsEditor", self._js_editor),
        ):
            if ref is None:
                raise LookupError(f"INF03Workspace .ui missing widget {name!r}")
        SqlHighlighter(self._sql_editor.document())
        self._php_editor.set_language("php")
        self._html_editor.set_language("html")
        self._css_editor.set_language("css")
        self._js_editor.set_language("javascript")

    # ------------------------------------------------------------------
    # Signal wiring + auto-save
    # ------------------------------------------------------------------
    def _wire_signals(self, widget: QWidget) -> None:
        # 500 ms debounced auto-save timer.
        self._autosave_timer = QTimer(widget)
        self._autosave_timer.setSingleShot(True)
        self._autosave_timer.setInterval(AUTOSAVE_DEBOUNCE_MS)
        self._autosave_timer.timeout.connect(self._flush_drafts)

        # Restart the debounce on every text change.
        for editor in (
            self._sql_editor,
            self._php_editor,
            self._html_editor,
            self._css_editor,
            self._js_editor,
        ):
            assert editor is not None
            editor.textChanged.connect(self._autosave_timer.start)

        # Ctrl+Enter executes SQL.
        if self._sql_editor is not None:
            shortcut = QShortcut(QKeySequence("Ctrl+Return"), self._sql_editor)
            shortcut.activated.connect(self._run_sql)
            run_btn = widget.findChild(QPushButton, "runSqlButton")
            if run_btn is not None:
                run_btn.clicked.connect(self._run_sql)
            browser_btn = widget.findChild(QPushButton, "runBrowserButton")
            if browser_btn is not None:
                browser_btn.clicked.connect(self._run_in_browser)
            save_connection = widget.findChild(QPushButton, "saveConnectionButton")
            if save_connection is not None:
                save_connection.clicked.connect(self._save_connection_string)
            test_connection = widget.findChild(QPushButton, "testConnectionButton")
            if test_connection is not None:
                test_connection.clicked.connect(self._test_connection)
            save_code = widget.findChild(QPushButton, "saveCodeButton")
            if save_code is not None:
                save_code.clicked.connect(self._save_current_file)
            self._check_button = widget.findChild(QPushButton, "checkTaskButton")
            if self._check_button is not None:
                self._check_button.clicked.connect(self._check_task)
            send_chat_button = widget.findChild(QPushButton, "sendToChatButton")
            if send_chat_button is not None:
                send_chat_button.clicked.connect(self._send_active_tab_to_chat)
        connection_toggle = widget.findChild(QToolButton, "connectionSettingsToggle")
        connection_panel = widget.findChild(QWidget, "connectionSettingsPanel")
        if connection_toggle is not None and connection_panel is not None:
            connection_panel.setVisible(connection_toggle.isChecked())
            connection_toggle.toggled.connect(connection_panel.setVisible)
            connection_toggle.toggled.connect(
                lambda expanded: connection_toggle.setArrowType(
                    Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow
                )
            )
        self._load_schemas()

    def _restore_drafts(self, _widget: QWidget) -> None:
        """Load any saved drafts from SQLite into the editors."""
        for editor, file_name in (
            (self._sql_editor, "query.sql"),
            (self._php_editor, "index.php"),
            (self._html_editor, "index.html"),
            (self._css_editor, "style.css"),
            (self._js_editor, "script.js"),
        ):
            if editor is None:
                continue
            saved = self.db.load_draft(self.attempt_id, file_name)
            if saved:
                editor.setPlainText(saved)

    def _flush_drafts(self) -> None:
        """Persist every editor's current content to the drafts table."""
        for editor, file_name in (
            (self._sql_editor, "query.sql"),
            (self._php_editor, "index.php"),
            (self._html_editor, "index.html"),
            (self._css_editor, "style.css"),
            (self._js_editor, "script.js"),
        ):
            if editor is None:
                continue
            self.db.save_draft(self.attempt_id, file_name, editor.toPlainText())

    # ------------------------------------------------------------------
    # SQL execution
    # ------------------------------------------------------------------
    def _run_sql(self) -> None:
        """Execute the current SQL against MySQL (pure-client, no XAMPP coupling)."""
        if self._sql_editor is None or self._results_view is None:
            return
        query = self._sql_editor.toPlainText().strip()
        if not query:
            self._set_status(translate("INF03Workspace", "Nothing to run."))
            return

        schema = self._current_schema()
        start = time.perf_counter()
        try:
            rows, columns = self._execute_mysql(schema, query)
        except Exception as exc:  # noqa: BLE001 — surface as status text
            logger.exception("SQL execution failed")
            self._set_status(
                translate("INF03Workspace", "MySQL error: %1").replace("%1", str(exc))
            )
            return
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        self._populate_results_table(columns, rows)
        self._set_status(
            translate("INF03Workspace", "OK — %1 row(s), %2 ms")
            .replace("%1", str(len(rows)))
            .replace("%2", str(elapsed_ms))
        )

    @staticmethod
    def _split_sql_statements(query: str) -> list[str]:
        """Split SQL on semicolons outside quoted strings."""
        statements: list[str] = []
        current: list[str] = []
        quote: str | None = None
        escaped = False
        for character in query:
            if escaped:
                current.append(character)
                escaped = False
                continue
            if character == "\\" and quote:
                current.append(character)
                escaped = True
                continue
            if character in {"'", '"', "`"}:
                if quote == character:
                    quote = None
                elif quote is None:
                    quote = character
                current.append(character)
            elif character == ";" and quote is None:
                statement = "".join(current).strip()
                if statement:
                    statements.append(statement)
                current = []
            else:
                current.append(character)
        statement = "".join(current).strip()
        if statement:
            statements.append(statement)
        return statements

    def _load_schemas(self) -> None:
        """Populate the schema selector without failing workspace startup."""
        if self._schema_combo is None:
            return
        try:
            connection = self._connect_mysql()
            try:
                cursor = connection.cursor()
                cursor.execute("SHOW DATABASES")
                schemas = [str(row[0]) for row in cursor.fetchall()]
            finally:
                connection.close()
            self._schema_combo.clear()
            self._schema_combo.addItem("(no schema)")
            self._schema_combo.addItems(schemas)
        except Exception as exc:  # noqa: BLE001
            logger.info("MySQL schemas unavailable: %s", exc)

    def _connection_parameters(self, schema: str | None = None) -> dict[str, Any]:
        """Parse the user-facing MySQL URL into mysql-connector arguments."""
        value = (self._connection_input.text() if self._connection_input else "").strip()
        value = (
            value
            or self.db.get_config(cfg.MYSQL_CONNECTION, DEFAULT_CONNECTION_STRING)
            or DEFAULT_CONNECTION_STRING
        )
        parsed = urlsplit(value if "://" in value else f"mysql://{value}")
        database = parsed.path.lstrip("/") or None
        return {
            "host": parsed.hostname or "localhost",
            "port": parsed.port or 3306,
            "user": unquote(parsed.username or "root"),
            "password": unquote(parsed.password or ""),
            "database": schema if schema and schema != "(no schema)" else database,
        }

    def _connect_mysql(self, schema: str | None = None):
        import mysql.connector

        return mysql.connector.connect(**self._connection_parameters(schema))

    def _save_connection_string(self) -> None:
        value = self._connection_input.text().strip() if self._connection_input else ""
        if not value:
            self._set_status(translate("INF03Workspace", "Connection string cannot be empty."))
            return
        self.db.set_config(cfg.MYSQL_CONNECTION, value)
        self._set_status(translate("INF03Workspace", "Connection string saved."))

    def _test_connection(self) -> None:
        try:
            connection = self._connect_mysql()
            connection.close()
            self._save_connection_string()
            message = translate("INF03Workspace", "MySQL connection OK.")
            self._set_status(message)
            if self._connection_callback is not None:
                self._connection_callback(message)
            self._load_schemas()
        except Exception as exc:  # noqa: BLE001
            self._set_status(
                translate("INF03Workspace", "MySQL connection failed: %1").replace("%1", str(exc))
            )

    def _execute_mysql(self, schema: str, query: str) -> tuple[list[tuple], list[str]]:
        """Connect to local MySQL via mysql-connector and run the query.

        Returns (rows, column_names). Raises on connection/auth/SQL errors.
        """
        connection = self._connect_mysql(schema)
        try:
            cursor = connection.cursor()
            rows: list[tuple] = []
            columns: list[str] = []
            for statement in self._split_sql_statements(query):
                cursor.execute(statement)
                if cursor.description is not None:
                    columns = [col[0] for col in cursor.description]
                    rows = [tuple(row) for row in cursor.fetchall()]
            connection.commit()
            return rows, columns
        finally:
            connection.close()

    def _populate_results_table(self, columns: list[str], rows: list[tuple]) -> None:
        """Fill the QTableView model with `columns` + `rows`."""
        from PySide6.QtGui import QStandardItem, QStandardItemModel

        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(columns)
        for row in rows:
            model.appendRow([QStandardItem(str(cell)) for cell in row])
        if self._results_view is not None:
            self._results_view.setModel(model)

    def _run_in_browser(self) -> None:
        """Write the current HTML draft to a temp folder and open it."""
        html = self._current_html()
        php = self._current_php()
        css = self._current_css()
        javascript = self._current_javascript()
        content = html or php
        file_name = "index.html" if html else "index.php"
        if not content:
            self._set_status(translate("INF03Workspace", "Nothing to open in browser."))
            return
        folder = Path(tempfile.gettempdir()) / "ai_exam_tutor" / str(self.attempt_id)
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / file_name
        target.write_text(content, encoding="utf-8")
        if html and css:
            (folder / "style.css").write_text(css, encoding="utf-8")
        if html and javascript:
            (folder / "script.js").write_text(javascript, encoding="utf-8")
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        self._set_status(
            translate("INF03Workspace", "Opened %1 in the default browser.").replace(
                "%1", file_name
            )
        )

    def _resolve_save_path(
        self,
        file_name: str,
        file_filter: str | None = None,
        default_name: str | None = None,
    ) -> str:
        """Return the saved path for this file in the current attempt/session.

        The first time a file is saved for an attempt, the user is prompted. The
        chosen path is persisted and reused automatically for the remainder of the
        session without re-opening the file picker.
        """
        saved_path = self.db.get_config(cfg.code_file_key(self.attempt_id, file_name), "")
        if saved_path:
            return saved_path

        start_path = default_name or file_name or ""
        folder = str(Path(start_path).resolve().parent) if Path(start_path).parent else ""
        chosen, _ = QFileDialog.getSaveFileName(
            self._root,
            f"Save {file_name}",
            saved_path or folder or file_name,
            f"{file_filter};;All files (*)" if file_filter else "All files (*)",
        )
        if not chosen:
            return ""
        self.db.set_config(cfg.code_file_key(self.attempt_id, file_name), chosen)
        return chosen

    def _save_current_file(self) -> None:
        """Save the selected PHP, HTML, CSS, or JavaScript tab to its file."""
        if self._code_tabs is None:
            return
        file_index = self._code_tabs.currentIndex() - 1
        if file_index < 0:
            self._set_status(translate("INF03Workspace", "Select a source file first."))
            return
        files = (
            (self._php_editor, "index.php", "PHP files (*.php)"),
            (self._html_editor, "index.html", "HTML files (*.html)"),
            (self._css_editor, "style.css", "CSS files (*.css)"),
            (self._js_editor, "script.js", "JavaScript files (*.js)"),
        )
        editor, file_name, file_filter = files[file_index]
        if editor is None:
            return

        path = self._resolve_save_path(file_name, file_filter, file_name)
        if not path:
            return

        Path(path).write_text(editor.toPlainText(), encoding="utf-8")
        self._set_status(translate("INF03Workspace", "Saved %1.").replace("%1", Path(path).name))

    def _send_active_tab_to_chat(self) -> None:
        """Forward the currently selected tab's source into the AI chat panel."""
        tab_name, content = self._active_tab_snapshot()
        if not content.strip():
            self._set_status(translate("INF03Workspace", "Current tab is empty."))
            return
        payload = f"[Selected file: {tab_name}]\n\n{content[:20000]}"
        self.send_to_chat(payload)
        self._set_status(translate("INF03Workspace", "Sent %1 to chat.").replace("%1", tab_name))

    def _active_tab_snapshot(self) -> tuple[str, str]:
        """Return the active file / SQL tab and the current text body."""
        if self._code_tabs is None:
            return ("workspace", self._current_sql())
        index = self._code_tabs.currentIndex()
        if index == 0:
            return ("query.sql", self._current_sql())
        files = (
            ("index.php", self._current_php()),
            ("index.html", self._current_html()),
            ("style.css", self._current_css()),
            ("script.js", self._current_javascript()),
        )
        file_index = index - 1
        if 0 <= file_index < len(files):
            name, content = files[file_index]
            return (name, content)
        return ("workspace", self._current_sql())

    def _set_status(self, text: str) -> None:
        if self._status is not None:
            self._status.setText(text)
        if self._status_callback is not None:
            self._status_callback(text)

    def _check_task(self) -> None:
        """Start asynchronous grading and persist the returned score."""
        if self._grade_worker is not None:
            return
        if not self.db.get_config(cfg.ANSWER_KEY_PDF, ""):
            self._set_status(
                translate("INF03Workspace", "Load an answer key PDF before checking the task.")
            )
            return
        self._grade_worker = GradeWorker(
            self.llm_client,
            self.llm_client.connection_settings(),
            self._build_grade_messages(),
        )
        self._grade_worker.succeeded.connect(self._on_grade_succeeded)
        self._grade_worker.failed.connect(self._on_grade_failed)
        self._grade_worker.finished.connect(self._on_grade_finished)
        if self._check_button is not None:
            self._check_button.setEnabled(False)
            self._check_button.setText(translate("INF03Workspace", "Checking..."))
        self._set_status(translate("INF03Workspace", "Checking solution against the answer key..."))
        self._grade_worker.start()

    def _on_grade_succeeded(self, response: str) -> None:
        if not self._active:
            return
        try:
            score = self._parse_grade_response(response)
            self.db.finish_attempt(self.attempt_id, score)
            total = score.get("total_score", "?")
            maximum = score.get("max_score", "?")
            percentage = score.get("percentage", "?")
            self._set_status(
                translate("INF03Workspace", "Score: %1/%2 (%3%). Details saved.")
                .replace("%1", str(total))
                .replace("%2", str(maximum))
                .replace("%3", str(percentage))
            )
            self._show_grade_report(score)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._set_status(
                translate("INF03Workspace", "Evaluator returned invalid JSON: %1").replace(
                    "%1", str(exc)
                )
            )

    def _on_grade_failed(self, error: str) -> None:
        if not self._active:
            return
        self._set_status(translate("INF03Workspace", "Evaluation failed: %1").replace("%1", error))

    def _on_grade_finished(self) -> None:
        self._grade_worker = None
        if self._check_button is not None:
            self._check_button.setEnabled(True)
            self._check_button.setText(translate("INF03Workspace", "Check task"))

    def _show_grade_report(self, score: dict[str, Any]) -> None:
        """Present the structured evaluator feedback in a compact report."""
        lines = [
            f"Score: {score.get('total_score', '?')}/{score.get('max_score', '?')} "
            f"({score.get('percentage', '?')}%)",
            "",
            str(score.get("summary", "")),
        ]
        for criterion in score.get("criteria", []):
            if isinstance(criterion, dict):
                lines.append(
                    f"{criterion.get('name', 'criterion')}: "
                    f"{criterion.get('score', '?')}/{criterion.get('max_score', '?')} - "
                    f"{criterion.get('feedback', '')}"
                )
        missing = score.get("missing_requirements", [])
        if missing:
            lines.extend(["", "Missing requirements:", *[f"- {item}" for item in missing]])
        QMessageBox.information(
            self._root,
            translate("INF03Workspace", "Evaluation report"),
            "\n".join(lines),
        )

    def _build_grade_messages(self) -> list[dict[str, str]]:
        """Build the evaluator prompt and a complete, bounded task payload."""
        from importlib import resources

        prompt = resources.files("prompts").joinpath("inf03_grader.txt").read_text(encoding="utf-8")
        exam_path = self.db.get_config(cfg.LAST_PDF, "") or ""
        key_path = self.db.get_config(cfg.ANSWER_KEY_PDF, "") or ""
        payload = {
            "exam_sheet_text": self._extract_pdf_text(exam_path),
            "answer_key_text": self._extract_pdf_text(key_path),
            "sql_query": self._current_sql(),
            "php_source": self._current_php(),
            "html_source": self._current_html(),
            "css_source": self._current_css(),
            "javascript_source": self._current_javascript(),
            "schema": self._current_schema(),
        }
        return [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

    @staticmethod
    def _extract_pdf_text(path: str) -> str:
        """Extract enough PDF text for grading without exceeding the prompt size."""
        if not path or not Path(path).exists():
            return ""
        try:
            import fitz

            with fitz.open(path) as document:
                text = "\n".join(page.get_text() for page in document)
            return text[:MAX_PDF_CONTEXT_CHARS]
        except Exception:  # noqa: BLE001
            return ""

    @staticmethod
    def _parse_grade_response(response: str) -> dict[str, Any]:
        """Parse evaluator JSON while tolerating accidental surrounding text."""
        start = response.find("{")
        end = response.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("No JSON object in evaluator response")
        result = json.loads(response[start : end + 1])
        if not isinstance(result, dict) or "total_score" not in result:
            raise ValueError("Evaluator JSON is missing total_score")
        return result

    # ------------------------------------------------------------------
    # Convenience getters
    # ------------------------------------------------------------------
    def _current_sql(self) -> str:
        return self._sql_editor.toPlainText() if self._sql_editor else ""

    def _current_php(self) -> str:
        return self._php_editor.toPlainText() if self._php_editor else ""

    def _current_html(self) -> str:
        return self._html_editor.toPlainText() if self._html_editor else ""

    def _current_css(self) -> str:
        return self._css_editor.toPlainText() if self._css_editor else ""

    def _current_javascript(self) -> str:
        return self._js_editor.toPlainText() if self._js_editor else ""

    def _current_schema(self) -> str:
        if self._schema_combo is None:
            return ""
        return self._schema_combo.currentText()

    # ------------------------------------------------------------------
    # Tutor chat entry point (called by MainWindow's right pane)
    # ------------------------------------------------------------------
    def send_tutor_message(self, message_text: str) -> str:
        """Convenience wrapper for MainWindow's chat panel.

        Adds the user message to history, calls the LLM with auto-context
        injected into the system prompt, and stores the assistant reply.
        Returns the assistant's reply text.
        """
        # Ensure Socratic system prompt is in history (only once).
        existing = self.db.list_messages(self.attempt_id)
        if not any(m["role"] == "system" for m in existing):
            prompt = self._socratic_prompt()
            self.db.add_message(self.attempt_id, "system", prompt)

        # Inject workspace context into the system prompt on every call.
        context = self.build_context_payload()
        context_note = (
            f"\n\n[Current workspace state] "
            f"sql={context.get('sql_query', '')[:500]!r} "
            f"php_len={len(context.get('php_source', ''))} "
            f"html_len={len(context.get('html_source', ''))} "
            f"css_len={len(context.get('css_source', ''))} "
            f"javascript_len={len(context.get('javascript_source', ''))} "
            f"schema={context.get('schema', '')!r}"
        )
        self.db.add_message(self.attempt_id, "system", context_note)

        # Persist user message
        self.db.add_message(self.attempt_id, "user", message_text)

        # Load full history and call LLM
        history = self.db.list_messages(self.attempt_id)
        try:
            reply = self.llm_client.chat(history, images=None)
        except LLMError as exc:
            reply = f"[LLM error] {exc}"
        self.db.add_message(self.attempt_id, "assistant", reply)
        return reply

    @staticmethod
    def _socratic_prompt() -> str:
        """Read the Socratic system prompt from disk; fall back to inline default."""
        from importlib import resources

        try:
            with resources.as_file(
                resources.files("prompts").joinpath("inf03_socratic.txt")
            ) as path:
                if path.exists():
                    return path.read_text(encoding="utf-8")
        except (ModuleNotFoundError, FileNotFoundError):
            pass
        return (
            "You are a Socratic tutor for Polish vocational INF.03 "
            "(SQL, PHP, HTML, CSS, JavaScript) exam prep. Never reveal the final SQL query, "
            "PHP code, HTML markup, CSS stylesheet, or JavaScript directly. "
            "Always ask a guiding question first."
        )


# Auto-register so WorkspaceFactory.available() includes "inf03".
WorkspaceFactory.register(INF03Workspace.workspace_id, INF03Workspace)
