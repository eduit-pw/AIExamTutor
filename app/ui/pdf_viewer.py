"""PDF Viewer widget — left pane.

Renders CKE exam PDFs at 300 DPI using PyMuPDF (fitz). Provides page
navigation, zoom, and region snipping (Ctrl+Shift+S) for Vision payloads.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QBuffer, QRect, Qt, Signal
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.core.localization import translate

try:
    import fitz  # PyMuPDF

    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False


class PDFViewer(QWidget):
    """Scrollable PDF viewer with page selector, zoom, and snip-to-Vision."""

    # Emitted when user finishes a snip region (returns PNG bytes)
    region_snipped = Signal(bytes)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._doc: fitz.Document | None = None
        self._current_page = 0
        self._zoom_factor = 2.0  # 2.0 ≈ 300 DPI on typical 96 DPI screens
        self._snipping = False
        self._snip_start = None
        self._snip_rect = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Toolbar
        toolbar = QHBoxLayout()
        self._page_combo = QComboBox()
        self._page_combo.currentIndexChanged.connect(self._on_page_changed)
        toolbar.addWidget(QLabel(translate("PDFViewer", "Page:")))
        toolbar.addWidget(self._page_combo)

        self._zoom_combo = QComboBox()
        self._zoom_combo.addItems(["75%", "100%", "150%", "200%", "300%"])
        self._zoom_combo.setCurrentIndex(3)  # 200%
        self._zoom_combo.currentIndexChanged.connect(self._on_zoom_changed)
        toolbar.addWidget(QLabel(translate("PDFViewer", "Zoom:")))
        toolbar.addWidget(self._zoom_combo)

        snip_btn = QPushButton(translate("PDFViewer", "Snip Region (Ctrl+Shift+S)"))
        snip_btn.clicked.connect(self._start_snip)
        toolbar.addWidget(snip_btn)

        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Scroll area with image label
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setMouseTracking(True)
        self._image_label.installEventFilter(self)

        self._scroll.setWidget(self._image_label)
        layout.addWidget(self._scroll)

        # Status
        self._status = QLabel(translate("PDFViewer", "No PDF loaded"))
        layout.addWidget(self._status)

        # Shortcuts
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, activated=self._start_snip)
        QShortcut(QKeySequence("Ctrl++"), self, activated=lambda: self._zoom_delta(1))
        QShortcut(QKeySequence("Ctrl+-"), self, activated=lambda: self._zoom_delta(-1))
        QShortcut(QKeySequence("Ctrl+0"), self, activated=self._zoom_reset)

    def load_pdf(self, path: str) -> bool:
        """Open a PDF file. Returns True on success."""
        if not FITZ_AVAILABLE:
            self._status.setText(translate("PDFViewer", "PyMuPDF not available"))
            return False

        try:
            if self._doc:
                self._doc.close()
            self._doc = fitz.open(path)
            self._current_page = 0
            self._page_combo.clear()
            for i in range(self._doc.page_count):
                self._page_combo.addItem(f"{i + 1} / {self._doc.page_count}")
            self._render_current_page()
            self._status.setText(
                translate("PDFViewer", "Loaded: %1 (%2 pages)")
                .replace("%1", Path(path).name)
                .replace("%2", str(self._doc.page_count))
            )
            return True
        except Exception as exc:  # noqa: BLE001
            self._status.setText(
                translate("PDFViewer", "Failed to load PDF: %1").replace("%1", str(exc))
            )
            return False

    def _render_current_page(self) -> None:
        if not self._doc:
            return

        page = self._doc[self._current_page]
        # 72 DPI is PDF default; multiply by zoom_factor for target DPI
        mat = fitz.Matrix(self._zoom_factor, self._zoom_factor)
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # Convert to QImage → QPixmap
        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
        self._pixmap = QPixmap.fromImage(img)
        self._image_label.setPixmap(self._pixmap)
        self._image_label.resize(self._pixmap.size())
        self._page_combo.setCurrentIndex(self._current_page)

    def _on_page_changed(self, index: int) -> None:
        if self._doc and 0 <= index < self._doc.page_count:
            self._current_page = index
            self._render_current_page()

    def _on_zoom_changed(self, index: int) -> None:
        zoom_map = [0.75, 1.0, 1.5, 2.0, 3.0]
        self._zoom_factor = zoom_map[index]
        self._render_current_page()

    def _zoom_delta(self, delta: int) -> None:
        idx = self._zoom_combo.currentIndex()
        new_idx = max(0, min(self._zoom_combo.count() - 1, idx + delta))
        self._zoom_combo.setCurrentIndex(new_idx)

    def _zoom_reset(self) -> None:
        self._zoom_combo.setCurrentIndex(3)  # 200%

    # ------------------------------------------------------------------
    # Region snipping (for Vision payload)
    # ------------------------------------------------------------------
    def _start_snip(self) -> None:
        if not self._doc:
            return
        self._snipping = True
        self._image_label.setCursor(Qt.CursorShape.CrossCursor)
        self._status.setText(translate("PDFViewer", "Drag to select region... (Esc to cancel)"))

    def eventFilter(self, obj, event) -> bool:  # noqa: D102
        if obj is self._image_label and self._snipping:
            if event.type() == event.Type.MouseButtonPress:
                self._snip_start = event.position().toPoint()
                self._snip_rect = QRect(self._snip_start, self._snip_start)
                return True
            elif event.type() == event.Type.MouseMove and self._snip_start:
                self._snip_rect = QRect(self._snip_start, event.position().toPoint()).normalized()
                self._update_snip_overlay()
                return True
            elif event.type() == event.Type.MouseButtonRelease:
                self._finish_snip()
                return True
            elif event.type() == event.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
                self._cancel_snip()
                return True
        return super().eventFilter(obj, event)

    def _update_snip_overlay(self) -> None:
        """Draw a semi-transparent overlay showing the snip region."""
        if not self._pixmap or not self._snip_rect:
            return
        # Create a copy with overlay
        overlay = self._pixmap.copy()
        from PySide6.QtGui import QColor, QPainter, QPen

        painter = QPainter(overlay)
        painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.PenStyle.DashLine))
        painter.setBrush(QColor(0, 120, 215, 50))
        painter.drawRect(self._snip_rect)
        painter.end()
        self._image_label.setPixmap(overlay)

    def _finish_snip(self) -> None:
        if not self._snip_rect or self._snip_rect.isNull():
            self._cancel_snip()
            return

        # Map widget coords → pixmap coords
        label_rect = self._image_label.rect()
        pixmap_rect = self._pixmap.rect()
        # Simple scaling since label is centered in scroll area
        scale_x = pixmap_rect.width() / label_rect.width()
        scale_y = pixmap_rect.height() / label_rect.height()

        crop_rect = QRect(
            int(self._snip_rect.left() * scale_x),
            int(self._snip_rect.top() * scale_y),
            int(self._snip_rect.width() * scale_x),
            int(self._snip_rect.height() * scale_y),
        )

        # Crop and emit as PNG bytes
        cropped = self._pixmap.copy(crop_rect)
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        cropped.save(buffer, "PNG")
        png_bytes = bytes(buffer.data())
        buffer.close()

        self.region_snipped.emit(png_bytes)

        self._snipping = False
        self._snip_start = None
        self._snip_rect = None
        self._image_label.setCursor(Qt.CursorShape.ArrowCursor)
        self._render_current_page()  # redraw without overlay
        self._status.setText(translate("PDFViewer", "Region captured → sent to AI Tutor"))

    def _cancel_snip(self) -> None:
        self._snipping = False
        self._snip_start = None
        self._snip_rect = None
        self._image_label.setCursor(Qt.CursorShape.ArrowCursor)
        self._render_current_page()
        self._status.setText(translate("PDFViewer", "Snip cancelled"))

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    @property
    def current_page(self) -> int:
        return self._current_page

    @property
    def page_count(self) -> int:
        return self._doc.page_count if self._doc else 0
