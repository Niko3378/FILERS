import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow
from core.theme import apply_theme
from core import settings


def _resource_path(relative: str) -> str:
    # PyInstaller unpacks resources to sys._MEIPASS at runtime
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Files Manager")
    app.setOrganizationName("IA-Projet6")
    app.setStyle("Fusion")
    from PyQt6.QtGui import QFont
    app.setFont(QFont("Segoe UI", 13))

    icon_path = _resource_path("icon.ico")
    app_icon = QIcon(icon_path) if os.path.isfile(icon_path) else QIcon()
    app.setWindowIcon(app_icon)

    apply_theme(dark=settings.get("dark_mode", False))

    window = MainWindow()
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
