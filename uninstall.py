"""
FILERS - Desinstallateur
Place dans install_dir\ par l'installateur.
"""
import sys
import os
import subprocess
import tempfile

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    print("tkinter non disponible.")
    sys.exit(1)

INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))
REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\FILERS"

C_BG     = "#f5f6fa"
C_HEADER = "#2c3e50"
C_TEXT   = "#2c3e50"
C_MUTED  = "#7f8c8d"
C_RED    = "#e74c3c"
C_RED2   = "#c0392b"
C_GREY   = "#bdc3c7"


def _remove_registry():
    try:
        import winreg
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, REG_KEY)
    except Exception:
        pass


def _remove_shortcut():
    lnk = os.path.join(os.path.expanduser("~"), "Desktop", "FILERS.lnk")
    try:
        if os.path.exists(lnk):
            os.remove(lnk)
    except Exception:
        pass


def _schedule_delete(path: str):
    """Lance un .bat temporaire qui supprime path apres la sortie de Python."""
    tmp = tempfile.mktemp(suffix=".bat")
    # Normalise les antislashs
    path = path.replace("/", "\\")
    with open(tmp, "w", encoding="ascii") as f:
        f.write(
            "@echo off\r\n"
            "timeout /t 3 /nobreak >nul\r\n"
            f'rd /s /q "{path}"\r\n'
            'del "%~f0"\r\n'
        )
    subprocess.Popen(
        ["cmd", "/c", tmp],
        close_fds=True,
        creationflags=subprocess.CREATE_NO_WINDOW
        if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )


class UninstallApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FILERS — Désinstallation")
        self.geometry("460x260")
        self.resizable(False, False)
        self.configure(bg=C_BG)
        self._build()

    def _build(self):
        # En-tete
        hdr = tk.Frame(self, bg=C_HEADER)
        hdr.pack(fill="x")
        tk.Label(hdr, text="FILERS", fg="white", bg=C_HEADER,
                 font=("Segoe UI", 16, "bold")).pack(side="left", padx=14, pady=10)
        tk.Label(hdr, text="Désinstallation", fg="#95a5a6", bg=C_HEADER,
                 font=("Segoe UI", 9)).pack(side="left")

        body = tk.Frame(self, bg=C_BG, padx=24, pady=16)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Désinstaller FILERS ?",
                 fg=C_TEXT, bg=C_BG,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w")
        tk.Label(body,
                 text="Le dossier suivant et tous ses fichiers seront supprimés :",
                 fg=C_MUTED, bg=C_BG,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(6, 2))

        path_frame = tk.Frame(body, bg="#eaf0fb", padx=8, pady=4)
        path_frame.pack(fill="x", pady=(0, 10))
        tk.Label(path_frame, text=INSTALL_DIR,
                 fg=C_TEXT, bg="#eaf0fb",
                 font=("Courier New", 8), anchor="w").pack(anchor="w")

        tk.Label(body,
                 text="Le raccourci bureau et l’entrée dans Programmes seront aussi retirés.",
                 fg=C_MUTED, bg=C_BG,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 8))

        self._status = tk.StringVar(value="")
        tk.Label(body, textvariable=self._status,
                 fg=C_RED, bg=C_BG,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")

        bf = tk.Frame(body, bg=C_BG)
        bf.pack(fill="x", side="bottom")
        self._btn = tk.Button(
            bf, text="Désinstaller", command=self._run,
            bg=C_RED, fg="white", relief="flat",
            font=("Segoe UI", 10, "bold"), padx=18, pady=6,
            cursor="hand2", activebackground=C_RED2, activeforeground="white")
        self._btn.pack(side="right", padx=(8, 0))
        tk.Button(
            bf, text="Annuler", command=self.destroy,
            bg=C_GREY, fg=C_TEXT, relief="flat",
            font=("Segoe UI", 10), padx=18, pady=6,
            cursor="hand2").pack(side="right")

    def _run(self):
        self._btn.configure(state="disabled")
        self._status.set("Désinstallation en cours…")
        self.update()

        _remove_registry()
        _remove_shortcut()
        _schedule_delete(INSTALL_DIR)

        messagebox.showinfo(
            "FILERS désinstallé",
            "FILERS a été désinstallé avec succès.\n\n"
            "Le dossier d’installation sera supprimé dans quelques secondes.",
        )
        self.destroy()


if __name__ == "__main__":
    UninstallApp().mainloop()
