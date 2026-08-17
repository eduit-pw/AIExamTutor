"""Metadata used by the startup exam selector."""

from __future__ import annotations

from dataclasses import dataclass

from app.workspaces.factory import WorkspaceFactory


@dataclass(frozen=True)
class ExamEntry:
    """One selectable exam/workspace entry shown to the student."""

    entry_id: str
    category_id: str
    category_label: str
    level_label: str
    subject_label: str
    workspace_id: str
    status: str = "planned"
    requirements: tuple[str, ...] = ()

    @property
    def is_available(self) -> bool:
        """Return whether the workspace has an implementation registered."""
        return self.status == "available" and self.workspace_id in WorkspaceFactory.available()


EXAM_ENTRIES: tuple[ExamEntry, ...] = (
    ExamEntry("e8_english", "e8", "Egzamin ósmoklasisty", "E8", "English", "e8_english"),
    ExamEntry("e8_polish", "e8", "Egzamin ósmoklasisty", "E8", "Język polski", "e8_polish"),
    ExamEntry("e8_math", "e8", "Egzamin ósmoklasisty", "E8", "Matematyka", "e8_math"),
    ExamEntry(
        "matura_english_basic",
        "matura",
        "Matura",
        "Matura podstawowa",
        "English",
        "foreign_language",
    ),
    ExamEntry(
        "matura_english_extended",
        "matura",
        "Matura",
        "Matura rozszerzona",
        "English",
        "foreign_language",
    ),
    ExamEntry(
        "matura_polish_basic",
        "matura",
        "Matura",
        "Matura podstawowa",
        "Język polski",
        "humanities",
    ),
    ExamEntry(
        "matura_polish_extended",
        "matura",
        "Matura",
        "Matura rozszerzona",
        "Język polski",
        "humanities",
    ),
    ExamEntry("matura_math_basic", "matura", "Matura", "Matura podstawowa", "Matematyka", "stem"),
    ExamEntry(
        "matura_math_extended", "matura", "Matura", "Matura rozszerzona", "Matematyka", "stem"
    ),
    ExamEntry(
        "matura_history_extended",
        "matura",
        "Matura",
        "Matura rozszerzona",
        "Historia",
        "humanities",
    ),
    ExamEntry(
        "matura_physics_extended", "matura", "Matura", "Matura rozszerzona", "Fizyka", "stem"
    ),
    ExamEntry(
        "matura_biology_extended", "matura", "Matura", "Matura rozszerzona", "Biologia", "science"
    ),
    ExamEntry(
        "matura_geography_extended",
        "matura",
        "Matura",
        "Matura rozszerzona",
        "Geografia",
        "science",
    ),
    ExamEntry(
        "matura_chemistry_extended", "matura", "Matura", "Matura rozszerzona", "Chemia", "science"
    ),
    ExamEntry(
        "vocational_inf03",
        "vocational",
        "Egzaminy zawodowe",
        "INF",
        "INF.03 — SQL i PHP/HTML/CSS/JavaScript",
        "inf03",
        status="available",
    ),
    ExamEntry(
        "vocational_inf04",
        "vocational",
        "Egzaminy zawodowe",
        "INF",
        "INF.04 — Projekt i testowanie",
        "inf04",
        requirements=("rocher",),
    ),
)


def entries_for_category(category_id: str) -> tuple[ExamEntry, ...]:
    """Return catalog entries in their stable display order."""
    return tuple(entry for entry in EXAM_ENTRIES if entry.category_id == category_id)