import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import List

from core.local_provider import LocalProvider


@dataclass
class InventoryEntry:
    name: str
    path: str
    is_dir: bool
    size: int
    modified: datetime
    extension: str
    owner: str
    is_hidden: bool
    depth: int


def _fmt_size(size: int) -> str:
    if size < 1024:
        return f"{size} o"
    elif size < 1024 ** 2:
        return f"{size / 1024:.1f} Ko"
    elif size < 1024 ** 3:
        return f"{size / 1024 ** 2:.1f} Mo"
    return f"{size / 1024 ** 3:.2f} Go"


def _fmt_date(dt: datetime) -> str:
    if dt == datetime.min:
        return ""
    return dt.strftime("%d/%m/%Y %H:%M")


def collect(folder: str, recursive: bool, show_hidden: bool) -> List[InventoryEntry]:
    provider = LocalProvider(show_hidden=show_hidden)
    results: List[InventoryEntry] = []

    def _scan(path: str, depth: int):
        try:
            entries = provider.list_dir(path)
        except Exception:
            return
        for fe in entries:
            ext = os.path.splitext(fe.name)[1].lower() if not fe.is_dir else ""
            results.append(InventoryEntry(
                name=fe.name,
                path=fe.path,
                is_dir=fe.is_dir,
                size=fe.size,
                modified=fe.modified,
                extension=ext,
                owner=fe.owner,
                is_hidden=fe.is_hidden,
                depth=depth,
            ))
            if fe.is_dir and recursive:
                _scan(fe.path, depth + 1)

    _scan(folder, 0)
    if recursive:
        _compute_dir_sizes(results)
    return results


def _compute_dir_sizes(entries: List[InventoryEntry]):
    # index path→entry pour les dossiers présents dans la liste
    dir_map = {e.path: e for e in entries if e.is_dir}
    for e in entries:
        if not e.is_dir:
            parent = os.path.dirname(e.path)
            while parent in dir_map:
                dir_map[parent].size += e.size
                parent = os.path.dirname(parent)


def compute_stats(entries: List[InventoryEntry]) -> dict:
    files = [e for e in entries if not e.is_dir]
    dirs = [e for e in entries if e.is_dir]
    total_size = sum(e.size for e in files)

    ext_counts: dict = {}
    for e in files:
        if e.extension:
            ext_counts[e.extension] = ext_counts.get(e.extension, 0) + 1

    top_ext = sorted(ext_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "files": len(files),
        "dirs": len(dirs),
        "total": len(entries),
        "size": total_size,
        "size_fmt": _fmt_size(total_size),
        "top_ext": top_ext,
    }


_CSS = """
body { font-family: Arial, sans-serif; font-size: 9pt; margin: 20pt; }
h2 { font-size: 13pt; color: #1565c0; margin-bottom: 4pt; }
.meta { color: #666; font-size: 8pt; margin-bottom: 12pt; }
table { border-collapse: collapse; width: 100%; }
th { background: #1565c0; color: white; padding: 5pt 8pt; text-align: left; font-size: 8.5pt; }
td { padding: 4pt 8pt; border-bottom: 1px solid #e0e0e0; font-size: 8pt; }
tr:nth-child(even) td { background: #f5f7fa; }
.dir { font-weight: bold; color: #1565c0; }
.stats { margin-top: 14pt; padding: 8pt; background: #f0f4ff; border-left: 3px solid #1565c0;
         font-size: 8.5pt; }
.ext-chip { display: inline-block; background: #e3f2fd; color: #0d47a1;
            padding: 1pt 5pt; border-radius: 3pt; margin: 1pt; }
"""


def analyze_disk_space(entries: List[InventoryEntry], top_n: int = 20) -> dict:
    files = [e for e in entries if not e.is_dir]
    dirs  = [e for e in entries if e.is_dir]
    total_size = sum(e.size for e in files)

    ext_map: dict = {}
    for e in files:
        key = e.extension if e.extension else "(aucune)"
        rec = ext_map.setdefault(key, {"count": 0, "size": 0})
        rec["count"] += 1
        rec["size"]  += e.size

    by_ext = sorted(
        [
            {
                "ext":      k,
                "count":    v["count"],
                "size":     v["size"],
                "size_fmt": _fmt_size(v["size"]),
                "pct":      v["size"] / total_size * 100 if total_size else 0.0,
            }
            for k, v in ext_map.items()
        ],
        key=lambda x: x["size"],
        reverse=True,
    )

    return {
        "total_size":     total_size,
        "total_size_fmt": _fmt_size(total_size),
        "total_files":    len(files),
        "total_dirs":     len(dirs),
        "top_files":      sorted(files, key=lambda e: e.size, reverse=True)[:top_n],
        "top_dirs":       sorted(dirs,  key=lambda e: e.size, reverse=True)[:top_n],
        "by_extension":   by_ext,
    }


def diskspace_to_csv(analysis: dict, path: str):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Extension", "Nb fichiers", "Taille", "Pourcentage"])
        for r in analysis["by_extension"]:
            writer.writerow([r["ext"], r["count"], r["size_fmt"], f"{r['pct']:.1f}%"])


_CSS_DS = _CSS + """
.section-title { font-size: 11pt; color: #1565c0; margin: 14pt 0 4pt 0;
                 border-bottom: 1px solid #1565c0; }
.bar-wrap { background: #e0e0e0; border-radius: 3pt; height: 8pt; width: 150pt;
            display: inline-block; vertical-align: middle; }
.bar-fill { background: #1565c0; border-radius: 3pt; height: 8pt; display: inline-block; }
"""


def diskspace_to_html(analysis: dict, folder: str) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    def file_rows(entries):
        rows = []
        for e in entries:
            rows.append(
                f"<tr><td>{_esc(e.name)}</td>"
                f"<td style='text-align:right'>{_fmt_size(e.size)}</td>"
                f"<td style='color:#888;font-size:7.5pt'>{_esc(e.path)}</td></tr>"
            )
        return "".join(rows)

    ext_rows = []
    for r in analysis["by_extension"]:
        w = max(1, int(r["pct"] * 1.5))
        ext_rows.append(
            f"<tr><td><b>{_esc(r['ext'])}</b></td>"
            f"<td style='text-align:right'>{r['count']}</td>"
            f"<td style='text-align:right'>{r['size_fmt']}</td>"
            f"<td>"
            f"<span class='bar-wrap'><span class='bar-fill' style='width:{w}pt'></span></span>"
            f"&nbsp;{r['pct']:.1f}%"
            f"</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_CSS_DS}</style></head>
<body>
<h2>Analyse d'espace disque</h2>
<div class="meta">
  Dossier : <b>{_esc(folder)}</b><br>
  Généré le {now}
</div>
<div class="stats">
  <b>Total :</b> {analysis['total_size_fmt']} ·
  {analysis['total_files']} fichier(s) ·
  {analysis['total_dirs']} dossier(s)
</div>

<p class="section-title">Top fichiers par taille</p>
<table>
  <thead><tr><th>Nom</th><th>Taille</th><th>Chemin</th></tr></thead>
  <tbody>{file_rows(analysis['top_files'])}</tbody>
</table>

<p class="section-title">Top dossiers par taille</p>
<table>
  <thead><tr><th>Nom</th><th>Taille</th><th>Chemin</th></tr></thead>
  <tbody>{file_rows(analysis['top_dirs'])}</tbody>
</table>

<p class="section-title">Répartition par extension</p>
<table>
  <thead><tr><th>Extension</th><th>Nb</th><th>Taille</th><th>Part</th></tr></thead>
  <tbody>{"".join(ext_rows)}</tbody>
</table>
</body></html>"""


def diskspace_to_pdf(analysis: dict, folder: str, path: str):
    from PyQt6.QtPrintSupport import QPrinter
    from PyQt6.QtGui import QTextDocument
    from PyQt6.QtCore import QSizeF

    html = diskspace_to_html(analysis, folder)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    doc = QTextDocument()
    doc.setHtml(html)
    page_rect = printer.pageRect(QPrinter.Unit.Point)
    doc.setPageSize(QSizeF(page_rect.width(), page_rect.height()))
    doc.print(printer)


def to_csv(entries: List[InventoryEntry], path: str):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["Nom", "Type", "Taille", "Date de modification", "Propriétaire", "Profondeur", "Chemin"])
        for e in entries:
            type_label = "Dossier" if e.is_dir else (e.extension.lstrip(".").upper() or "Fichier")
            writer.writerow([
                e.name,
                type_label,
                _fmt_size(e.size),
                _fmt_date(e.modified),
                e.owner,
                e.depth,
                e.path,
            ])


def to_html(entries: List[InventoryEntry], folder: str, stats: dict) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    rows = []
    for e in entries:
        indent = "&nbsp;&nbsp;&nbsp;&nbsp;" * e.depth
        type_label = "Dossier" if e.is_dir else (e.extension.lstrip(".").upper() or "Fichier")
        size_str = _fmt_size(e.size)
        cls = ' class="dir"' if e.is_dir else ""
        rows.append(
            f"<tr>"
            f"<td{cls}>{indent}{_esc(e.name)}</td>"
            f"<td>{type_label}</td>"
            f"<td style='text-align:right'>{size_str}</td>"
            f"<td>{_fmt_date(e.modified)}</td>"
            f"<td>{_esc(e.owner)}</td>"
            f"</tr>"
        )

    ext_chips = "".join(
        f'<span class="ext-chip">{_esc(ext)} ({n})</span>'
        for ext, n in stats["top_ext"]
    )
    if ext_chips:
        ext_line = f"<br>Extensions fréquentes : {ext_chips}"
    else:
        ext_line = ""

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{_CSS}</style></head>
<body>
<h2>Inventaire de dossier</h2>
<div class="meta">
  Dossier : <b>{_esc(folder)}</b><br>
  Généré le {now}
</div>
<table>
  <thead>
    <tr>
      <th>Nom</th><th>Type</th><th>Taille</th><th>Date de modification</th><th>Propriétaire</th>
    </tr>
  </thead>
  <tbody>
    {"".join(rows)}
  </tbody>
</table>
<div class="stats">
  <b>Résumé :</b> {stats['files']} fichier(s) · {stats['dirs']} dossier(s) · {stats['size_fmt']} total
  {ext_line}
</div>
</body></html>"""


def to_pdf(entries: List[InventoryEntry], folder: str, stats: dict, path: str):
    from PyQt6.QtPrintSupport import QPrinter
    from PyQt6.QtGui import QTextDocument
    from PyQt6.QtCore import QSizeF

    html = to_html(entries, folder, stats)
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    printer.setOutputFileName(path)
    doc = QTextDocument()
    doc.setHtml(html)
    page_rect = printer.pageRect(QPrinter.Unit.Point)
    doc.setPageSize(QSizeF(page_rect.width(), page_rect.height()))
    doc.print(printer)


def _esc(text: str) -> str:
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
