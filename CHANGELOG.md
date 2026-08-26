# Changelog

## Unreleased - 2026-08-26

### Fixed

- Include the geocoder, GeoPandas, and Shapely runtime dependencies in default installations so the tutorial can generate GMNS links without silently returning `None`.
- Keep the tutorial's optional SUMO conversion disabled by default and document in both the tutorial and conversion output that SUMO's `netconvert` executable must be available on the system `PATH` before enabling it.

## Unreleased - 2026-08-25

### Fixed

- Report a clear, actionable `ImportError` when `geopy` is unavailable during node geocoding instead of returning `None` and later raising an unrelated unpacking error.
