import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QLineEdit,
    QHeaderView, QAbstractItemView, QProgressBar, QMessageBox,
    QSpinBox, QComboBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core.inventory_reporter import (
    recent_files, recent_to_csv, recent_to_pdf, _fmt_size, _fmt_date,
)

_SORT_ROLE = Qt.ItemDataRole.UserRole

_PRESETS = [("7 derniers jours", 7), ("30 derniers jours", 30),
            ("90 derniers jours", 90), ("1 an", 365), ("Personnalisé…", -1)]


class RecentWorker(QThread):
    done  = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, folder: str, days: int, show_hidden: bool):
        super().__init__()
        self.folder      = folder
        self.days        = days
        self.show_hidden = show_hidden

    def run(self):
        try:
            entries = recent_files(self.folder, self.days, self.show_hidden)
            self.done.emit(entries)
        except Exception as e:
            self.error.emit(str(e))


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


class RecentPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries = []
        self._folder  = ""
        self._days    = 30
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
        top_row.addWidget(QLabel("Période :"))

        self._preset_combo = QComboBox()
        for label, _ in _PRESETS:
            self._preset_combo.addItem(label)
        self._preset_combo.setCurrentIndex(1)   # 30 jours par défaut
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        top_row.addWidget(self._preset_combo)

        self._days_spin = QSpinBox()
        self._days_spin.setRange(1, 3650)
        self._days_spin.setValue(30)
        self._days_spin.setSuffix(" jours")
        self._days_spin.setVisible(False)
        top_row.addWidget(self._days_spin)

        top_row.addSpacing(10)
        self._search_btn = QPushButton("Rechercher")
        self._search_btn.clicked.connect(self._start)
        top_row.addWidget(self._search_btn)
        layout.addLayout(top_row)

        # ── Progression ───────────────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # ── Tableau des résultats ──────────────────────────────────────────
        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["Nom", "Taille", "Date de modification", "Propriétaire", "Chemin"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._tree.setRootIsDecorated(False)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(2, Qt.SortOrder.DescendingOrder)
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

    def _on_preset_changed(self, idx: int):
        _, days = _PRESETS[idx]
        custom = days == -1
        self._days_spin.setVisible(custom)
        if not custom:
            self._days = days

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Choisir un dossier", self._folder or "")
        if path:
            self._folder_edit.setText(path)

    def _start(self):
        folder = self._folder_edit.text().strip()
        if not folder or not os.path.isdir(folder):
            QMessageBox.warning(self, "Fichiers récents", "Dossier invalide ou introuvable.")
            return
        _, days = _PRESETS[self._preset_combo.currentIndex()]
        self._days = self._days_spin.value() if days == -1 else days

        self._folder  = folder
        self._entries = []
        self._tree.setSortingEnabled(False)
        self._tree.clear()
        self._stats_label.setText("")
        self._export_pdf_btn.setEnabled(False)
        self._export_csv_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._search_btn.setEnabled(False)

        self._worker = RecentWorker(folder, self._days, show_hidden=False)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, entries: list):
        self._progress.setVisible(False)
        self._search_btn.setEnabled(True)
        self._entries = entries

        self._tree.setUpdatesEnabled(False)
        for e in entries:
            self._add_item(e)
        self._tree.setUpdatesEnabled(True)
        self._tree.setSortingEnabled(True)

        if entries:
            total_size = sum(e.size for e in entries)
            self._stats_label.setText(
                f"  {len(entries)} fichier(s) · {_fmt_size(total_size)} au total"
            )
            self._export_pdf_btn.setEnabled(True)
            self._export_csv_btn.setEnabled(True)
        else:
            self._stats_label.setText(
                f"  Aucun fichier modifié dans les {self._days} derniers jour(s)."
            )

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._search_btn.setEnabled(True)
        QMessageBox.critical(self, "Erreur", msg)

    def _add_item(self, e):
        item = _SortableItem([
            e.name,
            _fmt_size(e.size),
            _fmt_date(e.modified),
            e.owner,
            e.path,
        ])
        item.setData(0, _SORT_ROLE, e.name.lower())
        item.setData(1, _SORT_ROLE, e.size)
        item.setData(2, _SORT_ROLE, e.modified.timestamp())
        item.setData(3, _SORT_ROLE, e.owner.lower())
        item.setData(4, _SORT_ROLE, e.path.lower())
        item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._tree.addTopLevelItem(item)

    def _export_csv(self):
        if not self._entries:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            f"recents_{os.path.basename(self._folder) or 'dossier'}.csv"
        )
        path, _ = QFileDialog.getSaveFileName(self, "Exporter CSV", default, "CSV (*.csv)")
        if not path:
            return
        try:
            recent_to_csv(self._entries, path)
            QMessageBox.information(self, "Export CSV", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export CSV", str(ex))

    def _export_pdf(self):
        if not self._entries:
            return
        default = os.path.join(
            os.path.expanduser("~"),
            f"recents_{os.path.basename(self._folder) or 'dossier'}.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(self, "Exporter PDF", default, "PDF (*.pdf)")
        if not path:
            return
        try:
            recent_to_pdf(self._entries, self._folder, self._days, path)
            QMessageBox.information(self, "Export PDF", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export PDF", str(ex))

    # ── API externe ────────────────────────────────────────────────────────

    def set_folder(self, path: str):
        self._folder = path
        self._folder_edit.setText(path)
