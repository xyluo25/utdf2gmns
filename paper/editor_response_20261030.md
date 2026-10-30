# Final editorial corrections — October 30, 2026

Source: [Fangzhou Xie's final checklist](https://github.com/openjournals/joss-reviews/issues/10619#issuecomment-6525591358).

This audit maps all 14 requests to the corrected sources on `joss`. It preserves the existing scientific discussion and the distinct Winter Simulation Conference publication. Release/archive publication is recorded separately in the GitHub release and public response; the metadata below does not itself establish that an archive DOI has been registered.

| ID | Editor's request | Response and evidence |
| --- | --- | --- |
| E.1 | Acknowledge improvements made during JOSS review rather than present them as Research Impact. | Move the review-feedback paragraph into **Acknowledgements**, crediting Anita Graser and Georgia Stuart. Keep the research-use and developer-contribution evidence in **Research impact statement**. |
| E.2 | Mention GitHub issues/PRs in footnotes rather than as references. | Add `contribution` and `review-feedback` footnotes in `paper.md`. Remove the PR #1 and issue #15/#17/#18 bibliography entries. |
| E.3 | Expand acronyms at first use; introduce Sigma-X and identify Synchro. | Define UTDF, SUMO, GMNS, and GIS in **Summary**; identify Synchro as commercial traffic signal-timing software and introduce Sigma-X as a signalized-intersection analysis and visualization tool. Also define OSM, XML, I/O, PyPI, DOE, EERE, EEMS, USDOT, and JOSS at their first prose use. |
| E.4 | Move the initial funding information into Acknowledgements. | Move the UT-Battelle contract and DOE public-access statement from the opening footnote into **Acknowledgements**, retaining the contract number and public-access link. Group the existing DOE/Real-Twin funding information there. |
| E.5 | Insert the missing space after “gaps”. | Correct to `gaps [@zhang2024integration; ...]` in **Statement of need**. |
| E.6 | Replace “Official-Documentation” with proper link text. | Use “The documentation is available at [Read the Docs](https://utdf2gmns.readthedocs.io/en/latest/).” |
| E.7 | Use a consistent Sigma-X spelling. | Use **Sigma-X** throughout prose. Preserve the case-sensitive `sigma-x` installation-extra identifier in the tutorial code. |
| E.8 | Remove the leading space in the tutorial region and confirm the CSV ships with the repository. | Use `region_name = "Bullhead City, AZ"` in the paper and standalone tutorial. Confirm `datasets/data_bullhead_seg4/UTDF.csv` is tracked by Git. Explain running from an installed repository checkout, coordinate units/order, and the output directory. Execute the exact manuscript code block in an isolated copy; see validation below. |
| E.9 | Replace the fragment acknowledging Milan Zlatkovic. | Use a complete sentence: “We thank Prof. Milan Zlatkovic (University of Wyoming) for Sigma-X, which is used to visualize signalized intersections.” |
| E.10 | Remove “Luo and Zhou 2022”, which cites this submission itself. | Preserve the local removal of that linked self-citation. Retain `luo2025automating`, a separate peer-reviewed conference paper documenting the workflow and case studies. |
| E.11 | Repair truncated references, including Ban (2022) and Coogan (2021). | Supply complete author lists, report institutions, Coogan's report number, and stable National Transportation Library URLs. Also complete the Berg conference record and SUMO author list, correct proceedings/thesis fields and the Smith author list, supply the Real-Twin software DOI, and use the IEEE Access volume's 2018 publication year. All 17 remaining citation keys resolve. |
| E.12 | Make a new GitHub release reflecting review changes. | Prepare **v1.2.6** from the corrected `joss` branch, with synchronized package/runtime/documentation versions and release notes describing review changes. See [GitHub releases](https://github.com/xyluo25/utdf2gmns/releases) for publication status. |
| E.13 | Make a Zenodo or equivalent archive. | Add `.zenodo.json` with the exact manuscript title, confirmed three-author order, affiliations, ORCIDs, version 1.2.6, and MIT license. Use the existing Zenodo/GitHub integration to archive the release; verify the resulting record before reporting its DOI. `CITATION.cff` retains the separate six-author conference preferred citation; `.zenodo.json` supplies archive metadata. |
| E.14 | Confirm author list and affiliations. | The submitting author confirmed all three names, order, ORCIDs, and affiliations in this working session on October 30, 2026. No changes to manuscript author metadata were needed. |

## Validation

- Existing suite: **53 passed**, with the existing warning about non-unique pandas columns. Python 3.13.11; command: `python -m pytest -q --basetemp=build/joss_editor_20261030/pytest_tmp`. An initial run hit sandbox temporary-directory permissions; using workspace temporary directories resolved those errors.
- Run the exact Python block extracted from `paper.md`, preserving the relative dataset path in an isolated directory. Export **22 nodes, 42 links, 95 lanes, 72 movements, and signal data for all 8 signalized intersections**. Check required CSV columns, nonempty rows, and signal JSON. The original CSV SHA-256 remains `0bc9ab56fb4418c710dda64958795d700b9a7146d520926a42829520faeb3a01`.
- Both a fresh source distribution and wheel build successfully with Python sources present. The Bullhead tutorial CSV is **not included in those package formats**. The paper therefore explicitly requires the repository checkout; this task does not change distribution layout. The repository and its GitHub source archive include the tracked CSV.
- Resolve all **17** manuscript citation keys against **17** unique bibliography entries, with no unused entries, truncated ellipses, or residual GitHub issue/PR bibliography records. Verify all **12** supplied DOIs through Crossref/DataCite; the original report/catalog records support the corrected metadata. Use SUMO's own recommended author order for its reference publication. Request a fresh JOSS bot check for the revised bibliography, including the added Real-Twin DOI.
- Ruff lint passes for `tutorial_utdf2gmns.py`; the formatter reports pre-existing formatting. Keep the one-line region-name correction focused. `git diff --check` passes.
- Optional SUMO execution, plotting, and desktop Excel/Sigma-X are disabled in the manuscript example and were not rerun. Existing signal-validation limitations recorded in the October 23 changelog remain. Request a fresh official JOSS PDF after publishing the source corrections; the checked-in proof predates these edits.

## Reference verification sources

- Ban et al.: [National Transportation Library report record](https://rosap.ntl.bts.gov/view/dot/67308).
- Coogan and Thitsa: [National Transportation Library report FHWA-GA-21-1913](https://rosap.ntl.bts.gov/view/dot/56488).
- Berg et al.: [Transportation Research Board record TRBAM-22-02127](https://trid.trb.org/View/1909441).
- Lopez et al.: [official SUMO citation and full BibTeX](https://sumo.dlr.de/docs/Publications.html).
- Smith et al.: [original Volpe report and dataset record](https://rosap.ntl.bts.gov/view/dot/44136).
- Real-Twin: [ORNL software record](https://impact.ornl.gov/en/publications/real-twin/) and [software DOI](https://doi.org/10.11578/dc.20250602.3).
- Singh et al.: [IEEE Access publication metadata](https://doi.org/10.1109/ACCESS.2017.2739240); the 2017 DOI suffix is retained while the final volume 6 publication year is 2018.
- Archive metadata precedence: [Zenodo documentation](https://help.zenodo.org/docs/github/describe-software/zenodo-json/).

## Confirmed publication metadata

| Order | Author | ORCID | Affiliation |
| --- | --- | --- | --- |
| 1 | Xiangyong Luo | 0009-0003-1290-9983 | Oak Ridge National Laboratory, United States |
| 2 | Yiran Zhang | 0000-0002-7392-8841 | University of Washington, Seattle, WA, United States |
| 3 | Xuesong (Simon) Zhou | 0000-0002-9963-5369 | Arizona State University, Tempe, AZ, United States |
