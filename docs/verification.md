# Forecast verification

OpenWeather does not treat model agreement as proof of accuracy.

Every future observation adapter should retain:

- location/station identifier
- observation timestamp in UTC
- variable and unit
- source/provider
- quality flags

Forecast runs should retain:

- model/provider
- model run time
- valid time
- location
- forecast variable
- lead time

## Metrics

For continuous variables such as temperature and wind speed, calculate MAE, RMSE and bias. For probabilistic precipitation/snow events, calculate Brier score and reliability. Verification must be stratified by:

- district
- elevation band
- season/month
- forecast lead time
- variable

Source weights must eventually come from these measured skill scores. They must not be hand-tuned because one provider is assumed to be better.

## Kashmir-specific goal

The important end state is a verified error profile for each model and location class. That allows the deterministic fusion layer to use evidence-based weights and to expose uncertainty when models diverge, especially for mountain precipitation and snowfall.
