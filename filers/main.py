import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow


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

    app.setStyleSheet("""
        /* ── Fenêtre ─────────────────────────────────────────────────────── */
        QMainWindow, QWidget { background: #f0f2f8; color: #2c3e50; }

        /* ── Barre de menus ──────────────────────────────────────────────── */
        QMenuBar {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #34495e, stop:1 #2c3e50);
            color: white;
            padding: 2px 4px;
            spacing: 2px;
        }
        QMenuBar::item { padding: 5px 12px; border-radius: 4px; }
        QMenuBar::item:selected { background: #3498db; }
        QMenu {
            background: white;
            border: 1px solid #cdd0dc;
            border-radius: 6px;
            padding: 5px 4px;
        }
        QMenu::item { padding: 7px 22px 7px 10px; border-radius: 4px; font: 13px 'Segoe UI'; }
        QMenu::item:selected { background: #3498db; color: white; }
        QMenu::separator { background: #e4e6f0; height: 1px; margin: 4px 10px; }

        /* ── Barre d'outils ──────────────────────────────────────────────── */
        QToolBar {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #1e3a5f, stop:1 #152840);
            spacing: 3px;
            padding: 5px 8px;
            border: none;
            border-bottom: 1px solid #0d1e30;
        }
        QToolBar::separator {
            background: rgba(255,255,255,0.18);
            width: 1px;
            margin: 5px 6px;
        }
        QToolBar QToolButton {
            color: #ffffff;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 6px;
            padding: 5px 12px;
            font: 13px 'Segoe UI';
        }
        QToolBar QToolButton:hover {
            color: white;
            background: rgba(255,255,255,0.13);
            border-color: rgba(255,255,255,0.22);
        }
        QToolBar QToolButton:checked, QToolBar QToolButton:pressed {
            background: #2980b9;
            border-color: #1f6395;
            color: white;
        }

        /* ── Arborescences et listes ─────────────────────────────────────── */
        QTreeWidget, QListWidget {
            background: white;
            alternate-background-color: #f7f8fd;
            gridline-color: #eaecf4;
            border: none;
            outline: none;
            font: 13px 'Segoe UI';
        }
        QTreeWidget::item, QListWidget::item { padding: 4px 6px; border-radius: 3px; }
        QTreeWidget::item:selected, QListWidget::item:selected {
            background: #3498db; color: white;
        }
        QTreeWidget::item:hover, QListWidget::item:hover { background: #ebf5fb; }
        QTreeWidget::branch:selected { background: #3498db; }

        /* ── En-têtes de colonnes ────────────────────────────────────────── */
        QHeaderView::section {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #eef0f8, stop:1 #e4e6f0);
            border: none;
            border-right: 1px solid #d0d3de;
            border-bottom: 1px solid #c8cbda;
            padding: 5px 8px;
            font: bold 13px 'Segoe UI';
            color: #445;
        }
        QHeaderView::section:first { border-left: none; }

        /* ── Onglets ─────────────────────────────────────────────────────── */
        QTabWidget::pane {
            border: 1px solid #d0d3de;
            border-top: none;
            background: white;
        }
        QTabBar {
            background: transparent;
        }
        QTabBar::tab {
            background: #e4e6f0;
            border: 1px solid #d0d3de;
            border-bottom: none;
            padding: 6px 16px;
            font: 13px 'Segoe UI';
            color: #666;
            margin-right: 1px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        QTabBar::tab:selected {
            background: white;
            color: #2c3e50;
            font: bold 13px 'Segoe UI';
            border-bottom: 2px solid #3498db;
        }
        QTabBar::tab:hover:!selected { background: #eff1f8; color: #2c3e50; }

        /* ── Champs de texte ─────────────────────────────────────────────── */
        QLineEdit {
            border: 1.5px solid #d0d3de;
            border-radius: 5px;
            padding: 4px 8px;
            background: white;
            font: 13px 'Segoe UI';
            selection-background-color: #3498db;
        }
        QLineEdit:focus { border-color: #3498db; background: #f5fbff; }

        /* ── Boutons ─────────────────────────────────────────────────────── */
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #f5f7fc, stop:1 #e8eaf4);
            border: 1px solid #c8cbda;
            border-radius: 5px;
            padding: 5px 14px;
            font: 13px 'Segoe UI';
            color: #2c3e50;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #e0e5f5, stop:1 #d4d9ef);
            border-color: #b0b5c8;
        }
        QPushButton:pressed { background: #3498db; color: white; border-color: #2980b9; }
        QPushButton:disabled { color: #aaa; background: #f0f2f8; border-color: #ddd; }

        /* ── Scrollbars ──────────────────────────────────────────────────── */
        QScrollBar:vertical {
            background: #f0f2f8; width: 8px; margin: 0; border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #c0c5d8; border-radius: 4px; min-height: 24px;
        }
        QScrollBar::handle:vertical:hover { background: #3498db; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar:horizontal {
            background: #f0f2f8; height: 8px; margin: 0; border-radius: 4px;
        }
        QScrollBar::handle:horizontal {
            background: #c0c5d8; border-radius: 4px; min-width: 24px;
        }
        QScrollBar::handle:horizontal:hover { background: #3498db; }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

        /* ── Séparateurs ─────────────────────────────────────────────────── */
        QSplitter::handle { background: #d0d3de; }
        QSplitter::handle:horizontal { width: 2px; }
        QSplitter::handle:vertical   { height: 2px; }
        QSplitter::handle:hover { background: #3498db; }

        /* ── Barre d'état ────────────────────────────────────────────────── */
        QStatusBar {
            background: #e8eaf4;
            border-top: 1px solid #d0d3de;
            font: 10px 'Segoe UI';
            color: #555;
        }

        /* ── Barres de progression ───────────────────────────────────────── */
        QProgressBar {
            border: 1px solid #d0d3de;
            border-radius: 6px;
            background: #e8eaf4;
            height: 14px;
            text-align: center;
            color: transparent;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #3498db, stop:1 #27ae60);
            border-radius: 5px;
        }

        /* ── Cases à cocher ──────────────────────────────────────────────── */
        QCheckBox {
            color: #2c3e50;
            spacing: 6px;
            font: 13px 'Segoe UI';
        }
        QCheckBox::indicator {
            width: 15px; height: 15px;
            border: 1.5px solid #b0b5c8;
            border-radius: 4px;
            background: white;
        }
        QCheckBox::indicator:hover { border-color: #3498db; background: #f0f8ff; }
        QCheckBox::indicator:checked {
            background: #3498db;
            border-color: #2980b9;
        }

        /* ── ComboBox ────────────────────────────────────────────────────── */
        QComboBox {
            border: 1.5px solid #d0d3de;
            border-radius: 5px;
            padding: 3px 8px;
            background: white;
            font: 13px 'Segoe UI';
            min-width: 50px;
        }
        QComboBox:focus { border-color: #3498db; }
        QComboBox::drop-down { border: none; width: 18px; }
        QComboBox QAbstractItemView {
            background: white;
            border: 1px solid #cdd0dc;
            border-radius: 4px;
            selection-background-color: #3498db;
            selection-color: white;
        }

        /* ── Labels ──────────────────────────────────────────────────────── */
        QLabel { background: transparent; }

        /* ── Groupbox ────────────────────────────────────────────────────── */
        QGroupBox {
            border: 1px solid #d0d3de;
            border-radius: 6px;
            margin-top: 8px;
            padding-top: 6px;
            font: bold 13px 'Segoe UI';
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 10px;
            padding: 0 4px;
            color: #3498db;
        }

        /* ── Tooltip ─────────────────────────────────────────────────────── */
        QToolTip {
            background: #2c3e50;
            color: white;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            font: 13px 'Segoe UI';
        }
    """)

    window = MainWindow()
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
