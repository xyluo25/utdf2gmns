# Changelog

## Unreleased - 2026-10-07

### Fixed

- Restore explicit Setuptools package discovery so source distributions and wheels include the `utdf2gmns` Python packages.

- Constrain Setuptools below version 82 when installing the optional Kepler.gl visualization dependencies because the latest stable Kepler.gl release still imports the removed `pkg_resources` module.
- Fix reStructuredText list and docstring indentation and exclude generated documentation output from Sphinx source discovery.
- Align Read the Docs installation and optional-workflow guidance with the current package extras, platform support, and external application requirements.
- Make the recommended paper citation directly copyable and horizontally scrollable on the Read the Docs support page.

## Unreleased - 2026-10-06

### Fixed

- Treat Sigma-X visualization as an explicit Windows/macOS-only optional feature, skip it cleanly on Linux, and report its actual success status instead of raising an xlwings interactive-mode error.
- Keep the platform-specific xlwings dependency out of the general `base` extra and leave the Sigma-X tutorial step disabled by default.

## Unreleased - 2026-08-26

### Fixed

- Include the geocoder, GeoPandas, and Shapely runtime dependencies in default installations so the tutorial can generate GMNS links without silently returning `None`.
- Keep the tutorial's optional SUMO conversion disabled by default and document in both the tutorial and conversion output that SUMO's `netconvert` executable must be available on the system `PATH` before enabling it.

## Unreleased - 2026-08-25

### Fixed

- Report a clear, actionable `ImportError` when `geopy` is unavailable during node geocoding instead of returning `None` and later raising an unrelated unpacking error.
