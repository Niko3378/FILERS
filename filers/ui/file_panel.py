import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QPushButton, QMenu, QAbstractItemView,
    QHeaderView, QToolBar, QComboBox, QMessageBox, QInputDialog,
    QProgressDialog, QFileDialog, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QMimeData, QUrl
from PyQt6.QtGui import QIcon, QColor, QFont, QAction, QDrag, QKeySequence, QShortcut

from core.local_provider import LocalProvider, FileEntry
from core.ftp_provider import FTPProvider, SFTPProvider, RemoteEntry
from core.smb_provider import SMBProvider, SMBEntry
from core import long_path_utils as lp
from core import settings

DATETIME_FMT = "%Y-%m-%d %H:%M"
SIZE_UNITS = ["o", "Ko", "Mo", "Go", "To"]


def fmt_size(size: int) -> str:
    s = float(size)
    for unit in SIZE_UNITS:
        if s < 1024:
            return f"{s:.1f} {unit}"
        s /= 1024
    return f"{s:.1f} Po"


class SortableItem(QTreeWidgetItem):
    """QTreeWidgetItem with correct numeric sorting for size and date columns."""
    # Column indices
    COL_NAME, COL_SIZE, COL_TYPE, COL_DATE, COL_PERMS = range(5)

    def __lt__(self, other: QTreeWidgetItem) -> bool:
        tree = self.treeWidget()
        col = tree.sortColumn() if tree else 0
        e1 = self.data(0, Qt.ItemDataRole.UserRole)
        e2 = other.data(0, Qt.ItemDataRole.UserRole)

        if col == self.COL_SIZE:
            s1 = getattr(e1, "size", 0) if (e1 and not e1.is_dir) else -1
            s2 = getattr(e2, "size", 0) if (e2 and not e2.is_dir) else -1
            return s1 < s2

        if col == self.COL_DATE:
            d1 = e1.modified if e1 else None
            d2 = e2.modified if e2 else None
            if d1 and d2:
                return d1 < d2
            return d1 is not None

        return self.text(col).lower() < other.text(col).lower()


class FileTree(QTreeWidget):
    files_dropped = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def startDrag(self, supported_actions):
        paths = []
        for item in self.selectedItems():
            entry = item.data(0, Qt.ItemDataRole.UserRole)
            if entry and hasattr(entry, "path"):
                paths.append(entry.path)
        if not paths:
            return
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in paths])
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction | Qt.DropAction.MoveAction,
                  Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile()]
            if paths:
                self.files_dropped.emit(paths)
            event.setDropAction(Qt.DropAction.CopyAction)
            event.accept()
        else:
            event.ignore()


class SearchWorker(QThread):
    partial = pyqtSignal(list)
    found = pyqtSignal(int)
    error = pyqtSignal(str)
    BATCH_SIZE = 50

    def __init__(self, provider, root: str, pattern: str):
        super().__init__()
        self._provider = provider
        self._root = root
        self._pattern = pattern.lower()
        self._cancelled = False
        self._batch = []
        self._total = 0

    def cancel(self):
        self._cancelled = True

    def _flush(self):
        if self._batch:
            self.partial.emit(self._batch)
            self._total += len(self._batch)
            self._batch = []

    def run(self):
        try:
            self._walk(self._root)
            if not self._cancelled:
                self._flush()
                self.found.emit(self._total)
        except Exception as e:
            self.error.emit(str(e))

    def _walk(self, path: str):
        if self._cancelled:
            return
        try:
            for entry in self._provider.list_dir(path):
                if self._cancelled:
                    return
                if self._pattern in entry.name.lower():
                    self._batch.append(entry)
                    if len(self._batch) >= self.BATCH_SIZE:
                        self._flush()
                if entry.is_dir:
                    self._walk(entry.path)
        except Exception:
            pass


class LoadWorker(QThread):
    loaded = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, provider, path):
        super().__init__()
        self.provider = provider
        self.path = path

    def run(self):
        try:
            entries = self.provider.list_dir(self.path)
            self.loaded.emit(entries)
        except Exception as e:
            self.error.emit(str(e))


class FilePanel(QWidget):
    path_changed = pyqtSignal(str)
    selection_changed = pyqtSignal(list)
    request_diff = pyqtSignal(str, str)
    request_open_editor = pyqtSignal(str)
    request_preview = pyqtSignal(str)
    file_selected = pyqtSignal(str)
    request_copy_to = pyqtSignal(list)
    request_move_to = pyqtSignal(list)
    files_dropped = pyqtSignal(list)
    add_to_favorites = pyqtSignal(str)

    def __init__(self, local_provider: LocalProvider, label: str = "Panneau", parent=None):
        super().__init__(parent)
        self._local = local_provider
        self._provider = local_provider
        self._current_path = ""
        self._history = []
        self._future = []
        self._label_text = label
        self._worker = None
        self._search_worker = None
        self._is_searching = False
        self._total_count = 0
        self._build_ui()
        key = f"last_path_{label.lower()}"
        saved = settings.get(key, "")
        start = saved if saved and os.path.isdir(saved) else self._local.get_roots()[0]
        self._navigate(start)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self._label = QLabel(self._label_text)
        self._label.setStyleSheet("font-weight: bold; padding: 2px 4px;")
        layout.addWidget(self._label)

        bar = QHBoxLayout()
        self._back_btn = QPushButton("←")
        self._back_btn.setFixedWidth(28)
        self._back_btn.clicked.connect(self._go_back)
        self._fwd_btn = QPushButton("→")
        self._fwd_btn.setFixedWidth(28)
        self._fwd_btn.clicked.connect(self._go_forward)
        self._up_btn = QPushButton("↑")
        self._up_btn.setFixedWidth(28)
        self._up_btn.clicked.connect(self._go_up)

        self._path_edit = QLineEdit()
        self._path_edit.returnPressed.connect(self._on_path_enter)

        self._drive_combo = QComboBox()
        self._drive_combo.setFixedWidth(60)
        for root in self._local.get_roots():
            self._drive_combo.addItem(root)
        self._drive_combo.currentTextChanged.connect(self._navigate)

        bar.addWidget(self._back_btn)
        bar.addWidget(self._fwd_btn)
        bar.addWidget(self._up_btn)
        bar.addWidget(self._path_edit)
        bar.addWidget(self._drive_combo)
        layout.addLayout(bar)

        # Long path warning banner (hidden by default)
        self._long_path_banner = QLabel()
        self._long_path_banner.setWordWrap(True)
        self._long_path_banner.setStyleSheet(
            "background: #fef9e7; color: #856404; border: 1px solid #f0c040; "
            "border-radius: 3px; padding: 3px 8px; font-size: 11px;"
        )
        self._long_path_banner.hide()
        layout.addWidget(self._long_path_banner)

        # Filter / search bar
        self._filter_bar = QWidget()
        fb = QHBoxLayout(self._filter_bar)
        fb.setContentsMargins(2, 2, 2, 2)
        fb.addWidget(QLabel("Filtrer :"))
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Nom de fichier… (Échap pour fermer)")
        self._filter_edit.textChanged.connect(self._on_filter_changed)
        self._filter_edit.returnPressed.connect(self._on_search_trigger)
        fb.addWidget(self._filter_edit)
        self._subdirs_check = QCheckBox("Sous-dossiers")
        fb.addWidget(self._subdirs_check)
        search_btn = QPushButton("Chercher")
        search_btn.clicked.connect(self._on_search_trigger)
        fb.addWidget(search_btn)
        self._back_search_btn = QPushButton("← Retour")
        self._back_search_btn.clicked.connect(self._on_search_back)
        self._back_search_btn.hide()
        fb.addWidget(self._back_search_btn)
        self._filter_bar.hide()
        layout.addWidget(self._filter_bar)

        self._search_banner = QLabel()
        self._search_banner.setStyleSheet(
            "background:#e8f4fd;border:1px solid #aad4f5;border-radius:3px;"
            "padding:2px 6px;font-size:11px;")
        self._search_banner.hide()
        layout.addWidget(self._search_banner)

        QShortcut(QKeySequence("Ctrl+F"), self, self._toggle_filter_bar)
        QShortcut(QKeySequence("Escape"), self._filter_edit, self._clear_filter)
        QShortcut(QKeySequence("Delete"), self, self._delete_selected)
        QShortcut(QKeySequence("Ctrl+A"), self, lambda: self._tree.selectAll())

        self._tree = FileTree()
        self._tree.files_dropped.connect(self.files_dropped)
        self._tree.setColumnCount(5)
        self._tree.setHeaderLabels(["Nom", "Taille", "Type", "Modifié", "Droits"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.setSortingEnabled(True)
        self._tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        layout.addWidget(self._tree)

        status = QHBoxLayout()
        self._status_label = QLabel("")
        status.addWidget(self._status_label)
        layout.addLayout(status)

    def _navigate(self, path: str):
        if path == self._current_path:
            return
        if self._is_searching:
            self._on_search_back(clear_filter=False)
        if self._current_path:
            self._history.append(self._current_path)
            self._future.clear()
        self._current_path = path
        settings.set_value(f"last_path_{self._label_text.lower()}", path)
        self._path_edit.setText(path)
        self._path_edit.setToolTip(path)
        self._back_btn.setEnabled(bool(self._history))
        self._fwd_btn.setEnabled(bool(self._future))
        self._update_long_path_banner(path)
        self._load_entries()
        self.path_changed.emit(path)

    def _update_long_path_banner(self, path: str):
        plen = len(path)
        if lp.is_long(path):
            self._long_path_banner.setText(
                f"Chemin long ({plen} car.) — préfixe \\\\?\\ actif. "
                "Certaines apps tierces peuvent ne pas supporter ce chemin."
            )
            self._long_path_banner.show()
        elif plen > 200:
            self._long_path_banner.setText(
                f"Chemin long ({plen} car.) — approche de la limite de 260 caractères."
            )
            self._long_path_banner.show()
        else:
            self._long_path_banner.hide()

    def _load_entries(self):
        if self._worker and self._worker.isRunning():
            self._worker.terminate()
        self._worker = LoadWorker(self._provider, self._current_path)
        self._worker.loaded.connect(self._populate)
        self._worker.error.connect(self._on_load_error)
        self._worker.start()

    @pyqtSlot(list)
    def _populate(self, entries: list):
        self._tree.clear()
        for entry in entries:
            item = self._make_item(entry)
            self._tree.addTopLevelItem(item)
        self._total_count = len(entries)
        self._status_label.setText(f"{self._total_count} élément(s)")

    def _make_item(self, entry) -> QTreeWidgetItem:
        name = entry.name
        is_dir = entry.is_dir
        size_str = "" if is_dir else fmt_size(entry.size)
        kind = "Dossier" if is_dir else os.path.splitext(name)[1].lstrip(".").upper() or "Fichier"
        date_str = entry.modified.strftime(DATETIME_FMT) if entry.modified.year > 1 else ""
        perms = entry.permissions if hasattr(entry, "permissions") else ""

        item = SortableItem([name, size_str, kind, date_str, perms])
        item.setData(0, Qt.ItemDataRole.UserRole, entry)

        if is_dir:
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            item.setForeground(0, QColor("#2c3e50"))

        is_hidden = getattr(entry, "is_hidden", name.startswith("."))
        if is_hidden:
            for col in range(5):
                item.setForeground(col, QColor("#aaaaaa"))

        # Long path / long name indicators
        is_long_path = getattr(entry, "is_long_path", False) or lp.is_long(entry.path)
        if is_long_path:
            item.setBackground(0, QColor("#fef9e7"))
            item.setToolTip(0, f"Chemin long ({len(entry.path)} car.)\n{entry.path}")
        elif len(name) > 80:
            item.setToolTip(0, name)

        if len(entry.path) > 50:
            item.setToolTip(3, entry.path)

        return item

    @pyqtSlot(str)
    def _on_load_error(self, msg: str):
        self._status_label.setText(f"Erreur : {msg}")

    def _on_double_click(self, item: QTreeWidgetItem, col: int):
        entry = item.data(0, Qt.ItemDataRole.UserRole)
        if not entry:
            return
        if entry.is_dir:
            self._navigate(entry.path)
            return
        ext = os.path.splitext(entry.name)[1].lower()
        text_exts = {
            ".txt", ".py", ".pyw", ".js", ".mjs", ".ts", ".jsx", ".tsx",
            ".html", ".htm", ".xml", ".svg", ".css", ".scss", ".less",
            ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
            ".md", ".rst", ".log", ".sh", ".bat", ".cmd", ".ps1",
            ".c", ".h", ".cpp", ".hpp", ".cs", ".java", ".go", ".rs",
            ".php", ".rb", ".pl", ".sql", ".r", ".kt", ".swift",
        }
        preview_exts = {
            ".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp",
            ".tif", ".tiff", ".ico", ".pbm", ".pgm", ".ppm",
            ".xbm", ".xpm", ".pdf",
        }
        if ext in text_exts or not ext:
            self.request_open_editor.emit(entry.path)
        elif ext in preview_exts:
            self.request_preview.emit(entry.path)
        else:
            self._open_file(entry)

    def _on_selection_changed(self):
        items = self._tree.selectedItems()
        entries = [i.data(0, Qt.ItemDataRole.UserRole) for i in items if i.data(0, Qt.ItemDataRole.UserRole)]
        self.selection_changed.emit(entries)
        if len(entries) == 1 and not entries[0].is_dir:
            self.file_selected.emit(entries[0].path)
        total = getattr(self, "_total_count", self._tree.topLevelItemCount())
        if len(entries) > 1:
            sel_size = sum(getattr(e, "size", 0) for e in entries if not e.is_dir)
            size_str = f" — {fmt_size(sel_size)}" if sel_size else ""
            self._status_label.setText(
                f"{len(entries)} sélectionné(s){size_str} / {total} élément(s)"
            )
        elif len(entries) == 0:
            self._status_label.setText(f"{total} élément(s)")
        else:
            e = entries[0]
            if e.is_dir:
                self._status_label.setText(f"1 sélectionné / {total} élément(s)")
            else:
                self._status_label.setText(
                    f"1 sélectionné — {fmt_size(e.size)} / {total} élément(s)"
                )

    def _go_back(self):
        if self._history:
            self._future.append(self._current_path)
            path = self._history.pop()
            self._current_path = ""
            self._navigate(path)

    def _go_forward(self):
        if self._future:
            self._history.append(self._current_path)
            path = self._future.pop()
            self._current_path = ""
            self._navigate(path)

    def _go_up(self):
        parent = os.path.dirname(self._current_path.rstrip("\\/"))
        if parent and parent != self._current_path:
            self._navigate(parent)

    def _on_path_enter(self):
        path = self._path_edit.text().strip()
        if os.path.isdir(path):
            self._navigate(path)
        else:
            QMessageBox.warning(self, "Erreur", f"Chemin invalide : {path}")

    def _toggle_filter_bar(self):
        if self._filter_bar.isVisible():
            self._clear_filter()
        else:
            self._filter_bar.show()
            self._filter_edit.setFocus()
            self._filter_edit.selectAll()

    def _on_filter_changed(self, text: str):
        if self._subdirs_check.isChecked():
            return
        text = text.lower()
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            item.setHidden(bool(text) and text not in item.text(0).lower())

    def _on_search_trigger(self):
        text = self._filter_edit.text().strip()
        if not text:
            return
        if not self._subdirs_check.isChecked():
            self._on_filter_changed(text)
            return
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.cancel()
        self._is_searching = True
        self._search_banner.setText(f"Recherche «{text}» en cours…")
        self._search_banner.show()
        self._back_search_btn.show()
        self._tree.clear()
        self._status_label.setText("Recherche en cours…")
        self._search_worker = SearchWorker(self._provider, self._current_path, text)
        self._search_worker.partial.connect(self._on_search_partial)
        self._search_worker.found.connect(self._on_search_results)
        self._search_worker.error.connect(self._on_load_error)
        self._search_worker.start()

    @pyqtSlot(list)
    def _on_search_partial(self, entries: list):
        for entry in entries:
            self._tree.addTopLevelItem(self._make_item(entry))
        self._status_label.setText(f"{self._tree.topLevelItemCount()} élément(s)…")

    @pyqtSlot(int)
    def _on_search_results(self, total: int):
        text = self._filter_edit.text().strip()
        self._search_banner.setText(
            f"Résultats pour «{text}» — {total} élément(s)  |  "
            f"Racine : {self._current_path}")
        self._status_label.setText(f"{total} élément(s)")

    def _on_search_back(self, clear_filter: bool = True):
        if self._search_worker and self._search_worker.isRunning():
            self._search_worker.cancel()
        self._is_searching = False
        self._search_banner.hide()
        self._back_search_btn.hide()
        if clear_filter:
            self._clear_filter()
        self._load_entries()

    def _clear_filter(self):
        self._filter_edit.clear()
        self._filter_bar.hide()
        self._search_banner.hide()
        self._back_search_btn.hide()
        if self._is_searching:
            self._is_searching = False
            self._load_entries()
        else:
            for i in range(self._tree.topLevelItemCount()):
                self._tree.topLevelItem(i).setHidden(False)

    def _delete_to_trash(self, entries):
        names = ", ".join(e.name for e in entries[:3])
        if len(entries) > 3:
            names += f" (+{len(entries)-3})"
        is_local = isinstance(self._provider, LocalProvider)
        title = "Envoyer à la corbeille" if is_local else "Supprimer"
        reply = QMessageBox.question(
            self, title,
            f"{title} : {names} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for e in entries:
                try:
                    if is_local:
                        self._local.delete_to_trash(e.path)
                    elif isinstance(self._provider, SMBProvider):
                        self._provider.delete(e.path, is_dir=e.is_dir)
                    else:
                        self._provider.delete(e.path)
                except Exception as ex:
                    QMessageBox.warning(self, "Erreur", f"{e.name} : {ex}")
            self._load_entries()

    def _show_context_menu(self, pos):
        items = self._tree.selectedItems()
        entries = [i.data(0, Qt.ItemDataRole.UserRole) for i in items if i.data(0, Qt.ItemDataRole.UserRole)]
        menu = QMenu(self)

        if len(entries) == 1 and not entries[0].is_dir:
            open_act = menu.addAction("Ouvrir")
            open_act.triggered.connect(lambda: self._open_file(entries[0]))
            edit_act = menu.addAction("Ouvrir dans l'éditeur")
            edit_act.triggered.connect(lambda: self.request_open_editor.emit(entries[0].path))

        if len(entries) == 2 and all(not e.is_dir for e in entries):
            diff_act = menu.addAction("Comparer (diff)")
            diff_act.triggered.connect(lambda: self.request_diff.emit(entries[0].path, entries[1].path))

        menu.addSeparator()

        new_folder_act = menu.addAction("Nouveau dossier")
        new_folder_act.triggered.connect(self._new_folder)

        is_local = isinstance(self._provider, LocalProvider)

        if entries:
            if len(entries) == 1:
                rename_act = menu.addAction("Renommer")
                rename_act.triggered.connect(lambda: self._rename(entries[0]))
            trash_label = "Supprimer (Corbeille)" if is_local else "Supprimer"
            trash_act = menu.addAction(trash_label)
            trash_act.triggered.connect(lambda: self._delete_to_trash(entries))
            del_act = menu.addAction("Supprimer définitivement  [Suppr]")
            del_act.triggered.connect(lambda: self._delete(entries))
            if is_local and len(entries) == 1:
                menu.addSeparator()
                rights_act = menu.addAction("Droits / Permissions")
                rights_act.triggered.connect(lambda: self._show_rights(entries[0]))

        if entries and is_local:
            toggle_hidden_act = menu.addAction("Basculer caché")
            toggle_hidden_act.triggered.connect(lambda: self._toggle_hidden_multi(entries))

        if entries:
            menu.addSeparator()
            paths = [e.path for e in entries]
            copy_act = menu.addAction("Copier vers l'autre panneau  [F5]")
            copy_act.triggered.connect(lambda: self.request_copy_to.emit(paths))
            move_act = menu.addAction("Déplacer vers l'autre panneau  [F6]")
            move_act.triggered.connect(lambda: self.request_move_to.emit(paths))

        if len(entries) == 1 and entries[0].is_dir:
            menu.addSeparator()
            fav_act = menu.addAction("★ Ajouter aux favoris")
            fav_act.triggered.connect(lambda: self.add_to_favorites.emit(entries[0].path))

        menu.exec(self._tree.viewport().mapToGlobal(pos))

    def _open_file(self, entry):
        import subprocess
        try:
            if os.name == "nt":
                os.startfile(entry.path)
            else:
                subprocess.Popen(["xdg-open", entry.path])
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))

    def _path_join(self, base: str, name: str) -> str:
        if isinstance(self._provider, LocalProvider):
            return os.path.join(base, name)
        return base.rstrip("/") + "/" + name

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom :")
        if ok and name:
            try:
                self._provider.mkdir(self._path_join(self._current_path, name))
                self._load_entries()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _rename(self, entry):
        name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom :", text=entry.name)
        if ok and name and name != entry.name:
            try:
                if isinstance(self._provider, LocalProvider):
                    parent = os.path.dirname(entry.path)
                else:
                    parent = entry.path.rstrip("/").rsplit("/", 1)[0] or "/"
                dst = self._path_join(parent, name)
                self._provider.rename(entry.path, dst)
                self._load_entries()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _delete(self, entries):
        names = ", ".join(e.name for e in entries[:3])
        if len(entries) > 3:
            names += f" (+{len(entries)-3})"
        reply = QMessageBox.question(
            self, "Confirmer suppression",
            f"Supprimer : {names} ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for e in entries:
                try:
                    if isinstance(self._provider, SMBProvider):
                        self._provider.delete(e.path, is_dir=e.is_dir)
                    else:
                        self._provider.delete(e.path)
                except Exception as ex:
                    QMessageBox.warning(self, "Erreur", f"{e.name} : {ex}")
            self._load_entries()

    def _show_rights(self, entry):
        from ui.rights_dialog import RightsDialog
        perms = self._local.get_permissions_detail(entry.path)
        dlg = RightsDialog(perms, self)
        dlg.exec()

    def _delete_selected(self):
        items = self._tree.selectedItems()
        entries = [i.data(0, Qt.ItemDataRole.UserRole) for i in items
                   if i.data(0, Qt.ItemDataRole.UserRole)]
        if entries:
            self._delete(entries)

    def _toggle_hidden(self, entry):
        is_hidden = getattr(entry, "is_hidden", entry.name.startswith("."))
        try:
            self._local.set_hidden(entry.path, not is_hidden)
            self._load_entries()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))

    def _toggle_hidden_multi(self, entries):
        for e in entries:
            is_hidden = getattr(e, "is_hidden", e.name.startswith("."))
            try:
                self._local.set_hidden(e.path, not is_hidden)
            except Exception as ex:
                QMessageBox.warning(self, "Erreur", f"{e.name} : {ex}")
        self._load_entries()

    def get_selected_paths(self) -> list:
        items = self._tree.selectedItems()
        return [i.data(0, Qt.ItemDataRole.UserRole).path
                for i in items if i.data(0, Qt.ItemDataRole.UserRole)]

    def get_current_path(self) -> str:
        return self._current_path

    def refresh(self):
        self._load_entries()

    def set_show_hidden(self, show: bool):
        self._local.show_hidden = show
        self._load_entries()

    def set_provider(self, provider, root_path: str = "/"):
        self._provider = provider
        self._current_path = ""
        self._history.clear()
        self._future.clear()
        self._drive_combo.setEnabled(isinstance(provider, LocalProvider))
        self._navigate(root_path)

    def navigate_to(self, path: str):
        if not isinstance(self._provider, LocalProvider):
            self._provider = self._local
            self._drive_combo.setEnabled(True)
        self._navigate(path)
