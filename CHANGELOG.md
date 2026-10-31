# Changelog

## Unreleased - 2026-10-31

### Branch synchronization

- Merge `dev` at `ce550d8` into `main`, excluding every file under `paper/` and leaving the `joss` branch unchanged. Keep the current README and published Zenodo DOI badge.
- Bring in the Chattanooga and additional Tempe datasets, generated examples, documentation assets, GitHub documentation context, geocoding return documentation, and geographic utility functions from `dev`.
- Resolve overlapping older SUMO changes in favor of `main`'s current conversion APIs, signal/turn-bay implementation, reproducible tutorial, Bullhead map, and newer `utdf2gmns_datasets` submodule revision. Preserve the existing `point_on_line` utility name and correct the imported documentation link URL.

### Documentation

- Add the published, version-specific Zenodo DOI `10.5281/zenodo.23817796` and its DOI badge to the README for the final JOSS archive check.

### Validation

- Branch synchronization: 56 tests pass with one existing pandas warning; the Sphinx HTML build succeeds; 24 incoming XML/configuration files parse successfully, and both imported UTDF inputs load with nonempty intersection lists (26 Chattanooga and 756 Tempe intersections). The Tempe input also emits formatting warnings from the existing parser. Ruff passes for the changed utility, geocoding, and test modules. The documentation configuration retains its four pre-existing Ruff findings, and imported datasets retain their original whitespace warnings.
- Confirm that the DOI resolves publicly, DataCite lists it as findable for version 1.2.6, and the badge returns SVG successfully. Match the archive title, author order, ORCIDs, affiliations, and MIT license to the manuscript.
- Confirm that all 38 archived runtime source files match release v1.2.6, allowing line-ending differences. The archive ZIP contains the runtime package only; it does not include the tutorial dataset, manuscript, or repository installation files. No runtime code changed, so application tests were not rerun.

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
