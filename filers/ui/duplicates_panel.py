import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QLineEdit,
    QHeaderView, QAbstractItemView, QProgressBar, QMessageBox, QCheckBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from core.local_provider import LocalProvider
from core import long_path_utils as lp
from core.inventory_reporter import (
    duplicates_to_csv, duplicates_to_pdf, _fmt_size, _fmt_date,
)

# alternating group background colors
_GROUP_COLORS = ["#e3f2fd", "#f3e5f5", "#e8f5e9", "#fff8e1"]


class DuplicatesWorker(QThread):
    progress = pyqtSignal(int, int, str)   # current, total, filename
    done     = pyqtSignal(list)
    error    = pyqtSignal(str)

    def __init__(self, folder: str, show_hidden: bool):
        super().__init__()
        self.folder      = folder
        self.show_hidden = show_hidden

    def run(self):
        try:
            provider = LocalProvider(show_hidden=self.show_hidden)
            all_files = []

            def _scan(path: str):
                try:
                    for fe in provider.list_dir(path):
                        if fe.is_dir:
                            _scan(fe.path)
                        elif fe.size > 0:
                            all_files.append(fe)
                except Exception:
                    pass

            _scan(self.folder)

            # group by size — skip unique sizes to avoid unnecessary MD5
            by_size: dict = {}
            for fe in all_files:
                by_size.setdefault(fe.size, []).append(fe)
            candidates = [g for g in by_size.values() if len(g) > 1]
            total = sum(len(g) for g in candidates)

            # compute MD5 only for size-collision candidates
            by_hash: dict = {}
            current = 0
            for group in candidates:
                for fe in group:
                    self.progress.emit(current, total, fe.name)
                    current += 1
                    try:
                        h = lp.checksum(fe.path, "md5")
                        by_hash.setdefault(h, []).append(fe)
                    except Exception:
                        pass

            groups = [
                {
                    "hash":         h,
                    "size":         files[0].size,
                    "size_fmt":     _fmt_size(files[0].size),
                    "count":        len(files),
                    "wasted":       _fmt_size(files[0].size * (len(files) - 1)),
                    "wasted_bytes": files[0].size * (len(files) - 1),
                    "files":        files,
                }
                for h, files in by_hash.items()
                if len(files) > 1
            ]
            groups.sort(key=lambda g: g["wasted_bytes"], reverse=True)
            self.done.emit(groups)

        except Exception as e:
            self.error.emit(str(e))


class DuplicatesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._groups: list = []
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
        self._hidden_chk = QCheckBox("Fichiers cachés")
        top_row.addWidget(self._hidden_chk)
        top_row.addSpacing(10)
        self._analyze_btn = QPushButton("Rechercher")
        self._analyze_btn.clicked.connect(self._start)
        top_row.addWidget(self._analyze_btn)
        layout.addLayout(top_row)

        # ── Progression ───────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress_label = QLabel("")
        self._progress_label.setVisible(False)
        layout.addWidget(self._progress_label)
        layout.addWidget(self._progress)

        # ── Arbre des résultats ────────────────────────────────────────────
        self._tree = QTreeWidget()
        self._tree.setColumnCount(3)
        self._tree.setHeaderLabels(["Nom / Groupe", "Taille", "Date de modification"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setAlternatingRowColors(False)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
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
            QMessageBox.warning(self, "Doublons", "Dossier invalide ou introuvable.")
            return
        self._folder = folder
        self._groups = []
        self._tree.clear()
        self._stats_label.setText("")
        self._export_pdf_btn.setEnabled(False)
        self._export_csv_btn.setEnabled(False)
        self._progress.setValue(0)
        self._progress.setRange(0, 0)   # indéterminé pendant le scan
        self._progress.setVisible(True)
        self._progress_label.setText("Scan des fichiers…")
        self._progress_label.setVisible(True)
        self._analyze_btn.setEnabled(False)

        self._worker = DuplicatesWorker(folder, self._hidden_chk.isChecked())
        self._worker.progress.connect(self._on_progress)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, current: int, total: int, filename: str):
        if self._progress.maximum() == 0:
            self._progress.setRange(0, total)
        self._progress.setValue(current)
        self._progress_label.setText(f"Calcul MD5 : {current}/{total} — {filename}")

    def _on_done(self, groups: list):
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        self._analyze_btn.setEnabled(True)
        self._groups = groups

        self._tree.setUpdatesEnabled(False)
        for i, g in enumerate(groups):
            self._add_group(g, i)
        self._tree.setUpdatesEnabled(True)

        if groups:
            total_wasted = sum(g["wasted_bytes"] for g in groups)
            total_extra  = sum(g["count"] - 1 for g in groups)
            self._stats_label.setText(
                f"  {len(groups)} groupe(s) · "
                f"{total_extra} fichier(s) superflus · "
                f"{_fmt_size(total_wasted)} récupérables"
            )
            self._export_pdf_btn.setEnabled(True)
            self._export_csv_btn.setEnabled(True)
        else:
            self._stats_label.setText("  Aucun doublon trouvé.")

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        self._analyze_btn.setEnabled(True)
        QMessageBox.critical(self, "Erreur", msg)

    def _add_group(self, g: dict, idx: int):
        bg = QColor(_GROUP_COLORS[idx % len(_GROUP_COLORS)])

        # en-tête du groupe
        header = QTreeWidgetItem([
            f"Groupe {idx + 1}  —  {g['count']} copies · {g['size_fmt']} chacun",
            g["wasted"],
            "",
        ])
        font = header.font(0)
        font.setBold(True)
        header.setFont(0, font)
        for col in range(3):
            header.setBackground(col, bg)
        header.setForeground(1, QColor("#c62828"))
        self._tree.addTopLevelItem(header)

        # fichiers du groupe
        for fe in g["files"]:
            child = QTreeWidgetItem([
                "    " + fe.path,
                _fmt_size(fe.size),
                _fmt_date(fe.modified),
            ])
            for col in range(3):
                child.setBackground(col, bg)
            header.addChild(child)

        header.setExpanded(True)

    def _export_csv(self):
        if not self._groups:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            f"doublons_{os.path.basename(self._folder) or 'dossier'}.csv"
        )
        path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", default, "CSV (*.csv)")
        if not path:
            return
        try:
            duplicates_to_csv(self._groups, path)
            QMessageBox.information(self, "Export CSV", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export CSV", str(ex))

    def _export_pdf(self):
        if not self._groups:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            f"doublons_{os.path.basename(self._folder) or 'dossier'}.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            duplicates_to_pdf(self._groups, self._folder, path)
            QMessageBox.information(self, "Export PDF", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export PDF", str(ex))

    # ── API externe ────────────────────────────────────────────────────────

    def set_folder(self, path: str):
        self._folder = path
        self._folder_edit.setText(path)
