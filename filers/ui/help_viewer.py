from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser,
    QPushButton, QLineEdit, QLabel, QSplitter, QTreeWidget,
    QTreeWidgetItem, QAbstractItemView, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtPrintSupport import QPrinter


SECTIONS = [
    ("Introduction",               "intro"),
    ("Interface principale",       "interface"),
    ("Arborescence",               "tree"),
    ("  Favoris",                  "favorites"),
    ("Panneau de fichiers",        "files"),
    ("  Filtre et recherche",      "filter"),
    ("  Copie et déplacement",     "copymove"),
    ("  Glisser-déposer",          "dragdrop"),
    ("  Corbeille",                "trash"),
    ("Fichiers cachés",            "hidden"),
    ("Droits et permissions",      "rights"),
    ("Connexion réseau",           "network"),
    ("  SMB / Windows",            "smb"),
    ("  FTP",                      "ftp"),
    ("  SFTP",                     "sftp"),
    ("Éditeur de texte",           "editor"),
    ("  Coloration syntaxique",    "syntax"),
    ("  Recherche / Remplacement", "findreplace"),
    ("Diff — Comparaison",         "diff"),
    ("  Diff texte",               "difftexte"),
    ("  Comparaison dossiers",     "diffdir"),
    ("Aperçu de fichiers",         "apercu"),
    ("Chemins longs",              "longpath"),
    ("  Tester les chemins longs", "longpath-test"),
    ("Raccourcis clavier",         "shortcuts"),
    ("Dépannage",                  "troubleshoot"),
]

# ---------------------------------------------------------------------------
# CSS — écran
# ---------------------------------------------------------------------------
_CSS_SCREEN = """
  body  { font-family: Segoe UI, Arial, sans-serif; font-size: 13px;
          color: #222; margin: 0; padding: 0 24px 40px 24px; background: #fff; }
  h1    { font-size: 20px; color: #2c3e50; border-bottom: 3px solid #3498db;
          padding-bottom: 8px; margin-top: 32px; }
  h2    { font-size: 15px; color: #2980b9; border-left: 4px solid #3498db;
          padding-left: 10px; margin-top: 24px; }
  h3    { font-size: 13px; color: #34495e; margin-top: 16px; font-weight: bold; }
  p     { line-height: 1.7; margin: 8px 0; }
  code  { background: #f0f3f7; border: 1px solid #d5dbe7; border-radius: 3px;
          padding: 1px 5px; font-family: Courier New, monospace; font-size: 12px; }
  pre   { background: #f0f3f7; border: 1px solid #d5dbe7; border-radius: 5px;
          padding: 12px 16px; font-size: 12px;
          font-family: Courier New, monospace; line-height: 1.5;
          white-space: pre-wrap; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  th    { background: #2c3e50; color: white; padding: 8px 12px; text-align: left; }
  td    { padding: 7px 12px; border-bottom: 1px solid #e0e4ec; }
  tr:nth-child(even) td { background: #f7f9fc; }
  .tip  { background: #eafaf1; border-left: 4px solid #2ecc71;
          padding: 10px 14px; border-radius: 3px; margin: 12px 0; }
  .warn { background: #fef9e7; border-left: 4px solid #f39c12;
          padding: 10px 14px; border-radius: 3px; margin: 12px 0; }
  .info { background: #ebf5fb; border-left: 4px solid #3498db;
          padding: 10px 14px; border-radius: 3px; margin: 12px 0; }
  ul    { padding-left: 22px; line-height: 1.8; }
  ol    { padding-left: 22px; line-height: 1.8; }
  li    { margin: 2px 0; }
  a     { color: #2980b9; text-decoration: none; }
  a:hover { text-decoration: underline; }
  .anchor { display: block; position: relative; top: -60px; visibility: hidden; }
  kbd   { background:#ecf0f1; border:1px solid #bdc3c7; border-radius:3px;
          padding:1px 6px; font-family:Courier New,monospace; font-size:11px; }
  .badge { display:inline-block; background:#3498db; color:white;
           border-radius:10px; padding:1px 8px; font-size:11px; }
  .diagram { font-family: Courier New, monospace; font-size: 11px;
             background: #f8f9fb; border: 1px solid #d0d3de; border-radius: 4px;
             padding: 10px 14px; line-height: 1.4; color: #333;
             white-space: pre; }
"""

# ---------------------------------------------------------------------------
# CSS — impression PDF (unités en pt, indépendantes de la résolution écran)
# ---------------------------------------------------------------------------
_CSS_PRINT = """
  body  { font-family: Arial, sans-serif; font-size: 10pt;
          color: #000; margin: 0; padding: 0 10pt 16pt 10pt; background: #fff; }
  h1    { font-size: 14pt; color: #000; border-bottom: 2px solid #000;
          padding-bottom: 4pt; margin-top: 16pt; page-break-after: avoid; }
  h2    { font-size: 12pt; color: #000; border-left: 3px solid #555;
          padding-left: 8pt; margin-top: 12pt; page-break-after: avoid; }
  h3    { font-size: 10pt; color: #000; font-weight: bold; margin-top: 8pt;
          page-break-after: avoid; }
  p     { line-height: 1.5; margin: 5pt 0; }
  code  { background: #f0f0f0; border: 1px solid #ccc;
          padding: 1pt 4pt; font-family: Courier New, monospace; font-size: 9pt; }
  pre   { background: #f0f0f0; border: 1px solid #ccc;
          padding: 7pt 10pt; font-size: 9pt;
          font-family: Courier New, monospace; line-height: 1.4;
          page-break-inside: avoid; white-space: pre-wrap; }
  table { border-collapse: collapse; width: 100%; margin: 6pt 0;
          page-break-inside: avoid; }
  th    { background: #ddd; color: #000; padding: 4pt 7pt; text-align: left;
          border: 1px solid #999; font-size: 9pt; }
  td    { padding: 3pt 7pt; border: 1px solid #ccc; font-size: 9pt; }
  tr:nth-child(even) td { background: #f5f5f5; }
  .tip  { border-left: 3px solid #555; padding: 5pt 10pt; margin: 6pt 0; }
  .warn { border-left: 3px solid #999; padding: 5pt 10pt; margin: 6pt 0;
          font-style: italic; }
  .info { border-left: 3px solid #333; padding: 5pt 10pt; margin: 6pt 0; }
  ul    { padding-left: 16pt; line-height: 1.5; }
  ol    { padding-left: 16pt; line-height: 1.5; }
  li    { margin: 1pt 0; }
  a     { color: #000; text-decoration: none; }
  .anchor { display: none; }
  kbd   { background: #eee; border: 1px solid #aaa; border-radius: 2px;
          padding: 1pt 4pt; font-family: Courier New, monospace; font-size: 9pt; }
  .badge { display: inline; font-size: 9pt; font-weight: bold; }
  .diagram { font-family: Courier New, monospace; font-size: 9pt;
             background: #f5f5f5; border: 1px solid #ccc;
             padding: 6pt 10pt; line-height: 1.35; white-space: pre;
             page-break-inside: avoid; }
"""

# ---------------------------------------------------------------------------
# Corps HTML (partagé entre l'affichage écran et le PDF)
# ---------------------------------------------------------------------------
_HTML_BODY = r"""
<h1 id="intro"><span class="anchor" id="a-intro"></span>Files Manager — Notice d'utilisation</h1>
<p>
  <strong>Files Manager</strong> est un gestionnaire de fichiers double panneau pour Windows,
  avec support des partages réseau SMB, FTP et SFTP, un éditeur de texte intégré,
  des outils de comparaison de fichiers et de dossiers, et des fonctions avancées
  comme les favoris, le filtre temps réel, la recherche récursive, la corbeille et
  le glisser-déposer.
</p>
<div class="info">
  <strong>Version :</strong> 1.0.0 &nbsp;|&nbsp;
  <strong>Technologie :</strong> Python 3 + PyQt6 &nbsp;|&nbsp;
  <strong>Plateformes :</strong> Windows (NTFS), Linux, macOS
</div>

<!-- ================================================================== -->
<h1 id="interface"><span class="anchor" id="a-interface"></span>Interface principale</h1>
<p>L'interface est organisée en quatre zones principales :</p>
<table>
  <tr><th>Zone</th><th>Description</th></tr>
  <tr><td><strong>Barre de menus</strong></td><td>Fichier, Affichage, Outils, Aide</td></tr>
  <tr><td><strong>Barre d'outils</strong></td><td>Accès rapide : Copier (F5), Déplacer (F6), Réseau, Aide</td></tr>
  <tr><td><strong>Arborescence</strong> (gauche)</td><td>Navigation dans l'arborescence des disques, dossiers et favoris</td></tr>
  <tr><td><strong>Zone centrale</strong></td><td>Onglets : Fichiers · Diff texte · Comparaison dossiers · Éditeur · Aperçu</td></tr>
</table>

<h2>Disposition générale</h2>
<pre class="diagram">
+-------------------+-----------------------------------------------+
| Barre de menus : Fichier  Affichage  Outils  Aide                  |
+-------------------+-----------------------------------------------+
| Barre d'outils : [F5 Copier ->] [F6 Deplacer ->] [Reseau] [Aide]  |
+-------------------+-----------------------------------------------+
|                   | Onglets: Fichiers | Diff | Dossiers | Editeur  |
|  Arborescence     +-------------------------+---------------------+
|                   |   Panneau GAUCHE        |   Panneau DROIT     |
|  * Favoris        | [<][>][^] C:\Users\...  | [<][>][^] D:\...   |
|    Mon Projet     +-------------------------+---------------------+
|    Backup         | Nom         Taille Date | Nom       Taille   |
|  C:\              | [+] docs      --   ...  | [+] old     --     |
|    Users          | [ ] rapport.docx 42K.. | [ ] a.py   12K     |
|    Windows        | [ ] image.png   5M  .. |                     |
|  D:\              |                         |                     |
+-------------------+-------------------------+---------------------+</pre>

<p>
  L'arborescence de gauche et les deux panneaux de fichiers sont séparés par
  des diviseurs redimensionnables (glissez les barres verticales pour ajuster).
</p>

<!-- ================================================================== -->
<h1 id="tree"><span class="anchor" id="a-tree"></span>Arborescence</h1>
<p>
  Le panneau de gauche affiche l'arborescence complète des disques et dossiers.
  Les dossiers se chargent à la demande (<em>chargement lazy</em>) pour rester rapides
  même sur de grandes arborescences réseau.
</p>
<ul>
  <li><strong>Cliquer</strong> sur un dossier navigue le panneau de fichiers actif vers ce dossier.</li>
  <li><strong>Développer</strong> (flèche ▶) charge les sous-dossiers à la demande.</li>
  <li>Les dossiers cachés apparaissent en grisé quand l'affichage des cachés est activé.</li>
  <li>Les lecteurs réseau mappés (ex : <code>Z:\</code>) apparaissent automatiquement.</li>
</ul>
<div class="tip">Les lecteurs réseau mappés dans Windows apparaissent automatiquement dans l'arborescence (ex : <code>Z:\</code>, <code>Y:\</code>). Pour les partages non mappés, utilisez la connexion réseau (<kbd>Ctrl+N</kbd>).</div>

<!-- ------------------------------------------------------------------ -->
<h2 id="favorites"><span class="anchor" id="a-favorites"></span>Favoris</h2>
<p>
  Les <strong>Favoris</strong> permettent d'épingler vos dossiers les plus utilisés
  en haut de l'arborescence pour y accéder en un clic, sans naviguer dans
  toute l'arborescence.
</p>

<h3>Ajouter un dossier aux favoris</h3>
<ol>
  <li>Dans un panneau de fichiers, naviguez jusqu'au dossier parent contenant le dossier à mettre en favori.</li>
  <li>Clic droit sur le dossier → <strong>★ Ajouter aux favoris</strong>.</li>
  <li>Le dossier apparaît immédiatement dans la section <strong>★ Favoris</strong> (en orange)
    en haut de l'arborescence des deux panneaux.</li>
</ol>

<h3>Accéder à un favori</h3>
<p>
  La section <strong>★ Favoris</strong> s'affiche au-dessus des disques système dans l'arborescence.
  Cliquer sur un favori navigue directement vers ce dossier dans le panneau de fichiers actif.
  Survolez un favori pour voir son chemin complet dans l'infobulle.
</p>

<h3>Retirer un favori</h3>
<p>Dans l'arborescence, clic droit sur le nom du favori → <strong>★ Retirer des favoris</strong>.</p>

<div class="info">
  Les favoris sont conservés entre les sessions dans
  <code>%APPDATA%\Files Manager\settings.json</code>.
  Le nombre maximum de favoris est de 15 (les plus anciens sont supprimés au-delà).
</div>
<div class="tip">
  Utilisez les favoris pour vos dossiers de projets, vos partages réseau fréquents,
  ou tout chemin profond dans lequel vous naviguez régulièrement.
</div>

<!-- ================================================================== -->
<h1 id="files"><span class="anchor" id="a-files"></span>Panneau de fichiers</h1>
<p>
  Files Manager utilise un double panneau (gauche + droite), comme un gestionnaire
  de style <em>Commander</em>. Chaque panneau est indépendant et dispose de sa propre
  barre de navigation, son historique et ses outils.
</p>

<h2>Navigation</h2>
<table>
  <tr><th>Action</th><th>Méthode</th></tr>
  <tr><td>Entrer dans un dossier</td><td>Double-clic sur le dossier</td></tr>
  <tr><td>Remonter d'un niveau</td><td>Bouton <kbd>↑</kbd> ou retour arrière</td></tr>
  <tr><td>Historique avant / arrière</td><td>Boutons <kbd>←</kbd> <kbd>→</kbd></td></tr>
  <tr><td>Saisir un chemin direct</td><td>Écrire dans la barre de chemin + <kbd>Entrée</kbd></td></tr>
  <tr><td>Changer de lecteur</td><td>Menu déroulant des lecteurs (à droite de la barre de chemin)</td></tr>
  <tr><td>Actualiser le contenu</td><td><kbd>F5</kbd> (sans sélection) ou bouton "Actualiser"</td></tr>
</table>

<h2>Colonnes affichées</h2>
<table>
  <tr><th>Colonne</th><th>Description</th></tr>
  <tr><td>Nom</td><td>Nom du fichier ou dossier (dossiers en gras)</td></tr>
  <tr><td>Taille</td><td>Taille en o / Ko / Mo / Go (vide pour les dossiers)</td></tr>
  <tr><td>Type</td><td>Extension ou "Dossier"</td></tr>
  <tr><td>Modifié</td><td>Date et heure de dernière modification</td></tr>
  <tr><td>Droits</td><td>Mode Unix (ex : <code>-rwxr-xr-x</code>)</td></tr>
</table>

<h2>Sélection multiple</h2>
<ul>
  <li><kbd>Ctrl+Clic</kbd> — ajoute / retire un élément de la sélection</li>
  <li><kbd>Shift+Clic</kbd> — sélectionne une plage d'éléments</li>
  <li><kbd>Ctrl+A</kbd> — sélectionne tout le contenu du panneau</li>
</ul>

<h2>Menu contextuel (clic droit)</h2>
<ul>
  <li><strong>Ouvrir</strong> — ouvre avec l'application associée Windows</li>
  <li><strong>Ouvrir dans l'éditeur</strong> — ouvre dans l'éditeur Files Manager</li>
  <li><strong>Comparer (diff)</strong> — compare deux fichiers sélectionnés côte à côte</li>
  <li><strong>Nouveau dossier</strong> — crée un sous-dossier dans le dossier courant</li>
  <li><strong>Renommer</strong> — renomme le fichier ou dossier sélectionné</li>
  <li><strong>Supprimer (Corbeille)</strong> — envoie à la Corbeille Windows (récupérable)</li>
  <li><strong>Supprimer définitivement</strong> — suppression immédiate sans passage par la corbeille</li>
  <li><strong>★ Ajouter aux favoris</strong> — épingle un dossier dans la section Favoris</li>
  <li><strong>Droits / Permissions</strong> — affiche les droits et ACL NTFS détaillés</li>
  <li><strong>Basculer caché</strong> — masque ou démasque l'élément (attribut Windows)</li>
</ul>

<!-- ------------------------------------------------------------------ -->
<h2 id="filter"><span class="anchor" id="a-filter"></span>Filtre et recherche</h2>
<p>
  La barre de filtre permet de trouver rapidement des fichiers dans le dossier
  courant ou dans toute l'arborescence sous-jacente, sans quitter le panneau.
</p>

<h3>Ouvrir / fermer la barre de filtre</h3>
<p>
  Appuyez sur <kbd>Ctrl+F</kbd> dans n'importe quel panneau de fichiers
  pour afficher ou masquer la barre de filtre. Elle s'affiche sous la barre
  de navigation du panneau.
</p>

<h3>Filtre temps réel (dossier courant)</h3>
<ul>
  <li>Tapez une partie du nom de fichier — la liste se met à jour <strong>en temps réel</strong> à chaque touche.</li>
  <li>La recherche est <strong>insensible à la casse</strong> et porte sur tout le nom du fichier.</li>
  <li>Exemple : taper <code>rapport</code> affiche <em>Rapport_2024.docx</em>, <em>rapport_final.pdf</em>, etc.</li>
  <li>Effacer le champ restaure immédiatement l'affichage normal.</li>
  <li>Appuyez sur <kbd>Échap</kbd> ou cliquez <strong>✕</strong> pour fermer la barre.</li>
</ul>

<h3>Recherche récursive (sous-dossiers)</h3>
<ol>
  <li>Ouvrez la barre de filtre (<kbd>Ctrl+F</kbd>).</li>
  <li>Cochez la case <strong>Sous-dossiers</strong>.</li>
  <li>Tapez le terme à rechercher, puis appuyez sur <kbd>Entrée</kbd> ou cliquez <strong>Chercher</strong>.</li>
  <li>La recherche s'effectue en arrière-plan et affiche les résultats au fur et à mesure.</li>
  <li>Un bandeau en haut du panneau indique : <em>Résultats de recherche pour : terme</em>.</li>
  <li>Chaque résultat affiche le nom du fichier et son chemin relatif.</li>
  <li>Cliquez <strong>← Retour</strong> (dans le bandeau) pour revenir à l'affichage normal.</li>
</ol>

<div class="tip">
  La recherche récursive explore tous les sous-dossiers du dossier courant.
  Elle fonctionne aussi sur les partages réseau SMB, FTP et SFTP, mais peut être
  plus lente selon la bande passante.
</div>
<div class="tip">
  La recherche est toujours une recherche <em>contient</em> : <code>conf</code>
  correspond à <em>config.ini</em>, <em>interface_conf.py</em>, <em>CONF_2024.xlsx</em>, etc.
</div>

<!-- ------------------------------------------------------------------ -->
<h2 id="copymove"><span class="anchor" id="a-copymove"></span>Copie et déplacement entre panneaux</h2>
<p>
  Files Manager permet de copier ou déplacer des fichiers et dossiers directement
  entre le panneau gauche et le panneau droit, avec gestion des chemins longs
  et détection des conflits de noms.
</p>

<h3>Procédure pas à pas</h3>
<ol>
  <li>Dans le <strong>panneau source</strong>, sélectionnez les fichiers / dossiers
    (sélection multiple avec <kbd>Ctrl</kbd> ou <kbd>Shift</kbd>).</li>
  <li>Dans le <strong>panneau destination</strong> (l'autre panneau), naviguez
    jusqu'au dossier cible.</li>
  <li>Lancez l'opération depuis le panneau source :</li>
</ol>

<table>
  <tr><th>Opération</th><th>Raccourci</th><th>Bouton barre d'outils</th></tr>
  <tr><td>Copier vers le panneau opposé</td><td><kbd>F5</kbd></td><td>F5 Copier →</td></tr>
  <tr><td>Déplacer vers le panneau opposé</td><td><kbd>F6</kbd></td><td>F6 Déplacer →</td></tr>
</table>

<div class="info">
  <strong>Copier</strong> conserve les fichiers sources ; <strong>Déplacer</strong> les supprime
  de la source après transfert réussi.
</div>

<h3>Gestion des conflits de noms</h3>
<p>
  Si un fichier de même nom existe déjà dans le dossier de destination, une boîte
  de dialogue s'affiche pour chaque conflit :
</p>
<table>
  <tr><th>Option</th><th>Effet</th></tr>
  <tr><td><strong>Écraser</strong></td><td>Remplace le fichier existant par la nouvelle version</td></tr>
  <tr><td><strong>Renommer</strong></td><td>Copie avec un suffixe numérique automatique (<em>fichier_2.txt</em>, <em>fichier_3.txt</em>…)</td></tr>
  <tr><td><strong>Ignorer</strong></td><td>Ignore ce fichier et continue avec les suivants</td></tr>
  <tr><td><strong>Annuler</strong></td><td>Interrompt toute l'opération immédiatement</td></tr>
</table>

<h3>Barre de progression</h3>
<p>
  Pour les opérations longues, une barre de progression s'affiche indiquant
  le fichier en cours et l'avancement global (0–100 %).
  Cliquez <strong>Annuler</strong> dans la barre pour interrompre l'opération à tout moment.
  Les fichiers déjà copiés avant l'annulation restent dans la destination.
</p>

<div class="tip">
  Pour copier un seul fichier rapidement : sélectionnez-le, appuyez sur <kbd>F5</kbd>,
  et la copie s'effectue instantanément si aucun conflit n'existe.
</div>
<div class="info">
  Toutes les opérations de copie et de déplacement utilisent le préfixe
  <code>\\?\</code> en interne pour gérer sans erreur les chemins dépassant
  260 caractères (limite MAX_PATH de Windows).
</div>

<!-- ------------------------------------------------------------------ -->
<h2 id="dragdrop"><span class="anchor" id="a-dragdrop"></span>Glisser-déposer</h2>
<p>
  Les fichiers peuvent être déplacés entre les panneaux ou depuis l'Explorateur Windows
  par glisser-déposer (drag &amp; drop).
</p>

<h3>Glisser depuis Files Manager vers Files Manager</h3>
<ol>
  <li>Sélectionnez un ou plusieurs fichiers dans un panneau.</li>
  <li>Maintenez le bouton gauche de la souris et faites glisser vers l'autre panneau.</li>
  <li>Relâchez sur la zone de liste de l'autre panneau.</li>
  <li>Les fichiers sont <strong>copiés</strong> dans le dossier courant du panneau de destination.</li>
</ol>

<h3>Glisser depuis l'Explorateur Windows</h3>
<p>
  Les panneaux de Files Manager acceptent les fichiers glissés depuis l'Explorateur
  Windows ou tout autre gestionnaire de fichiers compatible. Les fichiers sont copiés
  dans le dossier affiché dans le panneau de réception.
</p>

<table>
  <tr><th>Source du glisser</th><th>Destination</th><th>Opération</th></tr>
  <tr><td>Panneau gauche</td><td>Panneau droit</td><td>Copie vers le dossier courant du panneau droit</td></tr>
  <tr><td>Panneau droit</td><td>Panneau gauche</td><td>Copie vers le dossier courant du panneau gauche</td></tr>
  <tr><td>Explorateur Windows</td><td>N'importe quel panneau</td><td>Copie vers le dossier affiché</td></tr>
</table>

<div class="tip">
  Le glisser-déposer effectue toujours une <strong>copie</strong> (les fichiers sources
  ne sont pas supprimés). Pour déplacer, utilisez <kbd>F6</kbd> après avoir sélectionné
  les fichiers.
</div>

<!-- ------------------------------------------------------------------ -->
<h2 id="trash"><span class="anchor" id="a-trash"></span>Corbeille Windows</h2>
<p>
  Files Manager propose deux modes de suppression : la suppression vers la corbeille
  (récupérable) et la suppression définitive (immédiate et irrécupérable).
</p>

<table>
  <tr><th>Action</th><th>Méthode</th><th>Récupérable ?</th></tr>
  <tr><td><strong>Supprimer (Corbeille)</strong></td>
      <td>Clic droit → Supprimer (Corbeille) ou touche <kbd>Suppr</kbd></td>
      <td>Oui — via la Corbeille Windows</td></tr>
  <tr><td><strong>Suppression définitive</strong></td>
      <td>Clic droit → Supprimer définitivement</td>
      <td>Non — irrécupérable</td></tr>
</table>

<h3>Fonctionnement de la corbeille</h3>
<ul>
  <li>La suppression vers la corbeille utilise l'API Windows <code>SHFileOperationW</code>,
    le même mécanisme que l'Explorateur Windows.</li>
  <li>Les fichiers déplacés vers la corbeille peuvent être restaurés depuis la
    Corbeille Windows (icône sur le Bureau ou dans l'Explorateur).</li>
  <li>Les dossiers entiers (avec tout leur contenu) peuvent être envoyés à la corbeille
    en une seule opération.</li>
  <li>La corbeille fonctionne sur toutes les partitions NTFS locales (C:\, D:\, etc.).</li>
</ul>

<h3>Limitations</h3>
<ul>
  <li>Sur les <strong>partages réseau SMB</strong> : la corbeille n'est pas disponible.
    La suppression est alors définitive même avec "Supprimer (Corbeille)".</li>
  <li>Sur les connexions <strong>FTP / SFTP</strong> : la suppression est toujours définitive.</li>
</ul>

<div class="warn">
  <strong>Supprimer définitivement</strong> ne peut pas être annulé et ne passe pas
  par la corbeille. Utilisez cette option uniquement pour des fichiers temporaires
  ou dont vous êtes certain de ne plus avoir besoin.
</div>

<!-- ================================================================== -->
<h1 id="hidden"><span class="anchor" id="a-hidden"></span>Fichiers cachés</h1>
<p>Par défaut, les fichiers et dossiers cachés ne sont pas affichés.</p>
<ul>
  <li>Activer / désactiver : menu <strong>Affichage → Fichiers cachés</strong> ou <kbd>Ctrl+H</kbd></li>
  <li>Sur Windows, les fichiers avec l'attribut <em>Hidden</em> sont masqués.</li>
  <li>Sur Linux / macOS, les fichiers dont le nom commence par <code>.</code> sont masqués.</li>
  <li>Les éléments cachés visibles apparaissent en <span style="color:#aaa">grisé</span> dans la liste.</li>
</ul>
<div class="tip">
  Utilisez le clic droit → <strong>Basculer caché</strong> pour modifier l'attribut caché
  d'un fichier ou dossier directement depuis Files Manager, sans passer par les propriétés Windows.
</div>

<!-- ================================================================== -->
<h1 id="rights"><span class="anchor" id="a-rights"></span>Droits et permissions</h1>
<p>
  Clic droit sur un fichier → <strong>Droits / Permissions</strong> ouvre la fenêtre de détail
  des droits et de la sécurité NTFS.
</p>

<h2>Informations affichées</h2>
<table>
  <tr><th>Information</th><th>Description</th></tr>
  <tr><td>Mode Unix</td><td>Ex : <code>-rwxr-xr--</code> — type + droits propriétaire / groupe / autres</td></tr>
  <tr><td>Propriétaire</td><td>Compte propriétaire (DOMAINE\Utilisateur sur Windows)</td></tr>
  <tr><td>Lecture / Écriture / Exécution</td><td>Accès effectif du processus courant</td></tr>
  <tr><td>ACL NTFS</td><td>Liste des entrées de contrôle d'accès Windows (Allow / Deny)</td></tr>
</table>

<h2>Lecture du mode Unix</h2>
<pre>-  r w x  r - x  r - -
^  ^^^^^  ^^^^^  ^^^^^
|  user   group  other
type</pre>
<ul>
  <li><code>-</code> fichier ordinaire &nbsp; <code>d</code> dossier &nbsp; <code>l</code> lien symbolique</li>
  <li><code>r</code> lecture &nbsp; <code>w</code> écriture &nbsp; <code>x</code> exécution &nbsp; <code>-</code> droit absent</li>
</ul>
<div class="warn">
  L'affichage des ACL NTFS nécessite le module <code>pywin32</code>.
  Sans lui, seuls les droits Unix et l'accès effectif sont affichés.
  Installez-le avec : <code>pip install pywin32</code>
</div>

<!-- ================================================================== -->
<h1 id="network"><span class="anchor" id="a-network"></span>Connexion réseau</h1>
<p>
  Files Manager supporte trois protocoles réseau : <strong>SMB</strong> (partages Windows),
  <strong>FTP</strong> et <strong>SFTP</strong>.
</p>
<p>Ouvrir la fenêtre de connexion : menu <strong>Fichier → Connexion réseau…</strong>
  ou <kbd>Ctrl+N</kbd> ou bouton <strong>Réseau…</strong> dans la barre d'outils.</p>
<p>
  Les hôtes récemment utilisés sont mémorisés dans les champs déroulants :
  cliquez la flèche du champ Hôte pour sélectionner une connexion précédente.
</p>

<h2 id="smb"><span class="anchor" id="a-smb"></span>SMB / Partages Windows</h2>
<table>
  <tr><th>Champ</th><th>Description</th><th>Exemple</th></tr>
  <tr><td>Hôte</td><td>Nom du serveur ou adresse IP</td><td><code>serveur</code> ou <code>192.168.1.10</code></td></tr>
  <tr><td>Partage</td><td>Nom du partage réseau</td><td><code>Documents</code></td></tr>
  <tr><td>Utilisateur</td><td>Compte Windows (laisser vide pour anonyme)</td><td><code>jean.dupont</code></td></tr>
  <tr><td>Mot de passe</td><td>Mot de passe du compte</td><td></td></tr>
  <tr><td>Domaine</td><td>Domaine Active Directory (optionnel)</td><td><code>ENTREPRISE</code></td></tr>
  <tr><td>Port</td><td>445 (direct TCP) ou 139 (NetBIOS)</td><td><code>445</code></td></tr>
</table>
<div class="tip">
  Utilisez le champ <strong>UNC</strong> pour coller directement un chemin
  <code>\\serveur\partage</code>, puis cliquez <strong>Parser</strong> pour
  remplir les champs automatiquement.
</div>

<h2 id="ftp"><span class="anchor" id="a-ftp"></span>FTP</h2>
<table>
  <tr><th>Champ</th><th>Description</th><th>Défaut</th></tr>
  <tr><td>Hôte</td><td>Serveur FTP</td><td></td></tr>
  <tr><td>Utilisateur</td><td>Compte FTP</td><td><code>anonymous</code></td></tr>
  <tr><td>Mot de passe</td><td>Mot de passe (vide pour anonyme)</td><td>(vide)</td></tr>
  <tr><td>Port</td><td>Port FTP</td><td><code>21</code></td></tr>
</table>

<h2 id="sftp"><span class="anchor" id="a-sftp"></span>SFTP (SSH)</h2>
<table>
  <tr><th>Champ</th><th>Description</th></tr>
  <tr><td>Hôte</td><td>Serveur SSH (nom ou IP)</td></tr>
  <tr><td>Utilisateur</td><td>Nom d'utilisateur SSH</td></tr>
  <tr><td>Mot de passe</td><td>Mot de passe (ou laisser vide si authentification par clé)</td></tr>
  <tr><td>Port</td><td>Port SSH (défaut : 22)</td></tr>
  <tr><td>Clé SSH</td><td>Chemin vers une clé privée (.pem, .ppk…) — optionnel</td></tr>
</table>
<div class="tip">
  L'authentification par clé SSH est recommandée pour la sécurité.
  Cliquez <strong>…</strong> pour sélectionner votre fichier de clé privée.
</div>

<!-- ================================================================== -->
<h1 id="editor"><span class="anchor" id="a-editor"></span>Éditeur de texte</h1>
<p>
  L'onglet <strong>Éditeur</strong> offre un éditeur de texte multi-onglets avec
  numéros de ligne et coloration syntaxique. Il peut accueillir plusieurs fichiers
  simultanément dans des onglets distincts.
</p>

<h2>Ouverture d'un fichier</h2>
<ul>
  <li>Double-clic sur un fichier texte dans les panneaux (ouverture automatique)</li>
  <li>Clic droit → <strong>Ouvrir dans l'éditeur</strong></li>
  <li>Menu <strong>Fichier → Ouvrir dans l'éditeur…</strong> ou <kbd>Ctrl+O</kbd></li>
  <li>Bouton <strong>Ouvrir…</strong> dans la barre de l'éditeur</li>
</ul>
<div class="info">
  Si un fichier est déjà ouvert dans l'éditeur, Files Manager y navigue directement
  (onglet existant) au lieu d'en ouvrir un doublon.
</div>

<h2>Gestion des onglets</h2>
<table>
  <tr><th>Action</th><th>Raccourci</th></tr>
  <tr><td>Nouvel onglet vide</td><td><kbd>Ctrl+T</kbd></td></tr>
  <tr><td>Fermer l'onglet courant</td><td><kbd>Ctrl+W</kbd></td></tr>
  <tr><td>Déplacer un onglet</td><td>Glisser-déposer l'onglet</td></tr>
  <tr><td>Enregistrer</td><td><kbd>Ctrl+S</kbd></td></tr>
  <tr><td>Enregistrer sous…</td><td>Bouton "Enreg. sous…" dans la barre</td></tr>
</table>
<div class="warn">
  Un onglet modifié non sauvegardé affiche un <strong>*</strong> avant son nom.
  Fermer un tel onglet ouvre une boîte de dialogue proposant de sauvegarder,
  ignorer les modifications ou annuler la fermeture.
</div>

<h2 id="syntax"><span class="anchor" id="a-syntax"></span>Coloration syntaxique</h2>
<p>La coloration est activée automatiquement selon l'extension du fichier :</p>
<table>
  <tr><th>Langage</th><th>Extensions</th></tr>
  <tr><td>Python</td><td><code>.py</code> <code>.pyw</code></td></tr>
  <tr><td>JavaScript / TypeScript</td><td><code>.js</code> <code>.mjs</code> <code>.ts</code> <code>.jsx</code> <code>.tsx</code></td></tr>
  <tr><td>HTML / XML / SVG</td><td><code>.html</code> <code>.htm</code> <code>.xml</code> <code>.svg</code></td></tr>
  <tr><td>CSS / SCSS / Less</td><td><code>.css</code> <code>.scss</code> <code>.less</code></td></tr>
  <tr><td>Texte brut</td><td>Autres extensions ou sans extension</td></tr>
</table>

<h2 id="findreplace"><span class="anchor" id="a-findreplace"></span>Recherche et remplacement</h2>
<p>Ouvrir la barre de recherche : <kbd>Ctrl+F</kbd> dans l'onglet Éditeur.</p>
<table>
  <tr><th>Option</th><th>Description</th></tr>
  <tr><td><strong>◀ ▶</strong></td><td>Résultat précédent / suivant</td></tr>
  <tr><td><strong>Casse</strong></td><td>Recherche sensible à la casse</td></tr>
  <tr><td><strong>Regex</strong></td><td>Expression régulière (syntaxe Python / PCRE)</td></tr>
  <tr><td><strong>Remplacer</strong></td><td>Remplace l'occurrence actuellement sélectionnée</td></tr>
  <tr><td><strong>Tout remplacer</strong></td><td>Remplace toutes les occurrences dans le fichier courant</td></tr>
</table>
<div class="tip">
  Si du texte est sélectionné avant d'ouvrir la barre, il est pré-rempli dans le champ de recherche.
</div>

<!-- ================================================================== -->
<h1 id="diff"><span class="anchor" id="a-diff"></span>Diff — Comparaison</h1>

<h2 id="difftexte"><span class="anchor" id="a-difftexte"></span>Diff texte (côte à côte)</h2>
<p>
  Compare deux fichiers texte ligne par ligne et affiche les différences en couleur,
  avec les numéros de ligne, dans deux panneaux synchronisés.
</p>
<h3>Ouvrir un diff texte</h3>
<ul>
  <li>Sélectionner un fichier dans le panneau gauche et un fichier dans le panneau droit,
    puis <kbd>Ctrl+D</kbd></li>
  <li>Sélectionner deux fichiers dans le même panneau → clic droit → <strong>Comparer (diff)</strong></li>
  <li>Double-clic sur un fichier "Modifié" dans la comparaison de dossiers</li>
</ul>
<h3>Code couleur</h3>
<table>
  <tr><th>Couleur</th><th>Signification</th></tr>
  <tr><td style="background:#ffc0c0">Rouge</td><td>Ligne supprimée (présente à gauche, absente à droite)</td></tr>
  <tr><td style="background:#e8ffe8">Vert</td><td>Ligne ajoutée (absente à gauche, présente à droite)</td></tr>
  <tr><td style="background:#ffeeba">Jaune</td><td>Ligne modifiée</td></tr>
  <tr><td>Blanc</td><td>Lignes identiques</td></tr>
</table>
<p>Les deux panneaux défilent de façon synchronisée (défilement vertical et horizontal liés).</p>

<h2 id="diffdir"><span class="anchor" id="a-diffdir"></span>Comparaison de dossiers</h2>
<p>
  L'onglet <strong>Comparaison dossiers</strong> compare récursivement le contenu
  de deux répertoires, fichier par fichier, en utilisant leur empreinte MD5.
</p>
<h3>Utilisation</h3>
<ol>
  <li>Saisir ou choisir le <strong>dossier gauche</strong> et le <strong>dossier droit</strong></li>
  <li>Cliquer <strong>Comparer</strong> (la comparaison s'effectue en arrière-plan)</li>
  <li>Les résultats s'affichent dans la liste avec un code couleur et un statut</li>
</ol>
<h3>Statuts possibles</h3>
<table>
  <tr><th>Icône</th><th>Statut</th><th>Couleur</th><th>Description</th></tr>
  <tr><td><code>=</code></td><td>Identique</td><td style="background:#f5f5f5">Gris pâle</td><td>Fichiers identiques (même MD5)</td></tr>
  <tr><td><code>≠</code></td><td>Modifié</td><td style="background:#fff8e1">Ambré</td><td>Fichiers de contenu différent</td></tr>
  <tr><td><code>◄</code></td><td>Gauche seul</td><td style="background:#e3f2fd">Bleu clair</td><td>Présent uniquement dans le dossier gauche</td></tr>
  <tr><td><code>►</code></td><td>Droite seul</td><td style="background:#f3e5f5">Mauve clair</td><td>Présent uniquement dans le dossier droit</td></tr>
  <tr><td><code>!</code></td><td>Type diff.</td><td style="background:#ffebee">Rouge clair</td><td>Fichier d'un côté, dossier de l'autre</td></tr>
</table>
<div class="tip">
  Cochez <strong>Masquer les identiques</strong> pour n'afficher que les différences —
  très utile quand on compare deux partages réseau avec des milliers de fichiers communs.
</div>
<div class="tip">
  Double-cliquez sur un fichier <strong>≠ Modifié</strong> pour ouvrir directement
  le diff texte côte à côte.
</div>
<div class="info">
  Cliquer sur <strong>Diff dossiers</strong> dans la barre d'outils pré-remplit automatiquement
  les chemins avec les dossiers courants des deux panneaux.
</div>

<!-- ================================================================== -->
<h1 id="apercu"><span class="anchor" id="a-apercu"></span>Aperçu de fichiers</h1>
<p>
  L'onglet <strong>Aperçu</strong> affiche automatiquement une prévisualisation
  du fichier sélectionné dans l'un des deux panneaux.
  Il se met à jour à chaque clic sur un fichier.
</p>

<h2>Formats supportés</h2>
<table>
  <tr><th>Catégorie</th><th>Extensions</th><th>Fonctionnalités</th></tr>
  <tr>
    <td><strong>Images</strong></td>
    <td><code>.png</code> <code>.jpg</code> <code>.jpeg</code> <code>.bmp</code>
        <code>.gif</code> <code>.webp</code> <code>.tif</code> <code>.svg</code>
        <code>.ico</code> et autres</td>
    <td>Zoom +/− · Ajuster à la fenêtre · <kbd>Ctrl</kbd>+Molette · Dimensions affichées</td>
  </tr>
  <tr>
    <td><strong>PDF</strong></td>
    <td><code>.pdf</code></td>
    <td>Navigation page par page · Zoom dpi · Rendu haute qualité (PyMuPDF)</td>
  </tr>
  <tr>
    <td>Autres fichiers</td>
    <td>Tous</td>
    <td>Placeholder — pas d'aperçu disponible</td>
  </tr>
</table>

<h2>Utilisation de l'aperçu image</h2>
<table>
  <tr><th>Action</th><th>Méthode</th></tr>
  <tr><td>Afficher un aperçu</td><td>Cliquer sur une image ou un PDF dans les panneaux</td></tr>
  <tr><td>Zoom avant</td><td>Bouton <strong>+</strong> ou <kbd>Ctrl</kbd>+Molette haut</td></tr>
  <tr><td>Zoom arrière</td><td>Bouton <strong>−</strong> ou <kbd>Ctrl</kbd>+Molette bas</td></tr>
  <tr><td>Ajuster à la fenêtre</td><td>Bouton <strong>Ajuster</strong></td></tr>
  <tr><td>Faire défiler</td><td>Molette ou barres de défilement</td></tr>
</table>

<h2>Utilisation de l'aperçu PDF</h2>
<table>
  <tr><th>Action</th><th>Méthode</th></tr>
  <tr><td>Page précédente</td><td>Bouton <strong>◀</strong></td></tr>
  <tr><td>Page suivante</td><td>Bouton <strong>▶</strong></td></tr>
  <tr><td>Aller à une page</td><td>Saisir le numéro dans le champ de page</td></tr>
  <tr><td>Augmenter la résolution</td><td>Bouton <strong>+</strong> (augmente les dpi)</td></tr>
  <tr><td>Diminuer la résolution</td><td>Bouton <strong>−</strong> (diminue les dpi)</td></tr>
</table>

<div class="tip">
  Le rendu PDF est effectué par <strong>PyMuPDF</strong>. Si ce module n'est pas installé,
  un message d'erreur s'affiche dans le panneau. Installez-le avec :
  <code>pip install PyMuPDF</code>
</div>

<!-- ================================================================== -->
<h1 id="longpath"><span class="anchor" id="a-longpath"></span>Chemins longs</h1>

<h2>La limite MAX_PATH de Windows</h2>
<p>
  Windows impose par défaut une limite de <strong>260 caractères</strong> sur la longueur
  totale des chemins de fichiers (<em>MAX_PATH</em>). Au-delà, les opérations standard
  (copie, déplacement, suppression) échouent avec une erreur d'accès ou de fichier introuvable.
</p>
<p>Files Manager contourne cette limite de deux façons complémentaires :</p>
<ul>
  <li><strong>Préfixe <code>\\?\</code></strong> — ajouté automatiquement à tout chemin
    dépassant 248 caractères pour toutes les opérations internes (lecture, écriture,
    copie, déplacement, suppression). Transparent pour l'utilisateur.</li>
  <li><strong>Activation native via le registre</strong> — la clé
    <code>LongPathsEnabled</code> supprime la limite pour tout le système.
    Menu <strong>Outils → Chemins longs Windows…</strong></li>
</ul>

<h2>Indicateurs visuels</h2>
<table>
  <tr><th>Indicateur</th><th>Signification</th></tr>
  <tr><td>Bandeau jaune dans la barre de chemin</td>
      <td>Le chemin courant dépasse 200 caractères</td></tr>
  <tr><td>Fond jaune sur une entrée de la liste</td>
      <td>Le chemin complet de ce fichier / dossier dépasse 248 caractères</td></tr>
  <tr><td>Tooltip sur une entrée jaune</td>
      <td>Affiche le chemin complet et le nombre exact de caractères</td></tr>
</table>

<h2>Dialogue Chemins longs (Outils → Chemins longs Windows…)</h2>
<table>
  <tr><th>Information</th><th>Description</th></tr>
  <tr><td>Plateforme</td><td>Version Windows détectée</td></tr>
  <tr><td>Support <code>\\?\</code> (Files Manager)</td><td>Toujours actif dans Files Manager</td></tr>
  <tr><td>LongPathsEnabled (registre)</td><td>État de la clé système (activée / désactivée)</td></tr>
  <tr><td>Python long paths actifs</td><td>Si Python peut ouvrir des chemins &gt; 260 nativement</td></tr>
</table>
<div class="warn">
  L'activation de <code>LongPathsEnabled</code> nécessite des <strong>droits administrateur</strong>
  et une déconnexion / reconnexion Windows pour prendre pleinement effet.
</div>

<!-- ================================================================== -->
<h2 id="longpath-test"><span class="anchor" id="a-longpath-test"></span>Tester les chemins longs</h2>

<h3>Test 1 — Créer une structure longue</h3>
<p>Dans un terminal Python (depuis le dossier <code>Files Manager/</code>) :</p>
<pre>python -c "
import sys, os
sys.path.insert(0, '.')
from core import long_path_utils as lp

seg = 'nom_de_dossier_tres_long_quarante_car_'
base = r'C:\Temp\TEST_LONG'
parts = [seg + str(i) for i in range(7)]
deep = base + os.sep + os.sep.join(parts)
print('Longueur :', len(deep), 'caracteres')

lp.makedirs(deep)
fpath = os.path.join(deep, 'fichier_long.txt')
with lp.open_file(fpath, 'w', encoding='utf-8') as f:
    f.write('Test chemin long OK\n')

print('Cree :', lp.is_long(fpath), '-- Prefixe :', lp.normalize(fpath)[:12])
print('Abrege :', lp.abbreviate(fpath, 60))
"</pre>
<p>Résultat attendu :</p>
<pre>Longueur : 312 caracteres
Cree : True -- Prefixe : \\?\C:\Temp
Abrege : C:/.../fichier_long.txt</pre>

<h3>Test 2 — Dans l'interface Files Manager</h3>
<ol>
  <li>Naviguez vers <code>C:\Temp\TEST_LONG</code> dans le panneau gauche</li>
  <li>Descendez dans les sous-dossiers jusqu'au niveau 4–5</li>
  <li>Vérifiez l'apparition du <strong>bandeau jaune</strong> dans la barre de chemin</li>
  <li>Vérifiez que <code>fichier_long.txt</code> s'affiche avec un <strong>fond jaune</strong></li>
  <li>Survolez-le : le tooltip affiche le chemin complet et le nombre de caractères</li>
</ol>

<h3>Test 3 — Opérations sur chemin long</h3>
<p>Sélectionnez <code>fichier_long.txt</code>, puis testez depuis le menu contextuel :</p>
<table>
  <tr><th>Opération</th><th>Résultat attendu</th></tr>
  <tr><td>Ouvrir dans l'éditeur</td><td>S'ouvre normalement dans l'onglet Éditeur</td></tr>
  <tr><td>Droits / Permissions</td><td>Affiche les droits sans erreur</td></tr>
  <tr><td>Renommer</td><td>Renomme sans erreur d'accès</td></tr>
  <tr><td>Supprimer</td><td>Supprime sans erreur d'accès</td></tr>
  <tr><td>Copier vers l'autre panneau (F5)</td><td>Copie réussie avec préfixe \\?\</td></tr>
</table>

<h3>Test 4 — Activer le support natif (optionnel)</h3>
<ol>
  <li>Relancez Files Manager <strong>en tant qu'administrateur</strong></li>
  <li>Menu <strong>Outils → Chemins longs Windows…</strong></li>
  <li>Cliquez <strong>Activer LongPathsEnabled dans le registre</strong></li>
  <li>Déconnectez-vous puis reconnectez-vous (ou redémarrez)</li>
  <li>Ouvrez à nouveau le dialogue : <em>LongPathsEnabled : Activé</em></li>
</ol>

<h3>Nettoyage</h3>
<pre>python -c "
import sys
sys.path.insert(0, '.')
from core import long_path_utils as lp
lp.rmtree(r'C:\Temp\TEST_LONG')
print('Nettoyage termine')
"</pre>

<div class="tip">
  Si un chemin long est accessible dans Files Manager mais pas dans l'Explorateur Windows
  ou d'autres applications, c'est normal : seul Files Manager utilise le préfixe <code>\\?\</code>
  en interne. Pour une compatibilité universelle, activez <code>LongPathsEnabled</code>
  dans le registre.
</div>

<!-- ================================================================== -->
<h1 id="shortcuts"><span class="anchor" id="a-shortcuts"></span>Raccourcis clavier</h1>
<table>
  <tr><th>Raccourci</th><th>Action</th></tr>
  <tr><td colspan="2" style="background:#f0f3f7; font-weight:bold; padding-top:8px">Navigation</td></tr>
  <tr><td><kbd>Double-clic</kbd></td><td>Entrer dans un dossier</td></tr>
  <tr><td><kbd>Retour arrière</kbd></td><td>Remonter d'un niveau</td></tr>
  <tr><td><kbd>Ctrl+H</kbd></td><td>Afficher / masquer les fichiers cachés</td></tr>
  <tr><td colspan="2" style="background:#f0f3f7; font-weight:bold; padding-top:8px">Copie et déplacement</td></tr>
  <tr><td><kbd>F5</kbd></td><td>Copier la sélection vers l'autre panneau</td></tr>
  <tr><td><kbd>F6</kbd></td><td>Déplacer la sélection vers l'autre panneau</td></tr>
  <tr><td colspan="2" style="background:#f0f3f7; font-weight:bold; padding-top:8px">Filtre et recherche</td></tr>
  <tr><td><kbd>Ctrl+F</kbd> (dans un panneau)</td><td>Ouvrir / fermer la barre de filtre</td></tr>
  <tr><td><kbd>Entrée</kbd> (barre filtre + Sous-dossiers)</td><td>Lancer la recherche récursive</td></tr>
  <tr><td><kbd>Échap</kbd></td><td>Fermer la barre de filtre</td></tr>
  <tr><td colspan="2" style="background:#f0f3f7; font-weight:bold; padding-top:8px">Suppression</td></tr>
  <tr><td><kbd>Suppr</kbd></td><td>Supprimer vers la Corbeille Windows</td></tr>
  <tr><td colspan="2" style="background:#f0f3f7; font-weight:bold; padding-top:8px">Réseau et diff</td></tr>
  <tr><td><kbd>Ctrl+N</kbd></td><td>Ouvrir la fenêtre de connexion réseau</td></tr>
  <tr><td><kbd>Ctrl+D</kbd></td><td>Comparer les fichiers sélectionnés (diff texte)</td></tr>
  <tr><td colspan="2" style="background:#f0f3f7; font-weight:bold; padding-top:8px">Éditeur</td></tr>
  <tr><td><kbd>Ctrl+T</kbd></td><td>Nouvel onglet éditeur</td></tr>
  <tr><td><kbd>Ctrl+O</kbd></td><td>Ouvrir un fichier dans l'éditeur</td></tr>
  <tr><td><kbd>Ctrl+S</kbd></td><td>Enregistrer le fichier courant</td></tr>
  <tr><td><kbd>Ctrl+W</kbd></td><td>Fermer l'onglet éditeur courant</td></tr>
  <tr><td><kbd>Ctrl+F</kbd> (dans l'éditeur)</td><td>Ouvrir la barre recherche / remplacement</td></tr>
  <tr><td><kbd>Tab</kbd></td><td>Insérer 4 espaces (indentation)</td></tr>
  <tr><td colspan="2" style="background:#f0f3f7; font-weight:bold; padding-top:8px">Application</td></tr>
  <tr><td><kbd>Ctrl+Q</kbd></td><td>Quitter Files Manager</td></tr>
</table>

<!-- ================================================================== -->
<h1 id="troubleshoot"><span class="anchor" id="a-troubleshoot"></span>Dépannage</h1>

<h2>L'application ne démarre pas</h2>
<pre>cd "C:\chemin\vers\Files Manager"
python main.py</pre>
<p>Vérifiez les messages d'erreur dans la console. Assurez-vous que les
dépendances sont installées :</p>
<pre>pip install -r requirements.txt</pre>

<h2>La connexion SMB échoue</h2>
<ul>
  <li>Vérifiez que le partage est accessible depuis Windows (<code>\\serveur\partage</code> dans l'Explorateur)</li>
  <li>Vérifiez le pare-feu : le port 445 doit être ouvert entre votre machine et le serveur</li>
  <li>Essayez le port 139 si 445 est bloqué</li>
  <li>Utilisez l'adresse IP si la résolution de nom DNS / NetBIOS échoue</li>
</ul>

<h2>La connexion SFTP échoue</h2>
<ul>
  <li>Vérifiez que le service SSH est actif sur le serveur</li>
  <li>Testez avec un client SSH : <code>ssh utilisateur@serveur</code></li>
  <li>Si vous utilisez une clé SSH, vérifiez que le format est OpenSSH (pas PuTTY .ppk — convertissez avec PuTTYgen)</li>
</ul>

<h2>Les droits NTFS ne s'affichent pas</h2>
<p>Installez le module <code>pywin32</code> :</p>
<pre>pip install pywin32</pre>

<h2>La corbeille n'est pas disponible sur un partage réseau</h2>
<p>
  La Corbeille Windows ne fonctionne que sur les partitions locales NTFS.
  Sur les partages SMB, FTP et SFTP, la suppression est toujours définitive.
  Vérifiez vos fichiers avant suppression.
</p>

<h2>L'encodage d'un fichier est incorrect</h2>
<p>Files Manager détecte automatiquement l'encodage via <code>chardet</code>.
Pour les fichiers avec encodage inhabituel (EBCDIC, UTF-32…),
la détection peut être imprécise. Sauvegardez une copie avant modification.</p>

<h2>La comparaison de dossiers est lente</h2>
<p>La comparaison utilise le hachage MD5 de chaque fichier, ce qui nécessite
de lire entièrement chaque fichier. Pour de grands dossiers réseau, comparez
un sous-dossier spécifique plutôt que la racine du partage, ou attendez la fin
du chargement (la comparaison s'effectue en arrière-plan).</p>

<h2>Outils → Désactiver la mise en veille</h2>
<p>
  Cette option empêche Windows de mettre l'ordinateur en veille pendant les opérations
  longues (copie, comparaison de grands dossiers). Elle peut être cochée / décochée
  à tout moment depuis le menu <strong>Outils</strong>. Elle est automatiquement
  désactivée à la fermeture de Files Manager.
</p>

</body>
"""


def _make_html(css: str) -> str:
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        f"<style>{css}</style></head>{_HTML_BODY}</html>"
    )


HELP_HTML = _make_html(_CSS_SCREEN)


class HelpViewer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Sommaire
        nav = QWidget()
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(4, 4, 4, 4)
        nav_layout.setSpacing(4)

        nav_lbl = QLabel("Sommaire")
        nav_lbl.setStyleSheet("font-weight: bold; font-size: 13px; padding: 4px;")
        nav_layout.addWidget(nav_lbl)

        self._nav_tree = QTreeWidget()
        self._nav_tree.setHeaderHidden(True)
        self._nav_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._nav_tree.setRootIsDecorated(False)
        self._nav_tree.setStyleSheet("border: 1px solid #d0d3de; background: #fafbfc;")
        self._nav_tree.itemClicked.connect(self._on_nav_click)

        for label, anchor in SECTIONS:
            item = QTreeWidgetItem([label])
            item.setData(0, Qt.ItemDataRole.UserRole, anchor)
            if not label.startswith(" "):
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
            else:
                item.setForeground(0, QColor("#555"))
            self._nav_tree.addTopLevelItem(item)

        nav_layout.addWidget(self._nav_tree)
        splitter.addWidget(nav)

        # Contenu
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        search_bar = QHBoxLayout()
        search_bar.setContentsMargins(6, 4, 6, 4)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Rechercher dans la notice…")
        self._search_edit.textChanged.connect(self._do_search)
        search_bar.addWidget(QLabel("🔍"))
        search_bar.addWidget(self._search_edit)
        pdf_btn = QPushButton("⬇ Exporter PDF")
        pdf_btn.setFixedWidth(130)
        pdf_btn.clicked.connect(self._export_pdf)
        search_bar.addWidget(pdf_btn)

        search_widget = QWidget()
        search_widget.setLayout(search_bar)
        search_widget.setStyleSheet("background: #f5f6fa; border-bottom: 1px solid #ddd;")
        content_layout.addWidget(search_widget)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(False)
        self._browser.setHtml(HELP_HTML)
        self._browser.setStyleSheet("border: none;")
        content_layout.addWidget(self._browser)

        splitter.addWidget(content)
        splitter.setSizes([200, 800])

        layout.addWidget(splitter)

    def _on_nav_click(self, item: QTreeWidgetItem, col: int):
        anchor = item.data(0, Qt.ItemDataRole.UserRole)
        if anchor:
            self._browser.scrollToAnchor(f"a-{anchor}")

    def _export_pdf(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter la notice en PDF",
            "Files_Manager_Notice.pdf",
            "PDF (*.pdf)"
        )
        if not path:
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        # Utilise le browser visible (taille réelle connue de Qt) avec le CSS
        # d'impression — un browser jamais affiché aurait une largeur nulle et
        # tout le contenu serait compressé.
        self._browser.setHtml(_make_html(_CSS_PRINT))
        self._browser.print(printer)
        self._browser.setHtml(HELP_HTML)

    def _do_search(self, text: str):
        if not text:
            self._browser.setHtml(HELP_HTML)
            return
        self._browser.find("")
        self._browser.setHtml(HELP_HTML)
        if text:
            self._browser.find(text)
