# Data sources

## Initial source: Open-Meteo

Open-Meteo is used as the first adapter because its forecast API can expose individual model families rather than forcing the engine to accept one opaque forecast. The current engine queries:

- ECMWF IFS
- NOAA/NCEP GFS seamless
- DWD ICON seamless

The adapter normalizes those responses into one internal schema. The fusion layer then calculates a deterministic consensus and records source/model metadata.

Open-Meteo documents that its API can combine national weather-service models and that individual models can be selected explicitly. Its current model catalogue includes ECMWF IFS, NCEP GFS, DWD ICON and many others. The API also supports elevation-aware grid-cell selection. See the upstream documentation before changing model IDs or variables.

## ECMWF

ECMWF publishes a subset of real-time IFS/AIFS forecast data as open data under CC-BY-4.0 and its terms of use. A native ECMWF adapter is planned so OpenWeather can ingest authoritative files directly instead of depending exclusively on a downstream API.

## IMD / Indian observations

An IMD/MOSDAC adapter is deliberately not hard-coded to an undocumented endpoint. Once an official, stable and legally usable API/file feed is identified, it should be added as a provider adapter with provenance, station IDs, observation timestamps and licensing metadata.

## Accuracy rule

Multiple models are not automatically more accurate. The project must retain forecast runs and compare them against observations. Future verification should report at least:

- temperature MAE and bias
- precipitation bias and categorical scores
- wind-speed error
- snowfall error where trustworthy observations exist
- reliability/calibration for probabilistic forecasts
- skill by district, elevation band and season

Only verified skill should drive source weights. Until then, the initial fusion is intentionally conservative and transparent.
