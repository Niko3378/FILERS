import csv
import os
import shutil

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QLabel, QFileDialog, QLineEdit,
    QHeaderView, QAbstractItemView, QProgressBar, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont

from core.diff_engine import compare_folders, FolderDiffEntry

# (bg_row, fg_text, icon, label)
STATUS_STYLES = {
    "equal":         ("#f5f5f5", "#bdbdbd", "=",  "Identique"),
    "modified":      ("#fff8e1", "#e65100", "≠",  "Modifié"),
    "left_only":     ("#e3f2fd", "#1565c0", "◄",  "Gauche seul"),
    "right_only":    ("#f3e5f5", "#7b1fa2", "►",  "Droite seul"),
    "type_mismatch": ("#ffebee", "#c62828", "!",  "Type diff."),
    "perms_differ":  ("#e8f5e9", "#2e7d32", "⚑",  "Droits diff."),
}


class SyncWorker(QThread):
    progress = pyqtSignal(int, int, str)   # current, total, filename
    done = pyqtSignal(int, int)            # copied/deleted, errors

    def __init__(self, results: list, direction: str,
                 left_dir: str, right_dir: str, delete_extra: bool = False):
        super().__init__()
        self._results = results
        self._ltr = direction == "ltr"     # left-to-right
        self._left_dir = left_dir
        self._right_dir = right_dir
        self._delete_extra = delete_extra
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        copied = errors = 0
        entries = self._results
        total = len(entries)
        for i, entry in enumerate(entries):
            if self._cancelled:
                break
            self.progress.emit(i, total, entry.name.strip())
            try:
                if self._ltr:
                    copied += self._sync_entry_ltr(entry)
                else:
                    copied += self._sync_entry_rtl(entry)
            except Exception:
                errors += 1
        self.done.emit(copied, errors)

    def _sync_entry_ltr(self, e: FolderDiffEntry) -> int:
        if e.status == "left_only":
            if e.is_dir:
                dst = os.path.join(self._right_dir,
                                   os.path.relpath(e.left_path, self._left_dir))
                shutil.copytree(e.left_path, dst, dirs_exist_ok=True)
            else:
                dst = os.path.join(self._right_dir,
                                   os.path.relpath(e.left_path, self._left_dir))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(e.left_path, dst)
            return 1
        if e.status == "modified" and not e.is_dir:
            shutil.copy2(e.left_path, e.right_path)
            return 1
        if e.status == "right_only" and self._delete_extra:
            if e.is_dir:
                shutil.rmtree(e.right_path)
            else:
                os.remove(e.right_path)
            return 1
        return 0

    def _sync_entry_rtl(self, e: FolderDiffEntry) -> int:
        if e.status == "right_only":
            if e.is_dir:
                dst = os.path.join(self._left_dir,
                                   os.path.relpath(e.right_path, self._right_dir))
                shutil.copytree(e.right_path, dst, dirs_exist_ok=True)
            else:
                dst = os.path.join(self._left_dir,
                                   os.path.relpath(e.right_path, self._right_dir))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(e.right_path, dst)
            return 1
        if e.status == "modified" and not e.is_dir:
            shutil.copy2(e.right_path, e.left_path)
            return 1
        if e.status == "left_only" and self._delete_extra:
            if e.is_dir:
                shutil.rmtree(e.left_path)
            else:
                os.remove(e.left_path)
            return 1
        return 0


class CompareWorker(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, left: str, right: str, recursive: bool = True,
                 compare_perms: bool = False):
        super().__init__()
        self.left = left
        self.right = right
        self.recursive = recursive
        self.compare_perms = compare_perms

    def run(self):
        try:
            results = compare_folders(self.left, self.right, self.recursive,
                                      self.compare_perms)
            self.done.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class FolderCompare(QWidget):
    open_diff = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_results = []
        self._build_ui()
        self._worker = None

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # ── Ligne chemins ─────────────────────────────────────────────────
        paths_row = QHBoxLayout()

        self._left_edit = QLineEdit()
        self._left_edit.setPlaceholderText("Dossier gauche…")
        left_btn = QPushButton("…")
        left_btn.setFixedWidth(30)
        left_btn.clicked.connect(lambda: self._pick(self._left_edit))

        self._right_edit = QLineEdit()
        self._right_edit.setPlaceholderText("Dossier droite…")
        right_btn = QPushButton("…")
        right_btn.setFixedWidth(30)
        right_btn.clicked.connect(lambda: self._pick(self._right_edit))

        self._compare_btn = QPushButton("Comparer")
        self._compare_btn.clicked.connect(self._start_compare)

        paths_row.addWidget(QLabel("Gauche :"))
        paths_row.addWidget(self._left_edit)
        paths_row.addWidget(left_btn)
        paths_row.addSpacing(10)
        paths_row.addWidget(QLabel("Droite :"))
        paths_row.addWidget(self._right_edit)
        paths_row.addWidget(right_btn)
        paths_row.addSpacing(10)
        paths_row.addWidget(self._compare_btn)

        self._hide_equal_chk = QCheckBox("Masquer les identiques")
        self._hide_equal_chk.toggled.connect(self._apply_filter)
        paths_row.addSpacing(16)
        paths_row.addWidget(self._hide_equal_chk)

        self._compare_perms_chk = QCheckBox("Comparer les droits")
        self._compare_perms_chk.setToolTip(
            "Compare les permissions NTFS (ACL) en plus du contenu.\n"
            "Peut être plus lent sur les grands dossiers."
        )
        paths_row.addSpacing(8)
        paths_row.addWidget(self._compare_perms_chk)

        layout.addLayout(paths_row)

        # ── Barre de progression ───────────────────────────────────────────
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        # ── Arbre des résultats ────────────────────────────────────────────
        self._tree = QTreeWidget()
        self._tree.setColumnCount(4)
        self._tree.setHeaderLabels(["Nom", "État", "Gauche", "Droite"])
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.setAlternatingRowColors(False)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self._tree)

        # ── Barre de synchronisation ───────────────────────────────────────
        sync_row = QHBoxLayout()

        self._sync_ltr_btn = QPushButton("Sync Gauche → Droite")
        self._sync_ltr_btn.setEnabled(False)
        self._sync_ltr_btn.setToolTip("Copie les fichiers manquants/modifiés vers le dossier droite")
        self._sync_ltr_btn.clicked.connect(lambda: self._start_sync("ltr"))

        self._sync_rtl_btn = QPushButton("Sync Droite → Gauche")
        self._sync_rtl_btn.setEnabled(False)
        self._sync_rtl_btn.setToolTip("Copie les fichiers manquants/modifiés vers le dossier gauche")
        self._sync_rtl_btn.clicked.connect(lambda: self._start_sync("rtl"))

        self._delete_extra_chk = QCheckBox("Supprimer les fichiers en trop (miroir)")
        self._delete_extra_chk.setToolTip(
            "Supprime aussi les fichiers présents uniquement dans le dossier destination.\n"
            "Rend les deux dossiers identiques."
        )

        self._cancel_sync_btn = QPushButton("Annuler")
        self._cancel_sync_btn.setVisible(False)
        self._cancel_sync_btn.clicked.connect(self._cancel_sync)

        sync_row.addWidget(self._sync_ltr_btn)
        sync_row.addWidget(self._sync_rtl_btn)
        sync_row.addSpacing(12)
        sync_row.addWidget(self._delete_extra_chk)
        sync_row.addStretch()
        sync_row.addWidget(self._cancel_sync_btn)
        layout.addLayout(sync_row)

        # ── Barre de stats + export ────────────────────────────────────────
        bottom_row = QHBoxLayout()

        self._stats_label = QLabel("")
        self._stats_label.setTextFormat(Qt.TextFormat.RichText)
        bottom_row.addWidget(self._stats_label, 1)

        self._export_btn = QPushButton("Exporter CSV…")
        self._export_btn.setEnabled(False)
        self._export_btn.clicked.connect(self._export_csv)
        bottom_row.addWidget(self._export_btn)

        layout.addLayout(bottom_row)

    def _pick(self, edit: QLineEdit):
        path = QFileDialog.getExistingDirectory(self, "Choisir un dossier")
        if path:
            edit.setText(path)

    def _start_compare(self):
        left = self._left_edit.text().strip()
        right = self._right_edit.text().strip()
        if not left or not right:
            QMessageBox.warning(self, "Erreur", "Deux dossiers requis.")
            return
        self._tree.clear()
        self._progress.setVisible(True)
        self._compare_btn.setEnabled(False)
        self._export_btn.setEnabled(False)
        compare_perms = self._compare_perms_chk.isChecked()
        self._worker = CompareWorker(left, right, compare_perms=compare_perms)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, results: list):
        self._progress.setVisible(False)
        self._compare_btn.setEnabled(True)
        self._last_results = results
        self._apply_filter()
        has = bool(results)
        self._export_btn.setEnabled(has)
        self._sync_ltr_btn.setEnabled(has)
        self._sync_rtl_btn.setEnabled(has)

    def _apply_filter(self):
        self._tree.clear()
        hide_eq = self._hide_equal_chk.isChecked()
        counts = {k: 0 for k in STATUS_STYLES}
        for entry in self._last_results:
            counts[entry.status] = counts.get(entry.status, 0) + 1
            if hide_eq and entry.status == "equal":
                continue
            self._add_item(entry)
        parts = []
        for status, (bg, fg, icon, label) in STATUS_STYLES.items():
            n = counts.get(status, 0)
            if n:
                parts.append(
                    f'<span style="background:{bg};color:{fg};'
                    f'padding:1px 7px;border-radius:3px;font-weight:bold">'
                    f'{icon} {label}: {n}</span>'
                )
        self._stats_label.setText("&nbsp;&nbsp;" + "&nbsp;&nbsp;".join(parts))

    def _on_error(self, msg: str):
        self._progress.setVisible(False)
        self._compare_btn.setEnabled(True)
        QMessageBox.critical(self, "Erreur comparaison", msg)

    def _add_item(self, entry: FolderDiffEntry):
        bg, fg, icon, label = STATUS_STYLES.get(entry.status, ("#fff", "#333", "?", "?"))
        item = QTreeWidgetItem([
            entry.name,
            f"{icon}  {label}",
            entry.left_path,
            entry.right_path,
        ])
        bg_color = QColor(bg)
        fg_color = QColor(fg)
        for col in range(4):
            item.setBackground(col, bg_color)
            item.setForeground(col, fg_color)
        item.setData(0, Qt.ItemDataRole.UserRole, entry)
        if entry.is_dir:
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
        if entry.left_perms or entry.right_perms:
            tip = f"Droits gauche : {entry.left_perms or '—'}\nDroits droite : {entry.right_perms or '—'}"
            item.setToolTip(0, tip)
            item.setToolTip(1, tip)
        self._tree.addTopLevelItem(item)

    def _on_double_click(self, item: QTreeWidgetItem, col: int):
        entry: FolderDiffEntry = item.data(0, Qt.ItemDataRole.UserRole)
        if entry and not entry.is_dir and entry.status == "modified":
            self.open_diff.emit(entry.left_path, entry.right_path)

    # ── Synchronisation ────────────────────────────────────────────────────

    def _start_sync(self, direction: str):
        if not self._last_results:
            return
        left = self._left_edit.text().strip()
        right = self._right_edit.text().strip()
        delete_extra = self._delete_extra_chk.isChecked()

        label = "Gauche → Droite" if direction == "ltr" else "Droite → Gauche"
        msg = f"Synchroniser {label} ?"
        if delete_extra:
            msg += "\n\nAttention : les fichiers présents uniquement dans le dossier destination seront supprimés."
        reply = QMessageBox.question(self, "Confirmer la synchronisation", msg,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._sync_ltr_btn.setEnabled(False)
        self._sync_rtl_btn.setEnabled(False)
        self._compare_btn.setEnabled(False)
        self._cancel_sync_btn.setVisible(True)
        self._progress.setRange(0, 0)
        self._progress.setVisible(True)

        self._sync_worker = SyncWorker(self._last_results, direction,
                                       left, right, delete_extra)
        self._sync_worker.progress.connect(self._on_sync_progress)
        self._sync_worker.done.connect(self._on_sync_done)
        self._sync_worker.start()

    def _cancel_sync(self):
        if hasattr(self, "_sync_worker") and self._sync_worker.isRunning():
            self._sync_worker.cancel()

    def _on_sync_progress(self, current: int, total: int, name: str):
        if total > 0:
            self._progress.setRange(0, total)
            self._progress.setValue(current)
        self._stats_label.setText(f"Synchronisation… {name}")

    def _on_sync_done(self, copied: int, errors: int):
        self._progress.setVisible(False)
        self._cancel_sync_btn.setVisible(False)
        self._compare_btn.setEnabled(True)
        self._sync_ltr_btn.setEnabled(bool(self._last_results))
        self._sync_rtl_btn.setEnabled(bool(self._last_results))
        if errors:
            QMessageBox.warning(self, "Synchronisation terminée",
                                f"{copied} élément(s) traité(s), {errors} erreur(s).")
        else:
            QMessageBox.information(self, "Synchronisation terminée",
                                    f"{copied} élément(s) traité(s) avec succès.")
        self._start_compare()

    # ── Export CSV ─────────────────────────────────────────────────────────

    def _export_csv(self):
        if not self._last_results:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter le rapport CSV",
            os.path.join(os.path.expanduser("~"), "comparaison.csv"),
            "CSV (*.csv)"
        )
        if not path:
            return
        try:
            has_perms = any(e.left_perms or e.right_perms for e in self._last_results)
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                headers = ["Nom", "État", "Chemin gauche", "Chemin droite"]
                if has_perms:
                    headers += ["Droits gauche", "Droits droite"]
                writer.writerow(headers)
                for e in self._last_results:
                    _, _, icon, label = STATUS_STYLES.get(e.status, ("", "", "?", "?"))
                    row = [e.name.strip(), f"{icon} {label}", e.left_path, e.right_path]
                    if has_perms:
                        row += [e.left_perms, e.right_perms]
                    writer.writerow(row)
            QMessageBox.information(self, "Export CSV", f"Rapport exporté :\n{path}")
        except Exception as ex:
            QMessageBox.critical(self, "Erreur export", str(ex))

    # ── API externe ────────────────────────────────────────────────────────

    def set_paths(self, left: str, right: str):
        self._left_edit.setText(left)
        self._right_edit.setText(right)
