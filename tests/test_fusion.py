from datetime import datetime, timezone

from weather.fusion import fuse
from weather.models import CurrentWeather, HourlyPoint, Location, SourceMeta
from weather.sources.base import SourceForecast


def source(temp: float, retrieved_at: datetime, wind: float | None = None, direction: float | None = None, weather_code: int | None = None, hourly_time: datetime | None = None) -> SourceForecast:
    return SourceForecast(
        current=CurrentWeather(temperature_c=temp, relative_humidity_pct=50,
                               wind_speed_kmh=wind, wind_direction_deg=direction, weather_code=weather_code),
        hourly=[HourlyPoint(time=hourly_time or datetime(2026, 9, 6, 12), temperature_c=temp,
                            wind_direction_deg=direction, weather_code=weather_code)],
        daily=[],
        meta=SourceMeta(provider="test", model="test", retrieved_at=retrieved_at),
    )


def location() -> Location:
    return Location(id="srinagar", name="Srinagar", district="Srinagar", kind="district",
                    latitude=34.0837, longitude=74.7973, elevation_m=1585)


def test_fusion_uses_median_for_scalar_fields():
    now = datetime.now(timezone.utc)
    result = fuse(location(), [source(20, now), source(22, now), source(60, now)])
    assert result.current is not None
    assert result.current.temperature_c == 22
    assert result.quality.source_count == 3
    assert result.quality.model_agreement < 0.6


def test_wind_direction_uses_circular_mean():
    now = datetime.now(timezone.utc)
    result = fuse(location(), [source(10, now, 5, 359), source(10, now, 5, 1)])
    assert result.current is not None
    assert result.current.wind_direction_deg is not None
    assert result.current.wind_direction_deg < 2 or result.current.wind_direction_deg > 358


def test_precipitation_probability_falls_back_to_weather_codes():
    now = datetime.now(timezone.utc)
    result = fuse(location(), [source(10, now, weather_code=61), source(10, now, weather_code=0)])
    assert result.current is not None
    assert result.current.precipitation_probability_pct == 50


def test_stale_sources_reduce_quality():
    now = datetime.now(timezone.utc)
    old = now.replace(year=2025)
    result = fuse(location(), [source(20, old), source(20, now)])
    assert result.quality.freshness_score < 0.01
    assert result.quality.score < 0.7


def test_fusion_normalizes_mixed_naive_and_aware_hourly_times():
    now = datetime.now(timezone.utc)
    naive = datetime(2026, 9, 6, 12)
    aware = datetime(2026, 9, 6, 12, tzinfo=timezone.utc)
    result = fuse(location(), [source(20, now, hourly_time=naive), source(22, now, hourly_time=aware)])
    assert len(result.hourly) == 1
    assert result.hourly[0].time.tzinfo is not None
    assert result.hourly[0].time.utcoffset() == timezone.utc.utcoffset(result.hourly[0].time)
    assert result.hourly[0].temperature_c == 21
