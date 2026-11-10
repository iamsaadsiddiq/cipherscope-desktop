"""Launch the native Qt application."""
import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication
    from cipherscope.ui.main import MainWindow
    from cipherscope.ui.theme import apply_theme
    from cipherscope.ui.icon import make_icon

    app = QApplication(sys.argv)
    app.setApplicationName("CipherScope")
    app.setOrganizationName("CipherScope")
    apply_theme(app)
    app.setWindowIcon(make_icon())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
