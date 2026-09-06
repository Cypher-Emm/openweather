from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from datetime import datetime, timezone

import httpx

from weather.models import CurrentWeather, DailyPoint, HourlyPoint, Location, SourceMeta
from weather.sources.base import SourceForecast, WeatherSource


class MetNoSource(WeatherSource):
    """Global ECMWF-backed provider using MET Norway Locationforecast 2.0 complete data."""

    name = "met-no"
    endpoint = "https://api.met.no/weatherapi/locationforecast/2.0/complete"
    user_agent = "KashmirOpenWeather/1.0 https://github.com/Cypher-Emm/openweather"

    async def forecast(self, location: Location, now: datetime) -> SourceForecast:
        return (await self.forecast_many([location], now))[0]

    async def forecast_many(self, locations: list[Location], now: datetime) -> list[SourceForecast]:
        if not locations:
            return []
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": self.user_agent, "Accept": "application/json"}) as client:
            semaphore = asyncio.Semaphore(4)

            async def fetch(location: Location) -> SourceForecast:
                async with semaphore:
                    started = time.perf_counter()
                    response = await client.get(self.endpoint, params={"lat": round(location.latitude, 4), "lon": round(location.longitude, 4), "altitude": round(location.elevation_m)})
                    response.raise_for_status()
                    return self._parse_payload(response.json(), round((time.perf_counter() - started) * 1000))

            return await asyncio.gather(*(fetch(location) for location in locations))

    @classmethod
    def _parse_payload(cls, payload: dict, latency_ms: int) -> SourceForecast:
        series = payload.get("properties", {}).get("timeseries", [])
        if not series:
            raise RuntimeError("MET Norway returned no forecast timeseries")
        hourly: list[HourlyPoint] = []
        daily_values: dict[str, list[dict]] = defaultdict(list)
        for point in series:
            timestamp = datetime.fromisoformat(point["time"].replace("Z", "+00:00"))
            data = point.get("data", {})
            instant = data.get("instant", {}).get("details", {})
            periods = [data.get("next_1_hours", {}), data.get("next_6_hours", {}), data.get("next_12_hours", {})]
            period_details = [p.get("details", {}) for p in periods]
            probabilities = [d.get("probability_of_precipitation") for d in period_details if isinstance(d.get("probability_of_precipitation"), (int, float))]
            precip_values = [d.get("precipitation_amount") for d in period_details if isinstance(d.get("precipitation_amount"), (int, float))]
            probability = max(probabilities) if probabilities else None
            precipitation = precip_values[0] if precip_values else None
            symbol = next((p.get("summary", {}).get("symbol_code") for p in periods if p.get("summary", {}).get("symbol_code")), None)
            hourly.append(HourlyPoint(
                time=timestamp, temperature_c=instant.get("air_temperature"), apparent_temperature_c=None,
                precipitation_probability_pct=probability, precipitation_mm=precipitation, rain_mm=precipitation,
                snowfall_cm=None, cloud_cover_pct=instant.get("cloud_area_fraction"), visibility_m=None,
                wind_speed_kmh=_mps_to_kmh(instant.get("wind_speed")), wind_gust_kmh=_mps_to_kmh(instant.get("wind_speed_of_gust")),
                wind_direction_deg=instant.get("wind_from_direction"), pressure_hpa=instant.get("air_pressure_at_sea_level"),
                weather_code=_symbol_to_code(symbol),
            ))
            local_date = timestamp.astimezone(timezone.utc).date().isoformat()
            daily_values[local_date].append({"temp": instant.get("air_temperature"), "precip": precipitation, "probability": probability, "gust": _mps_to_kmh(instant.get("wind_speed_of_gust"))})

        first = series[0]
        first_data = first.get("data", {})
        first_instant = first_data.get("instant", {}).get("details", {})
        first_periods = [first_data.get("next_1_hours", {}), first_data.get("next_6_hours", {}), first_data.get("next_12_hours", {})]
        first_probabilities = [p.get("details", {}).get("probability_of_precipitation") for p in first_periods if isinstance(p.get("details", {}).get("probability_of_precipitation"), (int, float))]
        first_period = next((p for p in first_periods if p.get("details")), {})
        first_details = first_period.get("details", {})
        symbol = next((p.get("summary", {}).get("symbol_code") for p in first_periods if p.get("summary", {}).get("symbol_code")), None)
        current = CurrentWeather(
            temperature_c=first_instant.get("air_temperature"), apparent_temperature_c=None, dew_point_c=first_instant.get("dew_point_temperature"),
            relative_humidity_pct=first_instant.get("relative_humidity"), pressure_hpa=first_instant.get("air_pressure_at_sea_level"),
            precipitation_probability_pct=max(first_probabilities) if first_probabilities else None,
            precipitation_mm=first_details.get("precipitation_amount"), rain_mm=first_details.get("precipitation_amount"), snowfall_cm=None,
            cloud_cover_pct=first_instant.get("cloud_area_fraction"), visibility_m=None, wind_speed_kmh=_mps_to_kmh(first_instant.get("wind_speed")),
            wind_gust_kmh=_mps_to_kmh(first_instant.get("wind_speed_of_gust")), wind_direction_deg=first_instant.get("wind_from_direction"), weather_code=_symbol_to_code(symbol),
        )
        daily: list[DailyPoint] = []
        for date, values in sorted(daily_values.items())[:9]:
            temps = [v["temp"] for v in values if isinstance(v["temp"], (int, float))]
            precip = [v["precip"] for v in values if isinstance(v["precip"], (int, float))]
            probs = [v["probability"] for v in values if isinstance(v["probability"], (int, float))]
            gusts = [v["gust"] for v in values if isinstance(v["gust"], (int, float))]
            daily.append(DailyPoint(date=date, temperature_max_c=max(temps) if temps else None, temperature_min_c=min(temps) if temps else None,
                precipitation_probability_max_pct=max(probs) if probs else None, precipitation_sum_mm=sum(precip) if precip else None,
                rain_sum_mm=sum(precip) if precip else None, snowfall_sum_cm=None, wind_gust_max_kmh=max(gusts) if gusts else None))
        meta = SourceMeta(provider="met.no", model="Locationforecast 2.0 / ECMWF", retrieved_at=datetime.now(timezone.utc), latency_ms=latency_ms)
        return SourceForecast(current=current, hourly=hourly, daily=daily, meta=meta)


def _mps_to_kmh(value: float | None) -> float | None:
    return round(value * 3.6, 1) if isinstance(value, (int, float)) else None


def _symbol_to_code(symbol: str | None) -> int | None:
    if not symbol:
        return None
    base = symbol.split("_")[0].lower()
    mapping = {"clearsky": 0, "fair": 1, "partlycloudy": 2, "cloudy": 3, "fog": 45, "lightrain": 61, "rain": 63, "heavyrain": 65,
               "lightrainshowers": 80, "rainshowers": 81, "heavyrainshowers": 82, "lightsnow": 71, "snow": 73, "heavysnow": 75,
               "lightsnowshowers": 85, "snowshowers": 85, "heavysnowshowers": 86, "sleet": 67, "lightsleet": 67, "heavysleet": 67, "thunderstorm": 95}
    return mapping.get(base, 3)
