import os
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QLineEdit,
    QHeaderView, QAbstractItemView, QProgressBar, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from core.inventory_reporter import (
    collect, compute_stats, to_csv, to_pdf, InventoryEntry,
    _fmt_size, _fmt_date,
)

_SORT_ROLE = Qt.ItemDataRole.UserRole


class _SortableItem(QTreeWidgetItem):
    """QTreeWidgetItem qui trie sur la clé numérique stockée en UserRole."""

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


class InventoryWorker(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, folder: str, recursive: bool, show_hidden: bool):
        super().__init__()
        self.folder = folder
        self.recursive = recursive
        self.show_hidden = show_hidden

    def run(self):
        try:
            entries = collect(self.folder, self.recursive, self.show_hidden)
            self.done.emit(entries)
        except Exception as e:
            self.error.emit(str(e))


class InventoryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._entries: list[InventoryEntry] = []
        self._folder = ""
        self._worker = None
        self._show_hidden = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── Ligne de contrôle ─────────────────────────────────────────────
        top_row = QHBoxLayout()

        top_row.addWidget(QLabel("Dossier :"))
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText("Chemin du dossier à inventorier…")
        top_row.addWidget(self._folder_edit)

        browse_btn = QPushButton("…")
        browse_btn.setFixedWidth(30)
        browse_btn.clicked.connect(self._browse)
        top_row.addWidget(browse_btn)

        top_row.addSpacing(10)

        self._recursive_chk = QCheckBox("Sous-dossiers")
        self._recursive_chk.setChecked(True)
        top_row.addWidget(self._recursive_chk)

        self._hidden_chk = QCheckBox("Fichiers cachés")
        top_row.addWidget(self._hidden_chk)

        top_row.addSpacing(10)

        self._generate_btn = QPushButton("Générer")
        self._generate_btn.clicked.connect(self._start)
        top_row.addWidget(self._generate_btn)

        layout.addLayout(top_row)

        # ── Barre de progression ───────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # ── Filtre rapide ──────────────────────────────────────────────────
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filtrer :"))
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Nom de fichier ou dossier…")
        self._filter_edit.setClearButtonEnabled(True)
        self._filter_edit.setEnabled(False)
        self._filter_edit.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter_edit)
        layout.addLayout(filter_row)

        # ── Tableau des résultats ──────────────────────────────────────────
        self._tree = QTreeWidget()
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["Nom", "Type", "Taille", "Date de modification", "Propriétaire"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setAlternatingRowColors(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
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
            QMessageBox.warning(self, "Inventaire", "Dossier invalide ou introuvable.")
            return
        self._folder = folder
        self._filter_edit.setEnabled(False)
        self._filter_edit.blockSignals(True)
        self._filter_edit.clear()
        self._filter_edit.blockSignals(False)
        self._tree.setSortingEnabled(False)
        self._tree.clear()
        self._entries = []
        self._stats_label.setText("")
        self._export_pdf_btn.setEnabled(False)
        self._export_csv_btn.setEnabled(False)
        self._progress.setVisible(True)
        self._generate_btn.setEnabled(False)

        recursive = self._recursive_chk.isChecked()
        show_hidden = self._hidden_chk.isChecked()

        self._worker = InventoryWorker(folder, recursive, show_hidden)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, entries: list):
        self._progress.setVisible(False)
        self._generate_btn.setEnabled(True)
        self._entries = entries

        self._tree.setUpdatesEnabled(False)
        self._build_tree(entries)
        self._tree.setUpdatesEnabled(True)

        stats = compute_stats(entries)
        self._stats_label.setText(
            f"  {stats['files']} fichier(s) · {stats['dirs']} dossier(s) · {stats['size_fmt']} total"
        )
        self._export_pdf_btn.setEnabled(bool(entries))
        self._export_csv_btn.setEnabled(bool(entries))
        self._filter_edit.setEnabled(bool(entries))

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._generate_btn.setEnabled(True)
        QMessageBox.critical(self, "Erreur inventaire", msg)

    def _apply_filter(self, text: str):
        text = text.strip().lower()
        root = self._tree.invisibleRootItem()
        if not text:
            self._set_subtree_visible(root)
            for i in range(root.childCount()):
                root.child(i).setExpanded(True)
            return
        self._tree.setUpdatesEnabled(False)
        self._filter_subtree(root, text)
        self._tree.setUpdatesEnabled(True)

    def _filter_subtree(self, item: QTreeWidgetItem, text: str) -> bool:
        """Retourne True si l'item ou un de ses descendants correspond au filtre."""
        is_root = item is self._tree.invisibleRootItem()
        match = not is_root and text in item.text(0).lower()
        any_child_match = False
        for i in range(item.childCount()):
            if self._filter_subtree(item.child(i), text):
                any_child_match = True
        visible = match or any_child_match
        if not is_root:
            item.setHidden(not visible)
            if any_child_match:
                item.setExpanded(True)
        return visible

    def _set_subtree_visible(self, item: QTreeWidgetItem):
        for i in range(item.childCount()):
            child = item.child(i)
            child.setHidden(False)
            self._set_subtree_visible(child)

    def _build_tree(self, entries: list):
        # maps directory path -> QTreeWidgetItem so children can be attached
        dir_items: dict[str, QTreeWidgetItem] = {}

        for e in entries:
            item = self._make_item(e)
            parent_path = os.path.dirname(e.path)
            parent_item = dir_items.get(parent_path)
            if parent_item is not None:
                parent_item.addChild(item)
            else:
                self._tree.addTopLevelItem(item)
            if e.is_dir:
                dir_items[e.path] = item

        # réactiver le tri puis étendre le premier niveau
        self._tree.setSortingEnabled(True)
        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            root.child(i).setExpanded(True)

    def _make_item(self, e: InventoryEntry) -> _SortableItem:
        type_label = "Dossier" if e.is_dir else (e.extension.lstrip(".").upper() or "Fichier")
        size_str = _fmt_size(e.size)
        ts = e.modified.timestamp() if e.modified != datetime.min else 0.0

        item = _SortableItem([
            e.name,
            type_label,
            size_str,
            _fmt_date(e.modified),
            e.owner,
        ])
        # clés de tri numériques par colonne (dirs toujours avant fichiers sur col 0)
        item.setData(0, _SORT_ROLE, (0 if e.is_dir else 1, e.name.lower()))
        item.setData(1, _SORT_ROLE, type_label.lower())
        item.setData(2, _SORT_ROLE, e.size)
        item.setData(3, _SORT_ROLE, ts)
        item.setData(4, _SORT_ROLE, e.owner.lower())

        item.setTextAlignment(2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if e.is_dir:
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
        return item

    def _export_csv(self):
        if not self._entries:
            return
        default_name = os.path.join(
            os.path.expanduser("~"),
            f"inventaire_{os.path.basename(self._folder) or 'dossier'}.csv"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter l'inventaire CSV", default_name, "CSV (*.csv)"
        )
        if not path:
            return
        try:
            to_csv(self._entries, path)
            QMessageBox.information(self, "Export CSV", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export CSV", str(ex))

    def _export_pdf(self):
        if not self._entries:
            return
        default_name = os.path.join(
            os.path.expanduser("~"),
            f"inventaire_{os.path.basename(self._folder) or 'dossier'}.pdf"
        )
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter l'inventaire PDF", default_name, "PDF (*.pdf)"
        )
        if not path:
            return
        try:
            stats = compute_stats(self._entries)
            to_pdf(self._entries, self._folder, stats, path)
            QMessageBox.information(self, "Export PDF", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export PDF", str(ex))

    # ── API externe ────────────────────────────────────────────────────────

    def set_folder(self, path: str):
        self._folder = path
        self._folder_edit.setText(path)

    def set_show_hidden(self, show: bool):
        self._show_hidden = show
        self._hidden_chk.setChecked(show)
