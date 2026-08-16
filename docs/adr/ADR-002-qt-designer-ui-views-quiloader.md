# ADR 002: Separation of UI Views (.ui XML) via QUiLoader

## Status
Accepted

## Context
Hardcoding UI layouts, nested widgets, and stylesheets directly inside Python classes creates bloated, difficult-to-read files ("spaghetti code"). High school student contributors need a visual, intuitive way to modify UI elements without breaking business logic.

## Decision
All window layouts, dialogs, and workspace components must be designed visually using **Qt Designer / Qt Creator** and saved as declarative `.ui` XML files inside `app/ui/views/`. Python controller classes dynamically load these files at runtime using `PySide6.QtUiTools.QUiLoader` and access widgets via their `objectName` identifiers.

## Consequences
### Positive
* Enforces the Single Responsibility Principle (SRP): visual presentation is isolated from application logic.
* High school contributors can iterate on UX/UI visually in Qt Designer without altering Python code.
* Simplifies maintenance and diff tracking across pull requests.

### Negative / Trade-offs
* `.ui` XML files must be bundled as data assets during PyInstaller packaging (`--add-data "app/ui/views;app/ui/views"`).
* Widget lookup relies on string `objectName` identifiers, requiring discipline in UI naming conventions.