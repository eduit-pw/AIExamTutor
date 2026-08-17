# Changelog

All notable changes to AI Exam Tutor are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and releases use Semantic Versioning.

## [Unreleased]

No changes yet.

## [1.2.0] - 2026-08-17

### Added

- Monaco Editor in the INF.03 PHP, HTML, CSS and JavaScript tabs, bundled locally through
    the `rocher` package so the code editor does not require a network connection.
- A deterministic `QPlainTextEdit` fallback for test, offscreen and unavailable-WebEngine
    environments.
- Theme synchronization between the application Light/Dark setting and Monaco's `vs`/
    `vs-dark` palettes.

### Changed

- INF.03 source tabs keep one continuous editor frame with no nested border and a clean
    active-tab connection.
- The PDF toolbar uses compact controls suitable for the 300 px minimum left pane.
- The AI send action fills the available input width and the panel header has clearer spacing.
- PDF empty-state text is translated through the compiled Polish Qt catalog.
- PyInstaller and CI now collect Rocher's local Monaco assets.

### Known limitations

- WebEngine rendering still depends on the Qt WebEngine runtime shipped with the installer;
    unsupported environments use the compatible plain-text fallback.
- MySQL must be running locally or on the configured network endpoint for SQL execution.
- AI features require a configured BYOK provider; no API key is bundled.

## [1.1.0] - 2026-08-17

### Added

- Initial v1.1 implementation of the exam selection screen.
- Exam catalog grouped into E8, Matura and vocational exams.
- Planned workspace entries are visible but disabled until implemented.

### Changed

- A fresh installation opens the exam selector instead of opening INF.03 directly.
- Selecting a workspace creates an attempt only after a valid workspace is chosen.
- The exam selector uses shared-width, top-aligned category cards and separate subject entries.
- Matura selection distinguishes basic and extended levels for English, Polish and Mathematics,
  while History, Physics, Biology, Geography and Chemistry are extended-only.
- Matura now shows one button per subject and opens the level choice after activation.
- Startup category cards share a top edge and balanced minimum height; the status bar is hidden
    while the student is choosing an exam.
- INF.03 now uses resizable three-pane proportions, SQL/application tabs, a collapsible database
    connection panel, clearer action hierarchy and a guided AI Assistant empty state.
- Exam actions use high-contrast solid surfaces, visible hover/focus states and text-only labels.
- Vision guidance is shown only for subjects that require image support, with a direct settings path.
- The startup window now opens at 1120x720 with a 920x600 minimum and no horizontal overflow.
- The main window shows one neutral connection status instead of technical PDF,
  LLM and MySQL indicators.
- Main menu items use one consistent application-bar style.
- INF.03 now exposes SQL, PHP, HTML, CSS and JavaScript as one flat tab bar.
- INF.03 source-file saving, preview and task checking use the active source tab.
- The AI panel keeps a usable input width and the PDF viewer has readable empty states
    in both themes.
- The main three-pane layout now respects practical minimum widths and responsive proportions.
- Added JavaScript syntax highlighting and JavaScript context to INF.03 drafts and grading.
- Updated Polish translations and the student manual for the refreshed INF.03 workflow.

### Known limitations

- MySQL must be running locally or on the configured network endpoint for SQL execution.
- AI features require a configured BYOK provider; no API key is bundled.
- Windows installer is the supported release artifact for this version.

## [1.0.0] - 2026-08-17

### Added

- INF.03 SQL and PHP/HTML reference workspace.
- Socratic AI Tutor with BYOK provider routing.
- SQLite persistence for configuration, attempts, messages and drafts.
- PDF exam and answer-key workflow.
- Light and dark themes.
- Windows PyInstaller and Inno Setup packaging.

[Unreleased]: https://github.com/eduit-pw/AIExamTutor/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/eduit-pw/AIExamTutor/releases/tag/v1.2.0
[1.1.0]: https://github.com/eduit-pw/AIExamTutor/releases/tag/v1.1.0
[1.0.0]: https://github.com/eduit-pw/AIExamTutor/releases/tag/v1.0.0
