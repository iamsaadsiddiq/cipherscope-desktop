import os

import pytest

from cipherscope.core import vault

PASSWORD = "correct-horse-battery-staple"


def test_bytes_roundtrip_and_unique_nonce():
    payload = os.urandom(16000) + bytes(range(256))
    first = vault.encrypt_bytes(payload, PASSWORD)
    second = vault.encrypt_bytes(payload, PASSWORD)
    assert first != second
    assert vault.decrypt_bytes(first, PASSWORD) == payload
    assert vault.inspect_header(first[:vault.HEADER.size])["cipher"] == "AES-256-GCM"


def test_tamper_wrong_password_and_truncation():
    blob = vault.encrypt_bytes(b"important payload", PASSWORD)
    with pytest.raises(vault.VaultError, match="Authentication failed"):
        vault.decrypt_bytes(blob, "incorrect-password")
    altered = bytearray(blob)
    altered[-20] ^= 0x80
    with pytest.raises(vault.VaultError, match="Authentication failed"):
        vault.decrypt_bytes(bytes(altered), PASSWORD)
    with pytest.raises(vault.VaultError, match="truncated"):
        vault.decrypt_bytes(blob[:5], PASSWORD)


def test_file_roundtrip_streaming(tmp_path):
    source, sealed, restored = (tmp_path / name for name in ("source.bin", "secret.cscp", "plain.bin"))
    data = os.urandom(vault.CHUNK_SIZE + 117)
    source.write_bytes(data)
    events = []
    vault.encrypt_file(source, sealed, PASSWORD, lambda done, total: events.append((done, total)))
    assert sealed.read_bytes().startswith(b"CSCP")
    vault.decrypt_file(sealed, restored, PASSWORD)
    assert restored.read_bytes() == data
    assert events[-1] == (len(data), len(data))


def test_file_decrypt_failure_never_leaves_plaintext(tmp_path):
    source, sealed, output = (tmp_path / name for name in ("source", "secret.cscp", "output"))
    source.write_bytes(b"private data" * 100)
    vault.encrypt_file(source, sealed, PASSWORD)
    with pytest.raises(vault.VaultError, match="Authentication failed"):
        vault.decrypt_file(sealed, output, "bad-password-123")
    assert not output.exists()
    assert not list(tmp_path.glob(".cipherscope-*.tmp"))
    blob = bytearray(sealed.read_bytes())
    blob[-1] ^= 1
    sealed.write_bytes(blob)
    with pytest.raises(vault.VaultError):
        vault.decrypt_file(sealed, output, PASSWORD)
    assert not output.exists()


def test_wont_overwrite_existing_files(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_bytes(b"stuff")
    destination.write_bytes(b"keep-me")
    with pytest.raises(vault.VaultError, match="already exists"):
        vault.encrypt_file(source, destination, PASSWORD)
    assert destination.read_bytes() == b"keep-me"


def test_empty_file_and_short_password(tmp_path):
    a, b, c = [tmp_path / p for p in ("a", "b", "c")]
    a.write_bytes(b"")
    vault.encrypt_file(a, b, PASSWORD)
    vault.decrypt_file(b, c, PASSWORD)
    assert c.read_bytes() == b""
    with pytest.raises(vault.VaultError, match="at least 8"):
        vault.encrypt_bytes(b"test", "short")
