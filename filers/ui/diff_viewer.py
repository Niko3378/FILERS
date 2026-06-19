from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QTextEdit,
    QLabel, QPushButton, QScrollBar, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextCharFormat, QColor, QFont, QTextCursor, QSyntaxHighlighter

from core.diff_engine import DiffLine


COLORS = {
    "equal":   ("#ffffff", "#ffffff"),
    "replace": ("#ffeeba", "#ffeeba"),
    "delete":  ("#ffc0c0", "#e8ffe8"),
    "insert":  ("#e8ffe8", "#ffc0c0"),
}


class DiffPane(QTextEdit):
    def __init__(self, side: str):
        super().__init__()
        self.side = side
        self.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.setFont(font)
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

    def set_lines(self, lines: list[DiffLine]):
        self.clear()
        cursor = self.textCursor()
        fmt = QTextCharFormat()
        for dl in lines:
            text = dl.left_text if self.side == "left" else dl.right_text
            num = dl.left_num if self.side == "left" else dl.right_num
            bg_l, bg_r = COLORS.get(dl.kind, ("#ffffff", "#ffffff"))
            bg = bg_l if self.side == "left" else bg_r

            if num:
                num_str = f"{num:>5} "
            else:
                num_str = "      "

            fmt.setBackground(QColor(bg))
            fmt.setForeground(QColor("#555555"))
            cursor.insertText(num_str, fmt)
            fmt.setForeground(QColor("#000000"))
            cursor.insertText(text + "\n", fmt)
        self.setTextCursor(cursor)
        self.moveCursor(QTextCursor.MoveOperation.Start)


class DiffViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        header = QHBoxLayout()
        self._left_label = QLabel("Gauche")
        self._right_label = QLabel("Droite")
        self._left_label.setStyleSheet("font-weight: bold; padding: 4px;")
        self._right_label.setStyleSheet("font-weight: bold; padding: 4px;")
        header.addWidget(self._left_label)
        header.addWidget(self._right_label)
        layout.addLayout(header)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._left_pane = DiffPane("left")
        self._right_pane = DiffPane("right")
        self._splitter.addWidget(self._left_pane)
        self._splitter.addWidget(self._right_pane)
        self._splitter.setSizes([500, 500])
        layout.addWidget(self._splitter)

        self._sync_scroll()

        stats = QHBoxLayout()
        self._stats_label = QLabel("")
        stats.addWidget(self._stats_label)
        layout.addLayout(stats)

    def _sync_scroll(self):
        l_vbar = self._left_pane.verticalScrollBar()
        r_vbar = self._right_pane.verticalScrollBar()
        l_hbar = self._left_pane.horizontalScrollBar()
        r_hbar = self._right_pane.horizontalScrollBar()
        l_vbar.valueChanged.connect(r_vbar.setValue)
        r_vbar.valueChanged.connect(l_vbar.setValue)
        l_hbar.valueChanged.connect(r_hbar.setValue)
        r_hbar.valueChanged.connect(l_hbar.setValue)

    def load(self, left_text: str, right_text: str,
             left_name: str = "Gauche", right_name: str = "Droite"):
        from core.diff_engine import diff_texts
        self._left_label.setText(left_name)
        self._right_label.setText(right_name)
        lines = diff_texts(left_text, right_text)
        self._left_pane.set_lines(lines)
        self._right_pane.set_lines(lines)

        added = sum(1 for l in lines if l.kind == "insert")
        removed = sum(1 for l in lines if l.kind == "delete")
        changed = sum(1 for l in lines if l.kind == "replace")
        self._stats_label.setText(
            f"  +{added} ajoutées  -{removed} supprimées  ~{changed} modifiées"
        )
