"""Draw the CipherScope insignia at runtime; no bundled font or binary asset required."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap


def make_icon() -> QIcon:
    pix = QPixmap(128, 128)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#162323"))
    p.setPen(QPen(QColor("#a5cfad"), 5))
    p.drawRoundedRect(QRectF(6, 6, 116, 116), 17, 17)
    p.setPen(QPen(QColor("#526d59"), 1))
    for x in range(20, 110, 15):
        p.drawLine(x, 19, x, 109)
    for y in range(20, 110, 15):
        p.drawLine(19, y, 109, y)
    p.setPen(QPen(QColor("#ffd29b"), 5))
    p.drawArc(QRectF(25, 25, 78, 78), 46 * 16, 264 * 16)
    p.setPen(QColor("#b5ffca"))
    font = QFont("Consolas", 26, QFont.Weight.Bold)
    p.setFont(font)
    p.drawText(QRectF(15, 28, 98, 66), Qt.AlignmentFlag.AlignCenter, "CS")
    p.setBrush(QColor("#ffd29b"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(QRectF(97, 21, 11, 11))
    p.end()
    return QIcon(pix)
