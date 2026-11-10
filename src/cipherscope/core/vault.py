"""Versioned authenticated encryption envelope, with streaming, atomic writes.

Format: magic(4) | version(1) | salt(16) | nonce(12) | ciphertext(N) | tag(16)
KDF: scrypt N=32768 r=8 p=1. AEAD: AES-256-GCM, header authenticated as AAD.
No original filenames or user passwords are stored in the envelope.
"""
from __future__ import annotations

import os
import struct
import tempfile
from pathlib import Path
from typing import Callable

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

MAGIC = b"CSCP"
VERSION = 1
HEADER = struct.Struct(">4sB16s12s")
TAG_SIZE = 16
CHUNK_SIZE = 1024 * 1024
Progress = Callable[[int, int], None]


class VaultError(ValueError):
    """Bad format, bad password, or integrity verification failure."""


def _password_bytes(password: str) -> bytes:
    if not isinstance(password, str) or len(password) < 8:
        raise VaultError("Use a password with at least 8 characters.")
    return password.encode("utf-8")


def _derive(password: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(_password_bytes(password))


def _header() -> bytes:
    return HEADER.pack(MAGIC, VERSION, os.urandom(16), os.urandom(12))


def inspect_header(header: bytes) -> dict[str, str | int]:
    if len(header) != HEADER.size:
        raise VaultError("Truncated CipherScope header.")
    magic, version, salt, nonce = HEADER.unpack(header)
    if magic != MAGIC or version != VERSION:
        raise VaultError("Not a supported CipherScope v1 envelope.")
    return {"format": "CSCP", "version": version, "kdf": "scrypt N=32768 r=8 p=1",
            "cipher": "AES-256-GCM", "salt_hex": salt.hex(), "nonce_hex": nonce.hex()}


def encrypt_bytes(data: bytes, password: str) -> bytes:
    header = _header()
    _, _, salt, nonce = HEADER.unpack(header)
    ciphertext = AESGCM(_derive(password, salt)).encrypt(nonce, data, header)
    return header + ciphertext


def decrypt_bytes(envelope: bytes, password: str) -> bytes:
    if len(envelope) < HEADER.size + TAG_SIZE:
        raise VaultError("Encrypted payload is truncated.")
    header = envelope[:HEADER.size]
    inspect_header(header)
    _, _, salt, nonce = HEADER.unpack(header)
    try:
        return AESGCM(_derive(password, salt)).decrypt(nonce, envelope[HEADER.size:], header)
    except InvalidTag as exc:
        raise VaultError("Authentication failed: wrong password or modified file.") from exc


def _paths(source: str | Path, destination: str | Path) -> tuple[Path, Path]:
    src, dst = Path(source).expanduser().resolve(), Path(destination).expanduser().resolve()
    if not src.is_file():
        raise VaultError("Source file does not exist.")
    if src == dst:
        raise VaultError("Input and output must be different paths.")
    if not dst.parent.is_dir():
        raise VaultError("Output directory does not exist.")
    if dst.exists():
        raise VaultError("Output already exists; select a different filename.")
    return src, dst


def _temp_file(directory: Path) -> Path:
    fd, path = tempfile.mkstemp(prefix=".cipherscope-", suffix=".tmp", dir=directory)
    os.close(fd)
    return Path(path)


def encrypt_file(source: str | Path, destination: str | Path, password: str,
                 progress: Progress | None = None) -> Path:
    src, dst = _paths(source, destination)
    _password_bytes(password)
    total = src.stat().st_size
    header = _header()
    _, _, salt, nonce = HEADER.unpack(header)
    encryptor = Cipher(algorithms.AES(_derive(password, salt)), modes.GCM(nonce)).encryptor()
    encryptor.authenticate_additional_data(header)
    temp = _temp_file(dst.parent)
    try:
        done = 0
        with src.open("rb") as input_file, temp.open("wb") as output_file:
            output_file.write(header)
            while chunk := input_file.read(CHUNK_SIZE):
                output_file.write(encryptor.update(chunk))
                done += len(chunk)
                if progress:
                    progress(done, total)
            output_file.write(encryptor.finalize())
            output_file.write(encryptor.tag)
        if dst.exists():
            raise VaultError("Output was created by another process.")
        os.replace(temp, dst)
        return dst
    finally:
        temp.unlink(missing_ok=True)


def decrypt_file(source: str | Path, destination: str | Path, password: str,
                 progress: Progress | None = None) -> Path:
    src, dst = _paths(source, destination)
    _password_bytes(password)
    size = src.stat().st_size
    if size < HEADER.size + TAG_SIZE:
        raise VaultError("Encrypted payload is truncated.")
    temp: Path | None = None
    try:
        with src.open("rb") as input_file:
            header = input_file.read(HEADER.size)
            inspect_header(header)
            _, _, salt, nonce = HEADER.unpack(header)
            input_file.seek(-TAG_SIZE, os.SEEK_END)
            tag = input_file.read(TAG_SIZE)
            input_file.seek(HEADER.size)
            remaining = size - HEADER.size - TAG_SIZE
            decryptor = Cipher(algorithms.AES(_derive(password, salt)),
                               modes.GCM(nonce, tag)).decryptor()
            decryptor.authenticate_additional_data(header)
            temp = _temp_file(dst.parent)
            with temp.open("wb") as output_file:
                done = 0
                while remaining:
                    chunk = input_file.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        raise VaultError("Unexpected end of encrypted file.")
                    output_file.write(decryptor.update(chunk))
                    remaining -= len(chunk)
                    done += len(chunk)
                    if progress:
                        progress(done, size - HEADER.size - TAG_SIZE)
                try:
                    output_file.write(decryptor.finalize())
                except InvalidTag as exc:
                    raise VaultError("Authentication failed: wrong password or modified file.") from exc
        if dst.exists():
            raise VaultError("Output was created by another process.")
        os.replace(temp, dst)
        return dst
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
