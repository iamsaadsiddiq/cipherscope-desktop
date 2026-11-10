"""Optional headless rendering smoke test when Qt is installed."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_qt_main_window():
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from cipherscope.ui.main import MainWindow
    from cipherscope.ui.theme import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app)
    window = MainWindow()
    assert window.stack.count() == 8
    window.go(5)
    assert window.stack.currentIndex() == 5
    assert window.current_report.nonlinearity == 112
    window.close()
