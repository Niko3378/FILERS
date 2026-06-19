import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "filers"))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QFont, QIcon
from ui.main_window import MainWindow

app = QApplication(sys.argv)
app.setApplicationName("Files Manager")
app.setOrganizationName("IA-Projet6")
app.setStyle("Fusion")
app.setFont(QFont("Segoe UI", 13))

icon_path = os.path.join(os.path.dirname(__file__), "filers", "icon.ico")
if os.path.isfile(icon_path):
    app.setWindowIcon(QIcon(icon_path))

# Charger le stylesheet depuis main.py
import importlib.util
spec = importlib.util.spec_from_file_location("main", os.path.join(os.path.dirname(__file__), "filers", "main.py"))
mod = importlib.util.module_from_spec(spec)
# Appliquer le stylesheet manuellement
exec(open(os.path.join(os.path.dirname(__file__), "filers", "main.py")).read().split("app.setStyleSheet")[1].split('window = MainWindow')[0])

window = MainWindow()
window.show()

# Naviguer vers l'onglet comparaison et pré-remplir les chemins
def setup():
    fc = window._folder_compare
    fc._left_edit.setText(r"C:\TestA")
    fc._right_edit.setText(r"C:\TestB")
    window._panels_tabs.setCurrentWidget(fc)

QTimer.singleShot(500, setup)

sys.exit(app.exec())
