import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QLineEdit,
    QHeaderView, QAbstractItemView, QProgressBar, QMessageBox, QTabWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core.inventory_reporter import (
    collect, analyze_disk_space, diskspace_to_csv, diskspace_to_pdf,
    _fmt_size,
)

_SORT_ROLE = Qt.ItemDataRole.UserRole


class _SortableItem(QTreeWidgetItem):
    def __lt__(self, other: QTreeWidgetItem) -> bool:
        col = self.treeWidget().sortColumn()
        a = self.data(col, _SORT_ROLE)
        b = other.data(col, _SORT_ROLE)
        if a is not None and b is not None:
            try:
                return a < b
            except TypeError:
                pass
        return self.text(col).lower() < other.text(col).lower()


class DiskSpaceWorker(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, folder: str, show_hidden: bool):
        super().__init__()
        self.folder = folder
        self.show_hidden = show_hidden

    def run(self):
        try:
            entries = collect(self.folder, recursive=True, show_hidden=self.show_hidden)
            analysis = analyze_disk_space(entries)
            self.done.emit(analysis)
        except Exception as e:
            self.error.emit(str(e))


def _bar(pct: float, width: int = 24) -> str:
    filled = round(pct / 100 * width)
    return "█" * filled + "░" * (width - filled)


class DiskSpacePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._analysis: dict | None = None
        self._folder = ""
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── Ligne de contrôle ─────────────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Dossier :"))
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText("Chemin du dossier à analyser…")
        top_row.addWidget(self._folder_edit)
        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(30)
        browse_btn.clicked.connect(self._browse)
        top_row.addWidget(browse_btn)
        top_row.addSpacing(10)
        self._analyze_btn = QPushButton("Analyser")
        self._analyze_btn.clicked.connect(self._start)
        top_row.addWidget(self._analyze_btn)
        layout.addLayout(top_row)

        # ── Barre de progression ───────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # ── Résumé ────────────────────────────────────────────────────────
        self._summary = QLabel("")
        self._summary.setStyleSheet(
            "padding: 6px; background: #e8f0fe; border-left: 3px solid #1565c0;"
        )
        self._summary.setVisible(False)
        layout.addWidget(self._summary)

        # ── Onglets résultats ─────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_file_tree(), "Top fichiers")
        self._tabs.addTab(self._build_dir_tree(), "Top dossiers")
        self._tabs.addTab(self._build_ext_tree(), "Par extension")
        layout.addWidget(self._tabs)

        # ── Export ────────────────────────────────────────────────────────
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        self._export_pdf_btn = QPushButton("Exporter PDF…")
        self._export_pdf_btn.setEnabled(False)
        self._export_pdf_btn.clicked.connect(self._export_pdf)
        bottom_row.addWidget(self._export_pdf_btn)
        self._export_csv_btn = QPushButton("Exporter CSV…")
        self._export_csv_btn.setEnabled(False)
        self._export_csv_btn.clicked.connect(self._export_csv)
        bottom_row.addWidget(self._export_csv_btn)
        layout.addLayout(bottom_row)

    def _make_tree(self, headers: list) -> QTreeWidget:
        tree = QTreeWidget()
        tree.setColumnCount(len(headers))
        tree.setHeaderLabels(headers)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, len(headers)):
            tree.header().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        tree.setAlternatingRowColors(True)
        tree.setRootIsDecorated(False)
        tree.setSortingEnabled(True)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        return tree

    def _build_file_tree(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._file_tree = self._make_tree(["Nom", "Taille", "Chemin"])
        layout.addWidget(self._file_tree)
        return w

    def _build_dir_tree(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._dir_tree = self._make_tree(["Dossier", "Taille", "Chemin"])
        layout.addWidget(self._dir_tree)
        return w

    def _build_ext_tree(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 4, 0, 0)
        self._ext_tree = self._make_tree(["Extension", "Nb fichiers", "Taille", "Part"])
        layout.addWidget(self._ext_tree)
        return w

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Choisir un dossier", self._folder or "")
        if path:
            self._folder_edit.setText(path)

    def _start(self):
        folder = self._folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Analyse", "Dossier invalide ou introuvable.")
            return
        self._folder = folder
        self._analysis = None
        self._file_tree.clear()
        self._dir_tree.clear()
        self._ext_tree.clear()
        self._summary.setVisible(False)
        self._export_pdf_btn.setEnabled(False)
        self._export_csv_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._analyze_btn.setEnabled(False)

        self._worker = DiskSpaceWorker(folder, show_hidden=False)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, analysis: dict):
        self._progress.setVisible(False)
        self._analyze_btn.setEnabled(True)
        self._analysis = analysis

        self._summary.setText(
            f"  <b>Total :</b> {analysis['total_size_fmt']} &nbsp;·&nbsp; "
            f"{analysis['total_files']} fichier(s) &nbsp;·&nbsp; "
            f"{analysis['total_dirs']} dossier(s)"
        )
        self._summary.setTextFormat(Qt.TextFormat.RichText)
        self._summary.setVisible(True)

        self._fill_file_tree(analysis["top_files"])
        self._fill_dir_tree(analysis["top_dirs"])
        self._fill_ext_tree(analysis["by_extension"])

        self._export_pdf_btn.setEnabled(True)
        self._export_csv_btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._analyze_btn.setEnabled(True)
        QMessageBox.critical(self, "Erreur analyse", msg)

    def _fill_file_tree(self, entries):
        self._file_tree.setSortingEnabled(False)
        for e in entries:
            item = _SortableItem([e.name, _fmt_size(e.size), e.path])
            item.setData(0, _SORT_ROLE, e.name.lower())
            item.setData(1, _SORT_ROLE, e.size)
            item.setData(2, _SORT_ROLE, e.path.lower())
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._file_tree.addTopLevelItem(item)
        self._file_tree.setSortingEnabled(True)
        self._file_tree.sortByColumn(1, Qt.SortOrder.DescendingOrder)

    def _fill_dir_tree(self, entries):
        self._dir_tree.setSortingEnabled(False)
        for e in entries:
            item = _SortableItem([e.name, _fmt_size(e.size), e.path])
            item.setData(0, _SORT_ROLE, e.name.lower())
            item.setData(1, _SORT_ROLE, e.size)
            item.setData(2, _SORT_ROLE, e.path.lower())
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._dir_tree.addTopLevelItem(item)
        self._dir_tree.setSortingEnabled(True)
        self._dir_tree.sortByColumn(1, Qt.SortOrder.DescendingOrder)

    def _fill_ext_tree(self, by_ext: list):
        self._ext_tree.setSortingEnabled(False)
        for r in by_ext:
            bar = _bar(r["pct"])
            item = _SortableItem([r["ext"], str(r["count"]), r["size_fmt"], bar])
            item.setData(0, _SORT_ROLE, r["ext"].lower())
            item.setData(1, _SORT_ROLE, r["count"])
            item.setData(2, _SORT_ROLE, r["size"])
            item.setData(3, _SORT_ROLE, r["pct"])
            item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._ext_tree.addTopLevelItem(item)
        self._ext_tree.setSortingEnabled(True)
        self._ext_tree.sortByColumn(2, Qt.SortOrder.DescendingOrder)

    def _export_csv(self):
        if not self._analysis:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            f"espace_{os.path.basename(self._folder) or 'disque'}.csv"
        )
        path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", default, "CSV (*.csv)")
        if not path:
            return
        try:
            diskspace_to_csv(self._analysis, path)
            QMessageBox.information(self, "Export CSV", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export CSV", str(ex))

    def _export_pdf(self):
        if not self._analysis:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            f"espace_{os.path.basename(self._folder) or 'disque'}.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            diskspace_to_pdf(self._analysis, self._folder, path)
            QMessageBox.information(self, "Export PDF", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export PDF", str(ex))

    # ── API externe ────────────────────────────────────────────────────────

    def set_folder(self, path: str):
        self._folder = path
        self._folder_edit.setText(path)
