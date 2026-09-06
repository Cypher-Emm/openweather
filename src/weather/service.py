from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from weather.fusion import fuse
from weather.geography import get_location
from weather.models import Location, WeatherResult
from weather.sources.base import WeatherSource


class WeatherService:
    def __init__(self, sources: list[WeatherSource]) -> None:
        self.sources = sources

    async def get(self, location: Location) -> WeatherResult:
        now = datetime.now(timezone.utc)
        results = await asyncio.gather(
            *(source.forecast(location, now) for source in self.sources),
            return_exceptions=True,
        )
        usable = [result for result in results if not isinstance(result, Exception)]
        if not usable:
            errors = "; ".join(str(result) for result in results if isinstance(result, Exception))
            raise RuntimeError(f"All weather sources failed: {errors}")
        return fuse(location, usable)

    async def by_name(self, name: str) -> WeatherResult:
        return await self.get(get_location(name))
