import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QAbstractItemView, QHeaderView, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QColor, QFont

from core.local_provider import LocalProvider
from core import settings


class TreeLoader(QThread):
    loaded = pyqtSignal(str, list)

    def __init__(self, provider: LocalProvider, path: str):
        super().__init__()
        self._provider = provider
        self._path = path

    def run(self):
        entries = [e for e in self._provider.list_dir(self._path) if e.is_dir]
        self.loaded.emit(self._path, entries)


class TreePanel(QWidget):
    navigate = pyqtSignal(str)
    remove_from_favorites = pyqtSignal(str)

    def __init__(self, local_provider: LocalProvider, parent=None):
        super().__init__(parent)
        self._local = local_provider
        self._workers = []
        self._build_ui()
        self._load_roots()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        lbl = QLabel("Arborescence")
        lbl.setStyleSheet("font-weight: bold; padding: 2px 4px;")
        layout.addWidget(lbl)

        self._tree = QTreeWidget()
        self._tree.setColumnCount(1)
        self._tree.setHeaderHidden(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.itemExpanded.connect(self._on_expand)
        self._tree.itemClicked.connect(self._on_click)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        layout.addWidget(self._tree)

    def _load_roots(self):
        self._tree.clear()
        favs = settings.get_history("favorites")
        if favs:
            fav_root = QTreeWidgetItem(["★ Favoris"])
            fav_root.setData(0, Qt.ItemDataRole.UserRole, None)
            fav_root.setData(0, Qt.ItemDataRole.UserRole + 1, "favorites_header")
            fav_root.setFlags(fav_root.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            font = fav_root.font(0)
            font.setBold(True)
            fav_root.setFont(0, font)
            fav_root.setForeground(0, QColor("#e67e22"))
            self._tree.addTopLevelItem(fav_root)
            for path in favs:
                name = os.path.basename(path.rstrip("\\/")) or path
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.ItemDataRole.UserRole, path)
                child.setData(0, Qt.ItemDataRole.UserRole + 1, "favorite")
                child.setToolTip(0, path)
                child.setForeground(0, QColor("#d35400"))
                fav_root.addChild(child)
            fav_root.setExpanded(True)

        for root in self._local.get_roots():
            item = QTreeWidgetItem([root])
            item.setData(0, Qt.ItemDataRole.UserRole, root)
            item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            item.setForeground(0, QColor("#2c3e50"))
            self._tree.addTopLevelItem(item)

    def _on_expand(self, item: QTreeWidgetItem):
        if item.childCount() > 0:
            return
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path:
            return
        worker = TreeLoader(self._local, path)
        worker.loaded.connect(self._on_loaded)
        self._workers.append(worker)
        worker.start()

    @pyqtSlot(str, list)
    def _on_loaded(self, path: str, entries: list):
        root = self._tree.invisibleRootItem()
        item = self._find_item(root, path)
        if not item:
            return
        for entry in entries:
            child = QTreeWidgetItem([entry.name])
            child.setData(0, Qt.ItemDataRole.UserRole, entry.path)
            child.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
            if entry.is_hidden:
                child.setForeground(0, QColor("#aaaaaa"))
            item.addChild(child)

    def _find_item(self, parent: QTreeWidgetItem, path: str) -> QTreeWidgetItem:
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.data(0, Qt.ItemDataRole.UserRole) == path:
                return child
            found = self._find_item(child, path)
            if found:
                return found
        return None

    def _on_click(self, item: QTreeWidgetItem, col: int):
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path:
            self.navigate.emit(path)

    def set_show_hidden(self, show: bool):
        self._local.show_hidden = show
        self._reload_visible()

    def _reload_visible(self):
        def reload_item(item: QTreeWidgetItem):
            if item.childCount() > 0:
                path = item.data(0, Qt.ItemDataRole.UserRole)
                while item.childCount():
                    item.removeChild(item.child(0))
                item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                self._on_expand(item)
            for i in range(item.childCount()):
                reload_item(item.child(i))

        root = self._tree.invisibleRootItem()
        for i in range(root.childCount()):
            reload_item(root.child(i))

    def refresh_favorites(self):
        self._load_roots()

    def _show_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if not item:
            return
        kind = item.data(0, Qt.ItemDataRole.UserRole + 1)
        if kind == "favorite":
            path = item.data(0, Qt.ItemDataRole.UserRole)
            menu = QMenu(self)
            act = menu.addAction("★ Retirer des favoris")
            act.triggered.connect(lambda: self.remove_from_favorites.emit(path))
            menu.exec(self._tree.viewport().mapToGlobal(pos))

    def add_network_root(self, label: str, path: str):
        item = QTreeWidgetItem([label])
        item.setData(0, Qt.ItemDataRole.UserRole, path)
        item.setForeground(0, QColor("#2980b9"))
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        self._tree.addTopLevelItem(item)
