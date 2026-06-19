import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QLineEdit, QPushButton, QMenu, QAbstractItemView,
    QHeaderView, QToolBar, QComboBox, QMessageBox, QInputDialog,
    QProgressDialog, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot, QMimeData, QUrl
from PyQt6.QtGui import QIcon, QColor, QFont, QAction, QDrag

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
    file_selected = pyqtSignal(str)

    def __init__(self, local_provider: LocalProvider, label: str = "Panneau", parent=None):
        super().__init__(parent)
        self._local = local_provider
        self._provider = local_provider
        self._current_path = ""
        self._history = []
        self._future = []
        self._label_text = label
        self._worker = None
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

        self._tree = QTreeWidget()
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
        count = len(entries)
        self._status_label.setText(f"{count} élément(s)")

    def _make_item(self, entry) -> QTreeWidgetItem:
        name = entry.name
        is_dir = entry.is_dir
        size_str = "" if is_dir else fmt_size(entry.size)
        kind = "Dossier" if is_dir else os.path.splitext(name)[1].lstrip(".").upper() or "Fichier"
        date_str = entry.modified.strftime(DATETIME_FMT) if entry.modified.year > 1 else ""
        perms = entry.permissions if hasattr(entry, "permissions") else ""

        item = QTreeWidgetItem([name, size_str, kind, date_str, perms])
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
        else:
            ext = os.path.splitext(entry.name)[1].lower()
            text_exts = {
                ".txt", ".py", ".pyw", ".js", ".mjs", ".ts", ".jsx", ".tsx",
                ".html", ".htm", ".xml", ".svg", ".css", ".scss", ".less",
                ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
                ".md", ".rst", ".log", ".sh", ".bat", ".cmd", ".ps1",
                ".c", ".h", ".cpp", ".hpp", ".cs", ".java", ".go", ".rs",
                ".php", ".rb", ".pl", ".sql", ".r", ".kt", ".swift",
            }
            if ext in text_exts or not ext:
                self.request_open_editor.emit(entry.path)

    def _on_selection_changed(self):
        items = self._tree.selectedItems()
        entries = [i.data(0, Qt.ItemDataRole.UserRole) for i in items if i.data(0, Qt.ItemDataRole.UserRole)]
        self.selection_changed.emit(entries)
        if len(entries) == 1 and not entries[0].is_dir:
            self.file_selected.emit(entries[0].path)

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

        if entries:
            rename_act = menu.addAction("Renommer")
            rename_act.triggered.connect(lambda: self._rename(entries[0]))
            del_act = menu.addAction("Supprimer")
            del_act.triggered.connect(lambda: self._delete(entries))
            menu.addSeparator()
            rights_act = menu.addAction("Droits / Permissions")
            rights_act.triggered.connect(lambda: self._show_rights(entries[0]))

        if entries:
            toggle_hidden_act = menu.addAction("Basculer caché")
            toggle_hidden_act.triggered.connect(lambda: self._toggle_hidden(entries[0]))

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

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom :")
        if ok and name:
            try:
                self._local.mkdir(os.path.join(self._current_path, name))
                self._load_entries()
            except Exception as e:
                QMessageBox.critical(self, "Erreur", str(e))

    def _rename(self, entry):
        name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom :", text=entry.name)
        if ok and name and name != entry.name:
            try:
                dst = os.path.join(os.path.dirname(entry.path), name)
                self._local.rename(entry.path, dst)
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
                    self._local.delete(e.path)
                except Exception as ex:
                    QMessageBox.warning(self, "Erreur", f"{e.name} : {ex}")
            self._load_entries()

    def _show_rights(self, entry):
        from ui.rights_dialog import RightsDialog
        perms = self._local.get_permissions_detail(entry.path)
        dlg = RightsDialog(perms, self)
        dlg.exec()

    def _toggle_hidden(self, entry):
        is_hidden = getattr(entry, "is_hidden", entry.name.startswith("."))
        try:
            self._local.set_hidden(entry.path, not is_hidden)
            self._load_entries()
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))

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

    def navigate_to(self, path: str):
        self._navigate(path)
