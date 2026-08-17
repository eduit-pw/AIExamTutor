# `app/ui/views/` — Declarative Qt Designer files

Per **ADR-002**, all window/dialog/workspace layouts live in `.ui` files in this
directory. Python code loads them at runtime with `QUiLoader` and never writes
manual layout code.

## Workflow for contributors

1. Open Qt Designer (`pyside6-designer.exe` or via PyCharm/VS Code plugin).
2. Open the relevant `.ui` file (e.g. `MainWindow.ui`).
3. Edit widgets, save. **Do not change `objectName` values** — Python code
   looks them up by name.
4. Commit the `.ui` only. PyInstaller will bundle it via `--add-data`.

## Expected widget tree (INF03Workspace.ui)

The INF.03 workspace (`app/workspaces/inf03.py`) expects the following
`objectName`s at minimum. Qt Designer must preserve them:

| objectName        | Type           |
|-------------------|----------------|
| `INF03Root`       | QWidget        |
| `schemaComboBox`  | QComboBox      |
| `runSqlButton`    | QPushButton    |
| `sqlSplitter`     | QSplitter      |
| `sqlEditor`       | QPlainTextEdit |
| `resultsTable`    | QTableView     |
| `codeSplitter`    | QSplitter      |
| `phpEditor`       | QPlainTextEdit |
| `htmlEditor`      | QPlainTextEdit |
| `statusLabel`     | QLabel         |

If any of these are missing, `INF03Workspace._capture_widget_refs()` will
raise `LookupError` at startup — by design, so we notice immediately.

## Placeholder behaviour

When a `.ui` is **not yet authored**, the corresponding workspace falls back
to a programmatically-built widget tree with the same `objectName`s. This
lets the app run during early development and CI smoke tests without Qt
Designer involvement. See `INF03Workspace._build_programmatic`.

## Startup screen contract

`StartupScreen.ui` is the first full-window view shown to the student. It uses
three shared-width, top-aligned `QFrame` cards (`categoryCard`) for E8, Matura
and vocational exams. The cards share a minimum height so the row remains
balanced; the surrounding `QScrollArea` handles smaller windows. Each subject
has one `QPushButton`. Matura entries with multiple levels share a button and
open a level menu after activation. The button object name is
`examButton_<entry_id>` for single-entry subjects and the shared subject id for
multi-level Matura entries. Do not combine multiple subjects into one button or
replace the cards with titled `QGroupBox` containers.