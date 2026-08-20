# AI Exam Tutor

Desktop app for Polish high-school exam prep (Matura + INF.03/04).
Built with **Python 3.12+**, **PySide6** (LGPLv3), **Qt Designer .ui**, **SQLite**, **PyInstaller + Inno Setup**.

## Quick Start

```bash
# 1. Create venv
python -m venv .venv
.venv\Scripts\activate

# 2. Install deps
pip install -r requirements.txt

# 3. Run
python main.py
```

## Manual dla ucznia

Instrukcja instalacji, konfiguracji AI i pracy z workspace INF.03 znajduje się w [manualu ucznia](docs/manual-ucznia.md).

## Architecture (TL;DR)

| Layer | File | Responsibility |
|-------|------|----------------|
| DB | `app/database/db_manager.py` | All SQLite access (config, attempts, messages, drafts) |
| LLM | `app/core/llm_client.py` | BYOK multi-provider router (OpenAI/Gemini/Groq/Local) |
| Theme | `app/core/theme_manager.py` | Light/Dark QSS + persistence |
| Workspaces | `app/workspaces/` | Subject-specific centres (INF.03 implemented in v1.0, including AI grading) |
| UI | `app/ui/` | QUiLoader controllers for MainWindow, Settings, PDF, Chat |

See `docs/adr/` for the project's published architectural decisions.

## Releases

Current stable release: `v1.2.2`.

Every published version must have a dated entry in the
[CHANGELOG](CHANGELOG.md). Release tags use the `vX.Y.Z` format and the
changelog entry must list user-visible changes, supported platforms, known
limitations, and the downloadable artifacts.

## INF.03 workflow

The reference workspace supports two PDF inputs: the exam sheet and a separate
answer key. The SQL runner and PHP/HTML/CSS/JavaScript tabs are included in the
grading payload. PHP, HTML, CSS and JavaScript use a locally bundled Monaco
Editor through Rocher; when Qt WebEngine is unavailable, the application keeps
the same text API through a plain-text fallback.
`Check task` sends that payload to the configured BYOK model using the dedicated
`prompts/inf03_grader.txt` system prompt. The evaluator must return JSON with
points, rubric feedback, missing requirements, and a summary. The validated
result is stored in the current attempt's `score_json` field and shown in a
report dialog. Tutor chat continues to use the separate Socratic prompt.

The INF.03 code is split by responsibility: `inf03.py` coordinates the
workspace UI, `inf03_highlighters.py` contains SQL/PHP/HTML highlighting, and
`inf03_grading.py` contains the background evaluator worker.

## Languages

The application starts in Polish by default. English can be selected in
`Settings > Language`; the selection is stored in SQLite and takes effect
after restarting the application. Translation sources live in
`translations/ai_exam_tutor_pl.ts` and the compiled Qt catalog is included in
the PyInstaller build.

API keys and MySQL connection settings are stored locally in the SQLite
configuration database so the application can restore them between runs. They
are not encrypted by the MVP; use a personal Windows account and do not share
the database file when it contains credentials.

## Tests

```bash
# Unit tests (built-in unittest, AAA + Gherkin)
python -m unittest discover -v

# Lint
ruff check .

```

## Build Installer (Windows)

```bash
# Requires: PyInstaller, Inno Setup (ISCC), GitHub CLI (optional)
pyinstaller --noconfirm --onedir --windowed \
  --add-data "prompts;prompts" \
  --add-data "app/database/schema.sql;app/database" \
  --add-data "app/ui/views;app/ui/views" \
  --add-data "translations;translations" \
  --add-data "resources;resources" \
  --collect-all PySide6 \
  --collect-all rocher \
  --collect-all mysql.connector \
  --name "AI_Exam_Tutor" \
  main.py

iscc setup_script.iss
# Output: Output_Installer/AI_Exam_Tutor_Setup.exe
```

GitHub Actions does this automatically on `git tag vX.Y.Z` (see
`.github/workflows/ci.yml`). The build collects Rocher's local `vs` assets so
the installer can run Monaco without downloading editor files.

## Contributing (high-school friendly)

1. **UI changes**: Open `.ui` files in Qt Designer (`pyside6-designer`), edit, save. Never hand-write Python layout code (ADR-002).
2. **Code style**: `ruff check .` — no custom config needed.
3. **Tests**: Write `unittest` with AAA sections and Gherkin docstrings (ADR-005).
4. **Commits**: Conventional commits preferred (`feat:`, `fix:`, `docs:`).

## License

Proprietary. The project uses PySide6 under LGPLv3 and does not add GPL-only Qt dependencies.