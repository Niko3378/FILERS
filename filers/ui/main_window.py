import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QToolBar, QStatusBar, QLabel, QCheckBox, QMenuBar,
    QMenu, QMessageBox, QApplication, QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from core.local_provider import LocalProvider
from core.ftp_provider import FTPProvider, SFTPProvider
from core.smb_provider import SMBProvider
from core import settings

from ui.tree_panel import TreePanel
from ui.file_panel import FilePanel
from ui.diff_viewer import DiffViewer
from ui.folder_compare import FolderCompare
from ui.connect_dialog import ConnectDialog
from ui.text_editor import TextEditor
from ui.help_viewer import HelpViewer
from ui.preview_panel import PreviewPanel
from ui.long_path_dialog import LongPathDialog
from ui.donation_dialog import DonationDialog
from core import long_path_utils as lp


class ConnectWorker(QThread):
    success = pyqtSignal(object, str)
    error = pyqtSignal(str)

    def __init__(self, data: dict):
        super().__init__()
        self._data = data

    def run(self):
        try:
            d = self._data
            if d["type"] == "ftp":
                p = FTPProvider()
                p.connect(d["host"], d["port"], d["user"], d["password"])
                self.success.emit(p, f"FTP: {d['host']}")
            elif d["type"] == "sftp":
                p = SFTPProvider()
                p.connect(d["host"], d["port"], d["user"], d["password"], d.get("key_path", ""))
                self.success.emit(p, f"SFTP: {d['host']}")
            elif d["type"] == "smb":
                p = SMBProvider()
                p.connect(d["host"], d["share"], d["user"], d["password"],
                          d.get("domain", ""), d["port"])
                self.success.emit(p, f"SMB: \\\\{d['host']}\\{d['share']}")
        except Exception as e:
            self.error.emit(str(e))


class CopyWorker(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(list)

    def __init__(self, operations: list, provider, move: bool = False):
        super().__init__()
        self._ops = operations
        self._provider = provider
        self._move = move

    def run(self):
        errors = []
        total = len(self._ops)
        for i, (src, dst) in enumerate(self._ops):
            self.progress.emit(i, total, os.path.basename(src))
            try:
                if self._move:
                    self._provider.move(src, dst)
                else:
                    self._provider.copy(src, dst)
            except Exception as e:
                errors.append(f"{os.path.basename(src)}: {e}")
        self.finished.emit(errors)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Files Manager")
        self.setMinimumSize(1200, 700)
        self._local = LocalProvider(show_hidden=False)
        self._connect_workers = []
        self._copy_workers = []
        self._active_panel = None
        self._build_menu()
        self._build_ui()
        self._build_statusbar()
        self._restore_settings()
        QTimer.singleShot(1000, self._show_donation)
        self._don_timer = QTimer(self)
        self._don_timer.timeout.connect(self._show_donation)
        self._don_timer.start(5 * 60 * 1000)

    def _build_menu(self):
        mb = self.menuBar()

        fichier = mb.addMenu("Fichier")
        act_new_editor = QAction("Nouvel onglet éditeur", self)
        act_new_editor.setShortcut(QKeySequence("Ctrl+T"))
        act_new_editor.triggered.connect(lambda: self._text_editor.new_tab())
        fichier.addAction(act_new_editor)
        act_open_editor = QAction("Ouvrir dans l'éditeur…", self)
        act_open_editor.setShortcut(QKeySequence("Ctrl+O"))
        act_open_editor.triggered.connect(self._open_in_editor_dialog)
        fichier.addAction(act_open_editor)
        act_save_editor = QAction("Enregistrer", self)
        act_save_editor.setShortcut(QKeySequence("Ctrl+S"))
        act_save_editor.triggered.connect(lambda: self._text_editor.save_current())
        fichier.addAction(act_save_editor)
        fichier.addSeparator()
        act_connect = QAction("Connexion réseau…", self)
        act_connect.setShortcut(QKeySequence("Ctrl+N"))
        act_connect.triggered.connect(self._open_connect)
        fichier.addAction(act_connect)
        fichier.addSeparator()
        act_quit = QAction("Quitter", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        fichier.addAction(act_quit)

        affichage = mb.addMenu("Affichage")
        self._act_hidden = QAction("Fichiers cachés", self, checkable=True)
        self._act_hidden.setShortcut(QKeySequence("Ctrl+H"))
        self._act_hidden.toggled.connect(self._toggle_hidden)
        affichage.addAction(self._act_hidden)

        outils = mb.addMenu("Outils")
        act_compare_files = QAction("Comparer fichiers…", self)
        act_compare_files.setShortcut(QKeySequence("Ctrl+D"))
        act_compare_files.triggered.connect(self._compare_selected)
        outils.addAction(act_compare_files)
        act_compare_dirs = QAction("Comparer dossiers…", self)
        act_compare_dirs.triggered.connect(self._open_folder_compare)
        outils.addAction(act_compare_dirs)
        outils.addSeparator()
        self._act_sleep = QAction("Désactiver la mise en veille", self, checkable=True)
        self._act_sleep.setToolTip("Empêche Windows de mettre l'ordinateur en veille.")
        self._act_sleep.toggled.connect(self._toggle_sleep)
        outils.addAction(self._act_sleep)
        outils.addSeparator()
        act_long_paths = QAction("Chemins longs Windows…", self)
        act_long_paths.triggered.connect(self._open_long_path_dialog)
        outils.addAction(act_long_paths)

        aide = mb.addMenu("Aide")
        act_help = QAction("Notice d'utilisation", self)
        act_help.setShortcut(QKeySequence("F1"))
        act_help.triggered.connect(self._show_help)
        aide.addAction(act_help)
        aide.addSeparator()
        act_about = QAction("À propos", self)
        act_about.triggered.connect(self._show_about)
        aide.addAction(act_about)
        aide.addSeparator()
        act_donate = QAction("Soutenir Files Manager…", self)
        act_donate.triggered.connect(self._show_donation)
        aide.addAction(act_donate)
        aide.addSeparator()
        act_uninstall = QAction("Désinstaller Files Manager…", self)
        act_uninstall.triggered.connect(self._uninstall)
        aide.addAction(act_uninstall)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        toolbar = QToolBar("Barre d'outils")
        toolbar.setMovable(False)

        act_hidden_tb = QAction("Cachés", self, checkable=True)
        act_hidden_tb.toggled.connect(self._act_hidden.setChecked)
        self._act_hidden.toggled.connect(act_hidden_tb.setChecked)
        toolbar.addAction(act_hidden_tb)

        act_refresh = QAction("Actualiser", self)
        act_refresh.setShortcut(QKeySequence("Ctrl+R"))
        act_refresh.triggered.connect(self._refresh_all)
        toolbar.addAction(act_refresh)

        act_copy_tb = QAction("F5 Copier →", self)
        act_copy_tb.setShortcut(QKeySequence("F5"))
        act_copy_tb.setToolTip("Copier la sélection vers l'autre panneau")
        act_copy_tb.triggered.connect(lambda: self._do_copy_to_other(move=False))
        toolbar.addAction(act_copy_tb)

        act_move_tb = QAction("F6 Déplacer →", self)
        act_move_tb.setShortcut(QKeySequence("F6"))
        act_move_tb.setToolTip("Déplacer la sélection vers l'autre panneau")
        act_move_tb.triggered.connect(lambda: self._do_copy_to_other(move=True))
        toolbar.addAction(act_move_tb)

        act_connect_tb = QAction("Réseau…", self)
        act_connect_tb.triggered.connect(self._open_connect)
        toolbar.addAction(act_connect_tb)

        act_compare_tb = QAction("Diff fichiers", self)
        act_compare_tb.triggered.connect(self._compare_selected)
        toolbar.addAction(act_compare_tb)

        act_compare_dirs_tb = QAction("Diff dossiers", self)
        act_compare_dirs_tb.triggered.connect(self._open_folder_compare)
        toolbar.addAction(act_compare_dirs_tb)

        toolbar.addSeparator()
        act_editor_tb = QAction("Éditeur", self)
        act_editor_tb.triggered.connect(self._focus_editor)
        toolbar.addAction(act_editor_tb)

        self.addToolBar(toolbar)

        h_splitter = QSplitter(Qt.Orientation.Horizontal)

        self._tree_panel = TreePanel(self._local)
        h_splitter.addWidget(self._tree_panel)

        panels_tabs = QTabWidget()

        v_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._left_panel = FilePanel(self._local, "Gauche")
        self._right_panel = FilePanel(self._local, "Droite")
        self._left_panel.request_diff.connect(self._open_diff)
        self._right_panel.request_diff.connect(self._open_diff)
        v_splitter.addWidget(self._left_panel)
        v_splitter.addWidget(self._right_panel)
        v_splitter.setSizes([500, 500])
        panels_tabs.addTab(v_splitter, "Fichiers")

        self._diff_viewer = DiffViewer()
        panels_tabs.addTab(self._diff_viewer, "Diff texte")

        self._folder_compare = FolderCompare()
        self._folder_compare.open_diff.connect(self._open_diff)
        panels_tabs.addTab(self._folder_compare, "Comparaison dossiers")

        self._text_editor = TextEditor()
        panels_tabs.addTab(self._text_editor, "Éditeur")

        self._preview_panel = PreviewPanel()
        panels_tabs.addTab(self._preview_panel, "Aperçu")

        self._help_viewer = HelpViewer()
        panels_tabs.addTab(self._help_viewer, "? Aide")

        self._panels_tabs = panels_tabs
        h_splitter.addWidget(panels_tabs)

        self._right_tree_panel = TreePanel(self._local)
        h_splitter.addWidget(self._right_tree_panel)

        h_splitter.setSizes([220, 960, 220])
        self._h_splitter = h_splitter

        self._tree_panel.navigate.connect(self._left_panel.navigate_to)
        self._right_tree_panel.navigate.connect(self._right_panel.navigate_to)
        self._left_panel.request_open_editor.connect(self._open_in_editor)
        self._right_panel.request_open_editor.connect(self._open_in_editor)
        self._left_panel.file_selected.connect(self._preview_panel.load_file)
        self._right_panel.file_selected.connect(self._preview_panel.load_file)

        self._left_panel.selection_changed.connect(lambda _: self._set_active(self._left_panel))
        self._right_panel.selection_changed.connect(lambda _: self._set_active(self._right_panel))
        self._left_panel.request_copy_to.connect(
            lambda paths: self._copy_between_panels(paths, self._right_panel.get_current_path(), move=False))
        self._left_panel.request_move_to.connect(
            lambda paths: self._copy_between_panels(paths, self._right_panel.get_current_path(), move=True))
        self._right_panel.request_copy_to.connect(
            lambda paths: self._copy_between_panels(paths, self._left_panel.get_current_path(), move=False))
        self._right_panel.request_move_to.connect(
            lambda paths: self._copy_between_panels(paths, self._left_panel.get_current_path(), move=True))

        main_layout.addWidget(h_splitter)

    def _restore_settings(self):
        show_hidden = settings.get("show_hidden", False)
        if show_hidden:
            self._act_hidden.setChecked(True)
        g = settings.get("window_geometry")
        if g:
            self.setGeometry(g["x"], g["y"], g["w"], g["h"])
        splitter_sizes = settings.get("h_splitter_sizes")
        if splitter_sizes:
            self._h_splitter.setSizes(splitter_sizes)

    def _build_statusbar(self):
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status_label = QLabel("Prêt")
        self._status.addWidget(self._status_label)

    def _set_active(self, panel):
        self._active_panel = panel

    def _do_copy_to_other(self, move: bool):
        src_panel = self._active_panel or self._left_panel
        dst_panel = self._right_panel if src_panel is self._left_panel else self._left_panel
        paths = src_panel.get_selected_paths()
        if not paths:
            QMessageBox.information(self, "Copie", "Aucun fichier sélectionné.")
            return
        self._copy_between_panels(paths, dst_panel.get_current_path(), move=move)

    def _copy_between_panels(self, sources: list, target_path: str, move: bool = False):
        if not target_path:
            QMessageBox.warning(self, "Copie", "Chemin de destination invalide.")
            return

        ops = [(src, os.path.join(target_path, os.path.basename(src))) for src in sources]
        verb = "Déplacement" if move else "Copie"

        dlg = QProgressDialog(f"{verb} en cours…", "Annuler", 0, len(ops), self)
        dlg.setWindowTitle(verb)
        dlg.setMinimumDuration(0)
        dlg.setModal(True)
        dlg.setValue(0)

        worker = CopyWorker(ops, self._local, move=move)
        self._copy_workers.append(worker)

        def on_progress(current, total, name):
            if dlg.wasCanceled():
                worker.terminate()
                return
            dlg.setLabelText(f"{verb} : {name}")
            dlg.setValue(current)

        def on_finished(errors):
            dlg.setValue(len(ops))
            dlg.close()
            self._left_panel.refresh()
            self._right_panel.refresh()
            if errors:
                QMessageBox.warning(self, f"{verb} — erreurs",
                                    "\n".join(errors[:10]))

        worker.progress.connect(on_progress)
        worker.finished.connect(on_finished)
        worker.start()

    def _toggle_hidden(self, show: bool):
        self._local.show_hidden = show
        self._left_panel.set_show_hidden(show)
        self._right_panel.set_show_hidden(show)
        self._tree_panel.set_show_hidden(show)
        self._right_tree_panel.set_show_hidden(show)

    def _refresh_all(self):
        self._left_panel.refresh()
        self._right_panel.refresh()

    def _open_connect(self):
        dlg = ConnectDialog(self)
        if dlg.exec():
            data = dlg.result_data
            self._status_label.setText(f"Connexion à {data.get('host', '')}…")
            worker = ConnectWorker(data)
            worker.success.connect(self._on_connected)
            worker.error.connect(self._on_connect_error)
            self._connect_workers.append(worker)
            worker.start()

    @pyqtSlot(object, str)
    def _on_connected(self, provider, label: str):
        self._status_label.setText(f"Connecté : {label}")
        QMessageBox.information(self, "Connexion réussie",
                                f"Connecté à {label}\n\nNavigation réseau disponible dans le panneau.")

    @pyqtSlot(str)
    def _on_connect_error(self, msg: str):
        self._status_label.setText("Erreur de connexion")
        QMessageBox.critical(self, "Erreur de connexion", msg)

    def _compare_selected(self):
        left_paths = self._left_panel.get_selected_paths()
        right_paths = self._right_panel.get_selected_paths()
        if left_paths and right_paths:
            self._open_diff(left_paths[0], right_paths[0])
        elif len(left_paths) == 2:
            self._open_diff(left_paths[0], left_paths[1])
        else:
            QMessageBox.information(self, "Diff",
                "Sélectionnez un fichier dans chaque panneau, ou deux fichiers dans un panneau.")

    def _open_diff(self, left_path: str, right_path: str):
        try:
            left_text = self._local.read_text(left_path)
            right_text = self._local.read_text(right_path)
            self._diff_viewer.load(
                left_text, right_text,
                os.path.basename(left_path),
                os.path.basename(right_path)
            )
            self._panels_tabs.setCurrentWidget(self._diff_viewer)
        except Exception as e:
            QMessageBox.warning(self, "Erreur diff", str(e))

    def _open_folder_compare(self):
        left = self._left_panel.get_current_path()
        right = self._right_panel.get_current_path()
        self._folder_compare.set_paths(left, right)
        self._panels_tabs.setCurrentWidget(self._folder_compare)

    def _open_long_path_dialog(self):
        LongPathDialog(self).exec()

    def _show_help(self):
        self._panels_tabs.setCurrentWidget(self._help_viewer)

    def _open_in_editor(self, path: str):
        self._text_editor.open_file(path)
        self._panels_tabs.setCurrentWidget(self._text_editor)

    def _open_in_editor_dialog(self):
        self._text_editor.open_file_dialog()
        self._panels_tabs.setCurrentWidget(self._text_editor)

    def _focus_editor(self):
        self._panels_tabs.setCurrentWidget(self._text_editor)

    def _show_about(self):
        QMessageBox.about(self, "Files Manager",
            "<b>Files Manager</b> — Gestionnaire de fichiers<br><br>"
            "Fonctionnalités :<br>"
            "• Double panneau, arborescence<br>"
            "• Fichiers cachés, droits NTFS<br>"
            "• Connexions SMB, FTP, SFTP<br>"
            "• Diff texte et comparaison dossiers<br>"
            "• Éditeur de texte multi-onglets avec coloration syntaxique<br>"
        )

    def _show_donation(self):
        DonationDialog(self).exec()

    def _toggle_sleep(self, prevent: bool):
        import ctypes
        ES_CONTINUOUS      = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        if prevent:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
            self._status_label.setText("Mise en veille désactivée")
        else:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            self._status_label.setText("Mise en veille rétablie")

    def closeEvent(self, event):
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        g = self.geometry()
        settings.set_value("window_geometry", {"x": g.x(), "y": g.y(), "w": g.width(), "h": g.height()})
        settings.set_value("show_hidden", self._act_hidden.isChecked())
        settings.set_value("h_splitter_sizes", self._h_splitter.sizes())
        super().closeEvent(event)

    def _uninstall(self):
        import subprocess, sys as _sys
        if getattr(_sys, "frozen", False):
            install_dir = os.path.dirname(_sys.executable)
        else:
            install_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        uninstall_vbs = os.path.join(install_dir, "uninstall.vbs")
        if not os.path.isfile(uninstall_vbs):
            QMessageBox.warning(self, "Désinstallation",
                f"Désinstallateur introuvable :\n{uninstall_vbs}")
            return
        r = QMessageBox.question(self, "Désinstaller Files Manager",
            "Cette action lancera le désinstallateur et fermera Files Manager.")
        if r == QMessageBox.StandardButton.Yes:
            subprocess.Popen(["wscript.exe", uninstall_vbs])
            QApplication.quit()
