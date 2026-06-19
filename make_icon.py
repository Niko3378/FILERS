"""Genere filers/icon.ico avec PyQt6. Lance une seule fois."""
import sys
import os
import struct


def create_ico(size_png_list):
    n = len(size_png_list)
    header = struct.pack('<HHH', 0, 1, n)
    offset = 6 + 16 * n
    directory = b''
    data = b''
    for size, png_data in size_png_list:
        w = size if size < 256 else 0
        directory += struct.pack('<BBBBHHII', w, w, 0, 0, 1, 32, len(png_data), offset)
        data += png_data
        offset += len(png_data)
    return header + directory + data


def render_png(size):
    from PyQt6.QtGui import (QPixmap, QPainter, QColor, QFont, QBrush,
                              QPen, QLinearGradient, QRadialGradient)
    from PyQt6.QtCore import Qt, QRectF, QPointF, QBuffer, QIODevice, QRect

    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    m = max(1, size // 16)
    r = size * 0.20
    rect = QRectF(m, m, size - 2*m, size - 2*m)

    # Fond : degrade indigo profond -> bleu marine
    grad = QLinearGradient(QPointF(0, 0), QPointF(size * 0.7, size))
    grad.setColorAt(0.0, QColor("#1a237e"))
    grad.setColorAt(0.6, QColor("#0d2057"))
    grad.setColorAt(1.0, QColor("#07122e"))
    p.setBrush(QBrush(grad))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(rect, r, r)

    # Reflet lumineux central-haut (lumiere chaude)
    glow = QRadialGradient(QPointF(size * 0.5, size * 0.22), size * 0.65)
    glow.setColorAt(0.0, QColor(100, 160, 255, 55))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    p.setBrush(QBrush(glow))
    p.drawRoundedRect(rect, r, r)

    # Deux panneaux semi-transparents (concept double-panneau) - seulement >= 48px
    if size >= 48:
        gap  = size * 0.05
        pw   = (size - 2*m - gap) * 0.44
        ph   = size * 0.30
        py   = m + size * 0.08
        pr2  = max(2, size * 0.06)
        p.setBrush(QBrush(QColor(255, 255, 255, 45)))
        p.drawRoundedRect(QRectF(m + size * 0.04, py, pw, ph), pr2, pr2)
        p.drawRoundedRect(QRectF(m + size * 0.04 + pw + gap, py, pw, ph), pr2, pr2)
    elif size >= 32:
        # Version simplifiee : un seul rectangle suggestif
        p.setBrush(QBrush(QColor(255, 255, 255, 35)))
        p.drawRoundedRect(QRectF(m + size*0.1, m + size*0.08, size*0.8, size*0.28),
                          size*0.05, size*0.05)

    # Barre d'accent cyan en bas
    accent_h = max(2, int(size * 0.065))
    accent_r = min(accent_h * 0.8, r * 0.5)
    p.setBrush(QBrush(QColor("#00bcd4")))
    p.drawRoundedRect(QRectF(m, size - m - accent_h, size - 2*m, accent_h),
                      accent_r, accent_r)

    # Ombre portee du "F" (decalee, sombre)
    fs = max(8, int(size * 0.50))
    font = QFont("Segoe UI", fs, QFont.Weight.Black)
    p.setFont(font)
    shadow_rect = QRect(int(size * 0.06 + size * 0.025), int(size * 0.025),
                        size, int(size * 0.92))
    p.setPen(QPen(QColor(0, 0, 0, 80)))
    p.drawText(shadow_rect,
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
               "F")

    # Lettre F blanche
    text_rect = QRect(int(size * 0.06), 0, size, int(size * 0.92))
    p.setPen(QPen(QColor("#ffffff")))
    p.drawText(text_rect,
               Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
               "F")

    p.end()

    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    pix.save(buf, "PNG")
    return bytes(buf.data())


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)

    out = os.path.join(os.path.dirname(__file__), "filers", "icon.ico")
    sizes = [16, 32, 48, 256]
    images = [(s, render_png(s)) for s in sizes]
    ico = create_ico(images)
    with open(out, "wb") as f:
        f.write(ico)
    print(f"OK : {out}  ({len(ico):,} octets)")
