from datetime import datetime, timezone

from weather.fusion import fuse
from weather.models import CurrentWeather, HourlyPoint, Location, SourceMeta
from weather.sources.base import SourceForecast


def source(temp: float, retrieved_at: datetime) -> SourceForecast:
    return SourceForecast(
        current=CurrentWeather(temperature_c=temp, relative_humidity_pct=50),
        hourly=[HourlyPoint(time=datetime(2026, 9, 6, 12), temperature_c=temp)],
        daily=[],
        meta=SourceMeta(provider="test", model="test", retrieved_at=retrieved_at),
    )


def test_fusion_averages_independent_sources():
    location = Location(
        id="srinagar", name="Srinagar", district="Srinagar", kind="district",
        latitude=34.0837, longitude=74.7973, elevation_m=1585,
    )
    now = datetime.now(timezone.utc)
    result = fuse(location, [source(20, now), source(22, now)])
    assert result.current is not None
    assert result.current.temperature_c == 21
    assert result.quality.source_count == 2
    assert result.quality.model_agreement == 0.8
