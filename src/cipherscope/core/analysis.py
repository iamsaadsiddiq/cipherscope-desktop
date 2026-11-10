"""Reproducible educational cryptanalysis measurements, not security proofs."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import blake2b, sha256, sha3_256
from math import log2, sqrt
from random import Random

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes


@dataclass(frozen=True)
class ByteStats:
    size: int
    entropy: float
    chi_square: float
    serial_correlation: float
    unique_bytes: int
    histogram: list[int]

    def to_dict(self) -> dict:
        return asdict(self)


def byte_stats(data: bytes) -> ByteStats:
    counts = Counter(data)
    hist = [counts.get(i, 0) for i in range(256)]
    count = len(data)
    if count == 0:
        return ByteStats(0, 0.0, 0.0, 0.0, 0, hist)
    entropy = -sum((n / count) * log2(n / count) for n in hist if n)
    expected = count / 256
    chi = sum((n - expected) ** 2 / expected for n in hist)
    if count < 2:
        corr = 0.0
    else:
        a, b = data[:-1], data[1:]
        ma, mb = sum(a) / len(a), sum(b) / len(b)
        numerator = sum((x - ma) * (y - mb) for x, y in zip(a, b))
        den_a = sum((x - ma) ** 2 for x in a)
        den_b = sum((y - mb) ** 2 for y in b)
        corr = numerator / sqrt(den_a * den_b) if den_a and den_b else 0.0
    return ByteStats(count, entropy, chi, corr, len(counts), hist)


def hamming_distance(a: bytes, b: bytes) -> int:
    if len(a) != len(b):
        raise ValueError("Byte arrays must have equal lengths.")
    return sum((x ^ y).bit_count() for x, y in zip(a, b))


def aes_block(block: bytes, key: bytes) -> bytes:
    """One-block AES primitive for demos; never use ECB for user file encryption."""
    if len(block) != 16 or len(key) not in (16, 24, 32):
        raise ValueError("Expected a 16-byte block and 16/24/32-byte AES key.")
    e = Cipher(algorithms.AES(key), modes.ECB()).encryptor()
    return e.update(block) + e.finalize()


def flip_bit(data: bytes, bit: int) -> bytes:
    if not 0 <= bit < len(data) * 8:
        raise ValueError("Bit index out of bounds.")
    out = bytearray(data)
    out[bit // 8] ^= 1 << (bit % 8)
    return bytes(out)


def avalanche_once(block: bytes, bit: int = 0, key: bytes | None = None) -> dict:
    key = key if key is not None else bytes(range(16))
    base = aes_block(block, key)
    changed = aes_block(flip_bit(block, bit), key)
    distance = hamming_distance(base, changed)
    return {"baseline": base.hex(), "modified": changed.hex(), "flipped_input_bit": bit,
            "changed_bits": distance, "percentage": distance * 100 / 128}


def avalanche_trials(trials: int = 32, seed: int = 2026) -> dict:
    if not 1 <= trials <= 4096:
        raise ValueError("trials must be between 1 and 4096")
    rng = Random(seed)  # Deterministic demo input; never used for cryptographic key generation.
    samples = []
    for _ in range(trials):
        block = rng.randbytes(16)
        key = rng.randbytes(16)
        bit = rng.randrange(128)
        samples.append(avalanche_once(block, bit, key)["changed_bits"])
    return {"trials": trials, "seed": seed, "samples": samples,
            "average_bits": sum(samples) / len(samples),
            "average_percent": 100 * sum(samples) / (len(samples) * 128)}


def hash_digest(data: bytes, algorithm: str) -> str:
    functions = {"SHA-256": sha256, "SHA3-256": sha3_256,
                 "BLAKE2b-256": lambda blob: blake2b(blob, digest_size=32)}
    try:
        return functions[algorithm](data).hexdigest()
    except KeyError as exc:
        raise ValueError("Unsupported hash algorithm.") from exc


def hash_avalanche(data: bytes, algorithm: str, bit: int = 0) -> dict:
    if not data:
        raise ValueError("Input cannot be empty.")
    first = bytes.fromhex(hash_digest(data, algorithm))
    second = bytes.fromhex(hash_digest(flip_bit(data, bit), algorithm))
    changed = hamming_distance(first, second)
    return {"changed_bits": changed, "total_bits": len(first) * 8,
            "percentage": 100 * changed / (len(first) * 8),
            "original": first.hex(), "modified": second.hex()}
