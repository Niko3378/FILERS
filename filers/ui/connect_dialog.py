from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QLabel, QSpinBox, QComboBox, QTabWidget, QWidget,
    QFileDialog, QMessageBox, QCheckBox
)
from PyQt6.QtCore import Qt
from core import settings


class ConnectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connexion réseau")
        self.setMinimumWidth(420)
        self.result_data = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        self._tabs.addTab(self._smb_tab(), "SMB / Windows")
        self._tabs.addTab(self._ftp_tab(), "FTP")
        self._tabs.addTab(self._sftp_tab(), "SFTP")
        layout.addWidget(self._tabs)
        self._tabs.setCurrentIndex(settings.get("connect_last_tab", 0))

        btns = QHBoxLayout()
        ok = QPushButton("Connecter")
        ok.setDefault(True)
        ok.clicked.connect(self._on_ok)
        cancel = QPushButton("Annuler")
        cancel.clicked.connect(self.reject)
        btns.addStretch()
        btns.addWidget(ok)
        btns.addWidget(cancel)
        layout.addLayout(btns)

    def _host_combo(self, history_key: str, placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo.lineEdit().setPlaceholderText(placeholder)
        for h in settings.get_history(history_key):
            combo.addItem(h)
        combo.setCurrentIndex(-1)
        combo.lineEdit().clear()
        return combo

    def _smb_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        self._smb_host = self._host_combo("smb_hosts", "serveur ou IP")
        self._smb_share = QLineEdit()
        self._smb_share.setPlaceholderText("nom_du_partage")
        self._smb_user = QLineEdit()
        self._smb_pass = QLineEdit()
        self._smb_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._smb_domain = QLineEdit()
        self._smb_port = QSpinBox()
        self._smb_port.setRange(1, 65535)
        self._smb_port.setValue(445)
        f.addRow("Hôte :", self._smb_host)
        f.addRow("Partage :", self._smb_share)
        f.addRow("Utilisateur :", self._smb_user)
        f.addRow("Mot de passe :", self._smb_pass)
        f.addRow("Domaine :", self._smb_domain)
        f.addRow("Port :", self._smb_port)

        unc_row = QHBoxLayout()
        self._smb_unc = QLineEdit()
        self._smb_unc.setPlaceholderText(r"\\serveur\partage")
        parse_btn = QPushButton("Parser")
        parse_btn.clicked.connect(self._parse_unc)
        unc_row.addWidget(self._smb_unc)
        unc_row.addWidget(parse_btn)
        f.addRow("UNC :", unc_row)
        return w

    def _ftp_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        self._ftp_host = self._host_combo("ftp_hosts", "serveur ou IP")
        self._ftp_user = QLineEdit()
        self._ftp_user.setText("anonymous")
        self._ftp_pass = QLineEdit()
        self._ftp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._ftp_port = QSpinBox()
        self._ftp_port.setRange(1, 65535)
        self._ftp_port.setValue(21)
        f.addRow("Hôte :", self._ftp_host)
        f.addRow("Utilisateur :", self._ftp_user)
        f.addRow("Mot de passe :", self._ftp_pass)
        f.addRow("Port :", self._ftp_port)
        return w

    def _sftp_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        self._sftp_host = self._host_combo("sftp_hosts", "serveur ou IP")
        self._sftp_user = QLineEdit()
        self._sftp_pass = QLineEdit()
        self._sftp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._sftp_port = QSpinBox()
        self._sftp_port.setRange(1, 65535)
        self._sftp_port.setValue(22)
        self._sftp_key = QLineEdit()
        self._sftp_key.setPlaceholderText("Optionnel")
        key_btn = QPushButton("…")
        key_btn.setFixedWidth(30)
        key_btn.clicked.connect(self._pick_key)
        key_row = QHBoxLayout()
        key_row.addWidget(self._sftp_key)
        key_row.addWidget(key_btn)
        f.addRow("Hôte :", self._sftp_host)
        f.addRow("Utilisateur :", self._sftp_user)
        f.addRow("Mot de passe :", self._sftp_pass)
        f.addRow("Port :", self._sftp_port)
        f.addRow("Clé SSH :", key_row)
        return w

    def _parse_unc(self):
        from core.smb_provider import SMBProvider
        host, share, _ = SMBProvider.parse_unc(self._smb_unc.text())
        self._smb_host.setText(host)
        self._smb_share.setText(share)

    def _pick_key(self):
        path, _ = QFileDialog.getOpenFileName(self, "Clé SSH privée")
        if path:
            self._sftp_key.setText(path)

    def _on_ok(self):
        tab = self._tabs.currentIndex()
        settings.set_value("connect_last_tab", tab)
        if tab == 0:
            self.result_data = {
                "type": "smb",
                "host": self._smb_host.currentText().strip(),
                "share": self._smb_share.text().strip(),
                "user": self._smb_user.text().strip(),
                "password": self._smb_pass.text(),
                "domain": self._smb_domain.text().strip(),
                "port": self._smb_port.value(),
            }
            if not self.result_data["host"] or not self.result_data["share"]:
                QMessageBox.warning(self, "Erreur", "Hôte et partage requis.")
                return
            settings.add_to_history("smb_hosts", self.result_data["host"])
        elif tab == 1:
            self.result_data = {
                "type": "ftp",
                "host": self._ftp_host.currentText().strip(),
                "user": self._ftp_user.text().strip(),
                "password": self._ftp_pass.text(),
                "port": self._ftp_port.value(),
            }
            if not self.result_data["host"]:
                QMessageBox.warning(self, "Erreur", "Hôte requis.")
                return
            settings.add_to_history("ftp_hosts", self.result_data["host"])
        else:
            self.result_data = {
                "type": "sftp",
                "host": self._sftp_host.currentText().strip(),
                "user": self._sftp_user.text().strip(),
                "password": self._sftp_pass.text(),
                "port": self._sftp_port.value(),
                "key_path": self._sftp_key.text().strip(),
            }
            if not self.result_data["host"]:
                QMessageBox.warning(self, "Erreur", "Hôte requis.")
                return
            settings.add_to_history("sftp_hosts", self.result_data["host"])
        self.accept()
