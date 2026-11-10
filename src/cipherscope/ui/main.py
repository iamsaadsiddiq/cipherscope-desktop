"""CipherScope: native, offline, retro workstation for cryptographic experiments."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QPixmap, QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox,
    QStackedWidget, QVBoxLayout, QWidget)

from cipherscope import __version__
from cipherscope.core import analysis, sbox, vault
from cipherscope.ui.theme import AMBER, MINT
from cipherscope.ui.widgets import (Heatmap, Histogram, ImageView, MetricCard,
                                     Panel, SboxGrid, Spectrum, text_label)


def button(label: str, primary: bool = False) -> QPushButton:
    widget = QPushButton(label)
    if primary:
        widget.setObjectName("primary")
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    return widget


def action_row(*widgets: QWidget) -> QHBoxLayout:
    box = QHBoxLayout()
    box.setSpacing(10)
    for widget in widgets:
        box.addWidget(widget)
    return box


def page(title: str, caption: str) -> tuple[QScrollArea, QVBoxLayout]:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    inner = QWidget()
    layout = QVBoxLayout(inner)
    layout.setContentsMargins(24, 22, 24, 30)
    layout.setSpacing(17)
    layout.addWidget(text_label("CIPHERSCOPE  /  WORKSTATION SERIES 01", "overline"))
    layout.addWidget(text_label(title, "pageTitle"))
    layout.addWidget(text_label(caption))
    scroll.setWidget(inner)
    return scroll, layout


def field_row(name: str, control: QWidget) -> QHBoxLayout:
    line = QHBoxLayout()
    label = text_label(name, "sectionTitle")
    label.setFixedWidth(110)
    line.addWidget(label)
    line.addWidget(control, 1)
    return line


class FileWorker(QObject):
    progress = Signal(int)
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, action: str, source: str, destination: str, password: str):
        super().__init__()
        self.action, self.source, self.destination = action, source, destination
        self.password = password

    @Slot()
    def run(self):
        try:
            method = vault.encrypt_file if self.action == "encrypt" else vault.decrypt_file
            result = method(self.source, self.destination, self.password,
                            lambda done, total: self.progress.emit(int(100 * done / max(1, total))))
            self.succeeded.emit(str(result))
        except Exception as exc:
            self.failed.emit(str(exc))
        finally:
            self.password = ""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"CipherScope {__version__}  //  Cryptographic Workstation")
        self.resize(1320, 860)
        self.setMinimumSize(1050, 700)
        self._thread: QThread | None = None
        self._worker: FileWorker | None = None
        self.image_data: bytes | None = None
        self.image_envelope: bytes | None = None
        self.sbox_values: list[int] = sbox.aes_sbox()
        self.current_report: sbox.SBoxReport | None = None
        shell = QWidget()
        self.setCentralWidget(shell)
        overall = QVBoxLayout(shell)
        overall.setContentsMargins(0, 0, 0, 0)
        overall.setSpacing(0)

        top = QFrame()
        top.setObjectName("topbar")
        bar = QHBoxLayout(top)
        bar.setContentsMargins(20, 12, 20, 12)
        bar.addWidget(text_label("◈ CIPHERSCOPE", "appLogo"))
        bar.addStretch()
        bar.addWidget(text_label("ENCRYPTION  ◆  CRYPTANALYSIS  ◆  RESEARCH", "overline"))
        overall.addWidget(top)

        middle = QHBoxLayout()
        middle.setContentsMargins(0, 0, 0, 0)
        middle.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        nav = QVBoxLayout(sidebar)
        nav.setContentsMargins(11, 22, 11, 14)
        nav.setSpacing(2)
        nav.addWidget(text_label("// SYSTEM MODULES", "overline"))
        self.nav_items = []
        labels = ("01  OVERVIEW", "02  FILE VAULT", "03  IMAGE LAB", "04  BYTE ANALYZER",
                  "05  AVALANCHE LAB", "06  S-BOX STUDIO", "07  HASH CONSOLE", "08  ABOUT")
        for index, label in enumerate(labels):
            btn = button(label)
            btn.setObjectName("nav")
            btn.setCheckable(True)
            btn.clicked.connect(lambda _checked=False, i=index: self.go(i))
            nav.addWidget(btn)
            self.nav_items.append(btn)
        nav.addStretch()
        nav.addWidget(text_label("● LOCAL ENGINE ONLINE", "status"))
        nav.addWidget(text_label("OFFLINE BY DESIGN\nAES-256-GCM  /  SCRYPT\nWORKSTATION v1.0.0"))
        middle.addWidget(sidebar)

        self.stack = QStackedWidget()
        middle.addWidget(self.stack, 1)
        overall.addLayout(middle, 1)

        self.status = text_label("READY  •  NO NETWORK CONNECTION REQUIRED", "status")
        status_box = QFrame()
        status_box.setObjectName("topbar")
        status_layout = QHBoxLayout(status_box)
        status_layout.setContentsMargins(15, 5, 15, 5)
        status_layout.addWidget(self.status)
        status_layout.addStretch()
        status_layout.addWidget(text_label("CSPRNG  /  AUTHENTICATED CIPHER  /  LOCAL PROCESSING"))
        overall.addWidget(status_box)

        self.stack.addWidget(self.build_overview())
        self.stack.addWidget(self.build_vault())
        self.stack.addWidget(self.build_images())
        self.stack.addWidget(self.build_bytes())
        self.stack.addWidget(self.build_avalanche())
        self.stack.addWidget(self.build_sbox())
        self.stack.addWidget(self.build_hashes())
        self.stack.addWidget(self.build_about())
        self.go(0)

    def go(self, index: int):
        self.stack.setCurrentIndex(index)
        for n, item in enumerate(self.nav_items):
            item.setChecked(n == index)
        self.status.setText(f"MODULE {index + 1:02d} ONLINE  /  LOCAL PROCESSING")

    def _error(self, message: str):
        self.status.setText("ERROR  /  " + message[:120])
        QMessageBox.warning(self, "CipherScope / Operation failed", message)

    def build_overview(self):
        scroll, layout = page("WORKSTATION CONTROL DECK", "An offline encryption and research suite with classic control-panel ergonomics.")
        cards = QHBoxLayout()
        cards.addWidget(MetricCard("Secure file vault", "AES-256", "GCM authenticated encryption"))
        cards.addWidget(MetricCard("Password derivation", "scrypt", "Unique salt for every file"))
        cards.addWidget(MetricCard("S-box laboratory", "8 × 8", "Nonlinearity / DDT / SAC"))
        layout.addLayout(cards)
        scope = Panel("Signal observatory", "Animated retro instrument display; visualization only.")
        scope.body.addWidget(Spectrum())
        layout.addWidget(scope)
        tools = Panel("Quick launch", "Each module is implemented natively; nothing is uploaded to a server.")
        launch = action_row(button("OPEN FILE VAULT  →", True), button("LAUNCH S-BOX STUDIO  →"),
                            button("RUN AVALANCHE LAB  →"))
        launch.itemAt(0).widget().clicked.connect(lambda: self.go(1))
        launch.itemAt(1).widget().clicked.connect(lambda: self.go(5))
        launch.itemAt(2).widget().clicked.connect(lambda: self.go(4))
        tools.body.addLayout(launch)
        tools.body.addWidget(text_label("LAB PROTOCOL  //  Measurements are educational diagnostics, not cryptographic proofs."))
        layout.addWidget(tools)
        layout.addStretch()
        return scroll

    def build_vault(self):
        scroll, layout = page("FILE VAULT  /  AES-256-GCM", "Encrypt and decrypt arbitrary files using a versioned authenticated container format.")
        panel = Panel("Local secure storage", "Files are processed in chunks, and decrypted output is only committed after authentication succeeds.")
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("Select source file...")
        browse = button("BROWSE")
        browse.clicked.connect(self.browse_source)
        panel.body.addLayout(action_row(self.file_path, browse))
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Output filename (must not exist)...")
        browse_out = button("SAVE AS")
        browse_out.clicked.connect(self.browse_output)
        panel.body.addLayout(action_row(self.output_path, browse_out))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Password (minimum 8 characters)")
        panel.body.addWidget(self.password)
        self.vault_progress = QProgressBar()
        self.vault_progress.setValue(0)
        panel.body.addWidget(self.vault_progress)
        self.encrypt_btn, self.decrypt_btn = button("ENCRYPT FILE  →", True), button("←  DECRYPT FILE")
        self.encrypt_btn.clicked.connect(lambda: self.start_file_task("encrypt"))
        self.decrypt_btn.clicked.connect(lambda: self.start_file_task("decrypt"))
        inspect_btn = button("INSPECT HEADER")
        inspect_btn.clicked.connect(self.inspect_file)
        panel.body.addLayout(action_row(self.encrypt_btn, self.decrypt_btn, inspect_btn))
        layout.addWidget(panel)
        info = Panel("Container protocol", "CSCP/1   |   16-byte random salt   |   12-byte random nonce   |   16-byte GCM tag")
        info.body.addWidget(text_label("SECURITY: Header metadata is authenticated as associated data. Files cannot be partially decrypted on bad credentials. Each encryption generates a new nonce and salt. Passwords are never saved."))
        info.body.addWidget(text_label("NOTE: Output files are never overwritten. Use unique output paths. Password length is only a minimum; long, unique passphrases are strongly recommended."))
        layout.addWidget(info)
        layout.addStretch()
        return scroll

    def browse_source(self):
        name, _ = QFileDialog.getOpenFileName(self, "Select file for CipherScope")
        if name:
            self.file_path.setText(name)
            self.output_path.setText(name + ".cscp" if not name.endswith(".cscp") else name[:-5] + ".restored")

    def browse_output(self):
        name, _ = QFileDialog.getSaveFileName(self, "Choose output file")
        if name:
            self.output_path.setText(name)

    def inspect_file(self):
        try:
            with Path(self.file_path.text()).open("rb") as handle:
                details = vault.inspect_header(handle.read(vault.HEADER.size))
            QMessageBox.information(self, "CSCP/1 metadata", "\n".join(f"{k}: {v}" for k, v in details.items()))
        except Exception as exc:
            self._error(str(exc))

    def start_file_task(self, action: str):
        if self._thread is not None and self._thread.isRunning():
            return
        if len(self.password.text()) < 8:
            self._error("Enter a password of at least 8 characters.")
            return
        self.vault_progress.setValue(0)
        self.encrypt_btn.setEnabled(False)
        self.decrypt_btn.setEnabled(False)
        self._thread = QThread(self)
        self._worker = FileWorker(action, self.file_path.text().strip(),
                                  self.output_path.text().strip(), self.password.text())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self.vault_progress.setValue)
        self._worker.succeeded.connect(self.file_success)
        self._worker.failed.connect(self._error)
        self._worker.succeeded.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self.file_finished)
        self.status.setText(f"VAULT  /  {action.upper()} IN PROGRESS")
        self._thread.start()

    def file_success(self, destination: str):
        self.vault_progress.setValue(100)
        self.status.setText("VAULT  /  AUTHENTICATION OK  /  SAVED")
        QMessageBox.information(self, "CipherScope / Complete", f"Successfully saved:\n{destination}")

    def file_finished(self):
        self.encrypt_btn.setEnabled(True)
        self.decrypt_btn.setEnabled(True)
        self.password.clear()
        self._worker = None
        self._thread = None

    def build_images(self):
        scroll, layout = page("IMAGE CRYPTO LAB", "Visualize encrypted image bytes. The static-like preview is SHAKE-derived from ciphertext, not a literal pixel cipher.")
        panel = Panel("Image processing terminal")
        pick = button("LOAD IMAGE", True)
        pick.clicked.connect(self.load_image)
        process = button("ENCRYPT + VISUALIZE")
        process.clicked.connect(self.encrypt_image)
        decrypt = button("VERIFY ROUND TRIP")
        decrypt.clicked.connect(self.verify_image)
        save = button("SAVE .CSCP")
        save.clicked.connect(self.save_image_envelope)
        panel.body.addLayout(action_row(pick, process, decrypt, save))
        self.image_pass = QLineEdit()
        self.image_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.image_pass.setPlaceholderText("Password for image envelope (minimum 8 characters)")
        panel.body.addWidget(self.image_pass)
        previews = QHBoxLayout()
        first, second = QVBoxLayout(), QVBoxLayout()
        self.source_view, self.cipher_view = ImageView("LOAD AN IMAGE TO BEGIN"), ImageView("AWAITING CIPHERTEXT")
        first.addWidget(text_label("PLAIN IMAGE   /   SOURCE", "sectionTitle"))
        first.addWidget(self.source_view, 1)
        second.addWidget(text_label("CIPHERTEXT   /   SYNTHETIC NOISE PREVIEW", "sectionTitle"))
        second.addWidget(self.cipher_view, 1)
        previews.addLayout(first, 1)
        previews.addLayout(second, 1)
        panel.body.addLayout(previews)
        self.image_info = text_label("STATE: No image loaded.")
        panel.body.addWidget(self.image_info)
        layout.addWidget(panel)
        layout.addStretch()
        return scroll

    def load_image(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp *.tif)")
        if not path:
            return
        try:
            with Image.open(path) as file:
                file.load()
                image = file.convert("RGB")
            image.thumbnail((1000, 1000))
            with BytesIO() as buffer:
                image.save(buffer, "PNG")
                self.image_data = buffer.getvalue()
            self.image_envelope = None
            self.source_view.set_picture(self._pixmap(self.image_data))
            self.cipher_view.clear()
            self.cipher_view.setText("READY FOR ENCRYPTION")
            self.image_info.setText(f"SOURCE: {Path(path).name}  /  PREVIEW: {image.width}×{image.height}  /  PNG BYTES: {len(self.image_data):,}")
        except Exception as exc:
            self._error(f"Unable to load image: {exc}")

    @staticmethod
    def _pixmap(blob: bytes) -> QPixmap:
        pix = QPixmap()
        if not pix.loadFromData(blob):
            raise ValueError("Unable to render image.")
        return pix

    def encrypt_image(self):
        if self.image_data is None:
            self._error("Load an image first.")
            return
        try:
            self.image_envelope = vault.encrypt_bytes(self.image_data, self.image_pass.text())
            # Visual representation only, no claim that actual JPEG/PNG pixels were encrypted.
            with Image.open(BytesIO(self.image_data)) as original:
                width, height = original.size
            sample_width = min(420, width)
            sample_height = min(320, height)
            noise = hashlib.shake_256(self.image_envelope[vault.HEADER.size:]).digest(
                sample_width * sample_height * 3)
            picture = Image.frombytes("RGB", (sample_width, sample_height), noise)
            buffer = BytesIO()
            picture.save(buffer, format="PNG")
            self.cipher_view.set_picture(self._pixmap(buffer.getvalue()))
            self.image_info.setText(f"ENCRYPTED: {len(self.image_envelope):,} bytes  /  AES-256-GCM  /  fresh salt + nonce  /  noise preview derived from ciphertext")
            self.status.setText("IMAGE LAB  /  ENCRYPTION COMPLETED")
        except Exception as exc:
            self._error(str(exc))

    def verify_image(self):
        if self.image_envelope is None or self.image_data is None:
            self._error("Encrypt an image first.")
            return
        try:
            recovered = vault.decrypt_bytes(self.image_envelope, self.image_pass.text())
            if recovered != self.image_data:
                raise ValueError("Round-trip mismatch")
            QMessageBox.information(self, "Authenticated image round-trip", "VERIFIED: Recovered image bytes match the original exactly. GCM tag accepted.")
        except Exception as exc:
            self._error(str(exc))

    def save_image_envelope(self):
        if self.image_envelope is None:
            self._error("Encrypt an image first.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save encrypted image", "image.png.cscp", "CipherScope (*.cscp)")
        if path:
            try:
                output = Path(path)
                if output.exists():
                    raise ValueError("Output exists. Select a new filename.")
                output.write_bytes(self.image_envelope)
                self.status.setText("IMAGE LAB  /  ENCRYPTED ENVELOPE SAVED")
            except Exception as exc:
                self._error(str(exc))

    def build_bytes(self):
        scroll, layout = page("BYTE FREQUENCY ANALYZER", "Examine entropy, byte distribution and serial correlation of a bounded local file sample.")
        box = Panel("Input sample", "Up to 8 MiB are analyzed. High entropy alone does not imply secure encryption.")
        self.byte_path = QLineEdit()
        self.byte_path.setPlaceholderText("Choose a local file to analyze...")
        browse = button("SELECT FILE")
        browse.clicked.connect(lambda: self._pick_to(self.byte_path))
        run = button("ANALYZE BYTES", True)
        run.clicked.connect(self.analyze_file)
        box.body.addLayout(action_row(self.byte_path, browse, run))
        metrics = QHBoxLayout()
        self.byte_entropy = MetricCard("Shannon entropy", "--", "bits per byte; maximum 8")
        self.byte_unique = MetricCard("Byte symbols", "--", "out of 256 possible")
        self.byte_corr = MetricCard("Serial correlation", "--", "adjacent-byte Pearson r")
        for card in (self.byte_entropy, self.byte_unique, self.byte_corr):
            metrics.addWidget(card)
        box.body.addLayout(metrics)
        self.byte_graph = Histogram()
        box.body.addWidget(self.byte_graph)
        self.byte_info = text_label("AWAITING SAMPLE  /  Histogram represents 256 byte values.")
        box.body.addWidget(self.byte_info)
        layout.addWidget(box)
        layout.addStretch()
        return scroll

    def _pick_to(self, widget: QLineEdit):
        name, _ = QFileDialog.getOpenFileName(self, "Select data file")
        if name:
            widget.setText(name)

    def analyze_file(self):
        try:
            name = Path(self.byte_path.text())
            with name.open("rb") as file:
                sample = file.read(8 * 1024 * 1024)
            stats = analysis.byte_stats(sample)
            self.byte_entropy.set_value(f"{stats.entropy:.4f}")
            self.byte_unique.set_value(f"{stats.unique_bytes}/256")
            self.byte_corr.set_value(f"{stats.serial_correlation:+.4f}")
            self.byte_graph.set_data(stats.histogram)
            self.byte_info.setText(f"ANALYZED {stats.size:,} BYTES  /  χ² = {stats.chi_square:,.1f}  /  SAMPLE CAP 8 MiB")
        except Exception as exc:
            self._error(str(exc))

    def build_avalanche(self):
        scroll, layout = page("AVALANCHE EFFECT LAB", "Observe how a single input-bit change propagates through one 128-bit AES block.")
        box = Panel("Interactive AES primitive experiment", "Uses a fixed demonstration key for reproducibility, never the file vault key.")
        self.block_hex = QLineEdit("00112233445566778899aabbccddeeff")
        self.block_hex.setPlaceholderText("Exactly 32 hex characters (16 bytes)")
        box.body.addLayout(field_row("INPUT BLOCK", self.block_hex))
        self.bit_slider = QSlider(Qt.Orientation.Horizontal)
        self.bit_slider.setRange(0, 127)
        self.bit_slider.valueChanged.connect(self.single_avalanche)
        self.bit_display = text_label("BIT 000", "sectionTitle")
        box.body.addLayout(action_row(self.bit_slider, self.bit_display))
        self.run_single = button("MEASURE 1-BIT FLIP", True)
        self.run_single.clicked.connect(self.single_avalanche)
        box.body.addWidget(self.run_single)
        self.avalanche_card = MetricCard("Changed output bits", "-- / 128", "Ideal average ≈ 64, not a guaranteed value")
        box.body.addWidget(self.avalanche_card)
        self.avalanche_detail = QPlainTextEdit()
        self.avalanche_detail.setReadOnly(True)
        self.avalanche_detail.setMaximumHeight(125)
        box.body.addWidget(self.avalanche_detail)
        layout.addWidget(box)
        trials = Panel("Statistical repeated trials", "Deterministic simulated inputs for comparisons; experimental AES keys are not used for production encryption.")
        self.trial_count = QSpinBox()
        self.trial_count.setRange(1, 512)
        self.trial_count.setValue(32)
        run_trials = button("RUN TRIALS")
        run_trials.clicked.connect(self.run_avalanche_trials)
        trials.body.addLayout(action_row(self.trial_count, run_trials))
        self.trial_graph = Histogram()
        trials.body.addWidget(self.trial_graph)
        self.trial_result = text_label("Run repeated trials to view Hamming-distance distribution.")
        trials.body.addWidget(self.trial_result)
        layout.addWidget(trials)
        layout.addStretch()
        self.single_avalanche()
        return scroll

    def single_avalanche(self, _value=None):
        bit = self.bit_slider.value()
        self.bit_display.setText(f"BIT {bit:03d}")
        try:
            block = bytes.fromhex(self.block_hex.text())
            result = analysis.avalanche_once(block, bit)
            self.avalanche_card.set_value(f"{result['changed_bits']} / 128")
            self.avalanche_detail.setPlainText("INPUT BIT: " + str(bit) + "\nBASE  : " + result["baseline"] +
                                               "\nFLIPPED: " + result["modified"] +
                                               f"\nOUTPUT DIFFERENCE: {result['percentage']:.2f}%")
        except Exception:
            self.avalanche_card.set_value("INVALID INPUT")
            self.avalanche_detail.setPlainText("Enter exactly 32 hexadecimal characters.")

    def run_avalanche_trials(self):
        try:
            report = analysis.avalanche_trials(self.trial_count.value())
            # 256-bin histogram by mapping possible Hamming distances 0..128 to 0..255.
            bins = [0] * 256
            for distance in report["samples"]:
                bins[distance * 2] += 1
            self.trial_graph.set_data(bins)
            self.trial_result.setText(f"TRIALS {report['trials']}  /  AVERAGE: {report['average_bits']:.2f} / 128 bits  ({report['average_percent']:.2f}%)  /  SEED {report['seed']}")
        except Exception as exc:
            self._error(str(exc))

    def build_sbox(self):
        scroll, layout = page("S-BOX RESEARCH STUDIO", "Inspect 8×8 bijective substitutions, Walsh nonlinearity, differential uniformity and avalanche properties.")
        panel = Panel("Permutation generator", "AES is standardized; Random and Triadic modes are experimental and must never be used to secure files.")
        self.sbox_selector = QComboBox()
        self.sbox_selector.addItems(["AES STANDARD", "SEEDED RANDOM EXPERIMENT", "TRIADIC EXPERIMENT"])
        self.sbox_seed = QSpinBox()
        self.sbox_seed.setRange(0, 999999999)
        self.sbox_seed.setValue(2026)
        recalc = button("GENERATE + EVALUATE", True)
        recalc.clicked.connect(self.refresh_sbox)
        export_json = button("EXPORT JSON")
        export_json.clicked.connect(self.export_sbox_json)
        export_pdf = button("EXPORT PDF")
        export_pdf.clicked.connect(self.export_sbox_pdf)
        panel.body.addLayout(action_row(self.sbox_selector, self.sbox_seed, recalc, export_json, export_pdf))
        cards = QHBoxLayout()
        self.sbox_nonlinear = MetricCard("Nonlinearity", "--", "Minimum component NL")
        self.sbox_du = MetricCard("Differential max", "--", "Smaller is generally preferable")
        self.sbox_sac = MetricCard("SAC mean", "--", "Ideal bit flip probability 0.50")
        for card in (self.sbox_nonlinear, self.sbox_du, self.sbox_sac):
            cards.addWidget(card)
        panel.body.addLayout(cards)
        grids = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(text_label("SUBSTITUTION TABLE  /  HEX", "sectionTitle"))
        self.sbox_grid = SboxGrid()
        left.addWidget(self.sbox_grid)
        right = QVBoxLayout()
        right.addWidget(text_label("STRICT AVALANCHE  /  8 × 8 PROBABILITIES", "sectionTitle"))
        self.sbox_heat = Heatmap()
        right.addWidget(self.sbox_heat)
        right.addWidget(text_label("Rows: flipped input bit  /  Columns: changed output bit"))
        right.addStretch()
        grids.addLayout(left, 3)
        grids.addLayout(right, 2)
        panel.body.addLayout(grids)
        self.sbox_summary = text_label("READY")
        panel.body.addWidget(self.sbox_summary)
        layout.addWidget(panel)
        diff = Panel("Differential distribution probe", "Choose input XOR difference and view the 256 output XOR frequencies (DDT row).")
        self.input_diff = QSpinBox()
        self.input_diff.setRange(1, 255)
        self.input_diff.setValue(1)
        self.input_diff.valueChanged.connect(self.update_ddt)
        diff.body.addLayout(field_row("INPUT Δ", self.input_diff))
        self.diff_hist = Histogram()
        diff.body.addWidget(self.diff_hist)
        self.diff_info = text_label("DDT row")
        diff.body.addWidget(self.diff_info)
        layout.addWidget(diff)
        self.refresh_sbox()
        return scroll

    def refresh_sbox(self):
        try:
            mode = self.sbox_selector.currentIndex()
            seed = self.sbox_seed.value()
            name = ["AES FIPS-197", "Seeded random (experimental)", "Triadic permutation (experimental)"][mode]
            table = [lambda: sbox.aes_sbox(), lambda: sbox.random_sbox(seed),
                     lambda: sbox.triadic_sbox(seed)][mode]()
            report = sbox.evaluate(table, name)
            self.sbox_values = table
            self.current_report = report
            self.sbox_grid.set_data(table)
            self.sbox_heat.set_data(report.sac)
            self.sbox_nonlinear.set_value(str(report.nonlinearity))
            self.sbox_du.set_value(str(report.differential_uniformity))
            self.sbox_sac.set_value(f"{report.sac_mean:.4f}")
            self.sbox_summary.setText(f"{name.upper()}  /  FIXED POINTS {report.fixed_points}  /  MAX SAC DEVIATION {report.sac_max_deviation:.4f}")
            self.update_ddt()
            self.status.setText("S-BOX STUDIO  /  ANALYSIS COMPLETE")
        except Exception as exc:
            self._error(str(exc))

    def update_ddt(self, _value=None):
        counts = sbox.differential_row(self.sbox_values, self.input_diff.value())
        self.diff_hist.set_data(counts)
        self.diff_info.setText(f"ΔIN = 0x{self.input_diff.value():02X}  /  MAX COUNT {max(counts)}  /  NONZERO CELLS {sum(x > 0 for x in counts)}  /  TOTAL {sum(counts)}")

    def _sbox_export_data(self) -> dict:
        if self.current_report is None:
            raise ValueError("No S-box analysis available.")
        return {"application": "CipherScope", "version": __version__,
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "warning": "Experimental S-box metrics are not proofs of cryptographic security.",
                "seed": self.sbox_seed.value(), "report": self.current_report.to_dict()}

    def export_sbox_json(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export research dataset", "sbox-analysis.json", "JSON (*.json)")
        if path:
            try:
                Path(path).write_text(json.dumps(self._sbox_export_data(), indent=2), encoding="utf-8")
                self.status.setText("S-BOX LAB  /  JSON EXPORT COMPLETE")
            except Exception as exc:
                self._error(str(exc))

    def export_sbox_pdf(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export research report", "sbox-report.pdf", "PDF (*.pdf)")
        if path:
            try:
                data = self._sbox_export_data()
                r = data["report"]
                html = ("<h1>CipherScope / S-box Research Report</h1>"
                        f"<p><b>Construction:</b> {r['name']}</p>"
                        f"<p><b>Generated (UTC):</b> {data['generated_utc']}</p>"
                        f"<p><b>Nonlinearity:</b> {r['nonlinearity']}<br>"
                        f"<b>Differential uniformity:</b> {r['differential_uniformity']}<br>"
                        f"<b>Mean SAC:</b> {r['sac_mean']:.6f}<br>"
                        f"<b>Max SAC deviation:</b> {r['sac_max_deviation']:.6f}<br>"
                        f"<b>Fixed points:</b> {r['fixed_points']}</p>"
                        "<h2>Substitution mapping</h2><pre>" +
                        "\n".join(" ".join(f"{n:02X}" for n in r["table"][i:i+16]) for i in range(0,256,16)) +
                        "</pre><h2>Safety</h2><p>Statistical diagnostics are not a security proof. "
                        "Do not use experimental S-box designs to protect real data.</p>")
                doc = QTextDocument()
                doc.setHtml(html)
                printer = QPrinter(QPrinter.PrinterMode.HighResolution)
                printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
                printer.setOutputFileName(path)
                doc.print_(printer)
                self.status.setText("S-BOX LAB  /  PDF EXPORT COMPLETE")
            except Exception as exc:
                self._error(str(exc))

    def build_hashes(self):
        scroll, layout = page("HASH CONSOLE", "Compare modern cryptographic digests and observe bit-level hash diffusion.")
        panel = Panel("Message digest terminal", "Hash functions are one-way; this module does not reverse or crack a hash.")
        self.hash_alg = QComboBox()
        self.hash_alg.addItems(["SHA-256", "SHA3-256", "BLAKE2b-256"])
        self.hash_text = QPlainTextEdit("CipherScope: change one character and observe the digest.")
        self.hash_text.setMinimumHeight(100)
        panel.body.addWidget(self.hash_text)
        panel.body.addWidget(self.hash_alg)
        self.hash_file = QLineEdit()
        self.hash_file.setPlaceholderText("Optional: choose a file instead of text")
        file_btn = button("USE FILE")
        file_btn.clicked.connect(lambda: self._pick_to(self.hash_file))
        clear_btn = button("CLEAR FILE")
        clear_btn.clicked.connect(lambda: self.hash_file.clear())
        panel.body.addLayout(action_row(self.hash_file, file_btn, clear_btn))
        calc = button("CALCULATE DIGEST", True)
        calc.clicked.connect(self.calculate_hash)
        flip = button("FLIP 1 BIT + COMPARE")
        flip.clicked.connect(self.compare_hash)
        panel.body.addLayout(action_row(calc, flip))
        self.hash_result = QPlainTextEdit()
        self.hash_result.setReadOnly(True)
        self.hash_result.setMaximumHeight(140)
        panel.body.addWidget(self.hash_result)
        self.hash_change = MetricCard("Changed hash bits", "--", "A demonstration of diffusion")
        panel.body.addWidget(self.hash_change)
        layout.addWidget(panel)
        layout.addStretch()
        self.calculate_hash()
        return scroll

    def _hash_bytes(self) -> bytes:
        if self.hash_file.text().strip():
            with Path(self.hash_file.text().strip()).open("rb") as file:
                if Path(self.hash_file.text().strip()).stat().st_size > 8 * 1024 * 1024:
                    raise ValueError("For interactive hash comparison, choose a file <= 8 MiB. Use cipherscope-cli for larger files.")
                return file.read()
        return self.hash_text.toPlainText().encode("utf-8")

    def calculate_hash(self):
        try:
            data = self._hash_bytes()
            digest = analysis.hash_digest(data, self.hash_alg.currentText())
            self.hash_result.setPlainText(f"ALGORITHM : {self.hash_alg.currentText()}\nINPUT SIZE: {len(data):,} bytes\nDIGEST    : {digest}")
        except Exception as exc:
            self._error(str(exc))

    def compare_hash(self):
        try:
            data = self._hash_bytes()
            report = analysis.hash_avalanche(data, self.hash_alg.currentText(), 0)
            self.hash_change.set_value(f"{report['changed_bits']} / {report['total_bits']}")
            self.hash_result.setPlainText(f"BASE    : {report['original']}\nBIT-FLIP: {report['modified']}\nHAMMING : {report['percentage']:.2f}% of digest bits")
        except Exception as exc:
            self._error(str(exc))

    def build_about(self):
        scroll, layout = page("ABOUT THE WORKSTATION", "CipherScope v1.0.0  /  Offline cryptography & cryptanalysis desktop studio.")
        overview = Panel("Design manifesto", "Classic computing aesthetics; contemporary, authenticated file protection.")
        overview.body.addWidget(text_label("The instrument-inspired interface combines beveled controls, CRT green indicators, warm amber highlights, hexadecimal grids, and a 1990s-style control deck. It is built with native Qt widgets, not Electron or a webview."))
        overview.body.addWidget(text_label("SECURE MODULE: AES-256-GCM, per-file fresh randomness, scrypt password KDF, authenticated metadata, and verified atomic decrypt-to-file behavior."))
        overview.body.addWidget(text_label("EDUCATIONAL MODULES: byte-frequency statistics, AES block avalanche, S-box permutation construction, Walsh nonlinearity, DDT analysis, SAC heatmaps, SHA-2, SHA-3, and BLAKE2b."))
        overview.body.addWidget(text_label("THREAT-MODEL NOTE: This application is a research/educational tool, not independently audited. S-box statistics and colorful noise do not prove security. File metadata (file size) is not concealed."))
        layout.addWidget(overview)
        layout.addStretch()
        return scroll

    def closeEvent(self, event):
        if self._thread is not None and self._thread.isRunning():
            event.ignore()
            QMessageBox.warning(self, "CipherScope", "A file operation is active. Please complete it before exiting.")
        else:
            event.accept()
