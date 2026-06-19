"""
FILERS - Installateur graphique
Necessite uniquement Python + tkinter (integre).
Peut etre compile en install.exe avec PyInstaller (voir build.bat).
"""

import sys
import os
import shutil
import subprocess
import threading
import platform

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    print("tkinter non disponible. Installez Python depuis python.org")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Chemins : fonctionne en source ET en bundle PyInstaller
# ---------------------------------------------------------------------------
if hasattr(sys, "_MEIPASS"):
    BUNDLE_DIR     = sys._MEIPASS
    IS_BUNDLED     = True
    FILERS_EXE_SRC = os.path.join(BUNDLE_DIR, "FILERS.exe")
else:
    BUNDLE_DIR     = None
    IS_BUNDLED     = False
    FILERS_EXE_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "FILERS.exe")

DEFAULT_INSTALL = os.path.join(os.environ.get("LOCALAPPDATA", r"C:\Users\Public"), "FILERS")
REQUIRED_MB     = 80   # FILERS.exe ~ 70 Mo

FEATURES = [
    "Double panneau, arborescence",
    "Connexions reseau SMB / FTP / SFTP",
    "Editeur multi-onglets avec coloration",
    "Comparaison de fichiers et dossiers",
    "Apercu images et PDF",
    "Droits NTFS, chemins longs",
]

# ---------------------------------------------------------------------------
# Couleurs
# ---------------------------------------------------------------------------
C_BG      = "#f5f6fa"
C_HEADER  = "#2c3e50"
C_ACCENT  = "#3498db"
C_SUCCESS = "#27ae60"
C_ERROR   = "#e74c3c"
C_WARN    = "#e67e22"
C_TEXT    = "#2c3e50"
C_MUTED   = "#7f8c8d"
C_LOG_BG  = "#1e272e"
C_LOG_FG  = "#dfe6e9"

# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------
def fmt_bytes(n: int) -> str:
    for unit in ("o", "Ko", "Mo", "Go", "To"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} Po"

def free_space(path: str) -> int:
    try:
        os.makedirs(path, exist_ok=True)
        return shutil.disk_usage(path).free
    except Exception:
        return 0

def create_uninstall_vbs(install_dir: str) -> str:
    """Genere uninstall.vbs dans install_dir (pas besoin de Python)."""
    vbs_path = os.path.join(install_dir, "uninstall.vbs")
    lnk = os.path.join(os.path.expanduser("~"), "Desktop", "FILERS.lnk")
    reg_key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FILERS"
    lines = [
        'Set WshShell = WScript.CreateObject("WScript.Shell")',
        'Dim answer',
        f'answer = MsgBox("Desinstaller FILERS ?" & Chr(13) & Chr(13) & "{install_dir}",'
        ' vbYesNo + vbQuestion + vbDefaultButton2, "FILERS - Desinstallation")',
        'If answer = vbYes Then',
        '    On Error Resume Next',
        '    WshShell.Run "taskkill /f /im FILERS.exe", 0, True',
        '    WshShell.Run "reg delete ""HKCU\\' + reg_key + '"" /f", 0, True',
        '    Set fso = CreateObject("Scripting.FileSystemObject")',
        f'    If fso.FileExists("{lnk}") Then fso.DeleteFile "{lnk}"',
        '    Dim tmpBat',
        r'    tmpBat = WshShell.ExpandEnvironmentStrings("%TEMP%") & "\filers_remove.bat"',
        '    Dim f',
        '    Set f = fso.OpenTextFile(tmpBat, 2, True)',
        '    f.WriteLine "@echo off"',
        '    f.WriteLine "timeout /t 2 /nobreak >nul"',
        f'    f.WriteLine "rd /s /q " & Chr(34) & "{install_dir}" & Chr(34)',
        '    f.WriteLine "del " & Chr(34) & "%~f0" & Chr(34)',
        '    f.Close',
        '    WshShell.Run "cmd /c " & Chr(34) & tmpBat & Chr(34), 0, False',
        '    MsgBox "FILERS a ete desinstalle.", vbInformation, "FILERS"',
        'End If',
    ]
    with open(vbs_path, "w", encoding="utf-8") as fh:
        fh.write('\r\n'.join(lines) + '\r\n')
    return vbs_path

def create_shortcut(install_dir: str):
    filers_exe = os.path.join(install_dir, "FILERS.exe")
    desktop    = os.path.join(os.path.expanduser("~"), "Desktop")
    link       = os.path.join(desktop, "FILERS.lnk")
    if sys.platform != "win32":
        return
    try:
        ps = (
            f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{link}");'
            f'$s.TargetPath="{filers_exe}";'
            f'$s.WorkingDirectory="{install_dir}";'
            f'$s.Description="FILERS - Gestionnaire de fichiers";'
            f'$s.IconLocation="{filers_exe},0";'
            f'$s.Save()'
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, timeout=10)
    except Exception:
        pass

def register_uninstall(install_dir: str):
    """Enregistre FILERS dans Ajout/Suppression de programmes (HKCU, sans droits admin)."""
    try:
        import winreg
        key_path       = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FILERS"
        filers_exe     = os.path.join(install_dir, "FILERS.exe")
        uninstall_vbs  = os.path.join(install_dir, "uninstall.vbs")
        total = sum(
            os.path.getsize(os.path.join(dp, f))
            for dp, _, files in os.walk(install_dir)
            for f in files
            if not os.path.islink(os.path.join(dp, f))
        )
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            winreg.SetValueEx(k, "DisplayName",    0, winreg.REG_SZ,    "FILERS - Gestionnaire de fichiers")
            winreg.SetValueEx(k, "DisplayVersion", 0, winreg.REG_SZ,    "1.0.0")
            winreg.SetValueEx(k, "Publisher",      0, winreg.REG_SZ,    "IA-Projet6")
            winreg.SetValueEx(k, "InstallLocation",0, winreg.REG_SZ,    install_dir)
            winreg.SetValueEx(k, "UninstallString",0, winreg.REG_SZ,    f'wscript.exe "{uninstall_vbs}"')
            winreg.SetValueEx(k, "DisplayIcon",    0, winreg.REG_SZ,    f"{filers_exe},0")
            winreg.SetValueEx(k, "EstimatedSize",  0, winreg.REG_DWORD, total // 1024)
            winreg.SetValueEx(k, "NoModify",       0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(k, "NoRepair",       0, winreg.REG_DWORD, 1)
    except Exception:
        pass


def launch_filers(install_dir: str):
    exe = os.path.join(install_dir, "FILERS.exe")
    if os.path.isfile(exe):
        subprocess.Popen([exe], cwd=install_dir)

# ---------------------------------------------------------------------------
# Widgets partagés
# ---------------------------------------------------------------------------
class Header(tk.Frame):
    STEPS = ["Bienvenue", "Dossier", "Installation", "Termine"]

    def __init__(self, parent, step: int):
        super().__init__(parent, bg=C_HEADER)
        tk.Label(self, text="FILERS", fg="white", bg=C_HEADER,
                 font=("Segoe UI", 20, "bold")).pack(side="left", padx=18, pady=12)
        tk.Label(self, text="Gestionnaire de fichiers",
                 fg="#95a5a6", bg=C_HEADER,
                 font=("Segoe UI", 9)).pack(side="left")

        sf = tk.Frame(self, bg=C_HEADER)
        sf.pack(side="right", padx=14)
        for i, s in enumerate(self.STEPS, 1):
            active = (i == step)
            done   = (i < step)
            if done:
                icon, color = "✔", "#2ecc71"
            elif active:
                icon, color = "●", "white"
            else:
                icon, color = "○", "#566573"
            tk.Label(sf, text=f"{icon} {i}. {s}",
                     fg=color, bg=C_HEADER,
                     font=("Segoe UI", 8 + (active))).pack(side="left", padx=5)

def _btn(parent, text, command, bg=C_ACCENT, fg="white", bold=False):
    return tk.Button(parent, text=text, command=command,
                     bg=bg, fg=fg, relief="flat",
                     font=("Segoe UI", 10, "bold" if bold else "normal"),
                     padx=18, pady=6, cursor="hand2",
                     activebackground=bg, activeforeground=fg)

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
class InstallerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FILERS — Installation")
        self.geometry("640x540")
        self.resizable(False, False)
        self.configure(bg=C_BG)
        self._frame   = None
        self.install_dir = tk.StringVar(value=DEFAULT_INSTALL)
        self.shortcut    = tk.BooleanVar(value=True)
        self._show_welcome()

    def _switch(self, FrameClass, **kw):
        if self._frame:
            self._frame.destroy()
        self._frame = FrameClass(self, **kw)
        self._frame.pack(fill="both", expand=True)

    def _show_welcome(self):   self._switch(WelcomePage)
    def _show_folder(self):    self._switch(FolderPage)
    def _show_install(self):   self._switch(InstallPage)
    def _show_done(self, ok, msg): self._switch(DonePage, success=ok, message=msg)

# ---------------------------------------------------------------------------
# Page 1 : Bienvenue
# ---------------------------------------------------------------------------
class WelcomePage(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=C_BG)
        Header(self, 1).pack(fill="x")
        body = tk.Frame(self, bg=C_BG, padx=30, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Bienvenue dans l'installation de FILERS",
                 fg=C_TEXT, bg=C_BG,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Label(body,
                 text="Cet assistant installe FILERS et ses composants sur votre machine.\n"
                      "Duree estimee : 1 a 3 minutes selon votre connexion.",
                 fg=C_MUTED, bg=C_BG, justify="left",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 14))

        comp = tk.LabelFrame(body, text="Fonctionnalites incluses", bg=C_BG, fg=C_TEXT,
                             font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        comp.pack(fill="x", pady=(0, 14))
        for feat in FEATURES:
            r = tk.Frame(comp, bg=C_BG)
            r.pack(fill="x", pady=1)
            tk.Label(r, text="•", fg=C_ACCENT, bg=C_BG,
                     font=("Segoe UI", 11)).pack(side="left")
            tk.Label(r, text=f" {feat}", fg=C_TEXT, bg=C_BG,
                     font=("Segoe UI", 9)).pack(side="left")

        sys_frame = tk.LabelFrame(body, text="Systeme", bg=C_BG, fg=C_TEXT,
                                  font=("Segoe UI", 9, "bold"), padx=10, pady=6)
        sys_frame.pack(fill="x", pady=(0, 14))
        rows = [
            ("Systeme",       platform.system() + " " + platform.release()),
            ("Espace requis", f"{REQUIRED_MB} Mo minimum"),
            ("Dependances",   "Aucune — application autonome"),
        ]
        for lbl, val in rows:
            r = tk.Frame(sys_frame, bg=C_BG)
            r.pack(fill="x", pady=1)
            tk.Label(r, text=f"{lbl} :", fg=C_MUTED, bg=C_BG,
                     font=("Segoe UI", 9), width=14, anchor="e").pack(side="left")
            tk.Label(r, text=val, fg=C_TEXT, bg=C_BG,
                     font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)

        bf = tk.Frame(body, bg=C_BG)
        bf.pack(fill="x", side="bottom", pady=(8, 0))
        _btn(bf, "Annuler", master.destroy, bg="#bdc3c7", fg=C_TEXT).pack(side="right", padx=(8, 0))
        _btn(bf, "Suivant  ▶", master._show_folder, bold=True).pack(side="right")

# ---------------------------------------------------------------------------
# Page 2 : Dossier d'installation
# ---------------------------------------------------------------------------
class FolderPage(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=C_BG)
        self._master = master
        Header(self, 2).pack(fill="x")
        body = tk.Frame(self, bg=C_BG, padx=30, pady=18)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Choisissez le dossier d'installation",
                 fg=C_TEXT, bg=C_BG,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))
        tk.Label(body,
                 text="FILERS sera installe dans le dossier ci-dessous.\n"
                      "Vous pouvez le modifier en cliquant sur Parcourir.",
                 fg=C_MUTED, bg=C_BG, justify="left",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 16))

        # Champ dossier
        folder_frame = tk.LabelFrame(body, text="Dossier d'installation",
                                     bg=C_BG, fg=C_TEXT,
                                     font=("Segoe UI", 9, "bold"),
                                     padx=10, pady=10)
        folder_frame.pack(fill="x", pady=(0, 12))

        row = tk.Frame(folder_frame, bg=C_BG)
        row.pack(fill="x")
        self._entry = tk.Entry(row, textvariable=master.install_dir,
                               font=("Segoe UI", 10), relief="solid", bd=1)
        self._entry.pack(side="left", fill="x", expand=True, ipady=4)
        tk.Button(row, text="Parcourir…", command=self._browse,
                  bg="#ecf0f1", fg=C_TEXT, relief="flat",
                  font=("Segoe UI", 9), padx=10, pady=4,
                  cursor="hand2").pack(side="left", padx=(6, 0))

        # Infos espace disque
        self._space_frame = tk.Frame(folder_frame, bg=C_BG)
        self._space_frame.pack(fill="x", pady=(8, 0))
        self._space_lbl = tk.Label(self._space_frame, text="",
                                   fg=C_MUTED, bg=C_BG,
                                   font=("Segoe UI", 9))
        self._space_lbl.pack(anchor="w")
        master.install_dir.trace_add("write", lambda *_: self._update_space())
        self._update_space()

        # Option raccourci bureau
        opt_frame = tk.LabelFrame(body, text="Options",
                                  bg=C_BG, fg=C_TEXT,
                                  font=("Segoe UI", 9, "bold"),
                                  padx=10, pady=8)
        opt_frame.pack(fill="x", pady=(0, 12))
        tk.Checkbutton(opt_frame, text="Creer un raccourci sur le Bureau",
                       variable=master.shortcut,
                       bg=C_BG, fg=C_TEXT, activebackground=C_BG,
                       font=("Segoe UI", 10)).pack(anchor="w")

        # Apercu
        self._preview_lbl = tk.Label(body, text="", fg=C_MUTED, bg=C_BG,
                                     font=("Courier New", 8), justify="left")
        self._preview_lbl.pack(anchor="w", pady=(0, 8))
        master.install_dir.trace_add("write", lambda *_: self._update_preview())
        self._update_preview()

        bf = tk.Frame(body, bg=C_BG)
        bf.pack(fill="x", side="bottom")
        _btn(bf, "Annuler", master.destroy, bg="#bdc3c7", fg=C_TEXT).pack(side="right", padx=(8, 0))
        _btn(bf, "Installer  ▶", self._start, bold=True).pack(side="right")
        _btn(bf, "◀ Retour", master._show_welcome, bg="#ecf0f1", fg=C_TEXT).pack(side="left")

    def _browse(self):
        d = filedialog.askdirectory(title="Choisir le dossier d'installation",
                                    initialdir=self._master.install_dir.get())
        if d:
            self._master.install_dir.set(os.path.normpath(d))

    def _update_space(self):
        path = self._master.install_dir.get()
        free = free_space(path)
        required = REQUIRED_MB * 1024 * 1024
        color = C_SUCCESS if free >= required else C_ERROR
        self._space_lbl.configure(
            text=f"Espace libre : {fmt_bytes(free)}   —   Requis : {fmt_bytes(required)}",
            fg=color
        )

    def _update_preview(self):
        d = self._master.install_dir.get()
        txt = (
            f"{d}\\\n"
            f"  filers\\        (sources)\n"
            f"  FILERS.bat     (lanceur)\n"
        )
        self._preview_lbl.configure(text=txt)

    def _start(self):
        d = self._master.install_dir.get().strip()
        if not d:
            messagebox.showerror("Erreur", "Veuillez choisir un dossier d'installation.")
            return
        free = free_space(d)
        if free < REQUIRED_MB * 1024 * 1024:
            messagebox.showerror("Espace insuffisant",
                                 f"Espace libre insuffisant dans {d}\n"
                                 f"Requis : {REQUIRED_MB} Mo")
            return
        self._master._show_install()

# ---------------------------------------------------------------------------
# Page 3 : Installation
# ---------------------------------------------------------------------------
class InstallPage(tk.Frame):
    def __init__(self, master):
        super().__init__(master, bg=C_BG)
        self._master = master
        Header(self, 3).pack(fill="x")
        body = tk.Frame(self, bg=C_BG, padx=30, pady=14)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Installation en cours…",
                 fg=C_TEXT, bg=C_BG,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 4))

        self._status_var = tk.StringVar(value="Preparation…")
        tk.Label(body, textvariable=self._status_var,
                 fg=C_ACCENT, bg=C_BG,
                 font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 6))

        total_steps = 2   # copie exe + finalisation
        self._progress = ttk.Progressbar(body, mode="determinate",
                                         maximum=total_steps, length=570)
        self._progress.pack(fill="x", pady=(0, 4))
        self._prog_lbl = tk.Label(body, text="", fg=C_MUTED, bg=C_BG,
                                  font=("Segoe UI", 8))
        self._prog_lbl.pack(anchor="e", pady=(0, 6))

        steps_frame = tk.Frame(body, bg=C_BG)
        steps_frame.pack(fill="x", pady=(0, 6))
        self._step_labels = {}
        all_steps = [
            ("Copie de FILERS.exe", "_copy"),
            ("Raccourci, desinstallateur, registre", "_launcher"),
        ]
        for label, key in all_steps:
            r = tk.Frame(steps_frame, bg=C_BG)
            r.pack(fill="x", pady=1)
            icon = tk.Label(r, text="○", fg=C_MUTED, bg=C_BG,
                            font=("Segoe UI", 10), width=2)
            icon.pack(side="left")
            tk.Label(r, text=label, fg=C_TEXT, bg=C_BG,
                     font=("Segoe UI", 9), width=34, anchor="w").pack(side="left")
            slbl = tk.Label(r, text="En attente", fg=C_MUTED, bg=C_BG,
                            font=("Segoe UI", 9))
            slbl.pack(side="left")
            self._step_labels[key] = (icon, slbl)

        # Log
        log_frame = tk.Frame(body, bg=C_LOG_BG)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))
        self._log = tk.Text(log_frame, bg=C_LOG_BG, fg=C_LOG_FG,
                            font=("Courier New", 8), relief="flat",
                            state="disabled", wrap="word", height=5,
                            padx=8, pady=6)
        sb = tk.Scrollbar(log_frame, command=self._log.yview)
        self._log.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._log.pack(fill="both", expand=True)
        self._log.tag_configure("ok",   foreground="#2ecc71")
        self._log.tag_configure("err",  foreground="#e74c3c")
        self._log.tag_configure("info", foreground="#3498db")

        self._step = 0
        self._total = total_steps
        threading.Thread(target=self._run, daemon=True).start()

    # ---- Helpers thread-safe ----
    def _log_write(self, text: str, tag: str = ""):
        def _do():
            self._log.configure(state="normal")
            self._log.insert("end", text + "\n", tag)
            self._log.see("end")
            self._log.configure(state="disabled")
        self.after(0, _do)

    def _set_status(self, txt: str):
        self.after(0, lambda: self._status_var.set(txt))

    def _set_step(self, key: str, icon: str, color: str, txt: str):
        def _do():
            if key in self._step_labels:
                self._step_labels[key][0].configure(text=icon, fg=color)
                self._step_labels[key][1].configure(text=txt, fg=color)
        self.after(0, _do)

    def _advance(self):
        self._step += 1
        s, t = self._step, self._total
        def _do():
            self._progress["value"] = s
            self._prog_lbl.configure(text=f"Etape {s} / {t}")
        self.after(0, _do)

    # ---- Thread principal ----
    def _run(self):
        install_dir = self._master.install_dir.get()

        # --- 1. Copie de FILERS.exe ---
        self._set_step("_copy", "⟳", C_ACCENT, "Copie…")
        self._set_status("Copie de FILERS.exe…")
        self._log_write(f"Source : {FILERS_EXE_SRC}", "info")
        self._log_write(f"Destination : {install_dir}", "info")

        if not os.path.isfile(FILERS_EXE_SRC):
            msg = f"FILERS.exe introuvable : {FILERS_EXE_SRC}"
            self._set_step("_copy", "✘", C_ERROR, "Source introuvable")
            self._log_write(f"[ERREUR] {msg}", "err")
            self.after(0, lambda: self._master._show_done(False, msg))
            return

        try:
            os.makedirs(install_dir, exist_ok=True)
            dst_exe = os.path.join(install_dir, "FILERS.exe")
            shutil.copy2(FILERS_EXE_SRC, dst_exe)
            size_mo = os.path.getsize(dst_exe) / (1024 * 1024)
            self._set_step("_copy", "✔", C_SUCCESS, "Copie terminee")
            self._log_write(f"[OK] FILERS.exe copie ({size_mo:.1f} Mo).", "ok")
        except Exception as e:
            self._set_step("_copy", "✘", C_ERROR, "Echec")
            self._log_write(f"[ERREUR] {e}", "err")
            self.after(0, lambda: self._master._show_done(False, f"Echec de la copie :\n{e}"))
            return
        self._advance()

        # --- 2. Raccourci, desinstallateur, registre ---
        self._set_step("_launcher", "⟳", C_ACCENT, "Creation…")
        self._set_status("Finalisation…")
        try:
            vbs = create_uninstall_vbs(install_dir)
            self._log_write(f"[OK] Desinstallateur : {vbs}", "ok")
            if self._master.shortcut.get():
                create_shortcut(install_dir)
                self._log_write("[OK] Raccourci bureau cree.", "ok")
            register_uninstall(install_dir)
            self._log_write("[OK] Entre dans Programmes et fonctionnalites.", "ok")
            self._set_step("_launcher", "✔", C_SUCCESS, "OK")
        except Exception as e:
            self._set_step("_launcher", "⚠", C_WARN, "Avertissement")
            self._log_write(f"[WARN] {e}")
        self._advance()

        self.after(0, lambda: self._master._show_done(True, ""))

# ---------------------------------------------------------------------------
# Page 4 : Terminé
# ---------------------------------------------------------------------------
class DonePage(tk.Frame):
    def __init__(self, master, success: bool, message: str):
        super().__init__(master, bg=C_BG)
        Header(self, 4).pack(fill="x")
        body = tk.Frame(self, bg=C_BG, padx=30, pady=24)
        body.pack(fill="both", expand=True)

        install_dir = master.install_dir.get()

        if success:
            banner_bg, banner_fg = "#eafaf1", C_SUCCESS
            icon  = "✔"
            title = "Installation reussie !"
            sub   = (f"FILERS a ete installe dans :\n{install_dir}\n\n"
                     "Cliquez sur Lancer FILERS pour demarrer l'application.")
        else:
            banner_bg, banner_fg = "#fdedec", C_ERROR
            icon  = "✘"
            title = "Echec de l'installation"
            sub   = message

        banner = tk.Frame(body, bg=banner_bg, padx=16, pady=14)
        banner.pack(fill="x", pady=(0, 18))
        tk.Label(banner, text=icon, fg=banner_fg, bg=banner_bg,
                 font=("Segoe UI", 30)).pack(side="left", padx=(0, 14))
        right = tk.Frame(banner, bg=banner_bg)
        right.pack(side="left", fill="x", expand=True)
        tk.Label(right, text=title, fg=banner_fg, bg=banner_bg,
                 font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x")
        tk.Label(right, text=sub, fg=C_TEXT, bg=banner_bg,
                 font=("Segoe UI", 9), justify="left",
                 anchor="w", wraplength=420).pack(fill="x")

        if success:
            recap = tk.LabelFrame(body, text="Resume", bg=C_BG, fg=C_TEXT,
                                  font=("Segoe UI", 9, "bold"), padx=10, pady=8)
            recap.pack(fill="x", pady=(0, 18))
            rows = [
                ("Dossier",     install_dir),
                ("Executable",  os.path.join(install_dir, "FILERS.exe")),
                ("Raccourci",   "Bureau cree" if master.shortcut.get() else "Non cree"),
            ]
            for lbl, val in rows:
                r = tk.Frame(recap, bg=C_BG)
                r.pack(fill="x", pady=1)
                tk.Label(r, text=f"{lbl} :", fg=C_MUTED, bg=C_BG,
                         font=("Segoe UI", 9), width=12, anchor="e").pack(side="left")
                tk.Label(r, text=val, fg=C_TEXT, bg=C_BG,
                         font=("Segoe UI", 9, "bold"),
                         wraplength=380, justify="left").pack(side="left", padx=6)

        bf = tk.Frame(body, bg=C_BG)
        bf.pack(fill="x", side="bottom")
        _btn(bf, "Fermer", master.destroy, bg="#bdc3c7", fg=C_TEXT).pack(side="right", padx=(8, 0))
        if success:
            def _launch():
                launch_filers(install_dir)
                master.destroy()
            _btn(bf, "Lancer FILERS  ▶", _launch, bg=C_SUCCESS, bold=True).pack(side="right")
        else:
            _btn(bf, "◀ Reessayer", master._show_folder, bg=C_ACCENT, bold=True).pack(side="right")

# ---------------------------------------------------------------------------
# Entree
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
