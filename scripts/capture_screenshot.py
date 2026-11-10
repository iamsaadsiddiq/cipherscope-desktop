"""Capture a real app screenshot for local documentation (requires a Qt display)."""
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtWidgets import QApplication
from cipherscope.ui.icon import make_icon
from cipherscope.ui.main import MainWindow
from cipherscope.ui.theme import apply_theme

app = QApplication([])
apply_theme(app)
app.setWindowIcon(make_icon())
window = MainWindow()
window.show()
app.processEvents()
out = Path("screenshots/cipherscope-overview.png")
out.parent.mkdir(parents=True, exist_ok=True)
if not window.grab().save(str(out)):
    raise SystemExit("Unable to save screenshot")
print(f"Saved {out}")
window.close()
