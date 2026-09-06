import pytest

from weather.verification import brier_score, verify_continuous


def test_continuous_verification():
    stats = verify_continuous([10, 12, 14], [11, 11, 13])
    assert stats.count == 3
    assert stats.mae == pytest.approx(1.0)
    assert stats.rmse == pytest.approx(1.0)
    assert stats.bias == pytest.approx(1 / 3)


def test_brier_score():
    assert brier_score([0.0, 0.5, 1.0], [False, True, True]) == pytest.approx(1 / 12)


def test_verification_rejects_mismatched_series():
    with pytest.raises(ValueError):
        verify_continuous([1], [1, 2])
