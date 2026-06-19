path = r'C:\IA\Projet6 - FILERS\filers\ui\help_viewer.py'
with open(path, 'r', encoding='utf-8-sig') as f:
    content = f.read()

changes = 0

# 1. Icônes obsolètes dans la table de statuts
old = (
    '<h3>Statuts possibles</h3>\n'
    '<table>\n'
    '  <tr><th>Icône</th><th>Statut</th><th>Description</th></tr>\n'
    '  <tr><td><code>=</code></td><td style="color:#2ecc71">Identique</td><td>Fichiers identiques (même MD5)</td></tr>\n'
    '  <tr><td><code>~</code></td><td style="color:#e67e22">Modifié</td><td>Fichiers différents</td></tr>\n'
    '  <tr><td><code>&lt;</code></td><td style="color:#3498db">Gauche seul</td><td>Présent seulement à gauche</td></tr>\n'
    '  <tr><td><code>&gt;</code></td><td style="color:#9b59b6">Droite seul</td><td>Présent seulement à droite</td></tr>\n'
    '  <tr><td><code>!</code></td><td style="color:#e74c3c">Type diff.</td><td>Fichier d\'un côté, dossier de l\'autre</td></tr>\n'
    '</table>\n'
    '<div class="tip">\n'
    '  Double-cliquez sur un fichier avec le statut <strong>Modifié</strong> pour ouvrir\n'
    '  directement le diff texte côte à côte.\n'
    '</div>'
)
new = (
    '<h3>Statuts possibles</h3>\n'
    '<table>\n'
    '  <tr><th>Icône</th><th>Statut</th><th>Couleur</th><th>Description</th></tr>\n'
    '  <tr><td><code>=</code></td><td>Identique</td>'
        '<td style="background:#f5f5f5">Gris pâle</td>'
        '<td>Fichiers identiques (même MD5)</td></tr>\n'
    '  <tr><td><code>≠</code></td><td>Modifié</td>'
        '<td style="background:#fff8e1">Ambré</td>'
        '<td>Fichiers de contenu différent</td></tr>\n'
    '  <tr><td><code>◄</code></td><td>Gauche seul</td>'
        '<td style="background:#e3f2fd">Bleu clair</td>'
        '<td>Présent uniquement dans le dossier gauche</td></tr>\n'
    '  <tr><td><code>►</code></td><td>Droite seul</td>'
        '<td style="background:#f3e5f5">Mauve clair</td>'
        '<td>Présent uniquement dans le dossier droit</td></tr>\n'
    '  <tr><td><code>!</code></td><td>Type diff.</td>'
        '<td style="background:#ffebee">Rouge clair</td>'
        '<td>Fichier d\'un côté, dossier de l\'autre</td></tr>\n'
    '</table>\n'
    '<div class="tip">\n'
    '  Cochez <strong>Masquer les identiques</strong> pour n\'afficher que les différences —\n'
    '  très utile quand on compare deux partages réseau avec des milliers de fichiers communs.\n'
    '</div>\n'
    '<div class="tip">\n'
    '  Double-cliquez sur un fichier <strong>≠ Modifié</strong> pour ouvrir directement\n'
    '  le diff texte côte à côte.\n'
    '</div>'
)
if old in content:
    content = content.replace(old, new)
    changes += 1
    print('OK: table statuts mise à jour')
else:
    print('ERREUR: table statuts non trouvée')

# 2. Mise en veille dans la table des raccourcis
old2 = '  <tr><td><kbd>Ctrl+Q</kbd></td><td>Quitter Files Manager</td></tr>\n'
new2 = (
    '  <tr><td><kbd>Ctrl+Q</kbd></td><td>Quitter Files Manager</td></tr>\n'
    '  <tr><td colspan="2" style="background:#f0f3f7;font-weight:bold;padding-top:8px">Outils</td></tr>\n'
    '  <tr><td>Outils → Désactiver la mise en veille</td>'
        '<td>Empêche la mise en veille Windows pendant les opérations longues (option à cocher/décocher)</td></tr>\n'
)
if old2 in content:
    content = content.replace(old2, new2)
    changes += 1
    print('OK: mise en veille ajoutée')
else:
    print('ERREUR: ligne Ctrl+Q non trouvée')

# 3. Onglets : ajouter Aperçu
old3 = '<tr><td><strong>Onglets principaux</strong> (droite)</td><td>Fichiers · Diff texte · Comparaison dossiers · Éditeur</td></tr>'
new3 = '<tr><td><strong>Onglets principaux</strong> (droite)</td><td>Fichiers · Diff texte · Comparaison dossiers · Éditeur · Aperçu</td></tr>'
if old3 in content:
    content = content.replace(old3, new3)
    changes += 1
    print('OK: Aperçu ajouté aux onglets')
else:
    print('ERREUR: ligne onglets non trouvée')

# 4. Plateforme : BOM enlevé à l'écriture
with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n{changes} correction(s) appliquée(s). Fichier sauvegardé.')
