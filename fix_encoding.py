import re

path = r'C:\IA\Projet6 - FILERS\filers\ui\help_viewer.py'
with open(path, 'rb') as f:
    raw = f.read()

# Patterns doubles-mojibake a corriger
# c3 83 c2 XX -> c3 XX  (characters à ç è é ê ô etc.)
# c3 82 c2 XX -> c2 XX  (characters non-breaking space, etc.)

fixed = bytearray()
i = 0
corrections = 0
while i < len(raw):
    # Pattern 1: c3 83 c2 [80-bf]
    if (i + 3 < len(raw)
            and raw[i] == 0xc3 and raw[i+1] == 0x83
            and raw[i+2] == 0xc2 and 0x80 <= raw[i+3] <= 0xbf):
        fixed.append(0xc3)
        fixed.append(raw[i+3])
        i += 4
        corrections += 1
    # Pattern 2: c3 82 c2 [80-bf]
    elif (i + 3 < len(raw)
            and raw[i] == 0xc3 and raw[i+1] == 0x82
            and raw[i+2] == 0xc2 and 0x80 <= raw[i+3] <= 0xbf):
        fixed.append(0xc2)
        fixed.append(raw[i+3])
        i += 4
        corrections += 1
    else:
        fixed.append(raw[i])
        i += 1

# Verification: le resultat doit etre du UTF-8 valide
try:
    text = bytes(fixed).decode('utf-8')
    print(f"OK: {corrections} corrections, fichier UTF-8 valide ({len(text)} caracteres)")
    with open(path, 'wb') as f:
        f.write(bytes(fixed))
    print("Fichier sauvegarde.")
    # Verification spot
    idx = text.find('seulement')
    print("Spot check:", repr(text[idx:idx+25]))
except UnicodeDecodeError as e:
    print(f"ERREUR UTF-8: {e}")
