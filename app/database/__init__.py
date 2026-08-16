"""SQLite persistence layer (the only place that touches sqlite3)."""

from app.database.db_manager import DBManager

__all__ = ["DBManager"]