import os
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QTextEdit,
    QLabel, QPushButton, QLineEdit, QToolBar, QComboBox, QCheckBox,
    QFileDialog, QMessageBox, QFrame, QSizePolicy, QStatusBar,
    QTabWidget, QSplitter, QScrollArea
)
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal, QRegularExpression
from PyQt6.QtGui import (
    QColor, QPainter, QFont, QTextCharFormat, QSyntaxHighlighter,
    QTextCursor, QKeySequence, QAction, QPalette, QTextOption,
    QTextDocument
)


# ---------------------------------------------------------------------------
# Syntax highlighting
# ---------------------------------------------------------------------------

class HighlightRule:
    def __init__(self, pattern: str, fmt: QTextCharFormat, flags=QRegularExpression.PatternOption(0)):
        self.regex = QRegularExpression(pattern, flags)
        self.fmt = fmt


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(700)
    if italic:
        f.setFontItalic(True)
    return f


PYTHON_RULES = [
    HighlightRule(r"\b(False|None|True|and|as|assert|async|await|break|class|continue|"
                  r"def|del|elif|else|except|finally|for|from|global|if|import|in|is|"
                  r"lambda|nonlocal|not|or|pass|raise|return|try|while|with|yield)\b",
                  _fmt("#0000cd", bold=True)),
    HighlightRule(r"\b(int|str|float|bool|list|dict|set|tuple|type|len|range|print|"
                  r"super|self|cls|open|isinstance|enumerate|zip|map|filter|sorted|"
                  r"min|max|sum|abs|round|repr|vars|dir|hasattr|getattr|setattr)\b",
                  _fmt("#8b008b")),
    HighlightRule(r"#[^\n]*", _fmt("#6a737d", italic=True)),
    HighlightRule(r'"""[\s\S]*?"""', _fmt("#6a737d", italic=True),
                  QRegularExpression.PatternOption.DotMatchesEverythingOption),
    HighlightRule(r"'''[\s\S]*?'''", _fmt("#6a737d", italic=True),
                  QRegularExpression.PatternOption.DotMatchesEverythingOption),
    HighlightRule(r'"[^"\\]*(\\.[^"\\]*)*"', _fmt("#a31515")),
    HighlightRule(r"'[^'\\]*(\\.[^'\\]*)*'", _fmt("#a31515")),
    HighlightRule(r"\b\d+(\.\d+)?\b", _fmt("#098658")),
    HighlightRule(r"@\w+", _fmt("#795e26")),
    HighlightRule(r"\bdef\s+(\w+)", _fmt("#795e26", bold=True)),
    HighlightRule(r"\bclass\s+(\w+)", _fmt("#267f99", bold=True)),
]

JS_RULES = [
    HighlightRule(r"\b(var|let|const|function|return|if|else|for|while|do|switch|case|"
                  r"break|continue|new|delete|typeof|instanceof|in|of|class|extends|"
                  r"import|export|default|async|await|try|catch|finally|throw|null|"
                  r"undefined|true|false|this|super|yield)\b", _fmt("#0000cd", bold=True)),
    HighlightRule(r"//[^\n]*", _fmt("#6a737d", italic=True)),
    HighlightRule(r"/\*[\s\S]*?\*/", _fmt("#6a737d", italic=True),
                  QRegularExpression.PatternOption.DotMatchesEverythingOption),
    HighlightRule(r'"[^"\\]*(\\.[^"\\]*)*"', _fmt("#a31515")),
    HighlightRule(r"'[^'\\]*(\\.[^'\\]*)*'", _fmt("#a31515")),
    HighlightRule(r"`[^`\\]*(\\.[^`\\]*)*`", _fmt("#a31515")),
    HighlightRule(r"\b\d+(\.\d+)?\b", _fmt("#098658")),
]

HTML_RULES = [
    HighlightRule(r"<!--[\s\S]*?-->", _fmt("#6a737d", italic=True),
                  QRegularExpression.PatternOption.DotMatchesEverythingOption),
    HighlightRule(r"<[!?/]?[\w:-]+", _fmt("#0000cd", bold=True)),
    HighlightRule(r"/>|>", _fmt("#0000cd", bold=True)),
    HighlightRule(r'\b[\w:-]+=', _fmt("#795e26")),
    HighlightRule(r'"[^"]*"', _fmt("#a31515")),
    HighlightRule(r"'[^']*'", _fmt("#a31515")),
    HighlightRule(r"&\w+;", _fmt("#098658")),
]

CSS_RULES = [
    HighlightRule(r"/\*[\s\S]*?\*/", _fmt("#6a737d", italic=True),
                  QRegularExpression.PatternOption.DotMatchesEverythingOption),
    HighlightRule(r"[\w-]+\s*:", _fmt("#0000cd")),
    HighlightRule(r"#[\da-fA-F]{3,8}\b", _fmt("#a31515")),
    HighlightRule(r'"[^"]*"', _fmt("#a31515")),
    HighlightRule(r"'[^']*'", _fmt("#a31515")),
    HighlightRule(r"\b\d+(\.\d+)?(px|em|rem|%|vh|vw|pt|cm|mm|s|ms)?\b", _fmt("#098658")),
    HighlightRule(r"\.[a-zA-Z][\w-]*", _fmt("#267f99")),
    HighlightRule(r"#[a-zA-Z][\w-]*", _fmt("#795e26")),
]

RULES_BY_EXT = {
    ".py": PYTHON_RULES, ".pyw": PYTHON_RULES,
    ".js": JS_RULES, ".mjs": JS_RULES, ".ts": JS_RULES, ".jsx": JS_RULES, ".tsx": JS_RULES,
    ".html": HTML_RULES, ".htm": HTML_RULES, ".xml": HTML_RULES, ".svg": HTML_RULES,
    ".css": CSS_RULES, ".scss": CSS_RULES, ".less": CSS_RULES,
}


class Highlighter(QSyntaxHighlighter):
    def __init__(self, document, ext: str = ""):
        super().__init__(document)
        self._rules = RULES_BY_EXT.get(ext.lower(), [])

    def highlightBlock(self, text: str):
        for rule in self._rules:
            it = rule.regex.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), rule.fmt)

    def set_extension(self, ext: str):
        self._rules = RULES_BY_EXT.get(ext.lower(), [])
        self.rehighlight()


# ---------------------------------------------------------------------------
# Line number area
# ---------------------------------------------------------------------------

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor._line_number_width(), 0)

    def paintEvent(self, event):
        self._editor._paint_line_numbers(event)


# ---------------------------------------------------------------------------
# Code editor
# ---------------------------------------------------------------------------

class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        font = QFont("Courier New", 10)
        font.setFixedPitch(True)
        self.setFont(font)
        self.setTabStopDistance(40)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self._line_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_line_area_width()
        self._highlight_current_line()

    def _line_number_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * (digits + 1)

    def _update_line_area_width(self):
        self.setViewportMargins(self._line_number_width(), 0, 0, 0)

    def _update_line_area(self, rect, dy):
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(QRect(cr.left(), cr.top(),
                                          self._line_number_width(), cr.height()))

    def _paint_line_numbers(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))
        block = self.firstVisibleBlock()
        num = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor("#888888"))
                painter.drawText(0, top, self._line_area.width() - 4,
                                 self.fontMetrics().height(),
                                 Qt.AlignmentFlag.AlignRight, str(num + 1))
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            num += 1

    def _highlight_current_line(self):
        selections = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            sel.format.setBackground(QColor("#fffde7"))
            sel.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            selections.append(sel)
        self.setExtraSelections(selections)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            cursor = self.textCursor()
            cursor.insertText("    ")
            return
        super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Find/Replace bar
# ---------------------------------------------------------------------------

class FindBar(QWidget):
    closed = pyqtSignal()

    def __init__(self, editor: CodeEditor, parent=None):
        super().__init__(parent)
        self._editor = editor
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)

        self._find_edit = QLineEdit()
        self._find_edit.setPlaceholderText("Rechercher…")
        self._find_edit.setFixedWidth(200)
        self._find_edit.textChanged.connect(self._do_find)
        self._find_edit.returnPressed.connect(self._find_next)

        self._replace_edit = QLineEdit()
        self._replace_edit.setPlaceholderText("Remplacer par…")
        self._replace_edit.setFixedWidth(200)

        self._case_cb = QCheckBox("Casse")
        self._regex_cb = QCheckBox("Regex")

        prev_btn = QPushButton("◀")
        prev_btn.setFixedWidth(28)
        prev_btn.setToolTip("Précédent")
        prev_btn.clicked.connect(self._find_prev)

        next_btn = QPushButton("▶")
        next_btn.setFixedWidth(28)
        next_btn.setToolTip("Suivant")
        next_btn.clicked.connect(self._find_next)

        repl_btn = QPushButton("Remplacer")
        repl_btn.clicked.connect(self._replace_one)

        repl_all_btn = QPushButton("Tout remplacer")
        repl_all_btn.clicked.connect(self._replace_all)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet("color: #666; min-width: 60px;")

        close_btn = QPushButton("✕")
        close_btn.setFixedWidth(24)
        close_btn.setFlat(True)
        close_btn.clicked.connect(self.close_bar)

        layout.addWidget(QLabel("Rech.:"))
        layout.addWidget(self._find_edit)
        layout.addWidget(prev_btn)
        layout.addWidget(next_btn)
        layout.addWidget(self._case_cb)
        layout.addWidget(self._regex_cb)
        layout.addSpacing(8)
        layout.addWidget(QLabel("Rempl.:"))
        layout.addWidget(self._replace_edit)
        layout.addWidget(repl_btn)
        layout.addWidget(repl_all_btn)
        layout.addWidget(self._count_label)
        layout.addStretch()
        layout.addWidget(close_btn)

        self.setMaximumHeight(36)
        self.setStyleSheet("background: #fff9c4; border-top: 1px solid #f0c040;")

    def close_bar(self):
        self.hide()
        self.closed.emit()
        self._editor.setFocus()

    def show_bar(self):
        self.show()
        sel = self._editor.textCursor().selectedText()
        if sel:
            self._find_edit.setText(sel)
        self._find_edit.setFocus()
        self._find_edit.selectAll()

    def _flags(self) -> QTextDocument.FindFlag:
        from PyQt6.QtGui import QTextDocument
        flags = QTextDocument.FindFlag(0)
        if self._case_cb.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        return flags

    def _do_find(self):
        term = self._find_edit.text()
        if not term:
            self._count_label.setText("")
            return
        doc = self._editor.document()
        count = 0
        cursor = QTextCursor(doc)
        while True:
            if self._regex_cb.isChecked():
                cursor = doc.find(QRegularExpression(term), cursor, self._flags())
            else:
                cursor = doc.find(term, cursor, self._flags())
            if cursor.isNull():
                break
            count += 1
        self._count_label.setText(f"{count} résultat(s)")

    def _find_next(self):
        self._find(forward=True)

    def _find_prev(self):
        self._find(forward=False)

    def _find(self, forward: bool = True):
        from PyQt6.QtGui import QTextDocument
        term = self._find_edit.text()
        if not term:
            return
        flags = self._flags()
        if not forward:
            flags |= QTextDocument.FindFlag.FindBackward
        doc = self._editor.document()
        cursor = self._editor.textCursor()
        if self._regex_cb.isChecked():
            found = doc.find(QRegularExpression(term), cursor, flags)
        else:
            found = doc.find(term, cursor, flags)
        if found.isNull():
            cursor.movePosition(
                QTextCursor.MoveOperation.End if not forward else QTextCursor.MoveOperation.Start
            )
            if self._regex_cb.isChecked():
                found = doc.find(QRegularExpression(term), cursor, flags)
            else:
                found = doc.find(term, cursor, flags)
        if not found.isNull():
            self._editor.setTextCursor(found)
            self._find_edit.setStyleSheet("")
        else:
            self._find_edit.setStyleSheet("background: #ffc0c0;")

    def _replace_one(self):
        cursor = self._editor.textCursor()
        if cursor.hasSelection():
            cursor.insertText(self._replace_edit.text())
        self._find_next()

    def _replace_all(self):
        term = self._find_edit.text()
        replacement = self._replace_edit.text()
        if not term:
            return
        doc = self._editor.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        count = 0
        while True:
            if self._regex_cb.isChecked():
                found = doc.find(QRegularExpression(term), cursor, self._flags())
            else:
                found = doc.find(term, cursor, self._flags())
            if found.isNull():
                break
            found.insertText(replacement)
            cursor = found
            count += 1
        cursor.endEditBlock()
        self._count_label.setText(f"{count} remplacé(s)")


# ---------------------------------------------------------------------------
# Full editor widget (one tab/file)
# ---------------------------------------------------------------------------

class EditorWidget(QWidget):
    title_changed = pyqtSignal(str)
    modified_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._path = ""
        self._encoding = "utf-8"
        self._modified = False
        self._highlighter = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._editor = CodeEditor()
        self._editor.document().contentsChanged.connect(self._on_modified)
        layout.addWidget(self._editor)

        self._find_bar = FindBar(self._editor)
        self._find_bar.hide()
        layout.addWidget(self._find_bar)

        self._status = QLabel("  Ln 1, Col 1  |  UTF-8  |  Nouveau fichier")
        self._status.setStyleSheet("background: #f5f5f5; border-top: 1px solid #ddd; padding: 2px 6px; font-size: 11px;")
        layout.addWidget(self._status)

        self._editor.cursorPositionChanged.connect(self._update_status)
        self._highlighter = Highlighter(self._editor.document(), "")

    def _on_modified(self):
        if not self._modified:
            self._modified = True
            self.modified_changed.emit(True)
            self._update_title()

    def _update_title(self):
        name = os.path.basename(self._path) if self._path else "Nouveau"
        title = ("* " if self._modified else "") + name
        self.title_changed.emit(title)

    def _update_status(self):
        cursor = self._editor.textCursor()
        ln = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        fname = os.path.basename(self._path) if self._path else "Nouveau fichier"
        self._status.setText(f"  Ln {ln}, Col {col}  |  {self._encoding}  |  {fname}")

    def load_file(self, path: str):
        try:
            import chardet
            with open(path, "rb") as f:
                raw = f.read()
            enc = chardet.detect(raw)["encoding"] or "utf-8"
            text = raw.decode(enc, errors="replace")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", str(e))
            return
        self._path = path
        self._encoding = enc
        self._editor.document().contentsChanged.disconnect(self._on_modified)
        self._editor.setPlainText(text)
        self._editor.document().contentsChanged.connect(self._on_modified)
        self._modified = False
        ext = os.path.splitext(path)[1]
        self._highlighter.set_extension(ext)
        self._update_title()
        self._update_status()

    def save(self) -> bool:
        if not self._path:
            return self.save_as()
        try:
            text = self._editor.toPlainText()
            with open(self._path, "w", encoding=self._encoding, errors="replace") as f:
                f.write(text)
            self._modified = False
            self.modified_changed.emit(False)
            self._update_title()
            return True
        except Exception as e:
            QMessageBox.critical(self, "Erreur sauvegarde", str(e))
            return False

    def save_as(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(self, "Enregistrer sous")
        if path:
            self._path = path
            ext = os.path.splitext(path)[1]
            self._highlighter.set_extension(ext)
            return self.save()
        return False

    def show_find(self):
        self._find_bar.show_bar()

    def get_path(self) -> str:
        return self._path

    def is_modified(self) -> bool:
        return self._modified

    def can_close(self) -> bool:
        if not self._modified:
            return True
        name = os.path.basename(self._path) if self._path else "Nouveau fichier"
        reply = QMessageBox.question(
            self, "Modifications non sauvegardées",
            f"« {name} » a des modifications non sauvegardées.\nSauvegarder ?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel
        )
        if reply == QMessageBox.StandardButton.Save:
            return self.save()
        return reply == QMessageBox.StandardButton.Discard


# ---------------------------------------------------------------------------
# Multi-tab text editor
# ---------------------------------------------------------------------------

class TextEditor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("QToolBar { background: #ecf0f1; border-bottom: 1px solid #d0d3de; spacing: 2px; padding: 2px; }")

        act_new = QAction("Nouveau", self)
        act_new.setShortcut(QKeySequence("Ctrl+T"))
        act_new.triggered.connect(self.new_tab)
        toolbar.addAction(act_new)

        act_open = QAction("Ouvrir…", self)
        act_open.setShortcut(QKeySequence("Ctrl+O"))
        act_open.triggered.connect(self.open_file_dialog)
        toolbar.addAction(act_open)

        act_save = QAction("Enregistrer", self)
        act_save.setShortcut(QKeySequence("Ctrl+S"))
        act_save.triggered.connect(self.save_current)
        toolbar.addAction(act_save)

        act_save_as = QAction("Enreg. sous…", self)
        act_save_as.triggered.connect(self.save_as_current)
        toolbar.addAction(act_save_as)

        toolbar.addSeparator()

        act_find = QAction("Rechercher  Ctrl+F", self)
        act_find.setShortcut(QKeySequence("Ctrl+F"))
        act_find.triggered.connect(self.show_find)
        toolbar.addAction(act_find)

        toolbar.addSeparator()

        act_close = QAction("Fermer onglet", self)
        act_close.setShortcut(QKeySequence("Ctrl+W"))
        act_close.triggered.connect(self.close_current_tab)
        toolbar.addAction(act_close)

        layout.addWidget(toolbar)

        self._tabs = QTabWidget()
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self.close_tab)
        self._tabs.setMovable(True)
        layout.addWidget(self._tabs)

        self.new_tab()

    def new_tab(self) -> EditorWidget:
        editor = EditorWidget()
        editor.title_changed.connect(lambda t, w=editor: self._on_title_changed(t, w))
        idx = self._tabs.addTab(editor, "Nouveau")
        self._tabs.setCurrentIndex(idx)
        editor._editor.setFocus()
        return editor

    def _on_title_changed(self, title: str, widget: EditorWidget):
        idx = self._tabs.indexOf(widget)
        if idx >= 0:
            self._tabs.setTabText(idx, title)

    def open_file(self, path: str):
        for i in range(self._tabs.count()):
            w = self._tabs.widget(i)
            if isinstance(w, EditorWidget) and w.get_path() == path:
                self._tabs.setCurrentIndex(i)
                return
        current = self._tabs.currentWidget()
        if isinstance(current, EditorWidget) and not current.get_path() and not current.is_modified():
            editor = current
        else:
            editor = self.new_tab()
        editor.load_file(path)

    def open_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Ouvrir un fichier")
        if path:
            self.open_file(path)

    def save_current(self):
        w = self._tabs.currentWidget()
        if isinstance(w, EditorWidget):
            w.save()

    def save_as_current(self):
        w = self._tabs.currentWidget()
        if isinstance(w, EditorWidget):
            w.save_as()

    def show_find(self):
        w = self._tabs.currentWidget()
        if isinstance(w, EditorWidget):
            w.show_find()

    def close_tab(self, idx: int):
        w = self._tabs.widget(idx)
        if isinstance(w, EditorWidget):
            if not w.can_close():
                return
        self._tabs.removeTab(idx)
        if self._tabs.count() == 0:
            self.new_tab()

    def close_current_tab(self):
        self.close_tab(self._tabs.currentIndex())
