# Files Manager

Gestionnaire de fichiers double panneau pour Windows, développé en Python + PyQt6.

![Python](https://img.shields.io/badge/Python-3.13-blue) ![PyQt6](https://img.shields.io/badge/PyQt6-6.11-green) ![Windows](https://img.shields.io/badge/Windows-10%2F11-blue)

## Fonctionnalités

- **Double panneau** avec navigation indépendante et historique (←/→/↑)
- **Arborescence** de fichiers avec chargement lazy
- **Fichiers cachés** Windows (toggle Ctrl+H)
- **Droits NTFS** et ACL (lecture + modification)
- **Connexions réseau** SMB/FTP/SFTP avec historique des hôtes
- **Diff texte** côte à côte avec coloration et scroll synchronisé
- **Comparaison de dossiers** (MD5) avec worker thread
- **Éditeur de texte** multi-onglets avec coloration syntaxique
- **Aperçu** de fichiers (images, PDF, texte)
- **Chemins longs** Windows (> 260 caractères) avec préfixe `\\?\`
- **Persistance** des préférences : géométrie, derniers chemins, connexions (via `%APPDATA%\Files Manager\settings.json`)

## Prérequis

- Windows 10 / 11
- Python 3.13+

## Installation

```bash
git clone https://github.com/Niko3378/FILERS.git
cd FILERS
pip install -r filers/requirements.txt
```

## Lancement

```bash
python filers/main.py
```

Ou via le script fourni :

```bash
FILERS.bat
```

## Structure

```
filers/
├── main.py                  # Point d'entrée
├── core/
│   ├── local_provider.py    # Fichiers locaux, droits NTFS
│   ├── ftp_provider.py      # FTP et SFTP (paramiko)
│   ├── smb_provider.py      # SMB / partages Windows (pysmb)
│   ├── diff_engine.py       # Diff ligne à ligne et comparaison MD5
│   ├── long_path_utils.py   # Gestion chemins > 260 caractères
│   └── settings.py          # Persistance des préférences (JSON)
└── ui/
    ├── main_window.py        # Fenêtre principale
    ├── file_panel.py         # Panneau fichiers
    ├── tree_panel.py         # Arborescence
    ├── diff_viewer.py        # Visionneur diff
    ├── folder_compare.py     # Comparaison dossiers
    ├── text_editor.py        # Éditeur multi-onglets
    ├── preview_panel.py      # Aperçu fichiers
    ├── connect_dialog.py     # Dialog connexion réseau
    ├── rights_dialog.py      # Dialog droits NTFS
    ├── long_path_dialog.py   # Dialog chemins longs
    ├── help_viewer.py        # Notice d'utilisation
    └── donation_dialog.py    # Dialog don
```

## Raccourcis clavier

| Raccourci | Action |
|---|---|
| `Ctrl+H` | Afficher/masquer les fichiers cachés |
| `Ctrl+N` | Connexion réseau |
| `Ctrl+D` | Comparer les fichiers sélectionnés |
| `Ctrl+T` | Nouvel onglet éditeur |
| `Ctrl+O` | Ouvrir un fichier dans l'éditeur |
| `Ctrl+S` | Enregistrer (éditeur) |
| `F1` | Notice d'utilisation |
| `F5` | Actualiser |

## Build (exécutable Windows)

```bash
build.bat
```

Génère un exécutable standalone via PyInstaller dans `dist/`.
