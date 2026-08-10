# CHANGELOG — FILERS

Tous les changements notables de ce projet sont documentés ici.
Format : [version/date] — description.

---

## [1.1.0] — 2026-08-10

### Maintenance
- Rebuild de `Files Manager.exe` et `FILERS_1.1.0.msi` avec les sources v1.1.0.
- Version WiX (`FILERS.wxs`) mise à jour de 1.0.0 à 1.1.0.
- Ancien `FILERS_1.0.0_Finale.msi` supprimé du dépôt.
- `*.wixpdb` ajouté au `.gitignore`.

### Nouvelles fonctionnalités
- **Mode sombre** : bascule via **Ctrl+Shift+D** ou menu Affichage → Mode sombre. Thème Catppuccin Mocha (fond `#1e1e2e`, accent `#89b4fa`). Préférence sauvegardée et restaurée au démarrage.
- **Persistance de session** : au redémarrage, l'application restaure l'onglet actif, les fichiers ouverts dans l'éditeur, les tailles des splitters horizontal et vertical, les chemins des panneaux et l'état des fichiers cachés.
- **Synchronisation de dossiers** : boutons "Sync Gauche → Droite" et "Sync Droite → Gauche" dans la vue de comparaison. Mode miroir optionnel (supprime les fichiers en trop dans la destination). Progression en temps réel, bouton Annuler, relance automatique de la comparaison après sync.
- **Tri des colonnes** : tri correct sur toutes les colonnes — Taille par octets réels, Modifié chronologiquement, Nom/Type/Droits alphabétiquement insensible à la casse. Clic sur l'en-tête pour trier, second clic pour inverser.
- **Sélection multiple** : Ctrl+A pour tout sélectionner, Suppr pour supprimer la sélection, barre de statut affichant le nombre et la taille totale des éléments sélectionnés. Menu contextuel adaptatif (Renommer et Droits masqués en multi-sélection, Basculer caché et Copier/Déplacer appliqués à toute la sélection).
- **Comparaison des droits/permissions** : la comparaison de dossiers peut désormais comparer les permissions NTFS (ACL) en plus du contenu. Les fichiers dont les droits diffèrent apparaissent avec le statut « Droits diff. » (⚑).
- **Export CSV enrichi** : lorsque la comparaison des droits est activée, le rapport CSV inclut deux colonnes supplémentaires « Droits gauche » et « Droits droite ».

### Corrections
- **Crash au démarrage** : le raccourci Ctrl+A référençait `_tree` avant sa création — corrigé avec une lambda différée.
- **Navigation distante** : après connexion FTP/SFTP/SMB via ConnectWorker, le provider est maintenant correctement transmis au panneau actif (`set_provider()`), rendant la navigation distante fonctionnelle.
- **Opérations fichiers distantes** : création de dossier, renommage, suppression et menu contextuel adaptent désormais leur comportement selon le type de provider (local vs distant).
- **Jointure de chemins distants** : utilisation d'un helper `_path_join()` pour éviter les séparateurs Windows (`\`) sur les chemins distants qui attendent `/`.

---

## [1.0.1] — 2026-07-10

### Améliorations
- **Barre de recherche (éditeur de texte)** : touche Échap pour fermer, délai anti-rebond sur la saisie, libellé allégé.
- **Double-clic** : les images et PDF s'ouvrent dans le panneau de prévisualisation intégré ; les autres fichiers sont ouverts avec l'application par défaut du système.
- **Dialogue de don** : affiché au maximum une fois par jour, après 10 minutes d'utilisation.

### Corrections
- **Fuites mémoire workers** : les threads QThread sont correctement détruits après usage ; vérification de recherche redondante supprimée.
- **Recherche récursive** : les résultats sont maintenant diffusés progressivement par lots de 50 au lieu d'attendre la fin complète.
- **Export PDF** : utilisation de `QTextDocument` pour l'impression, éliminant le flash d'interface visible précédemment.

### Maintenance
- Artefacts de build, anciennes versions et scripts ponctuels supprimés du dépôt.
- README mis à jour avec l'ensemble des fonctionnalités actuelles.
- Rebuild de l'exécutable et du MSI avec toutes les corrections de juillet 2026.

---

## [1.0.0] — 2026-06-20

### Version initiale (release finale)

#### Fonctionnalités principales
- Gestionnaire de fichiers dual-panel avec arbre de navigation latéral.
- Copie/déplacement entre panneaux (F5/F6) avec progression granulaire et gestion des conflits.
- Favoris, filtre, recherche récursive, corbeille, glisser-déposer.
- Connexion distante : FTP, SFTP (paramiko), SMB (pysmb) via dialogue dédié.
- Éditeur de texte multi-onglets avec coloration syntaxique (Python, JS/TS, HTML/CSS) et barre de recherche/remplacement.
- Visionneuse de différences côte à côte (difflib) avec synchronisation du défilement.
- Comparaison de dossiers avec statuts : identique, modifié, gauche seul, droite seul, type différent.
- Panneau de prévisualisation : images (zoom), PDF page à page (PyMuPDF), texte avec encodage automatique (chardet).
- Dialogue de droits NTFS : permissions Unix, ACL DACL éditable, changement de propriétaire.
- Support des chemins longs Windows (> 260 caractères) via préfixe `\\?\`.
- Manuel d'aide intégré avec export PDF.
- Persistance des paramètres (`%APPDATA%\Files Manager\settings.json`).

#### Corrections pré-release
- Export PDF : utilisation du browser visible puis passage à `QTextDocument`.
- Menu de désinstallation MSI corrigé.
- Encodage du manuel d'aide corrigé.

---

*Mis à jour le 2026-08-10.*
