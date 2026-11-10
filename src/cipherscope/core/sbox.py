"""8x8 permutation S-box constructions and differential/linear/SAC metrics."""
from __future__ import annotations

import hashlib
import random
from dataclasses import asdict, dataclass


def gf_mul(a: int, b: int) -> int:
    result = 0
    for _ in range(8):
        if b & 1:
            result ^= a
        a = (a << 1) ^ (0x11B if a & 0x80 else 0)
        b >>= 1
    return result & 0xFF


def gf_pow(a: int, n: int) -> int:
    out = 1
    while n:
        if n & 1:
            out = gf_mul(out, a)
        a = gf_mul(a, a)
        n >>= 1
    return out


def aes_sbox() -> list[int]:
    table = []
    for x in range(256):
        inv = gf_pow(x, 254) if x else 0
        rotated = inv
        for shift in range(1, 5):
            rotated ^= ((inv << shift) | (inv >> (8 - shift))) & 0xFF
        table.append(rotated ^ 0x63)
    return table


def random_sbox(seed: int = 2026) -> list[int]:
    values = list(range(256))
    random.Random(seed).shuffle(values)  # Educational permutation, not secure randomness.
    return values


def triadic_sbox(seed: int = 2026) -> list[int]:
    """Experimental trit-mixing ranking permutation; NOT a vetted cryptosystem.

    Maps each x to six base-3 digits; mixes neighbors modulo three, then
    ranks domain values by SHA3-256(seed || trit fingerprint || domain index).
    Ranking guarantees a bijection; it does NOT establish cryptographic strength.
    """
    def fingerprint(x: int) -> bytes:
        trits = []
        for _ in range(6):
            trits.append(x % 3)
            x //= 3
        mixed = [(trits[i] + 2 * trits[(i + 1) % 6] + trits[(i + 3) % 6]) % 3
                 for i in range(6)]
        return bytes(mixed)

    seed_bytes = str(seed).encode("ascii")
    ranking = sorted(range(256), key=lambda x: hashlib.sha3_256(
        seed_bytes + x.to_bytes(2, "big") + fingerprint(x)).digest())
    return ranking


def validate_sbox(table: list[int]) -> None:
    if len(table) != 256 or set(table) != set(range(256)):
        raise ValueError("An 8x8 S-box must be a permutation of integers 0..255.")


def differential_row(table: list[int], input_difference: int) -> list[int]:
    validate_sbox(table)
    if not 0 <= input_difference <= 255:
        raise ValueError("Input difference must be 0..255.")
    row = [0] * 256
    for x in range(256):
        row[table[x] ^ table[x ^ input_difference]] += 1
    return row


def differential_uniformity(table: list[int]) -> int:
    validate_sbox(table)
    return max(max(differential_row_unchecked(table, difference)) for difference in range(1, 256))


def differential_row_unchecked(table: list[int], difference: int) -> list[int]:
    row = [0] * 256
    for x in range(256):
        row[table[x] ^ table[x ^ difference]] += 1
    return row


def walsh_nonlinearity(table: list[int]) -> int:
    validate_sbox(table)
    lowest = 128
    # For vectorial S-boxes, minimize nonlinearity over every nonzero output mask.
    for mask in range(1, 256):
        transform = [1 if (table[x] & mask).bit_count() % 2 == 0 else -1
                     for x in range(256)]
        step = 1
        while step < 256:
            for base in range(0, 256, step * 2):
                for i in range(base, base + step):
                    a, b = transform[i], transform[i + step]
                    transform[i], transform[i + step] = a + b, a - b
            step *= 2
        lowest = min(lowest, 128 - max(abs(x) for x in transform) // 2)
    return lowest


def sac_matrix(table: list[int]) -> list[list[float]]:
    validate_sbox(table)
    return [[sum(bool((table[x] ^ table[x ^ (1 << input_bit)]) & (1 << output_bit))
                 for x in range(256)) / 256
             for output_bit in range(8)] for input_bit in range(8)]


@dataclass
class SBoxReport:
    name: str
    nonlinearity: int
    differential_uniformity: int
    sac_mean: float
    sac_max_deviation: float
    fixed_points: int
    table: list[int]
    sac: list[list[float]]

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate(table: list[int], name: str = "Custom permutation") -> SBoxReport:
    validate_sbox(table)
    sac = sac_matrix(table)
    values = [cell for row in sac for cell in row]
    return SBoxReport(name, walsh_nonlinearity(table), differential_uniformity(table),
                      sum(values) / len(values), max(abs(v - 0.5) for v in values),
                      sum(i == v for i, v in enumerate(table)), list(table), sac)
