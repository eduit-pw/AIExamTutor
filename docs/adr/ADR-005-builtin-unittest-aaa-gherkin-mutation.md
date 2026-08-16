# ADR 005: Built-in `unittest`, AAA + Gherkin Standards

## Status
Accepted

## Context
In Polish vocational exams (INF.04), students are required to write automated unit tests on offline computers where third-party packages (like `pytest`) cannot be installed via `pip`. Furthermore, tests must adhere to professional structural standards to teach industry-grade software engineering habits.

## Decision
All automated test suites must use Python's built-in **`unittest`** module. Every test must be structured using the **AAA (Arrange-Act-Assert)** pattern and documented with **Gherkin syntax (Given-When-Then)** in its docstring. Test quality is validated by focused unit and smoke tests in CI.

## Consequences
### Positive
* Serves as a direct educational preparation tool for the INF.04 national vocational exam.
* Zero third-party testing dependencies required for test execution.
* Test execution remains deterministic and dependency-light.

### Negative / Trade-offs
* `unittest` syntax is slightly more verbose than `pytest` fixtures, but easily mastered through boilerplate patterns.