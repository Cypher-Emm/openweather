from __future__ import annotations

import time
from datetime import datetime, timezone

import httpx

from weather.models import CurrentWeather, DailyPoint, HourlyPoint, Location, SourceMeta
from weather.sources.base import SourceForecast, WeatherSource


class OpenMeteoSource(WeatherSource):
    name = "open-meteo"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def forecast(self, location: Location, now: datetime) -> SourceForecast:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "elevation": location.elevation_m,
            "timezone": "auto",
            "forecast_days": 7,
            "current": ",".join([
                "temperature_2m", "apparent_temperature", "relative_humidity_2m",
                "dew_point_2m", "surface_pressure", "precipitation", "rain", "snowfall",
                "cloud_cover", "visibility", "wind_speed_10m", "wind_gusts_10m",
                "wind_direction_10m", "weather_code",
            ]),
            "hourly": ",".join([
                "temperature_2m", "apparent_temperature", "precipitation_probability",
                "precipitation", "rain", "snowfall", "cloud_cover", "visibility",
                "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m", "surface_pressure",
            ]),
            "daily": ",".join([
                "temperature_2m_max", "temperature_2m_min", "precipitation_probability_max",
                "precipitation_sum", "rain_sum", "snowfall_sum", "wind_gusts_10m_max",
            ]),
        }
        started = time.perf_counter()
        if self._client is None:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        else:
            response = await self._client.get("https://api.open-meteo.com/v1/forecast", params=params)
        response.raise_for_status()
        payload = response.json()
        latency_ms = round((time.perf_counter() - started) * 1000)

        current_raw = payload.get("current") or {}
        current = CurrentWeather(
            temperature_c=current_raw.get("temperature_2m"),
            apparent_temperature_c=current_raw.get("apparent_temperature"),
            dew_point_c=current_raw.get("dew_point_2m"),
            relative_humidity_pct=current_raw.get("relative_humidity_2m"),
            pressure_hpa=current_raw.get("surface_pressure"),
            precipitation_mm=current_raw.get("precipitation"),
            rain_mm=current_raw.get("rain"),
            snowfall_cm=current_raw.get("snowfall"),
            cloud_cover_pct=current_raw.get("cloud_cover"),
            visibility_m=current_raw.get("visibility"),
            wind_speed_kmh=current_raw.get("wind_speed_10m"),
            wind_gust_kmh=current_raw.get("wind_gusts_10m"),
            wind_direction_deg=current_raw.get("wind_direction_10m"),
            weather_code=current_raw.get("weather_code"),
        )

        hourly_raw = payload.get("hourly") or {}
        hourly_times = hourly_raw.get("time", [])
        hourly = [
            HourlyPoint(
                time=datetime.fromisoformat(t),
                temperature_c=hourly_raw.get("temperature_2m", [None] * len(hourly_times))[i],
                apparent_temperature_c=hourly_raw.get("apparent_temperature", [None] * len(hourly_times))[i],
                precipitation_probability_pct=hourly_raw.get("precipitation_probability", [None] * len(hourly_times))[i],
                precipitation_mm=hourly_raw.get("precipitation", [None] * len(hourly_times))[i],
                rain_mm=hourly_raw.get("rain", [None] * len(hourly_times))[i],
                snowfall_cm=hourly_raw.get("snowfall", [None] * len(hourly_times))[i],
                cloud_cover_pct=hourly_raw.get("cloud_cover", [None] * len(hourly_times))[i],
                visibility_m=hourly_raw.get("visibility", [None] * len(hourly_times))[i],
                wind_speed_kmh=hourly_raw.get("wind_speed_10m", [None] * len(hourly_times))[i],
                wind_gust_kmh=hourly_raw.get("wind_gusts_10m", [None] * len(hourly_times))[i],
                wind_direction_deg=hourly_raw.get("wind_direction_10m", [None] * len(hourly_times))[i],
                pressure_hpa=hourly_raw.get("surface_pressure", [None] * len(hourly_times))[i],
            )
            for i, t in enumerate(hourly_times)
        ]

        daily_raw = payload.get("daily") or {}
        daily_times = daily_raw.get("time", [])
        daily = [
            DailyPoint(
                date=t,
                temperature_max_c=daily_raw.get("temperature_2m_max", [None] * len(daily_times))[i],
                temperature_min_c=daily_raw.get("temperature_2m_min", [None] * len(daily_times))[i],
                precipitation_probability_max_pct=daily_raw.get("precipitation_probability_max", [None] * len(daily_times))[i],
                precipitation_sum_mm=daily_raw.get("precipitation_sum", [None] * len(daily_times))[i],
                rain_sum_mm=daily_raw.get("rain_sum", [None] * len(daily_times))[i],
                snowfall_sum_cm=daily_raw.get("snowfall_sum", [None] * len(daily_times))[i],
                wind_gust_max_kmh=daily_raw.get("wind_gusts_10m_max", [None] * len(daily_times))[i],
            )
            for i, t in enumerate(daily_times)
        ]

        meta = SourceMeta(
            provider=self.name,
            model=payload.get("generationtime_ms", "best-match").__str__(),
            retrieved_at=datetime.now(timezone.utc),
            forecast_run=None,
            latency_ms=latency_ms,
        )
        return SourceForecast(current=current, hourly=hourly, daily=daily, meta=meta)
