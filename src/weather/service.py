from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from weather.fusion import fuse
from weather.geography import get_location
from weather.models import Location, WeatherResult
from weather.sources.base import WeatherSource


class WeatherService:
    """Provider orchestration with bounded concurrency and a short in-memory cache."""

    def __init__(self, sources: list[WeatherSource], cache_ttl_seconds: int = 300, max_concurrency: int = 1) -> None:
        self.sources = sources
        self.cache_ttl_seconds = cache_ttl_seconds
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._cache: dict[str, tuple[float, WeatherResult]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _key(self, location: Location) -> str:
        return f"{location.latitude:.5f}:{location.longitude:.5f}:{location.elevation_m:.0f}"

    async def _fetch_one_source(self, source: WeatherSource, location: Location, now: datetime):
        try:
            return await source.forecast(location, now)
        except Exception:
            return None

    async def get(self, location: Location, force_refresh: bool = False) -> WeatherResult:
        key = self._key(location)
        now_mono = time.monotonic()
        cached = self._cache.get(key)
        if not force_refresh and cached and now_mono - cached[0] < self.cache_ttl_seconds:
            return cached[1]

        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            now_mono = time.monotonic()
            cached = self._cache.get(key)
            if not force_refresh and cached and now_mono - cached[0] < self.cache_ttl_seconds:
                return cached[1]
            async with self._semaphore:
                now = datetime.now(timezone.utc)
                results = await asyncio.gather(*(self._fetch_one_source(source, location, now) for source in self.sources))
                usable = [result for result in results if result is not None]
                if not usable:
                    raise RuntimeError("All weather sources failed")
                result = fuse(location, usable)
            self._cache[key] = (time.monotonic(), result)
            return result

    async def get_many(self, locations: tuple[Location, ...], force_refresh: bool = False) -> list[WeatherResult]:
        """Fetch a location set from every provider concurrently, then fuse each location."""
        if not locations:
            return []

        cached_results: list[WeatherResult | None] = [None] * len(locations)
        missing: list[tuple[int, Location]] = []
        now_mono = time.monotonic()

        for index, location in enumerate(locations):
            cached = self._cache.get(self._key(location))
            if not force_refresh and cached and now_mono - cached[0] < self.cache_ttl_seconds:
                cached_results[index] = cached[1]
            else:
                missing.append((index, location))

        if not missing:
            return [result for result in cached_results if result is not None]

        missing_locations = [location for _, location in missing]
        async with self._semaphore:
            now = datetime.now(timezone.utc)
            batches = await asyncio.gather(
                *(source.forecast_many(missing_locations, now) for source in self.sources),
                return_exceptions=True,
            )

        usable_batches = [batch for batch in batches if not isinstance(batch, Exception)]
        if not usable_batches:
            raise RuntimeError("All weather sources failed")

        for offset, (index, location) in enumerate(missing):
            forecasts = [batch[offset] for batch in usable_batches if offset < len(batch)]
            if not forecasts:
                raise RuntimeError(f"No usable weather forecast for {location.id}")
            fused = fuse(location, forecasts)
            self._cache[self._key(location)] = (time.monotonic(), fused)
            cached_results[index] = fused

        return [result for result in cached_results if result is not None]

    async def by_name(self, name: str, force_refresh: bool = False) -> WeatherResult:
        return await self.get(get_location(name), force_refresh=force_refresh)

    def cache_stats(self) -> dict[str, int]:
        return {"entries": len(self._cache), "ttl_seconds": self.cache_ttl_seconds}
