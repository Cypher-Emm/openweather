from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import httpx

from weather.models import CurrentWeather, DailyPoint, HourlyPoint, Location, SourceMeta
from weather.sources.base import SourceForecast, WeatherSource


class OpenMeteoSource(WeatherSource):
    name = "open-meteo"

    def __init__(self, model: str = "best_match", client: httpx.AsyncClient | None = None) -> None:
        self.model = model
        self._client = client

    async def forecast(self, location: Location, now: datetime) -> SourceForecast:
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "elevation": location.elevation_m,
            "timezone": "auto",
            "forecast_days": 7,
            "models": self.model,
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
        client = self._client
        owns_client = client is None
        if owns_client:
            client = httpx.AsyncClient(timeout=20)
        try:
            response: httpx.Response | None = None
            for attempt in range(3):
                response = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
                if response.status_code != 429:
                    break
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = min(float(retry_after), 8.0) if retry_after else 2.0 * (attempt + 1)
                except ValueError:
                    delay = 2.0 * (attempt + 1)
                await asyncio.sleep(delay)
            assert response is not None
            response.raise_for_status()
        finally:
            if owns_client:
                await client.aclose()
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
        def h(name: str) -> list:
            return hourly_raw.get(name, [None] * len(hourly_times))
        hourly = [
            HourlyPoint(
                time=datetime.fromisoformat(t), temperature_c=h("temperature_2m")[i],
                apparent_temperature_c=h("apparent_temperature")[i],
                precipitation_probability_pct=h("precipitation_probability")[i],
                precipitation_mm=h("precipitation")[i], rain_mm=h("rain")[i],
                snowfall_cm=h("snowfall")[i], cloud_cover_pct=h("cloud_cover")[i],
                visibility_m=h("visibility")[i], wind_speed_kmh=h("wind_speed_10m")[i],
                wind_gust_kmh=h("wind_gusts_10m")[i], wind_direction_deg=h("wind_direction_10m")[i],
                pressure_hpa=h("surface_pressure")[i],
            ) for i, t in enumerate(hourly_times)
        ]

        daily_raw = payload.get("daily") or {}
        daily_times = daily_raw.get("time", [])
        def d(name: str) -> list:
            return daily_raw.get(name, [None] * len(daily_times))
        daily = [
            DailyPoint(
                date=t, temperature_max_c=d("temperature_2m_max")[i],
                temperature_min_c=d("temperature_2m_min")[i],
                precipitation_probability_max_pct=d("precipitation_probability_max")[i],
                precipitation_sum_mm=d("precipitation_sum")[i], rain_sum_mm=d("rain_sum")[i],
                snowfall_sum_cm=d("snowfall_sum")[i], wind_gust_max_kmh=d("wind_gusts_10m_max")[i],
            ) for i, t in enumerate(daily_times)
        ]

        meta = SourceMeta(
            provider=self.name, model=self.model,
            retrieved_at=datetime.now(timezone.utc), latency_ms=latency_ms,
        )
        return SourceForecast(current=current, hourly=hourly, daily=daily, meta=meta)
