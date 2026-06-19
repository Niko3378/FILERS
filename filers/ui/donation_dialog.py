from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QFont, QColor, QLinearGradient, QPainter, QBrush

PAYPAL_URL = "https://www.paypal.com/donate?business=niko_3378@yahoo.fr&currency_code=EUR"


class _Header(QFrame):
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, QColor("#1e3c72"))
        grad.setColorAt(1.0, QColor("#0a1628"))
        p.fillRect(self.rect(), QBrush(grad))


class DonationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Soutenir Files Manager")
        self.setFixedSize(400, 310)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.MSWindowsFixedSizeDialogHint
        )
        self.setStyleSheet("QDialog { background: #f8f9fb; border-radius: 8px; }")
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── En-tête dégradé ──────────────────────────────────────────────────
        hdr = _Header()
        hdr.setFixedHeight(90)
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(20, 10, 20, 10)
        hl.setSpacing(14)

        emoji = QLabel("💙")
        emoji.setFont(QFont("Segoe UI Emoji", 36))
        emoji.setStyleSheet("background: transparent; color: white;")
        hl.addWidget(emoji)

        col = QVBoxLayout()
        col.setSpacing(2)
        t = QLabel("Soutenir Files Manager")
        t.setStyleSheet("background: transparent; color: white; font: bold 16px 'Segoe UI';")
        s = QLabel("Application 100 % gratuite, développée avec passion")
        s.setStyleSheet("background: transparent; color: #95a5a6; font: 9px 'Segoe UI';")
        col.addWidget(t)
        col.addWidget(s)
        hl.addLayout(col)
        hl.addStretch()
        root.addWidget(hdr)

        # ── Séparateur accent bleu ────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(3)
        sep.setStyleSheet("background: #3498db;")
        root.addWidget(sep)

        # ── Corps ────────────────────────────────────────────────────────────
        body = QFrame()
        body.setStyleSheet("background: #f8f9fb;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(28, 22, 28, 22)
        bl.setSpacing(14)

        msg = QLabel(
            "Files Manager vous fait gagner du temps chaque jour.\n"
            "Si vous l'appréciez, un petit don aide à le\n"
            "maintenir et à ajouter de nouvelles fonctionnalités."
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(
            "color: #4a5568; font: 10px 'Segoe UI'; background: transparent; "
            "line-height: 1.5;"
        )
        msg.setWordWrap(True)
        bl.addWidget(msg)

        # Bouton PayPal
        pp = QPushButton("  💳   Faire un don via PayPal")
        pp.setFixedHeight(46)
        pp.setCursor(Qt.CursorShape.PointingHandCursor)
        pp.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        pp.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #0070ba, stop:1 #003087);
                color: white;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #1a82cc, stop:1 #0a3d9e);
            }
            QPushButton:pressed { background: #001f5c; }
        """)
        pp.clicked.connect(self._donate)
        bl.addWidget(pp)

        # Ligne basse
        row = QHBoxLayout()
        row.setSpacing(8)

        later = QPushButton("Plus tard")
        later.setFixedHeight(30)
        later.setCursor(Qt.CursorShape.PointingHandCursor)
        later.setStyleSheet("""
            QPushButton {
                background: transparent; color: #7f8c8d;
                border: 1px solid #d0d3de; border-radius: 4px;
                font: 9px 'Segoe UI'; padding: 0 12px;
            }
            QPushButton:hover { color: #2c3e50; border-color: #aaa; }
        """)
        later.clicked.connect(self.reject)

        note = QLabel("Réapparaît dans 5 min")
        note.setStyleSheet("color: #bdc3c7; font: 8px 'Segoe UI'; background: transparent;")
        note.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        note.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        row.addWidget(later)
        row.addWidget(note)
        bl.addLayout(row)

        root.addWidget(body)

    def _donate(self):
        QDesktopServices.openUrl(QUrl(PAYPAL_URL))
        self.accept()
