# Changelog

## Unreleased - 2026-10-08

### Documentation

- Synchronize the README, contribution guide, issue configuration, and framework images from `joss` into `main`, keeping all files under `paper/` excluded from `main`.
- Document collaborative project conception, another developer's signal-conversion contributions, DOE-supported Real-Twin research use, and improvements prompted by JOSS review feedback in the paper's Research impact statement.
- Add references to the contribution, public feedback, Real-Twin project, and Sim2Signal's citation of the UTDF-to-SUMO workflow;
- Refresh the local manuscript preview and document its build commands and preview metadata in the paper folder.

### Validation

- Verify that the synchronization changes only the six intended files outside `paper/`, matches `joss` except for this changelog record, includes valid YAML and documentation assets, and passes `git diff --cached --check`.
- The existing test suite passes in the `ug` environment: 53 passed, with one existing pandas warning about non-unique columns.
- All 21 manuscript citation keys resolve without duplicate bibliography entries; the manuscript contains approximately 1,675 words including the tutorial and excluding metadata and references.
- The edited support configuration parses successfully, and the local seven-page PDF compiles and passes visual inspection.
- Official JOSS Docker rendering was not run because the Docker daemon is unavailable. The reviewer response is saved locally for posting after the revisions are published on `joss`.

## Unreleased - 2026-10-07

### Fixed

- Restore explicit Setuptools package discovery and package-data rules so distributions include the `utdf2gmns` Python sources and Sigma-X workbook/CSV assets while excluding repository tests.
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
