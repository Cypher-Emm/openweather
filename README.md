# OpenWeather — Kashmir Valley Weather Engine

A pure, deterministic weather engine for the Kashmir Valley. It is **not an AI model** and does not generate weather values with an LLM.

OpenWeather ingests numerical weather guidance and observations, validates and normalizes them, compares independent models, and produces a stable weather product for districts, towns, hill stations, mountain corridors, and arbitrary coordinates.

## Scope

OpenWeather is designed around the full Kashmir Valley weather network, not Srinagar alone.

- 10 districts
- Major towns and population centres
- Hill stations and high-altitude destinations
- Mountain corridors and passes
- Arbitrary latitude/longitude queries

## Design principles

1. **Meteorological data first** — values come from weather providers or observations.
2. **Deterministic** — identical inputs produce identical fusion output.
3. **Multi-model** — independent model guidance is compared instead of blindly trusting one provider.
4. **Robust fusion** — median aggregation reduces the impact of a single model outlier; circular statistics are used for wind direction.
5. **Elevation aware** — high-altitude locations are first-class locations.
6. **Freshness aware** — source retrieval metadata is preserved and stale data lowers quality.
7. **Evidence-based quality** — model agreement and freshness are reported explicitly; they are not presented as forecast accuracy.
8. **Provider-independent core** — new adapters do not require changing the fusion/API layer.
9. **Verifiable** — forecast runs and observations can be scored by variable, lead time, elevation and season.
10. **No AI dependency** — no LLM is required anywhere in the weather calculation path.

## Architecture

```text
Weather providers / observations
              │
              ▼
       Source adapters
              │
              ▼
   validation + normalization
              │
              ▼
 robust deterministic fusion
              │
       ┌──────┼─────────┐
       ▼      ▼         ▼
    current  hourly    daily
       │      │         │
       └──────┼─────────┘
              ▼
     quality + provenance
              │
              ▼
          FastAPI /v1
```

## Current model guidance

The initial engine explicitly compares ECMWF IFS, NOAA/NCEP GFS and DWD ICON through the Open-Meteo forecast interface. Open-Meteo documents model selection and historical forecast access; its current catalogue includes these model families. The engine keeps the adapter boundary so native provider ingestion can be added later.

ECMWF also publishes a subset of real-time IFS/AIFS data as open data under its stated terms. See `docs/data-sources.md`.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn weather.api.app:app --reload
```

Useful endpoints:

```text
GET /v1/health
GET /v1/locations
GET /v1/locations/gulmarg
GET /v1/weather/current?lat=34.0484&lon=74.3805&elevation_m=2650
GET /v1/weather/forecast?location=gulmarg
GET /v1/valley/overview
```

## Accuracy roadmap

The engine does **not** claim Kashmir-specific forecast accuracy yet. Accuracy must be earned against observations.

1. Multi-model ingestion
2. Station/observation ingestion
3. Persistent forecast-run + observation archive
4. Automated verification: MAE, RMSE, bias, probabilistic reliability/Brier score
5. Verification stratified by district, elevation, season and forecast lead time
6. Evidence-based model weighting
7. Kashmir-specific bias correction
8. Snowfall/precipitation verification and mountain-risk products
9. Native authoritative feeds where access is technically and legally available

See `docs/verification.md`.
