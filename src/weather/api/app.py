from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Query

from weather.geography import DISTRICTS, HILL_STATIONS, LOCATIONS
from weather.models import DistrictSummary, Location, ValleyOverview
from weather.service import WeatherService
from weather.sources.open_meteo import OpenMeteoSource

app = FastAPI(
    title="OpenWeather — Kashmir Valley Weather Engine",
    version="0.1.0",
    description="Deterministic multi-source weather engine for Kashmir Valley locations.",
)


@lru_cache(maxsize=1)
def service() -> WeatherService:
    # Three independent global model families. The fusion layer never asks an LLM to choose weather values.
    models = ("ecmwf_ifs", "ncep_gfs_seamless", "icon_seamless")
    return WeatherService([OpenMeteoSource(model=model) for model in models])


@app.get("/v1/health")
def health() -> dict[str, str]:
    return {"status": "ok", "engine": "openweather", "mode": "deterministic"}


@app.get("/v1/locations")
def locations():
    return LOCATIONS


@app.get("/v1/weather/current")
async def current(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    elevation_m: float = Query(0, ge=-500, le=10000),
):
    location = Location(
        id=f"coord_{lat}_{lon}", name="Coordinate", kind="town",
        latitude=lat, longitude=lon, elevation_m=elevation_m,
    )
    return await service().get(location)


@app.get("/v1/weather/forecast")
async def forecast(location: str):
    from weather.geography import get_location
    try:
        return await service().by_name(location)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/valley/overview", response_model=ValleyOverview)
async def valley_overview():
    district_results = await asyncio.gather(*(service().get(x) for x in DISTRICTS))
    hill_results = await asyncio.gather(*(service().get(x) for x in HILL_STATIONS))
    districts = [
        DistrictSummary(district=location.name, representative_location=location.id, weather=result)
        for location, result in zip(DISTRICTS, district_results)
    ]
    return ValleyOverview(
        generated_at=datetime.now(timezone.utc), districts=districts, hill_stations=list(hill_results)
    )
