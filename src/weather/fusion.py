from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean

from weather.models import CurrentWeather, HourlyPoint, Location, Quality, WeatherResult
from weather.sources.base import SourceForecast


_NUMERIC_CURRENT = (
    "temperature_c", "apparent_temperature_c", "dew_point_c", "relative_humidity_pct",
    "pressure_hpa", "precipitation_mm", "rain_mm", "snowfall_cm", "cloud_cover_pct",
    "visibility_m", "wind_speed_kmh", "wind_gust_kmh", "wind_direction_deg",
)


def _weighted_mean(values: list[float]) -> float | None:
    return mean(values) if values else None


def _fuse_current(items: list[SourceForecast]) -> CurrentWeather | None:
    currents = [x.current for x in items if x.current is not None]
    if not currents:
        return None
    result = {}
    for field in _NUMERIC_CURRENT:
        values = [getattr(item, field) for item in currents if getattr(item, field) is not None]
        result[field] = _weighted_mean(values)
    codes = [x.weather_code for x in currents if x.weather_code is not None]
    result["weather_code"] = max(set(codes), key=codes.count) if codes else None
    return CurrentWeather(**result)


def _fuse_hourly(items: list[SourceForecast]) -> list[HourlyPoint]:
    buckets: dict[datetime, list[HourlyPoint]] = {}
    for source in items:
        for point in source.hourly:
            buckets.setdefault(point.time, []).append(point)
    fields = (
        "temperature_c", "apparent_temperature_c", "precipitation_probability_pct",
        "precipitation_mm", "rain_mm", "snowfall_cm", "cloud_cover_pct", "visibility_m",
        "wind_speed_kmh", "wind_gust_kmh", "wind_direction_deg", "pressure_hpa",
    )
    result = []
    for timestamp in sorted(buckets):
        points = buckets[timestamp]
        data = {"time": timestamp}
        for field in fields:
            values = [getattr(p, field) for p in points if getattr(p, field) is not None]
            data[field] = _weighted_mean(values)
        result.append(HourlyPoint(**data))
    return result


def _fuse_daily(items: list[SourceForecast]):
    buckets: dict[str, list] = {}
    for source in items:
        for point in source.daily:
            buckets.setdefault(point.date, []).append(point)
    fields = (
        "temperature_max_c", "temperature_min_c", "precipitation_probability_max_pct",
        "precipitation_sum_mm", "rain_sum_mm", "snowfall_sum_cm", "wind_gust_max_kmh",
    )
    from weather.models import DailyPoint
    result = []
    for date in sorted(buckets):
        points = buckets[date]
        data = {"date": date}
        for field in fields:
            values = [getattr(p, field) for p in points if getattr(p, field) is not None]
            data[field] = _weighted_mean(values)
        result.append(DailyPoint(**data))
    return result


def _agreement(items: list[SourceForecast]) -> float:
    temps = [x.current.temperature_c for x in items if x.current and x.current.temperature_c is not None]
    if len(temps) < 2:
        return 0.5 if temps else 0.0
    spread = max(temps) - min(temps)
    # A 0°C spread is perfect agreement; >=10°C is treated as severe disagreement.
    return max(0.0, min(1.0, 1.0 - spread / 10.0))


def fuse(location: Location, sources: list[SourceForecast]) -> WeatherResult:
    now = datetime.now(timezone.utc)
    valid = [x for x in sources if x.current is not None or x.hourly or x.daily]
    agreement = _agreement(valid)
    freshness = 1.0
    if valid:
        ages = [(now - x.meta.retrieved_at).total_seconds() for x in valid]
        freshness = max(0.0, min(1.0, 1.0 - max(ages) / 3600.0))
    score = 0.55 * agreement + 0.45 * freshness
    notes = []
    if len(valid) < 2:
        notes.append("Single-source result: cross-provider agreement is unavailable.")
    if agreement < 0.5:
        notes.append("Forecast models disagree materially on near-term temperature.")
    return WeatherResult(
        location=location,
        generated_at=now,
        current=_fuse_current(valid),
        hourly=_fuse_hourly(valid),
        daily=_fuse_daily(valid),
        sources=[x.meta for x in valid],
        quality=Quality(
            score=score,
            source_count=len(valid),
            model_agreement=agreement,
            freshness_score=freshness,
            notes=notes,
        ),
    )
