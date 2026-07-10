# Files Manager

Gestionnaire de fichiers double panneau pour Windows, développé en Python + PyQt6.

![Python](https://img.shields.io/badge/Python-3.13-blue) ![PyQt6](https://img.shields.io/badge/PyQt6-6.11-green) ![Windows](https://img.shields.io/badge/Windows-10%2F11-blue)

## Fonctionnalités

### Navigation et panneaux
- **Double panneau** avec navigation indépendante et historique (←/→/↑)
- **Arborescence** de fichiers avec chargement lazy
- **Favoris** (★) : épingler des dossiers fréquents en haut de l'arborescence
- **Fichiers cachés** Windows (toggle `Ctrl+H`)
- **Indicateurs visuels** pour les chemins longs (> 248 caractères)

### Gestion de fichiers
- **Copie** (`F5`) et **déplacement** (`F6`) entre les deux panneaux
- **Glisser-déposer** entre panneaux et depuis l'Explorateur Windows
- **Corbeille** Windows (`Suppr`) et suppression définitive
- **Filtre temps réel** + **recherche récursive** dans les sous-dossiers (`Ctrl+F`)
- **Double-clic** : texte → éditeur, images/PDF → aperçu, autres → app Windows associée
- **Menu contextuel** complet : ouvrir, renommer, droits, favoris, caché…

### Connexions réseau
- **SMB** (partages Windows), **FTP**, **SFTP** avec historique des hôtes

### Outils intégrés
- **Diff texte** côte à côte avec coloration et scroll synchronisé
- **Comparaison de dossiers** par empreinte MD5 (worker thread)
- **Éditeur de texte** multi-onglets avec coloration syntaxique (Python, JS, HTML, CSS…)
- **Aperçu** d'images (zoom, ajuster) et de PDF (page par page, via PyMuPDF)
- **Droits NTFS** et ACL détaillées
- **Chemins longs** Windows (> 260 caractères) avec préfixe `\\?\`

### Notice d'utilisation
- Manuel intégré accessible via `F1` avec sommaire cliquable et recherche
- Export PDF sans interruption de l'interface (via `QTextDocument`)

### Qualité / UX
- Recherche récursive avec résultats progressifs (lots de 50, pas de blocage UI)
- Persistance : géométrie, derniers chemins, favoris, connexions (`%APPDATA%\Files Manager\settings.json`)
- Dialog de don : une fois par jour au plus, après 10 minutes d'utilisation

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
    ├── file_panel.py         # Panneau fichiers (filtre, recherche, copie, favoris)
    ├── tree_panel.py         # Arborescence
    ├── diff_viewer.py        # Visionneur diff texte
    ├── folder_compare.py     # Comparaison dossiers MD5
    ├── text_editor.py        # Éditeur multi-onglets
    ├── preview_panel.py      # Aperçu images et PDF
    ├── connect_dialog.py     # Dialog connexion réseau
    ├── rights_dialog.py      # Dialog droits NTFS
    ├── long_path_dialog.py   # Dialog chemins longs
    ├── help_viewer.py        # Notice d'utilisation + export PDF
    └── donation_dialog.py    # Dialog don
```

## Raccourcis clavier

| Raccourci | Action |
|---|---|
| `F1` | Notice d'utilisation |
| `F5` | Copier la sélection vers l'autre panneau |
| `F6` | Déplacer la sélection vers l'autre panneau |
| `Suppr` | Envoyer à la Corbeille Windows |
| `Ctrl+H` | Afficher/masquer les fichiers cachés |
| `Ctrl+F` | Ouvrir la barre de filtre/recherche |
| `Ctrl+N` | Connexion réseau |
| `Ctrl+D` | Comparer les fichiers sélectionnés (diff) |
| `Ctrl+T` | Nouvel onglet éditeur |
| `Ctrl+O` | Ouvrir un fichier dans l'éditeur |
| `Ctrl+S` | Enregistrer (éditeur) |
| `Ctrl+W` | Fermer l'onglet éditeur |
| `Ctrl+Q` | Quitter |

## Build (exécutable Windows)

```bash
build.bat
```

Génère `dist/Files Manager.exe` (standalone via PyInstaller) puis `dist/install.exe` (installateur graphique).

Pour générer le MSI, utiliser WiX Toolset avec `FILERS.wxs`.
