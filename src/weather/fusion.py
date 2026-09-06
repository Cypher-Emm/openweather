from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import median

from weather.models import CurrentWeather, DailyPoint, HourlyPoint, Location, Quality, WeatherResult
from weather.sources.base import SourceForecast


SCALAR_CURRENT = (
    "temperature_c", "apparent_temperature_c", "dew_point_c", "relative_humidity_pct",
    "pressure_hpa", "precipitation_mm", "rain_mm", "snowfall_cm", "cloud_cover_pct",
    "visibility_m", "wind_speed_kmh", "wind_gust_kmh",
)
SCALAR_HOURLY = (
    "temperature_c", "apparent_temperature_c", "precipitation_probability_pct",
    "precipitation_mm", "rain_mm", "snowfall_cm", "cloud_cover_pct", "visibility_m",
    "wind_speed_kmh", "wind_gust_kmh", "pressure_hpa",
)
SCALAR_DAILY = (
    "temperature_max_c", "temperature_min_c", "precipitation_probability_max_pct",
    "precipitation_sum_mm", "rain_sum_mm", "snowfall_sum_cm", "wind_gust_max_kmh",
)


def _median(values: list[float]) -> float | None:
    return float(median(values)) if values else None


def _circular_mean(degrees: list[float]) -> float | None:
    if not degrees:
        return None
    radians = [math.radians(x % 360) for x in degrees]
    x = sum(math.cos(v) for v in radians)
    y = sum(math.sin(v) for v in radians)
    if abs(x) < 1e-12 and abs(y) < 1e-12:
        return None
    return math.degrees(math.atan2(y, x)) % 360


def _spread(values: list[float]) -> float:
    return max(values) - min(values) if len(values) >= 2 else 0.0


def _agreement(items: list[SourceForecast]) -> float:
    """Conservative cross-model agreement score across several physical variables."""
    scores: list[float] = []
    for field, scale in (("temperature_c", 6.0), ("relative_humidity_pct", 35.0),
                         ("wind_speed_kmh", 20.0), ("pressure_hpa", 8.0)):
        values = [getattr(x.current, field) for x in items if x.current and getattr(x.current, field) is not None]
        if len(values) >= 2:
            scores.append(max(0.0, min(1.0, 1.0 - _spread(values) / scale)))
    return sum(scores) / len(scores) if scores else (0.5 if items else 0.0)


def _fuse_current(items: list[SourceForecast]) -> CurrentWeather | None:
    currents = [x.current for x in items if x.current is not None]
    if not currents:
        return None
    data = {field: _median([getattr(c, field) for c in currents if getattr(c, field) is not None])
            for field in SCALAR_CURRENT}
    data["wind_direction_deg"] = _circular_mean(
        [c.wind_direction_deg for c in currents if c.wind_direction_deg is not None]
    )
    codes = [c.weather_code for c in currents if c.weather_code is not None]
    data["weather_code"] = max(set(codes), key=codes.count) if codes else None
    return CurrentWeather(**data)


def _fuse_hourly(items: list[SourceForecast]) -> list[HourlyPoint]:
    buckets: dict[datetime, list[HourlyPoint]] = {}
    for source in items:
        for point in source.hourly:
            buckets.setdefault(point.time, []).append(point)
    result: list[HourlyPoint] = []
    for timestamp, points in sorted(buckets.items()):
        data = {field: _median([getattr(p, field) for p in points if getattr(p, field) is not None])
                for field in SCALAR_HOURLY}
        data["time"] = timestamp
        data["wind_direction_deg"] = _circular_mean(
            [p.wind_direction_deg for p in points if p.wind_direction_deg is not None]
        )
        result.append(HourlyPoint(**data))
    return result


def _fuse_daily(items: list[SourceForecast]) -> list[DailyPoint]:
    buckets: dict[str, list] = {}
    for source in items:
        for point in source.daily:
            buckets.setdefault(point.date, []).append(point)
    result: list[DailyPoint] = []
    for date, points in sorted(buckets.items()):
        data = {field: _median([getattr(p, field) for p in points if getattr(p, field) is not None])
                for field in SCALAR_DAILY}
        data["date"] = date
        result.append(DailyPoint(**data))
    return result


def fuse(location: Location, sources: list[SourceForecast]) -> WeatherResult:
    now = datetime.now(timezone.utc)
    valid = [x for x in sources if x.current is not None or x.hourly or x.daily]
    agreement = _agreement(valid)
    freshness = 0.0
    if valid:
        ages = [max(0.0, (now - x.meta.retrieved_at).total_seconds()) for x in valid]
        freshness = max(0.0, min(1.0, 1.0 - max(ages) / 3600.0))
    score = 0.65 * agreement + 0.35 * freshness
    notes: list[str] = []
    if len(valid) < 2:
        notes.append("Single-source result: cross-model agreement is unavailable.")
    if agreement < 0.5:
        notes.append("Forecast guidance is materially divergent; uncertainty is elevated.")
    if freshness < 0.5:
        notes.append("One or more source responses are older than the preferred freshness window.")
    return WeatherResult(
        location=location,
        generated_at=now,
        current=_fuse_current(valid),
        hourly=_fuse_hourly(valid),
        daily=_fuse_daily(valid),
        sources=[x.meta for x in valid],
        quality=Quality(score=score, source_count=len(valid), model_agreement=agreement,
                        freshness_score=freshness, notes=notes),
    )
