# ◈ CipherScope Desktop

**A cryptographic research workstation that looks like a lost piece of late-1990s laboratory software.**

![Python](https://img.shields.io/badge/Python-3.10%2B-1b302e?logo=python) ![Qt](https://img.shields.io/badge/UI-PySide6-1b302e) ![AES](https://img.shields.io/badge/Vault-AES--256--GCM-315543) ![License](https://img.shields.io/badge/License-MIT-493a2e)

CipherScope is an **offline, cross-platform desktop app** for authenticated file encryption and interactive cryptanalysis experiments. Its interface borrows from physical oscilloscopes, green CRT terminals, bevelled workstation panels, hex monitors and amber status lights. **It is a native Qt application, not Electron or a browser wrapper.**

> **Security boundary:** The file vault uses conventional authenticated encryption. The randomized and trit-inspired S-box constructions, entropy visuals, avalanche demos, and synthetic noise previews are **research tools, not secure encryption algorithms or evidence of security**. CipherScope has **not received an independent security audit**.

## The workstation

| Module | What it does |
|---|---|
| **01 Control Deck** | Retro dashboard, animated oscilloscope, module launchers and operational status |
| **02 File Vault** | Streaming AES-256-GCM file encryption/decryption with scrypt, authenticated metadata, atomic decrypted-output handling and explicit no-overwrite behavior |
| **03 Image Lab** | Import images; create password-encrypted containers; generate clearly marked noise-like ciphertext previews; verify exact round-trip; save `.cscp` |
| **04 Byte Analyzer** | 256-bin interactive frequency chart, byte Shannon entropy, chi-square metric, serial correlation and symbol count |
| **05 Avalanche Lab** | Flip any of 128 plaintext bits; inspect AES block output differences; run deterministic Hamming-distance trials |
| **06 S-Box Studio** | AES, seeded random, and trit-mixed experimental 8×8 permutations; Walsh nonlinearity, differential uniformity, SAC heatmap, DDT row, export JSON/PDF |
| **07 Hash Console** | SHA-256, SHA3-256 and BLAKE2b-256, text/file inputs and 1-bit avalanche comparisons |
| **08 About** | Architecture, limitations, ethics, and security considerations |

### Installation for developers

Requires **Python 3.10+** and Windows, Linux or macOS.

```bash
git clone https://github.com/iamsaadsiddiq/cipherscope-desktop.git
cd cipherscope-desktop
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m cipherscope
```

Or use the `cipherscope` console command after installation. Graphical execution needs a desktop environment; automated GUI smoke tests use Qt's `offscreen` platform plugin.

### Desktop installers

`.github/workflows/build.yml` contains native GitHub Actions jobs to create:

- **Windows:** Inno Setup `.exe` installer from PyInstaller on a Windows runner.
- **Linux:** `.deb` installer for AMD64 from PyInstaller on Ubuntu.
- **macOS:** `.dmg` image containing a PyInstaller `.app` bundle on a macOS runner.

**CI-built binaries are not notarized or signed.** macOS Gatekeeper and Windows SmartScreen may warn when downloading unsigned builds. The project does not bypass operating system security policies. Create a `v*` tag or use **Actions → Build Desktop Installers → Run workflow** to produce downloadable artifacts. These workflows provide packaging automation, but successful builds and installation on target machines must be confirmed by their respective Actions runs and user testing.

### CLI (headless)

```bash
cipherscope-cli encrypt ./notes.txt ./notes.txt.cscp
cipherscope-cli decrypt ./notes.txt.cscp ./notes-restored.txt
cipherscope-cli hash ./notes.txt --algorithm SHA3-256
cipherscope-cli analyze ./notes.txt
cipherscope-cli sbox --kind aes
cipherscope-cli sbox --kind triadic --seed 2026
```

Prompts for passwords are not echoed. The CLI uses the same audited-by-tests core as the desktop UI, but is not a substitute for an external security audit.

### CSCP v1 file format

```text
byte offset    length  data
0              4       magic = ASCII 'CSCP'
4              1       format version = 1
5              16      random scrypt salt
21             12      random GCM nonce
33             N       AES-256-GCM ciphertext
33+N           16      GCM authentication tag
```

- **KDF:** scrypt N=32768, r=8, p=1, key length 32 bytes.
- **AEAD:** AES-256-GCM with the entire 33-byte header authenticated as AAD.
- Each file obtains a fresh 16-byte salt and 12-byte nonce from the operating system CSPRNG.
- File vault operations process files in 1 MiB chunks; on decryption the plaintext stays in a temporary file until authentication succeeds. On authentication failure it is deleted.
- The source filename is not stored, but encrypted payload length is visible. The app does not erase original unencrypted files.
- User-selected destinations must not exist. Treat passwords as **secret, unique passphrases** (the minimum of 8 characters does not guarantee strength).
- Decryption does not run from untrusted extensions or execute content. Examine recovered files before opening them.

**Important:** Encryption secures confidentiality/integrity, not file-system access controls, malware protection, endpoint security or backup recovery. A forgotten password cannot be recovered.

### Research metrics

**Nonlinearity** is computed via a fast Walsh-Hadamard transform over each nonzero component function; **differential uniformity** is the maximum count for nonzero input XOR differences; **SAC** is the observed probability of each output bit toggling when each input bit is toggled across the full input domain. The AES S-box expected nonlinearity is **112**, differential uniformity **4**.

The “Triadic Experiment” uses base-3 trit-mixing fingerprints and seeded SHA3 ranking to construct a permutation; this is **an experimental mapping, not a cryptographic primitive**. The generator is deliberately deterministic for repeatable research and is never involved in the secure vault.

### Testing

```bash
python -m pytest -q
python -m compileall -q src tests
```

Tests cover FIPS-197 AES block and S-box vectors, authenticated file round-trips, wrong password/tampering rejection, output cleanup, reproducible simulations, CLI and an offscreen Qt smoke test. CI targets Windows, Ubuntu, and macOS for Python 3.11/3.12.

### Project structure

```text
src/cipherscope/
  core/
    vault.py          # CSCP envelope and AES-GCM streaming
    sbox.py           # mathematical substitution analysis
    analysis.py       # entropy, hashes, avalanche measurements
  ui/
    theme.py          # retro industrial workstation palette
    widgets.py        # oscilloscope, histograms, hex maps
    main.py           # eight interactive native desktop modules
  cli.py              # scriptable headless research CLI
  __main__.py         # GUI entry point
packaging/windows.iss # Inno Setup recipe
.github/workflows/     # tests + 3-platform installers
tests/                 # algorithm / integrity / UI test suite
```

## Contribution & license

Bug reports, reproducibility fixes and cryptographic review are welcome. Do not include real secrets or private files in bug reports. Published under the **MIT License**. See [LICENSE](LICENSE).
