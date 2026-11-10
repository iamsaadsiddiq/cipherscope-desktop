import pytest

from cipherscope.core import sbox


def test_aes_fips197_vector():
    values = sbox.aes_sbox()
    assert values[:16] == [0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5,
                           0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76]
    assert len(set(values)) == 256


def test_aes_metrics():
    report = sbox.evaluate(sbox.aes_sbox(), "AES")
    assert report.nonlinearity == 112
    assert report.differential_uniformity == 4
    assert 0.40 < report.sac_mean < 0.60
    assert sum(sbox.differential_row(report.table, 1)) == 256


def test_experimental_permutations_reproducible():
    for factory in (sbox.random_sbox, sbox.triadic_sbox):
        a, b, c = factory(5), factory(5), factory(6)
        assert a == b and a != c
        assert set(a) == set(range(256))


def test_invalid_sbox_rejected():
    with pytest.raises(ValueError):
        sbox.evaluate([0] * 256)
    with pytest.raises(ValueError):
        sbox.differential_row(sbox.aes_sbox(), 256)
