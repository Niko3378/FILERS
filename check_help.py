import re
path = r'C:\IA\Projet6 - FILERS\filers\ui\help_viewer.py'
with open(path, 'rb') as f:
    raw = f.read()

remaining = re.findall(b'\xc3\x83\xc2[\x80-\xbf]', raw)
print(f'Mojibake restants : {len(remaining)}')

text = raw.decode('utf-8')
print(f'Fichier UTF-8 valide : {len(text)} caracteres')

checks = [
    'a gauche', 'a droite', 'Editeur', 'Apercu',
    'Masquer les identiques', 'mise en veille',
    'Modifie', 'Gauche seul', 'Droite seul',
]
for w in checks:
    found = w.lower() in text.lower()
    status = 'OK' if found else 'MANQUANT'
    print(f'  [{status}] {w}')
