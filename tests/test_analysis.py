import hashlib

import pytest

from cipherscope.core import analysis


def test_entropy_basics():
    assert analysis.byte_stats(b"").entropy == 0
    assert analysis.byte_stats(b"x" * 200).entropy == 0
    assert analysis.byte_stats(bytes(range(256))).entropy == pytest.approx(8)
    assert analysis.byte_stats(bytes(range(256))).unique_bytes == 256


def test_aes_known_answer_and_avalanche():
    key = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
    plain = bytes.fromhex("00112233445566778899aabbccddeeff")
    assert analysis.aes_block(plain, key).hex() == "69c4e0d86a7b0430d8cdb78070b4c55a"
    measured = analysis.avalanche_once(plain, 12)
    assert 0 <= measured["changed_bits"] <= 128
    assert measured["baseline"] != measured["modified"]
    trials = analysis.avalanche_trials(32, seed=100)
    assert len(trials["samples"]) == 32
    assert trials == analysis.avalanche_trials(32, seed=100)


def test_hashes_and_bits():
    assert analysis.hash_digest(b"abc", "SHA-256") == hashlib.sha256(b"abc").hexdigest()
    assert len(analysis.hash_digest(b"abc", "SHA3-256")) == 64
    assert len(analysis.hash_digest(b"abc", "BLAKE2b-256")) == 64
    assert analysis.hamming_distance(b"\x00", b"\xff") == 8
    assert analysis.flip_bit(b"\x00", 0) == b"\x01"
    with pytest.raises(ValueError):
        analysis.flip_bit(b"\x00", 8)
