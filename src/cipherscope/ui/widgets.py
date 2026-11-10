"""Reusable native display components; no network, browser engine, or webview."""
from __future__ import annotations

import math
from typing import Iterable

from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
                               QSizePolicy)

from cipherscope.ui.theme import AMBER, MINT, MUTED


def text_label(text: str, role: str = "muted") -> QLabel:
    label = QLabel(text)
    label.setObjectName(role)
    label.setWordWrap(True)
    return label


def row(*widgets: QWidget, spacing: int = 10) -> QHBoxLayout:
    layout = QHBoxLayout()
    layout.setSpacing(spacing)
    for widget in widgets:
        layout.addWidget(widget)
    return layout


class Panel(QFrame):
    def __init__(self, title: str, intro: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("panel")
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(18, 15, 18, 17)
        self.body.setSpacing(11)
        label = text_label(f"[ {title.upper()} ]", "sectionTitle")
        self.body.addWidget(label)
        if intro:
            self.body.addWidget(text_label(intro))


class MetricCard(QFrame):
    def __init__(self, label: str, value: str, note: str):
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 13, 15, 13)
        layout.addWidget(text_label(label.upper(), "overline"))
        self.value_label = text_label(value, "metric")
        layout.addWidget(self.value_label)
        layout.addWidget(text_label(note))

    def set_value(self, value: str):
        self.value_label.setText(value)


class Spectrum(QWidget):
    """CRT-inspired animated oscilloscope, decoration only."""
    def __init__(self):
        super().__init__()
        self.setMinimumHeight(160)
        self.phase = 0.0
        timer = QTimer(self)
        timer.timeout.connect(self.advance)
        timer.start(45)

    def advance(self):
        if self.isVisible():
            self.phase += 0.075
            self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#101b1a"))
        w, h = self.width(), self.height()
        painter.setPen(QPen(QColor("#273b32"), 1))
        for x in range(0, w, 24):
            painter.drawLine(x, 0, x, h)
        for y in range(0, h, 20):
            painter.drawLine(0, y, w, y)
        points = []
        for x in range(max(0, w)):
            t = x / max(w, 1) * 9 * math.pi
            wave = math.sin(t + self.phase) * .44 + math.sin(2.7 * t - self.phase * .6) * .19
            wave += math.sin(t * .35 + self.phase * .4) * .13
            points.append((x, int(h / 2 - wave * h * .38)))
        painter.setPen(QPen(QColor("#8fe1a6"), 2))
        for i in range(1, len(points)):
            painter.drawLine(*points[i-1], *points[i])
        painter.setPen(QColor("#9bc3a2"))
        painter.drawText(12, 20, "LIVE  /  CIPHER ENGINE  /  SIGNAL MONITOR")
        painter.drawText(12, h - 10, "VISUAL DECORATION • NOT A SECURITY MEASUREMENT")
        painter.end()


class Histogram(QWidget):
    def __init__(self):
        super().__init__()
        self.data = [0] * 256
        self.setMinimumHeight(155)

    def set_data(self, frequencies: Iterable[int]):
        values = list(frequencies)
        if len(values) != 256:
            raise ValueError("Expected 256 frequencies.")
        self.data = values
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#111c1d"))
        w, h = self.width(), self.height()
        p.setPen(QPen(QColor("#344a43"), 1))
        for n in range(1, 5):
            y = n * h // 5
            p.drawLine(0, y, w, y)
        max_value = max(1, max(self.data))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#85c994"))
        for i, val in enumerate(self.data):
            x = i * (w - 1) / 256
            bar_h = val / max_value * (h - 23)
            p.drawRect(QRectF(x, h - bar_h - 12, max(1, w / 256), bar_h))
        p.setPen(QColor(MUTED))
        p.drawText(5, h - 2, "00")
        p.drawText(w - 28, h - 2, "FF")
        p.end()


class SboxGrid(QWidget):
    def __init__(self):
        super().__init__()
        self.table = list(range(256))
        self.setMinimumSize(370, 380)

    def set_data(self, values: list[int]):
        self.table = values
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#10191a"))
        p.setFont(QFont("Consolas", 9))
        area_w = min(self.width() - 40, 450)
        cell = area_w / 16
        top = 26
        for y in range(16):
            for x in range(16):
                val = self.table[y * 16 + x]
                rect = QRectF(24 + x * cell, top + y * cell, cell - 1, cell - 1)
                p.fillRect(rect, QColor("#243e34") if (x + y) % 2 == 0 else QColor("#1d302e"))
                p.setPen(QColor("#bdf5ce") if val > 127 else QColor("#dfc08c"))
                p.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{val:02X}")
        p.setPen(QColor(MUTED))
        for k in range(16):
            p.drawText(QRectF(24 + k * cell, 0, cell, 22), Qt.AlignmentFlag.AlignCenter, f"{k:X}")
            p.drawText(QRectF(0, top + k * cell, 21, cell), Qt.AlignmentFlag.AlignCenter, f"{k:X}")
        p.end()


class Heatmap(QWidget):
    def __init__(self):
        super().__init__()
        self.values = [[.5] * 8 for _ in range(8)]
        self.setMinimumHeight(220)
        self.setMinimumWidth(260)

    def set_data(self, data: list[list[float]]):
        self.values = data
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#10191a"))
        p.setFont(QFont("Consolas", 9))
        cell = min((self.width() - 42) / 8, (self.height() - 28) / 8)
        for r in range(8):
            for c in range(8):
                deviation = abs(self.values[r][c] - .5) * 2
                # More amber = further from ideal half-bit flip probability.
                p.fillRect(QRectF(27 + c*cell, 23 + r*cell, cell - 2, cell - 2),
                           QColor.fromRgbF(.18 + deviation * .6, .38 - deviation * .12, .28))
                p.setPen(QColor("#e6f6df"))
                p.drawText(QRectF(27+c*cell, 23+r*cell, cell-2, cell-2),
                           Qt.AlignmentFlag.AlignCenter, f"{self.values[r][c]:.2f}")
        p.setPen(QColor(MUTED))
        for i in range(8):
            p.drawText(QRectF(27+i*cell, 0, cell, 20), Qt.AlignmentFlag.AlignCenter, str(i))
            p.drawText(QRectF(0, 23+i*cell, 22, cell), Qt.AlignmentFlag.AlignCenter, str(i))
        p.end()


class ImageView(QLabel):
    def __init__(self, hint: str):
        super().__init__(hint)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(240)
        self.setMinimumWidth(240)
        self.setStyleSheet("background: #111b1d; border: 1px solid #546662; color: #839b95;")
        self._pixmap: QPixmap | None = None

    def set_picture(self, pixmap: QPixmap):
        self._pixmap = pixmap
        self._fit()

    def clear(self):
        self._pixmap = None
        super().clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit()

    def _fit(self):
        if self._pixmap is not None:
            self.setPixmap(self._pixmap.scaled(self.size(),
                                              Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation))
