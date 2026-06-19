import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QGridLayout, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from core import long_path_utils as lp


class LongPathDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gestion des chemins longs — Windows")
        self.setMinimumWidth(500)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # Explanation
        info = QLabel(
            "<b>Limite MAX_PATH sur Windows</b><br><br>"
            "Windows impose par défaut une limite de <b>260 caractères</b> sur la longueur "
            "totale des chemins de fichiers. Au-delà, les opérations de copie, déplacement "
            "et suppression peuvent échouer.<br><br>"
            "Files Manager contourne cette limite avec le préfixe <code>\\\\?\\</code> pour toutes "
            "les opérations internes. Pour une compatibilité système complète, vous pouvez "
            "activer le support natif via le registre Windows."
        )
        info.setWordWrap(True)
        info.setStyleSheet("padding: 8px; background: #ebf5fb; border-left: 4px solid #3498db; "
                           "border-radius: 3px;")
        layout.addWidget(info)

        # Status group
        status_group = QGroupBox("État actuel")
        status_grid = QGridLayout(status_group)

        rows = [
            ("Plateforme :",             self._platform_info()),
            ("Support \\\\?\\ (Files Manager) :", "Actif — toutes les opérations internes"),
            ("LongPathsEnabled (registre) :", self._registry_status()),
            ("Python long paths actifs :", self._python_status()),
        ]
        for row, (label, value) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setStyleSheet("font-weight: bold;")
            val = QLabel(value)
            val.setWordWrap(True)
            status_grid.addWidget(lbl, row, 0)
            status_grid.addWidget(val, row, 1)

        layout.addWidget(status_group)

        # Enable button (Windows only)
        if sys.platform == "win32":
            registry_enabled = lp.check_registry_long_paths()
            if not registry_enabled:
                enable_group = QGroupBox("Activer le support natif")
                eg_layout = QVBoxLayout(enable_group)
                eg_layout.addWidget(QLabel(
                    "Active la clé de registre <code>LongPathsEnabled</code>.<br>"
                    "Requiert les droits administrateur. Une déconnexion/reconnexion "
                    "ou un redémarrage est nécessaire pour prendre effet."
                ))
                self._enable_btn = QPushButton("Activer LongPathsEnabled dans le registre")
                self._enable_btn.setStyleSheet(
                    "font-weight: bold; background: #27ae60; color: white; "
                    "padding: 6px 14px; border-radius: 4px;"
                )
                self._enable_btn.clicked.connect(self._enable)
                eg_layout.addWidget(self._enable_btn)
                layout.addWidget(enable_group)
            else:
                ok_lbl = QLabel("Le support natif est déjà activé.")
                ok_lbl.setStyleSheet(
                    "color: #27ae60; font-weight: bold; padding: 6px; "
                    "background: #eafaf1; border-radius: 3px;"
                )
                layout.addWidget(ok_lbl)

        # Info block
        tip = QLabel(
            "<b>Ce que fait Files Manager automatiquement :</b><br>"
            "• Préfixe <code>\\\\?\\</code> ajouté aux chemins &gt; 248 caractères<br>"
            "• <code>\\\\?\\UNC\\</code> pour les partages réseau longs<br>"
            "• Copie/déplacement/suppression robuste sur chemins longs<br>"
            "• Avertissement visuel dans la barre de chemin"
        )
        tip.setWordWrap(True)
        tip.setStyleSheet("padding: 8px; background: #eafaf1; border-left: 4px solid #2ecc71; "
                          "border-radius: 3px;")
        layout.addWidget(tip)

        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _platform_info(self) -> str:
        if sys.platform == "win32":
            import platform
            return f"Windows {platform.release()} ({platform.version()})"
        return sys.platform

    def _registry_status(self) -> str:
        if sys.platform != "win32":
            return "N/A (non Windows)"
        enabled = lp.check_registry_long_paths()
        return ("✔ Activé" if enabled else "✘ Désactivé")

    def _python_status(self) -> str:
        if sys.platform != "win32":
            return "N/A"
        active = lp.python_long_paths_active()
        return ("✔ Actif (chemins > 260 car. supportés nativement)"
                if active else
                "✘ Inactif (Files Manager utilise \\\\?\\ comme contournement)")

    def _enable(self):
        err = lp.enable_registry_long_paths()
        if err:
            QMessageBox.critical(self, "Erreur", err)
        else:
            QMessageBox.information(
                self, "Succès",
                "LongPathsEnabled activé dans le registre.\n\n"
                "Déconnectez-vous puis reconnectez-vous (ou redémarrez) "
                "pour que le changement prenne effet."
            )
            self._enable_btn.setEnabled(False)
            self._enable_btn.setText("✔ Activé — reconnexion requise")
