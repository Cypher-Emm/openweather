# OpenWeather — Kashmir Valley Weather Engine

A pure, deterministic weather engine for the Kashmir Valley. It is **not an AI model** and does not generate weather values with an LLM.

The engine ingests numerical weather forecasts/observations, validates them, normalizes units, compares independent model guidance, and produces a stable weather product for districts, towns, hill stations, and arbitrary coordinates.

## Scope

OpenWeather is designed around the full Kashmir Valley weather network, not Srinagar alone.

- 10 Kashmir Valley districts
- Major towns and population centres
- Hill stations and high-altitude destinations
- Mountain corridors and passes as the catalogue grows
- Arbitrary latitude/longitude queries

## Design principles

1. **Physics/data first** — weather values come from meteorological data providers.
2. **Deterministic** — the same source inputs produce the same fusion result.
3. **Multi-model** — independent forecast guidance can be compared rather than blindly trusting one provider.
4. **Elevation aware** — high-altitude locations are first-class locations.
5. **Freshness aware** — every result carries source/run/freshness metadata.
6. **Confidence is evidence-based** — confidence reflects agreement, freshness and quality, not invented certainty.
7. **Provider-independent core** — adapters can be added without changing the API or fusion engine.
8. **Verifiable** — historical forecasts and observations are retained so forecast skill can be measured.
9. **No AI dependency** — no LLM is required anywhere in the weather calculation path.

## Initial architecture

```text
Weather providers
      │
      ▼
Source adapters ──► normalized model fields
      │
      ▼
Quality checks ──► invalid/stale/outlier rejection
      │
      ▼
Fusion engine ──► deterministic weighted consensus
      │
      ├──► current weather
      ├──► hourly/daily forecast
      ├──► snow/rain analysis
      ├──► mountain analysis
      └──► confidence + provenance
      │
      ▼
FastAPI /v1
```

## Data sources

The first production adapter targets Open-Meteo. Its API exposes forecast data from multiple national weather-service models, including ECMWF, NOAA, DWD, and others, and supports historical forecast/run archives useful for verification. See `docs/data-sources.md`.

ECMWF IFS open data is also available under ECMWF's open-data terms; the project keeps provider adapters separate so a native ECMWF ingestion path can be added without changing the engine.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn weather.api.app:app --reload
```

Then open `/docs` or query:

```text
GET /v1/weather/current?lat=34.0484&lon=74.7973
GET /v1/weather/forecast?location=gulmarg
GET /v1/valley/overview
GET /v1/locations
```

## Accuracy roadmap

The first release is a **weather data/fusion engine**, not a claimed Kashmir-specific forecast model. Accuracy must be demonstrated against observations.

1. Multi-model ingestion
2. Station/observation ingestion
3. Persistent forecast + observation archive
4. Automated forecast verification (MAE/RMSE/bias/CRPS where appropriate)
5. Kashmir-specific bias correction by elevation, season and location class
6. Ensemble/uncertainty products
7. Expanded IMD/MOSDAC and other authoritative data adapters where access is technically and legally available

Do not market a forecast as "accurate" merely because several APIs agree. The repository will earn that claim through verification.
