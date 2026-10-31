# Changelog

## Unreleased - 2026-10-31

### Documentation

- Add the published, version-specific Zenodo DOI `10.5281/zenodo.23817796` and its DOI badge to the README for the final JOSS archive check.

### Validation

- Confirm that the DOI resolves publicly, DataCite lists it as findable for version 1.2.6, and the badge returns SVG successfully. Match the archive title, author order, ORCIDs, affiliations, and MIT license to the manuscript.
- Confirm that all 38 archived runtime source files match release v1.2.6, allowing line-ending differences. The archive ZIP contains the runtime package only; it does not include the tutorial dataset, manuscript, or repository installation files. No runtime code changed, so application tests were not rerun.

## 1.2.6 - 2026-10-30

### Documentation and release metadata

- Address the final JOSS editorial corrections: define acronyms and Synchro at first use, introduce and consistently name Sigma-X, correct citation spacing and documentation link text, and preserve removal of the manuscript's self-citation.
- Move review-driven improvements and funding/public-access text into Acknowledgements; replace the fragment thanking Milan Zlatkovic with a complete sentence. Retain the scientific impact and collaboration evidence and move GitHub issue/PR citations to footnotes.
- Complete the Ban and Coogan technical reports from National Transportation Library records; correct the Berg meeting reference, SUMO authors and proceedings fields, Smith report authors/institution, thesis school field, and Real-Twin software DOI. Remove four issue/PR bibliography entries now represented by footnotes.
- Correct the Bullhead region name in the manuscript and standalone tutorial. State the repository checkout/install requirements, reference-coordinate convention, and generated output location without claiming the dataset is installed by package distributions.
- Prepare version 1.2.6 consistently in `pyproject.toml`, `utdf2gmns/__init__.py`, and `docs/source/conf.py`. Add `.zenodo.json` with the manuscript title, MIT license, and author order, names, affiliations, and ORCIDs confirmed by the submitting author on October 30, 2026. Preserve the distinct conference-paper preferred citation in `CITATION.cff`.
- Record the response to all 14 editorial requests in `paper/editor_response_20261030.md`.

### Validation

- Python 3.13.11: all 53 existing tests pass with one existing pandas warning about non-unique columns. Workspace temporary directories avoid a Windows sandbox temporary-directory permission error.
- Execute the exact manuscript Python block in an isolated copy: 22 nodes, 42 links, 95 lanes, 72 movements, and all 8 signalized intersections exported; the tracked input CSV remains byte-for-byte unchanged.
- Build a wheel and source distribution without changing the existing distribution directory; inspect both archive contents for the tutorial dataset and Python sources.
- Resolve all 17 citation keys against 17 unique bibliography entries, verify all 12 supplied DOIs through Crossref/DataCite, and match Zenodo title, author order, ORCIDs, and affiliations to the manuscript metadata. Verify report details against the original National Transportation Library and Transportation Research Board records.
- Ruff lint passes for the standalone tutorial. Its formatting check reports pre-existing formatting; leave unrelated formatting unchanged. Optional SUMO, interactive plotting, and desktop Excel/Sigma-X execution are not part of the default tutorial validation.

## Unreleased - 2026-10-29

### Fixed

- Remove obsolete Python 3.10.12, 3.11.8, and 3.12.2 matrix entries that fail interpreter setup on the Ubuntu 26.04 runner; retain Python 3.10, 3.11, 3.12, and 3.13 coverage.
- Add the missing `.gitmodules` path and repository URL for the existing `utdf2gmns_datasets` gitlink so Git can resolve the submodule during checkout cleanup.

### Validation

- Parse the workflow YAML, confirm that only the Python version matrix changes, validate submodule metadata and traversal without changing the dataset commit, and pass `git diff --check`. GitHub Actions execution remains pending publication of these fixes.

## Unreleased - 2026-10-23

### Documentation and validation

- Explain conversion-stage architecture, I/O coupling, shared helpers, and dependency trade-offs in the existing Software design section; preserve the Research impact statement and October 14 collaboration response.
- Render detailed public conversion method docstrings from the API reference source page.
- Align manuscript tutorial optional steps with the standalone tutorial prerequisites.
- Run both test workflows on `joss`, install the checked-out package, and propagate pytest failures while preserving result artifacts.
- Local Python 3.12 validation: 53 tests passed; Sphinx HTML build completed. Bullhead GMNS export and a 300-second SUMO 1.28.0 run completed, with unsafe-green warnings at intersections 78, 84, and 98 requiring further signal validation.

## Unreleased - 2026-10-08

### Documentation

- Document collaborative project conception, another developer's signal-conversion contributions, DOE-supported Real-Twin research use, and improvements prompted by JOSS review feedback in the paper's Research impact statement.
- Add references to the contribution, public feedback, Real-Twin project, and Sim2Signal's citation of the UTDF-to-SUMO workflow;
- Refresh the local manuscript preview and document its build commands and preview metadata in the paper folder.

### Validation

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
