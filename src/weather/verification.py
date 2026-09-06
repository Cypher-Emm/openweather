from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class VerificationStats:
    count: int
    mae: float | None
    rmse: float | None
    bias: float | None


def verify_continuous(forecasts: list[float], observations: list[float]) -> VerificationStats:
    if len(forecasts) != len(observations):
        raise ValueError("forecasts and observations must have the same length")
    if not forecasts:
        return VerificationStats(0, None, None, None)
    errors = [f - o for f, o in zip(forecasts, observations)]
    return VerificationStats(
        count=len(errors),
        mae=sum(abs(e) for e in errors) / len(errors),
        rmse=sqrt(sum(e * e for e in errors) / len(errors)),
        bias=sum(errors) / len(errors),
    )


def brier_score(probabilities: list[float], outcomes: list[bool]) -> float | None:
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must have the same length")
    if not probabilities:
        return None
    if any(p < 0 or p > 1 for p in probabilities):
        raise ValueError("probabilities must be between 0 and 1")
    return sum((p - float(o)) ** 2 for p, o in zip(probabilities, outcomes)) / len(probabilities)
