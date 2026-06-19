import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QGroupBox, QCheckBox, QGridLayout,
    QHeaderView, QAbstractItemView, QComboBox, QLineEdit,
    QMessageBox, QTabWidget, QWidget, QFormLayout, QFrame,
    QCompleter
)
from PyQt6.QtCore import Qt, QStringListModel
from PyQt6.QtGui import QColor, QFont


# ---------------------------------------------------------------------------
# NTFS rights constants
# ---------------------------------------------------------------------------

NTFS_RIGHTS = {
    "Lecture":            0x00120089,
    "Écriture":           0x00120116,
    "Exécution":          0x001200A0,
    "Lecture et exécution": 0x001200A9,
    "Modification":       0x001301BF,
    "Contrôle total":     0x001F01FF,
    "Suppression":        0x00010000,
}

# Map mask bits → label (for display only)
MASK_LABELS = [
    (0x001F01FF, "Contrôle total"),
    (0x001301BF, "Modification"),
    (0x001200A9, "Lecture et exécution"),
    (0x001200A0, "Exécution"),
    (0x00120116, "Écriture"),
    (0x00120089, "Lecture"),
    (0x00010000, "Suppression"),
]


def mask_to_labels(mask: int) -> list[str]:
    for m, label in MASK_LABELS:
        if (mask & m) == m:
            return [label]
    parts = []
    if mask & 0x00120089:
        parts.append("Lecture")
    if mask & 0x00120116:
        parts.append("Écriture")
    if mask & 0x001200A0:
        parts.append("Exécution")
    if mask & 0x00010000:
        parts.append("Suppression")
    return parts or [f"0x{mask:08X}"]


def _get_ntfs_acl(path: str) -> list[dict]:
    try:
        import win32security
        import ntsecuritycon as con
        sd = win32security.GetFileSecurity(
            path,
            win32security.DACL_SECURITY_INFORMATION | win32security.OWNER_SECURITY_INFORMATION,
        )
        dacl = sd.GetSecurityDescriptorDacl()
        if not dacl:
            return []
        entries = []
        for i in range(dacl.GetAceCount()):
            ace = dacl.GetAce(i)
            ace_type, ace_flags = ace[0]
            mask = ace[1]
            sid = ace[2]
            try:
                name, domain, _ = win32security.LookupAccountSid(None, sid)
                account = f"{domain}\\{name}" if domain else name
            except Exception:
                account = str(sid)
            entries.append({
                "account":  account,
                "rights":   mask_to_labels(mask),
                "mask":     mask,
                "type":     "Allow" if ace_type == 0 else "Deny",
                "sid":      sid,
            })
        return entries
    except ImportError:
        return []
    except Exception:
        return []


def _apply_ntfs_acl(path: str, entries: list[dict]) -> str:
    """Apply a new DACL to path. Returns '' on success or an error string."""
    try:
        import win32security
        import ntsecuritycon as con
        import pywintypes

        sd = win32security.GetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION)
        new_dacl = win32security.ACL()

        for e in entries:
            sid = e.get("sid")
            if sid is None:
                try:
                    sid, _, _ = win32security.LookupAccountName(None, e["account"])
                except Exception as ex:
                    return f"Compte introuvable « {e['account']} » : {ex}"
            mask = e.get("mask", 0)
            if e["type"] == "Allow":
                new_dacl.AddAccessAllowedAce(win32security.ACL_REVISION, mask, sid)
            else:
                new_dacl.AddAccessDeniedAce(win32security.ACL_REVISION, mask, sid)

        sd.SetSecurityDescriptorDacl(True, new_dacl, False)
        win32security.SetFileSecurity(path, win32security.DACL_SECURITY_INFORMATION, sd)
        return ""
    except ImportError:
        return "pywin32 non installé (pip install pywin32)"
    except Exception as ex:
        return str(ex)


def _set_owner(path: str, account: str) -> str:
    try:
        import win32security
        import win32api
        priv_flags = win32security.TOKEN_ADJUST_PRIVILEGES | win32security.TOKEN_QUERY
        token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), priv_flags)
        luid = win32security.LookupPrivilegeValue(None, win32security.SE_TAKE_OWNERSHIP_NAME)
        win32security.AdjustTokenPrivileges(token, False, [(luid, win32security.SE_PRIVILEGE_ENABLED)])
        sid, _, _ = win32security.LookupAccountName(None, account)
        sd = win32security.GetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION)
        sd.SetSecurityDescriptorOwner(sid, False)
        win32security.SetFileSecurity(path, win32security.OWNER_SECURITY_INFORMATION, sd)
        return ""
    except ImportError:
        return "pywin32 non installé"
    except Exception as ex:
        return str(ex)


# ---------------------------------------------------------------------------
# ACE editor dialog (add/edit one entry)
# ---------------------------------------------------------------------------

class ACEDialog(QDialog):
    def __init__(self, entry: dict | None = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Entrée ACL")
        self.setMinimumWidth(380)
        self._entry = dict(entry) if entry else {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._account_edit = QLineEdit(self._entry.get("account", ""))
        self._account_edit.setPlaceholderText("DOMAINE\\Utilisateur ou Groupe")
        form.addRow("Compte :", self._account_edit)

        self._type_combo = QComboBox()
        self._type_combo.addItems(["Allow", "Deny"])
        if self._entry.get("type") == "Deny":
            self._type_combo.setCurrentIndex(1)
        form.addRow("Type :", self._type_combo)

        self._rights_combo = QComboBox()
        self._rights_combo.addItems(list(NTFS_RIGHTS.keys()))
        current_rights = self._entry.get("rights", ["Lecture"])
        if current_rights:
            idx = self._rights_combo.findText(current_rights[0])
            if idx >= 0:
                self._rights_combo.setCurrentIndex(idx)
        form.addRow("Droits :", self._rights_combo)

        layout.addLayout(form)
        layout.addSpacing(8)

        btns = QHBoxLayout()
        ok = QPushButton("OK")
        ok.setDefault(True)
        ok.clicked.connect(self._on_ok)
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def _on_ok(self):
        account = self._account_edit.text().strip()
        if not account:
            QMessageBox.warning(self, "Erreur", "Compte requis.")
            return
        rights_label = self._rights_combo.currentText()
        mask = NTFS_RIGHTS.get(rights_label, 0)
        self._entry = {
            "account": account,
            "type":    self._type_combo.currentText(),
            "rights":  [rights_label],
            "mask":    mask,
            "sid":     None,
        }
        self.accept()

    def get_entry(self) -> dict:
        return self._entry


# ---------------------------------------------------------------------------
# Full rights dialog
# ---------------------------------------------------------------------------

class RightsDialog(QDialog):
    def __init__(self, perms: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Droits — {os.path.basename(perms.get('path', ''))}")
        self.setMinimumSize(580, 500)
        self._perms = perms
        self._path = perms.get("path", "")
        self._acl_entries: list[dict] = list(perms.get("ntfs_acl", []))
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Path header
        path_lbl = QLabel(self._path)
        path_lbl.setWordWrap(True)
        font = path_lbl.font()
        font.setBold(True)
        path_lbl.setFont(font)
        path_lbl.setStyleSheet("padding: 4px; background: #f0f3f7; border-radius: 4px;")
        layout.addWidget(path_lbl)

        tabs = QTabWidget()

        # ---- Tab 1 : Basic rights ----------------------------------------
        basic_tab = QWidget()
        g = QGridLayout(basic_tab)
        g.setSpacing(8)

        mode = self._perms.get("mode", "----------")
        owner = self._perms.get("owner", "N/A")

        g.addWidget(QLabel("Mode Unix :"), 0, 0)
        mode_lbl = QLabel(mode)
        mode_lbl.setFont(QFont("Courier New", 10))
        g.addWidget(mode_lbl, 0, 1)

        g.addWidget(QLabel("Propriétaire :"), 1, 0)
        g.addWidget(QLabel(owner), 1, 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #ddd;")
        g.addWidget(sep, 2, 0, 1, 4)

        for col, label in enumerate(["Lecture", "Écriture", "Exécution"]):
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(lbl, 3, col + 1)

        for row_i, (who, r, w, x) in enumerate([
            ("Processus courant",
             self._perms.get("readable"),
             self._perms.get("writable"),
             self._perms.get("executable")),
        ]):
            g.addWidget(QLabel(who + " :"), 4 + row_i, 0)
            for col, val in enumerate([r, w, x]):
                cb = QCheckBox()
                cb.setChecked(bool(val))
                cb.setEnabled(False)
                cb.setStyleSheet("margin-left: 24px;")
                g.addWidget(cb, 4 + row_i, col + 1)

        g.setRowStretch(10, 1)
        tabs.addTab(basic_tab, "Général")

        # ---- Tab 2 : NTFS ACL --------------------------------------------
        ntfs_tab = QWidget()
        ntfs_layout = QVBoxLayout(ntfs_tab)

        if os.name != "nt":
            ntfs_layout.addWidget(QLabel("Gestion des ACL NTFS disponible sur Windows uniquement."))
        else:
            self._acl_table = QTableWidget(0, 3)
            self._acl_table.setHorizontalHeaderLabels(["Compte", "Type", "Droits"])
            self._acl_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            self._acl_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            self._acl_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self._acl_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            self._populate_acl_table()
            ntfs_layout.addWidget(self._acl_table)

            # ACL action buttons
            acl_btns = QHBoxLayout()
            add_btn  = QPushButton("Ajouter")
            edit_btn = QPushButton("Modifier")
            del_btn  = QPushButton("Supprimer")
            apply_btn = QPushButton("Appliquer les droits")
            apply_btn.setStyleSheet("font-weight: bold; background: #27ae60; color: white; padding: 4px 12px;")
            add_btn.clicked.connect(self._add_ace)
            edit_btn.clicked.connect(self._edit_ace)
            del_btn.clicked.connect(self._del_ace)
            apply_btn.clicked.connect(self._apply_acl)
            acl_btns.addWidget(add_btn)
            acl_btns.addWidget(edit_btn)
            acl_btns.addWidget(del_btn)
            acl_btns.addStretch()
            acl_btns.addWidget(apply_btn)
            ntfs_layout.addLayout(acl_btns)

            ntfs_layout.addWidget(QLabel(
                "⚠ Droits élevés requis pour modifier les ACL. "
                "L'héritage n'est pas géré ici."
            ))

        tabs.addTab(ntfs_tab, "ACL NTFS")

        # ---- Tab 3 : Propriétaire ----------------------------------------
        owner_tab = QWidget()
        owner_layout = QFormLayout(owner_tab)
        self._owner_edit = QLineEdit(self._perms.get("owner", ""))
        self._owner_edit.setPlaceholderText("DOMAINE\\Compte")
        owner_layout.addRow("Nouveau propriétaire :", self._owner_edit)
        set_owner_btn = QPushButton("Changer le propriétaire")
        set_owner_btn.setStyleSheet("font-weight: bold; background: #2980b9; color: white; padding: 4px 12px;")
        set_owner_btn.clicked.connect(self._change_owner)
        if os.name != "nt":
            set_owner_btn.setEnabled(False)
            owner_layout.addRow(QLabel("Disponible sur Windows uniquement."))
        owner_layout.addRow("", set_owner_btn)
        tabs.addTab(owner_tab, "Propriétaire")

        layout.addWidget(tabs)

        # Error display
        error = self._perms.get("error")
        if error:
            err_lbl = QLabel(f"Erreur : {error}")
            err_lbl.setStyleSheet("color: #c0392b; padding: 4px;")
            layout.addWidget(err_lbl)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    # ---- ACL table -------------------------------------------------------

    def _populate_acl_table(self):
        self._acl_table.setRowCount(0)
        for entry in self._acl_entries:
            row = self._acl_table.rowCount()
            self._acl_table.insertRow(row)
            acc_item   = QTableWidgetItem(entry.get("account", ""))
            type_item  = QTableWidgetItem(entry.get("type", "Allow"))
            rights_item = QTableWidgetItem(", ".join(entry.get("rights", [])))

            color = QColor("#27ae60") if entry.get("type") == "Allow" else QColor("#c0392b")
            for item in (acc_item, type_item, rights_item):
                item.setForeground(color)

            self._acl_table.setItem(row, 0, acc_item)
            self._acl_table.setItem(row, 1, type_item)
            self._acl_table.setItem(row, 2, rights_item)

    def _selected_row(self) -> int:
        rows = self._acl_table.selectedItems()
        if not rows:
            return -1
        return self._acl_table.currentRow()

    def _add_ace(self):
        dlg = ACEDialog(parent=self)
        if dlg.exec():
            self._acl_entries.append(dlg.get_entry())
            self._populate_acl_table()

    def _edit_ace(self):
        row = self._selected_row()
        if row < 0:
            QMessageBox.information(self, "Modifier", "Sélectionnez une entrée.")
            return
        dlg = ACEDialog(entry=self._acl_entries[row], parent=self)
        if dlg.exec():
            self._acl_entries[row] = dlg.get_entry()
            self._populate_acl_table()

    def _del_ace(self):
        row = self._selected_row()
        if row < 0:
            QMessageBox.information(self, "Supprimer", "Sélectionnez une entrée.")
            return
        entry = self._acl_entries[row]
        reply = QMessageBox.question(
            self, "Confirmer",
            f"Supprimer le droit de « {entry.get('account')} » ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self._acl_entries[row]
            self._populate_acl_table()

    def _apply_acl(self):
        reply = QMessageBox.question(
            self, "Appliquer les droits",
            "Appliquer les droits NTFS sur :\n" + self._path +
            "\n\nCette opération peut bloquer l'accès au fichier si mal configurée.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        err = _apply_ntfs_acl(self._path, self._acl_entries)
        if err:
            QMessageBox.critical(self, "Erreur ACL", err)
        else:
            # Reload ACL from disk to verify
            self._acl_entries = _get_ntfs_acl(self._path)
            self._populate_acl_table()
            QMessageBox.information(self, "Droits appliqués", "ACL mise à jour avec succès.")

    def _change_owner(self):
        account = self._owner_edit.text().strip()
        if not account:
            QMessageBox.warning(self, "Erreur", "Compte requis.")
            return
        reply = QMessageBox.question(
            self, "Changer le propriétaire",
            f"Définir « {account} » comme propriétaire de :\n{self._path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        err = _set_owner(self._path, account)
        if err:
            QMessageBox.critical(self, "Erreur", err)
        else:
            QMessageBox.information(self, "Propriétaire", "Propriétaire modifié avec succès.")
