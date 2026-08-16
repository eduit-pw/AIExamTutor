# ADR 005: Built-in `unittest`, AAA + Gherkin Standards, and Mutation Testing

## Status
Accepted

## Context
In Polish vocational exams (INF.04), students are required to write automated unit tests on offline computers where third-party packages (like `pytest`) cannot be installed via `pip`. Furthermore, tests must adhere to professional structural standards to teach industry-grade software engineering habits.

## Decision
All automated test suites must use Python's built-in **`unittest`** module. Every test must be structured using the **AAA (Arrange-Act-Assert)** pattern and documented with **Gherkin syntax (Given-When-Then)** in its docstring. Test suite effectiveness is validated using mutation testing (`mutmut`).

## Consequences
### Positive
* Serves as a direct educational preparation tool for the INF.04 national vocational exam.
* Zero third-party testing dependencies required for test execution.
* High test quality and assertion rigor enforced by mutation testing.

### Negative / Trade-offs
* `unittest` syntax is slightly more verbose than `pytest` fixtures, but easily mastered through boilerplate patterns.