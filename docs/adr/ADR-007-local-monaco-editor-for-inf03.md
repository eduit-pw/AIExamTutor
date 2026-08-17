# ADR 007: Local Monaco Editor for the INF.03 Source Tabs

## Status
Accepted

## Context
The INF.03 workspace needs a capable editor for PHP, HTML, CSS and JavaScript,
including language-aware editing without adding a GPL-only Qt component. The
application is a Windows desktop product and must remain usable offline after
installation. Qt WebEngine is available in the supported PySide6 runtime, but
it may be unavailable in offscreen tests or restricted environments.

## Decision
Use the MIT-licensed `rocher` package to bundle Monaco's static `vs` assets and
wrap the editor in `app/ui/monaco_editor.py` as a reusable `QWidget`.

- The wrapper loads the local Monaco bundle through `QWebEngineView` and uses
  `QWebChannel` for content change notifications.
- The `.ui` view declares `MonacoEditor` for the four source tabs; the
  controller registers the class with `QUiLoader` before loading the view.
- SQL remains a native `QPlainTextEdit` because it has different execution and
  syntax-highlighting behavior.
- When Qt WebEngine is unavailable or the platform is `offscreen`, Monaco
  falls back to a borderless `QPlainTextEdit` with the same `setPlainText`,
  `toPlainText` and `textChanged` contract.
- The active application theme maps to Monaco's `vs` or `vs-dark` theme and is
  refreshed when the application theme is toggled.
- PyInstaller must collect `rocher` and PySide6 assets so the installed app
  never depends on a network download for the editor.

## Consequences

### Positive

- Students get a familiar, language-aware editor in the existing INF.03 tabs.
- The application remains compatible with the LGPLv3 dependency policy.
- Offline installs contain all Monaco resources locally.
- Unit tests remain deterministic without starting Chromium in offscreen mode.

### Negative / Trade-offs

- The installer is larger because it contains Monaco and Qt WebEngine assets.
- WebEngine startup and rendering add complexity compared with a native text
  edit, so the fallback path must remain tested.
- Monaco's browser model requires a small JavaScript/Python bridge rather than
  direct Qt document access.
