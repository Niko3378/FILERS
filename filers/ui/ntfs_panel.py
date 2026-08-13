import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QLineEdit,
    QHeaderView, QProgressBar, QMessageBox, QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from core.ntfs_reporter import (
    AclEntry, collect_paths, _read_acl,
    ntfs_to_csv, ntfs_to_pdf,
)


class NtfsWorker(QThread):
    progress = pyqtSignal(int, int, str)  # current, total, name
    done     = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, folder: str, recursive: bool, include_files: bool):
        super().__init__()
        self.folder        = folder
        self.recursive     = recursive
        self.include_files = include_files

    def run(self):
        try:
            paths = collect_paths(self.folder, self.recursive, self.include_files)
            total   = len(paths)
            results = []
            for i, (path, name, is_dir, depth) in enumerate(paths):
                self.progress.emit(i + 1, total, name)
                results.extend(_read_acl(path, name, is_dir, depth))
            self.done.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class NtfsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []
        self._folder  = ""
        self._worker  = None
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
        self._recursive_chk = QCheckBox("Récursif")
        self._recursive_chk.setChecked(True)
        top_row.addWidget(self._recursive_chk)

        self._files_chk = QCheckBox("Inclure fichiers")
        top_row.addWidget(self._files_chk)

        top_row.addSpacing(10)
        self._analyze_btn = QPushButton("Analyser")
        self._analyze_btn.clicked.connect(self._start)
        top_row.addWidget(self._analyze_btn)
        layout.addLayout(top_row)

        # ── Progression ───────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # ── Arbre des résultats ───────────────────────────────────────────
        self._tree = QTreeWidget()
        self._tree.setColumnCount(7)
        self._tree.setHeaderLabels(
            ["Nom", "Type", "Principal", "Droits", "Accès", "Hérité", "Chemin"]
        )
        for col in range(6):
            self._tree.header().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self._tree.setRootIsDecorated(True)
        self._tree.setAlternatingRowColors(False)
        layout.addWidget(self._tree)

        # ── Barre de stats + export ────────────────────────────────────────
        bottom_row = QHBoxLayout()
        self._stats_label = QLabel("")
        bottom_row.addWidget(self._stats_label, 1)
        self._export_pdf_btn = QPushButton("Exporter PDF…")
        self._export_pdf_btn.setEnabled(False)
        self._export_pdf_btn.clicked.connect(self._export_pdf)
        bottom_row.addWidget(self._export_pdf_btn)
        self._export_csv_btn = QPushButton("Exporter CSV…")
        self._export_csv_btn.setEnabled(False)
        self._export_csv_btn.clicked.connect(self._export_csv)
        bottom_row.addWidget(self._export_csv_btn)
        layout.addLayout(bottom_row)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Choisir un dossier", self._folder or "")
        if path:
            self._folder_edit.setText(path)

    def _start(self):
        folder = self._folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Droits NTFS", "Dossier invalide ou introuvable.")
            return

        self._folder  = folder
        self._entries = []
        self._tree.clear()
        self._stats_label.setText("")
        self._export_pdf_btn.setEnabled(False)
        self._export_csv_btn.setEnabled(False)
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)
        self._analyze_btn.setEnabled(False)

        self._worker = NtfsWorker(
            folder,
            recursive=self._recursive_chk.isChecked(),
            include_files=self._files_chk.isChecked(),
        )
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, name: str):
        if self._progress.maximum() == 0 and total > 0:
            self._progress.setRange(0, total)
        self._progress.setValue(current)
        self._stats_label.setText(f"  Lecture : {name}")

    def _on_done(self, entries: list):
        self._progress.setVisible(False)
        self._analyze_btn.setEnabled(True)
        self._entries = entries
        self._build_tree(entries)

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._analyze_btn.setEnabled(True)
        QMessageBox.critical(self, "Erreur", msg)

    def _build_tree(self, entries: list):
        self._tree.setUpdatesEnabled(False)
        self._tree.clear()

        # Group by path, preserving insertion order
        groups: dict = {}
        for e in entries:
            groups.setdefault(e.path, []).append(e)

        deny_count = 0
        bold_font = QFont()
        bold_font.setBold(True)

        for aces in groups.values():
            first = aces[0]

            # Top-level item: the file/dir object
            parent = QTreeWidgetItem()
            parent.setText(0, first.name)
            parent.setText(1, "Dossier" if first.is_dir else "Fichier")
            parent.setText(6, first.path)
            parent.setFont(0, bold_font)
            if first.is_dir:
                parent.setForeground(0, QColor("#1565c0"))

            # Child items: one per ACE
            for ace in aces:
                child = QTreeWidgetItem()
                child.setText(2, ace.principal)
                child.setText(3, ace.rights)
                child.setText(4, ace.ace_type)
                child.setText(5, "Oui" if ace.inherited else "Non")

                if ace.ace_type == "Refuser":
                    child.setForeground(4, QColor("#c62828"))
                    deny_count += 1
                else:
                    child.setForeground(4, QColor("#2e7d32"))

                if ace.inherited:
                    gray = QColor("#aaaaaa")
                    for col in range(7):
                        child.setForeground(col, gray)
                    # Keep deny visible even when inherited
                    if ace.ace_type == "Refuser":
                        child.setForeground(4, QColor("#e57373"))

                parent.addChild(child)

            self._tree.addTopLevelItem(parent)
            parent.setExpanded(True)

        self._tree.setUpdatesEnabled(True)

        nb_objects = len(groups)
        nb_aces    = len(entries)
        if entries:
            self._stats_label.setText(
                f"  {nb_objects} objet(s) · {nb_aces} entrée(s) ACL · {deny_count} refus"
            )
            self._export_pdf_btn.setEnabled(True)
            self._export_csv_btn.setEnabled(True)
        else:
            self._stats_label.setText("  Aucune ACL trouvée (droits insuffisants ?).")

    def _export_csv(self):
        if not self._entries:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            f"ntfs_{os.path.basename(self._folder) or 'dossier'}.csv",
        )
        path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", default, "CSV (*.csv)")
        if not path:
            return
        try:
            ntfs_to_csv(self._entries, path)
            QMessageBox.information(self, "Export CSV", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export CSV", str(ex))

    def _export_pdf(self):
        if not self._entries:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            f"ntfs_{os.path.basename(self._folder) or 'dossier'}.pdf",
        )
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            ntfs_to_pdf(self._entries, self._folder, path)
            QMessageBox.information(self, "Export PDF", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export PDF", str(ex))

    def set_folder(self, path: str):
        self._folder = path
        self._folder_edit.setText(path)
