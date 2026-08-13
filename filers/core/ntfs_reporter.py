import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

from core import long_path_utils as lp

_ACCESS_DENIED  = 1
_INHERITED_ACE  = 0x10

_MASK_LABELS = [
    (0x001F01FF, "Contrôle total"),
    (0x001301BF, "Modification"),
    (0x001200A9, "Lecture et exécution"),
    (0x001200A0, "Exécution"),
    (0x00120116, "Écriture"),
    (0x00120089, "Lecture"),
    (0x00010000, "Suppression"),
]


def _rights_str(mask: int) -> str:
    for m, label in _MASK_LABELS:
        if (mask & m) == m:
            return label
    parts = []
    if mask & 0x00120089: parts.append("Lecture")
    if mask & 0x00120116: parts.append("Écriture")
    if mask & 0x001200A0: parts.append("Exécution")
    if mask & 0x00010000: parts.append("Suppression")
    return " + ".join(parts) if parts else f"0x{mask:08X}"


@dataclass
class AclEntry:
    path: str
    name: str
    is_dir: bool
    depth: int
    principal: str
    mask: int
    rights: str
    ace_type: str    # "Autoriser" | "Refuser"
    inherited: bool


def _read_acl(path: str, name: str, is_dir: bool, depth: int) -> List[AclEntry]:
    try:
        import win32security
        sd = win32security.GetFileSecurity(
            lp.normalize(path),
            win32security.DACL_SECURITY_INFORMATION,
        )
        dacl = sd.GetSecurityDescriptorDacl()
        if not dacl:
            return []
    except Exception:
        return []

    entries = []
    for i in range(dacl.GetAceCount()):
        try:
            (ace_type_id, ace_flags), mask, sid = dacl.GetAce(i)
            inherited = bool(ace_flags & _INHERITED_ACE)
            try:
                n, domain, _ = win32security.LookupAccountSid(None, sid)
                principal = f"{domain}\\{n}" if domain else n
            except Exception:
                principal = str(sid)
            entries.append(AclEntry(
                path=path, name=name, is_dir=is_dir, depth=depth,
                principal=principal, mask=mask,
                rights=_rights_str(mask),
                ace_type="Refuser" if ace_type_id == _ACCESS_DENIED else "Autoriser",
                inherited=inherited,
            ))
        except Exception:
            continue
    return entries


def collect_paths(folder: str, recursive: bool, include_files: bool) -> list:
    """Returns list of (path, name, is_dir, depth) to process."""
    paths = []

    def _walk(path: str, depth: int):
        name = os.path.basename(path) or path
        paths.append((path, name, True, depth))
        try:
            with os.scandir(path) as it:
                items = sorted(
                    it,
                    key=lambda e: (not e.is_dir(follow_symlinks=False), e.name.lower()),
                )
        except PermissionError:
            return
        for entry in items:
            if entry.is_dir(follow_symlinks=False):
                if recursive:
                    _walk(entry.path, depth + 1)
            elif include_files:
                paths.append((entry.path, entry.name, False, depth + 1))

    _walk(folder, 0)
    return paths


def ntfs_to_csv(entries: List[AclEntry], path: str):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Nom", "Type", "Chemin", "Principal", "Droits", "Accès", "Hérité"])
        for e in entries:
            writer.writerow([
                e.name,
                "Dossier" if e.is_dir else "Fichier",
                e.path,
                e.principal,
                e.rights,
                e.ace_type,
                "Oui" if e.inherited else "Non",
            ])


_CSS = """
body { font-family: Arial, sans-serif; font-size: 9pt; margin: 20pt; }
h2 { font-size: 13pt; color: #1565c0; margin-bottom: 4pt; }
.meta { color: #666; font-size: 8pt; margin-bottom: 12pt; }
table { border-collapse: collapse; width: 100%; }
th { background: #1565c0; color: white; padding: 5pt 8pt; text-align: left; font-size: 8.5pt; }
td { padding: 4pt 8pt; border-bottom: 1px solid #e0e0e0; font-size: 8pt; }
.obj-row td { background: #e8eaf6; font-weight: bold; }
.deny { color: #c62828; font-weight: bold; }
.allow { color: #2e7d32; }
.dir-name { color: #1565c0; }
.inh { color: #aaa; }
.stats { margin-top: 14pt; padding: 8pt; background: #f0f4ff;
         border-left: 3px solid #1565c0; font-size: 8.5pt; }
"""


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def ntfs_to_html(entries: List[AclEntry], folder: str) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    groups: dict = {}
    for e in entries:
        groups.setdefault(e.path, []).append(e)

    rows = []
    for aces in groups.values():
        first = aces[0]
        type_label = "Dossier" if first.is_dir else "Fichier"
        name_cls = "dir-name" if first.is_dir else ""
        rows.append(
            f"<tr class='obj-row'>"
            f"<td colspan='4'>"
            f"<span class='{name_cls}'>{_esc(first.name)}</span>"
            f" <span style='color:#888;font-weight:normal;font-size:7.5pt'>"
            f"— {type_label} — {_esc(first.path)}</span>"
            f"</td></tr>"
        )
        for ace in aces:
            type_cls = "deny" if ace.ace_type == "Refuser" else "allow"
            inh_cls  = "inh" if ace.inherited else ""
            inh_txt  = "Oui" if ace.inherited else "<b>Non</b>"
            rows.append(
                f"<tr class='{inh_cls}'>"
                f"<td style='padding-left:20pt'>{_esc(ace.principal)}</td>"
                f"<td>{_esc(ace.rights)}</td>"
                f"<td class='{type_cls}'>{ace.ace_type}</td>"
                f"<td>{inh_txt}</td>"
                f"</tr>"
            )

    nb_objects = len(groups)
    nb_aces    = len(entries)
    deny_count = sum(1 for e in entries if e.ace_type == "Refuser")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>
<h2>Rapport droits NTFS</h2>
<div class="meta">
  Dossier : <b>{_esc(folder)}</b><br>Généré le {now}
</div>
<div class="stats">
  <b>{nb_objects}</b> objet(s) · <b>{nb_aces}</b> entrée(s) ACL ·
  <span class="deny">{deny_count} refus</span>
</div>
<table>
  <thead>
    <tr><th>Principal</th><th>Droits</th><th>Accès</th><th>Hérité</th></tr>
  </thead>
  <tbody>{"".join(rows)}</tbody>
</table>
</body></html>"""


def ntfs_to_pdf(entries: List[AclEntry], folder: str, path: str):
    from PyQt6.QtPrintSupport import QPrinter
    from PyQt6.QtGui import QTextDocument
    from PyQt6.QtCore import QSizeF

    html = ntfs_to_html(entries, folder)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    doc = QTextDocument()
    doc.setHtml(html)
    page_rect = printer.pageRect(QPrinter.Unit.Point)
    doc.setPageSize(QSizeF(page_rect.width(), page_rect.height()))
    doc.print(printer)
