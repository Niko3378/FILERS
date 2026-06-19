import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QStackedWidget, QSizePolicy, QSpinBox, QFrame,
    QSlider
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer
from PyQt6.QtGui import QPixmap, QImage, QColor, QFont, QWheelEvent

try:
    import fitz
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp",
    ".tif", ".tiff", ".ico", ".pbm", ".pgm", ".ppm",
    ".xbm", ".xpm", ".svg",
}
PDF_EXTS = {".pdf"}

SIZE_UNITS = ["o", "Ko", "Mo", "Go"]


def _fmt_size(size: int) -> str:
    s = float(size)
    for u in SIZE_UNITS:
        if s < 1024:
            return f"{s:.1f} {u}"
        s /= 1024
    return f"{s:.1f} To"


# ---------------------------------------------------------------------------
# Background loader
# ---------------------------------------------------------------------------

class PreviewLoader(QThread):
    image_ready = pyqtSignal(QPixmap, str)
    pdf_ready   = pyqtSignal(str, int)        # path, page_count
    error       = pyqtSignal(str)

    def __init__(self, path: str):
        super().__init__()
        self._path = path

    def run(self):
        ext = os.path.splitext(self._path)[1].lower()
        try:
            size = os.path.getsize(self._path)
        except OSError:
            size = 0

        if ext in IMAGE_EXTS:
            pix = QPixmap(self._path)
            if pix.isNull():
                self.error.emit("Image non lisible ou format non supporté.")
            else:
                info = f"{pix.width()} × {pix.height()} px  ·  {_fmt_size(size)}"
                self.image_ready.emit(pix, info)

        elif ext in PDF_EXTS:
            if not HAS_PYMUPDF:
                self.error.emit(
                    "PyMuPDF non installé.\n\n"
                    "Exécutez :\n    pip install PyMuPDF"
                )
                return
            try:
                doc = fitz.open(self._path)
                pages = doc.page_count
                doc.close()
                self.pdf_ready.emit(self._path, pages)
            except Exception as e:
                self.error.emit(f"Erreur PDF : {e}")

        else:
            self.error.emit("")   # empty string = show placeholder silently


# ---------------------------------------------------------------------------
# Zoomable image view
# ---------------------------------------------------------------------------

class ZoomableImageView(QScrollArea):
    def __init__(self):
        super().__init__()
        self._pixmap: QPixmap | None = None
        self._zoom = 1.0

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.setWidget(self._label)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: #2b2b2b; border: none;")

    def set_pixmap(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self.fit()

    def fit(self):
        if not self._pixmap:
            return
        vp = self.viewport().size()
        scaled = self._pixmap.scaled(
            vp.width() - 4, vp.height() - 4,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._zoom = scaled.width() / max(self._pixmap.width(), 1)
        self._apply(scaled)

    def zoom_in(self):
        self._set_zoom(self._zoom * 1.25)

    def zoom_out(self):
        self._set_zoom(self._zoom / 1.25)

    def _set_zoom(self, z: float):
        self._zoom = max(0.04, min(z, 20.0))
        if self._pixmap:
            w = int(self._pixmap.width() * self._zoom)
            h = int(self._pixmap.height() * self._zoom)
            scaled = self._pixmap.scaled(
                w, h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._apply(scaled)

    def _apply(self, scaled: QPixmap):
        self._label.setPixmap(scaled)
        self._label.resize(scaled.size())

    def zoom_pct(self) -> int:
        return int(self._zoom * 100)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap and self._zoom <= 1.0:
            self.fit()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
        else:
            super().wheelEvent(event)


# ---------------------------------------------------------------------------
# PDF viewer (one page at a time, rendered by PyMuPDF)
# ---------------------------------------------------------------------------

class PDFPageLoader(QThread):
    page_ready = pyqtSignal(QPixmap)
    error      = pyqtSignal(str)

    def __init__(self, path: str, page: int, dpi: float = 150.0):
        super().__init__()
        self._path = path
        self._page = page
        self._dpi = dpi

    def run(self):
        try:
            doc = fitz.open(self._path)
            pg = doc[self._page]
            zoom = self._dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = pg.get_pixmap(matrix=mat, alpha=False)
            img = QImage(
                bytes(pix.samples), pix.width, pix.height,
                pix.stride, QImage.Format.Format_RGB888,
            )
            doc.close()
            self.page_ready.emit(QPixmap.fromImage(img))
        except Exception as e:
            self.error.emit(str(e))


class PDFView(QWidget):
    def __init__(self):
        super().__init__()
        self._path = ""
        self._page_count = 0
        self._current_page = 0
        self._dpi = 150.0
        self._loader: PDFPageLoader | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Nav bar
        nav = QWidget()
        nav.setStyleSheet("background: #3c3c3c;")
        nav_row = QHBoxLayout(nav)
        nav_row.setContentsMargins(6, 4, 6, 4)

        self._prev_btn = QPushButton("◀")
        self._prev_btn.setFixedWidth(28)
        self._prev_btn.setStyleSheet("color:white; background:#555; border:none; border-radius:3px;")
        self._prev_btn.clicked.connect(self._prev_page)

        self._next_btn = QPushButton("▶")
        self._next_btn.setFixedWidth(28)
        self._next_btn.setStyleSheet("color:white; background:#555; border:none; border-radius:3px;")
        self._next_btn.clicked.connect(self._next_page)

        self._page_spin = QSpinBox()
        self._page_spin.setMinimum(1)
        self._page_spin.setFixedWidth(60)
        self._page_spin.setStyleSheet("color:white; background:#555; border:none; padding:2px;")
        self._page_spin.valueChanged.connect(self._on_spin)

        self._page_lbl = QLabel("/ 0")
        self._page_lbl.setStyleSheet("color:#ccc; margin:0 6px;")

        self._zoom_out_btn = QPushButton("−")
        self._zoom_out_btn.setFixedWidth(24)
        self._zoom_out_btn.setStyleSheet("color:white; background:#555; border:none; border-radius:3px;")
        self._zoom_out_btn.clicked.connect(self._zoom_out)

        self._zoom_lbl = QLabel("150 dpi")
        self._zoom_lbl.setStyleSheet("color:#ccc; margin:0 4px; min-width:55px;")
        self._zoom_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._zoom_in_btn = QPushButton("+")
        self._zoom_in_btn.setFixedWidth(24)
        self._zoom_in_btn.setStyleSheet("color:white; background:#555; border:none; border-radius:3px;")
        self._zoom_in_btn.clicked.connect(self._zoom_in)

        self._loading_lbl = QLabel("Chargement…")
        self._loading_lbl.setStyleSheet("color:#aaa; font-style:italic;")
        self._loading_lbl.hide()

        nav_row.addWidget(self._prev_btn)
        nav_row.addWidget(self._page_spin)
        nav_row.addWidget(self._page_lbl)
        nav_row.addWidget(self._next_btn)
        nav_row.addSpacing(16)
        nav_row.addWidget(self._zoom_out_btn)
        nav_row.addWidget(self._zoom_lbl)
        nav_row.addWidget(self._zoom_in_btn)
        nav_row.addStretch()
        nav_row.addWidget(self._loading_lbl)
        layout.addWidget(nav)

        self._image_view = ZoomableImageView()
        layout.addWidget(self._image_view)

    def load(self, path: str, page_count: int):
        self._path = path
        self._page_count = page_count
        self._current_page = 0
        self._page_spin.blockSignals(True)
        self._page_spin.setMaximum(page_count)
        self._page_spin.setValue(1)
        self._page_spin.blockSignals(False)
        self._page_lbl.setText(f"/ {page_count}")
        self._render()

    def _render(self):
        if self._loader and self._loader.isRunning():
            self._loader.terminate()
        self._loading_lbl.show()
        self._loader = PDFPageLoader(self._path, self._current_page, self._dpi)
        self._loader.page_ready.connect(self._on_page_ready)
        self._loader.error.connect(lambda e: self._loading_lbl.setText(f"Erreur: {e}"))
        self._loader.start()

    def _on_page_ready(self, pix: QPixmap):
        self._loading_lbl.hide()
        self._image_view.set_pixmap(pix)

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._page_spin.blockSignals(True)
            self._page_spin.setValue(self._current_page + 1)
            self._page_spin.blockSignals(False)
            self._render()

    def _next_page(self):
        if self._current_page < self._page_count - 1:
            self._current_page += 1
            self._page_spin.blockSignals(True)
            self._page_spin.setValue(self._current_page + 1)
            self._page_spin.blockSignals(False)
            self._render()

    def _on_spin(self, value: int):
        self._current_page = value - 1
        self._render()

    def _zoom_in(self):
        self._dpi = min(self._dpi * 1.3, 600.0)
        self._zoom_lbl.setText(f"{int(self._dpi)} dpi")
        self._render()

    def _zoom_out(self):
        self._dpi = max(self._dpi / 1.3, 36.0)
        self._zoom_lbl.setText(f"{int(self._dpi)} dpi")
        self._render()


# ---------------------------------------------------------------------------
# No-preview placeholder
# ---------------------------------------------------------------------------

class NoPreviewWidget(QWidget):
    def __init__(self, message: str = ""):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: #2b2b2b;")

        icon = QLabel("🗋")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = icon.font()
        font.setPointSize(48)
        icon.setFont(font)
        icon.setStyleSheet("color:#555; background:transparent;")

        self._msg = QLabel(message or "Sélectionnez un fichier\npour afficher un aperçu")
        self._msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._msg.setWordWrap(True)
        self._msg.setStyleSheet("color:#888; background:transparent; font-size:13px;")

        layout.addStretch()
        layout.addWidget(icon)
        layout.addSpacing(12)
        layout.addWidget(self._msg)
        layout.addStretch()

    def set_message(self, msg: str):
        self._msg.setText(msg)


# ---------------------------------------------------------------------------
# Main preview panel
# ---------------------------------------------------------------------------

class PreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_path = ""
        self._loader: PreviewLoader | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        bar = QWidget()
        bar.setStyleSheet("background:#3c3c3c;")
        bar_row = QHBoxLayout(bar)
        bar_row.setContentsMargins(8, 4, 8, 4)

        self._filename_lbl = QLabel("Aperçu")
        self._filename_lbl.setStyleSheet("color:white; font-weight:bold;")

        self._info_lbl = QLabel("")
        self._info_lbl.setStyleSheet("color:#aaa; margin-left:12px;")

        self._zoom_in_btn  = QPushButton("+")
        self._zoom_out_btn = QPushButton("−")
        self._fit_btn      = QPushButton("Ajuster")
        for btn in (self._zoom_in_btn, self._zoom_out_btn, self._fit_btn):
            btn.setFixedHeight(24)
            btn.setStyleSheet("color:white; background:#555; border:none; border-radius:3px; padding:0 8px;")

        self._zoom_in_btn.clicked.connect(self._zoom_in)
        self._zoom_out_btn.clicked.connect(self._zoom_out)
        self._fit_btn.clicked.connect(self._fit)
        self._zoom_in_btn.hide()
        self._zoom_out_btn.hide()
        self._fit_btn.hide()

        bar_row.addWidget(self._filename_lbl)
        bar_row.addWidget(self._info_lbl)
        bar_row.addStretch()
        bar_row.addWidget(self._zoom_out_btn)
        bar_row.addWidget(self._zoom_in_btn)
        bar_row.addWidget(self._fit_btn)
        layout.addWidget(bar)

        # Stack
        self._stack = QStackedWidget()
        self._no_preview = NoPreviewWidget()
        self._image_view = ZoomableImageView()
        self._pdf_view   = PDFView()

        self._stack.addWidget(self._no_preview)   # 0
        self._stack.addWidget(self._image_view)   # 1
        self._stack.addWidget(self._pdf_view)     # 2
        layout.addWidget(self._stack)

    # ---- public API --------------------------------------------------------

    def load_file(self, path: str):
        if path == self._current_path:
            return
        self._current_path = path

        if not path or not os.path.isfile(path):
            self._show_placeholder("")
            return

        ext = os.path.splitext(path)[1].lower()
        if ext not in IMAGE_EXTS and ext not in PDF_EXTS:
            self._show_placeholder("")
            return

        self._filename_lbl.setText(os.path.basename(path))
        self._info_lbl.setText("Chargement…")
        self._show_placeholder("Chargement…")

        if self._loader and self._loader.isRunning():
            self._loader.terminate()
        self._loader = PreviewLoader(path)
        self._loader.image_ready.connect(self._on_image_ready)
        self._loader.pdf_ready.connect(self._on_pdf_ready)
        self._loader.error.connect(self._on_error)
        self._loader.start()

    def clear(self):
        self._current_path = ""
        self._show_placeholder("")

    # ---- slots -------------------------------------------------------------

    def _on_image_ready(self, pix: QPixmap, info: str):
        self._info_lbl.setText(info)
        self._image_view.set_pixmap(pix)
        self._stack.setCurrentIndex(1)
        self._zoom_in_btn.show()
        self._zoom_out_btn.show()
        self._fit_btn.show()

    def _on_pdf_ready(self, path: str, page_count: int):
        self._info_lbl.setText(f"{page_count} page(s)")
        self._pdf_view.load(path, page_count)
        self._stack.setCurrentIndex(2)
        self._zoom_in_btn.hide()
        self._zoom_out_btn.hide()
        self._fit_btn.hide()

    def _on_error(self, msg: str):
        if msg:
            self._show_placeholder(msg)
            self._info_lbl.setText("Erreur")
        else:
            self._show_placeholder("")
            self._info_lbl.setText("")
            self._filename_lbl.setText("Aperçu")

    def _show_placeholder(self, msg: str):
        self._no_preview.set_message(msg or "Sélectionnez une image ou un PDF\npour afficher un aperçu")
        self._stack.setCurrentIndex(0)
        self._zoom_in_btn.hide()
        self._zoom_out_btn.hide()
        self._fit_btn.hide()

    def _zoom_in(self):
        self._image_view.zoom_in()

    def _zoom_out(self):
        self._image_view.zoom_out()

    def _fit(self):
        self._image_view.fit()
