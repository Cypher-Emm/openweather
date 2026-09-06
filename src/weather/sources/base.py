from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from weather.models import CurrentWeather, DailyPoint, HourlyPoint, Location, SourceMeta


@dataclass(frozen=True)
class SourceForecast:
    current: CurrentWeather | None
    hourly: list[HourlyPoint]
    daily: list[DailyPoint]
    meta: SourceMeta


class WeatherSource(ABC):
    name: str

    @abstractmethod
    async def forecast(self, location: Location, now: datetime) -> SourceForecast:
        raise NotImplementedError

    async def forecast_many(self, locations: list[Location], now: datetime) -> list[SourceForecast]:
        return await asyncio.gather(*(self.forecast(location, now) for location in locations))
