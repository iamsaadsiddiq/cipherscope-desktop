"""Original dark industrial control-panel styling, inspired by 1990s workstations."""
from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory

BG = "#111718"
PANEL = "#1b2527"
RAISED = "#253134"
EDGE = "#425456"
MINT = "#a7f3c0"
AMBER = "#ffc779"
MUTED = "#8da4a6"

QSS = r"""
QWidget { background: #111718; color: #dce7df; font-family: 'Consolas',
          'DejaVu Sans Mono', 'Liberation Mono', monospace; font-size: 12px; }
QMainWindow, QStackedWidget, QScrollArea, QScrollArea > QWidget > QWidget { background: #111718; }
QFrame#sidebar { background: #172022; border-right: 1px solid #435658; }
QFrame#topbar { background: #202b2c; border-bottom: 2px solid #46595a; }
QFrame#panel { background: #1b2527; border: 1px solid #435557;
                border-top: 2px solid #647879; border-radius: 4px; }
QFrame#card { background: #233032; border: 1px solid #526365;
               border-top: 2px solid #ffc779; border-radius: 3px; }
QLabel#appLogo { color: #b4ffce; font-size: 23px; font-weight: bold; letter-spacing: 2px; }
QLabel#overline { color: #e7b878; font-size: 10px; letter-spacing: 2px; }
QLabel#pageTitle { color: #e3f4e9; font-size: 21px; font-weight: bold; }
QLabel#sectionTitle { color: #ffd299; font-size: 12px; font-weight: bold; }
QLabel#muted { color: #97acaa; }
QLabel#metric { color: #c0ffd5; font-size: 23px; font-weight: bold; }
QLabel#status { color: #a7f3c0; }
QPushButton { color: #e3f5e9; background: #304143; border: 1px solid #6d8582;
              border-top: 2px solid #879d96; border-left: 2px solid #81948d;
              border-radius: 2px; padding: 9px 12px; font-weight: bold; }
QPushButton:hover { background: #3b5350; color: #c0ffd4; border-color: #b0d8bd; }
QPushButton:pressed { background: #151e1d; border-top: 1px solid #526661;
                      border-left: 1px solid #526661; }
QPushButton:disabled { background: #222a2b; color: #6b7f7a; border-color: #405051; }
QPushButton#nav { background: transparent; border: 0px; border-left: 3px solid transparent;
                  text-align: left; padding: 14px 13px; color: #9cb5ac; font-weight: normal; }
QPushButton#nav:hover { color: #d3f7d8; background: #273535; }
QPushButton#nav:checked { color: #c4fbd0; background: #2a3c37;
                          border-left: 3px solid #8cebb0; font-weight: bold; }
QPushButton#primary { background: #3c604e; border-color: #83bd91; color: #f2fff5; }
QPushButton#danger { background: #523c33; border-color: #aa7a55; color: #ffdab1; }
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox { background: #101a1b;
           color: #c0ffd5; selection-background-color: #426c54;
           border: 1px inset #647674; padding: 8px; border-radius: 2px; }
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QComboBox:focus { border: 1px solid #a2f1b7; }
QComboBox::drop-down { border: 0; width: 26px; }
QComboBox QAbstractItemView { background: #1b2527; selection-background-color: #3f5d4d; }
QProgressBar { background: #101718; color: #e0ffe5; border: 1px solid #5a716a;
               border-radius: 0; text-align: center; height: 15px; }
QProgressBar::chunk { background: #6aaf7b; }
QSlider::groove:horizontal { height: 6px; background: #3b4d4b; }
QSlider::handle:horizontal { background: #d3b078; width: 13px; margin: -5px 0; border: 1px solid #ffdb98; }
QToolTip { background: #30403d; color: #f1ffe9; border: 1px solid #8bac8a; }
QScrollBar:vertical { width: 12px; background: #142022; }
QScrollBar::handle:vertical { background: #4d6661; min-height: 24px; }
QSplitter::handle { background: #435254; }
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setFont(QFont("Consolas", 10))
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(BG))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#e0eae2"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#101a1b"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#c2f8d1"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#50775c"))
    palette.setColor(QPalette.ColorRole.Button, QColor(PANEL))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#dce7df"))
    app.setPalette(palette)
    app.setStyleSheet(QSS)
