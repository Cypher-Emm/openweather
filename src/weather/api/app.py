from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query

from weather.geography import DISTRICTS, HILL_STATIONS, LOCATIONS, get_location
from weather.models import DistrictSummary, Location, ValleyOverview
from weather.service import WeatherService
from weather.sources.met_no import MetNoSource

app = FastAPI(
    title="OpenWeather — Kashmir Valley Weather Engine",
    version="0.3.0",
    description="Deterministic weather engine for Kashmir Valley locations with a global MET Norway fallback provider.",
)


@lru_cache(maxsize=1)
def service() -> WeatherService:
    # MET Norway provides global Locationforecast coverage and avoids the
    # Open-Meteo IP throttling that was making the production engine return 500s.
    return WeatherService([MetNoSource()])


@app.get("/v1/health")
def health() -> dict:
    return {
        "status": "ok",
        "engine": "openweather",
        "mode": "deterministic",
        "sources": len(service().sources),
        "cache": service().cache_stats(),
    }


@app.get("/v1/locations")
def locations():
    return LOCATIONS


@app.get("/v1/locations/{location_id}")
def location(location_id: str):
    try:
        return get_location(location_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/weather/current")
async def current(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    elevation_m: float | None = Query(None, ge=-500, le=10000),
    refresh: bool = Query(False),
):
    location = Location(
        id=f"coord_{lat}_{lon}",
        name="Coordinate",
        kind="town",
        latitude=lat,
        longitude=lon,
        elevation_m=elevation_m if elevation_m is not None else 0,
    )
    return await service().get(location, force_refresh=refresh)


@app.get("/v1/weather/forecast")
async def forecast(location: str, refresh: bool = Query(False)):
    try:
        return await service().by_name(location, force_refresh=refresh)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/valley/overview", response_model=ValleyOverview)
async def valley_overview():
    all_locations = tuple(DISTRICTS) + tuple(HILL_STATIONS)
    results = await service().get_many(all_locations)
    district_count = len(DISTRICTS)
    district_results = results[:district_count]
    hill_results = results[district_count:]
    districts = [
        DistrictSummary(district=location.name, representative_location=location.id, weather=result)
        for location, result in zip(DISTRICTS, district_results)
    ]
    return ValleyOverview(
        generated_at=datetime.now(timezone.utc),
        districts=districts,
        hill_stations=list(hill_results),
    )
