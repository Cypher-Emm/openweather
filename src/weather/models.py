from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Location(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    district: str | None = None
    kind: Literal["district", "town", "hill_station", "mountain", "pass"]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    elevation_m: float = Field(ge=-500, le=10000)


class CurrentWeather(BaseModel):
    temperature_c: float | None = None
    apparent_temperature_c: float | None = None
    dew_point_c: float | None = None
    relative_humidity_pct: float | None = Field(default=None, ge=0, le=100)
    pressure_hpa: float | None = None
    precipitation_mm: float | None = Field(default=None, ge=0)
    rain_mm: float | None = Field(default=None, ge=0)
    snowfall_cm: float | None = Field(default=None, ge=0)
    cloud_cover_pct: float | None = Field(default=None, ge=0, le=100)
    visibility_m: float | None = Field(default=None, ge=0)
    wind_speed_kmh: float | None = Field(default=None, ge=0)
    wind_gust_kmh: float | None = Field(default=None, ge=0)
    wind_direction_deg: float | None = Field(default=None, ge=0, le=360)
    weather_code: int | None = None


class HourlyPoint(BaseModel):
    time: datetime
    temperature_c: float | None = None
    apparent_temperature_c: float | None = None
    precipitation_probability_pct: float | None = Field(default=None, ge=0, le=100)
    precipitation_mm: float | None = Field(default=None, ge=0)
    rain_mm: float | None = Field(default=None, ge=0)
    snowfall_cm: float | None = Field(default=None, ge=0)
    cloud_cover_pct: float | None = Field(default=None, ge=0, le=100)
    visibility_m: float | None = Field(default=None, ge=0)
    wind_speed_kmh: float | None = Field(default=None, ge=0)
    wind_gust_kmh: float | None = Field(default=None, ge=0)
    wind_direction_deg: float | None = Field(default=None, ge=0, le=360)
    pressure_hpa: float | None = None


class DailyPoint(BaseModel):
    date: str
    temperature_max_c: float | None = None
    temperature_min_c: float | None = None
    precipitation_probability_max_pct: float | None = None
    precipitation_sum_mm: float | None = None
    rain_sum_mm: float | None = None
    snowfall_sum_cm: float | None = None
    wind_gust_max_kmh: float | None = None


class SourceMeta(BaseModel):
    provider: str
    model: str
    retrieved_at: datetime
    forecast_run: datetime | None = None
    latency_ms: int | None = None


class Quality(BaseModel):
    score: float = Field(ge=0, le=1)
    source_count: int = Field(ge=0)
    model_agreement: float = Field(ge=0, le=1)
    freshness_score: float = Field(ge=0, le=1)
    notes: list[str] = Field(default_factory=list)


class WeatherResult(BaseModel):
    location: Location
    generated_at: datetime
    current: CurrentWeather | None = None
    hourly: list[HourlyPoint] = Field(default_factory=list)
    daily: list[DailyPoint] = Field(default_factory=list)
    sources: list[SourceMeta] = Field(default_factory=list)
    quality: Quality


class DistrictSummary(BaseModel):
    district: str
    representative_location: str
    weather: WeatherResult


class ValleyOverview(BaseModel):
    generated_at: datetime
    districts: list[DistrictSummary]
    hill_stations: list[WeatherResult]
