"""UI package: views (.ui) + window controllers."""

__all__ = ["MainWindow"]


def __getattr__(name: str):
    """Lazily resolve the main window to avoid import cycles during startup."""
    if name == "MainWindow":
        from app.ui.main_window import MainWindow

        return MainWindow
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
