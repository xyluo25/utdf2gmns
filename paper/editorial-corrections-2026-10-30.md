# Final JOSS editorial corrections, October 30, 2026

This record addresses [Fangzhou Xie's final corrections](https://github.com/openjournals/joss-reviews/issues/10619#issuecomment-6525591358), starting from `joss` commit `3aacc800535a79ccfa6389fd1d8230f565b0e37e` (merged PR #19). The manuscript's scientific claims, research-use examples, design trade-offs, author metadata, and input dataset are preserved. Generated tutorial outputs are not included in the correction commit.

## Corrections against the editor's list

| Request | Completed change |
| --- | --- |
| Move improvements resulting from JOSS review to Acknowledgements | Moved the paragraph about review-driven dependency, platform, geocoding, and visualization improvements out of Research impact; acknowledged the reviewers in Acknowledgements. Retained the independent research-use and development-contribution evidence. |
| Use footnotes for GitHub issues and pull requests | Replaced the PR #1 and issues #15, #17, and #18 bibliography citations with linked footnotes; removed all four entries from `paper.bib`. |
| Define acronyms and introduce the software | Defined UTDF, SUMO, GMNS, and GIS in the opening paragraph; identified Synchro as commercial signal-timing software and Sigma-X as an Excel-based intersection-analysis tool. Also expanded OSM, XML, I/O, DOE, PyPI, JOSS, and CSV at first use in the manuscript prose. |
| Move the opening funding footnote | Moved the UT-Battelle contract and DOE public-access text into Acknowledgements. Retained the existing funding agencies, contract number, public-access link, and disclaimer. |
| Fix the citation spacing | Added a space before the citation after "gaps" and spaces between citation keys. |
| Replace "Official-Documentation" | Used the sentence "The documentation is available at <URL>." |
| Use consistent Sigma-X terminology | Used `Sigma-X` consistently in manuscript prose and repaired the incomplete acknowledgement using the editor's suggested sentence. Package-extra identifiers in other documentation retain their executable `sigma-x` spelling. |
| Verify the tutorial and dataset | Removed the region-name leading space from the paper, README, quick-start source, and standalone tutorial. Added repository-root installation and input-path instructions and a direct dataset link. Verified the tracked CSV and ran the manuscript's core code. |
| Remove the citation to this submission | Removed the inline "Luo and Zhou 2022" repository self-citation. Retained the separate published WSC paper and other research references. |
| Repair incomplete references | Restored Ban's report and Coogan and Thitsa's report from their original title pages. Completed the Berg conference entry, the SUMO reference's author list, the thesis school field, and the Real-Twin software citation/DOI; removed the spurious "John, A" author from the GMNS dataset citation; corrected SUMO Conference Proceedings entry types and the Singh article's volume-publication year. |
| Disclose AI assistance | Extended the existing Codex disclosure to cover the final editorial corrections and bibliography verification. |

## Verification

- **Input:** `datasets/data_bullhead_seg4/UTDF.csv` is a tracked blob, SHA `829e87be6788b8652344eb002088ff42ce61c97f`, and contains the reference intersection `39` used by the tutorial.
- **Core tutorial:** Executed the Python block extracted directly from `paper/paper.md`, from the repository root with the checked-out package installed. It produced 22 GMNS nodes, 42 links, 95 lanes, 72 movements, and eight signal-control records. All four core CSV outputs were nonempty and the signal JSON parsed successfully.
- **Optional SUMO:** Enabled the manuscript's SUMO call using SUMO 1.28.0. Conversion succeeded, the generated XML files parsed, and a 300-second simulation from scenario time 32400 to 32700 completed with exit status 0. It inserted 153 vehicles. Existing unsafe-green warnings at intersections 78, 84, and 98 remain, as already recorded for PR #19; successful execution is not a validation of every signal plan. Desktop Excel/Sigma-X and Kepler.gl were not exercised on Linux.
- **Distribution boundary:** Built both `utdf2gmns-1.2.5.tar.gz` and `utdf2gmns-1.2.5-py3-none-any.whl` using the existing packaging configuration. Neither contains the tutorial CSV or standalone tutorial script. The tutorial now explicitly requires the repository checkout or a separate dataset download. This check covers fresh builds from this revision, not every historical PyPI artifact. Packaging behavior was not changed.
- **Tests:** Python 3.12, `python -m pytest -q`: 53 passed. Existing pandas deprecation warnings remain.
- **Documentation:** Sphinx HTML build completed without warnings, using the edited quick-start source.
- **Manuscript:** Pandoc citation processing completed without warnings; all 17 bibliography entries parsed, all manuscript citation keys resolved, and no bibliography entries were unused. The author ORCIDs passed checksum validation. `git diff --check` passed. These checks do not substitute for the editor's final JOSS PDF proof or the authors' metadata confirmation.

## Reference sources

| Entry | Source and verification |
| --- | --- |
| Ban et al. (2022) | [C2SMART project page](https://c2smart.engineering.nyu.edu/a-multiscale-simulation-platform-for-connected-and-automated-transportation-systems/) and its [original final report](https://cip.tandoncsmart.com/uploads/1679277577348-A%20Multiscale%20Simulation%20Platform%20for%20Connected%20and%20Automated%20Transportation%20Systems.pdf), title pages 2-3: Jeff Ban, Ohay Angah, Yiran Zhang, Qiangqiang Guo; August 2022; full C2SMART institutional name. The same-title Zenodo record `10.5281/zenodo.7199131` is a dataset, not this report, and has not been substituted as the report DOI. |
| Coogan and Thitsa (2021) | [National Transportation Library record](https://rosap.ntl.bts.gov/view/dot/56488) and its [report](https://rosap.ntl.bts.gov/view/dot/56488/dot_56488_DS1.pdf), title pages 2-3: two authors, April 2021, report FHWA-GA-21-1913, full Georgia DOT office name. No DOI was assigned to this reference without evidence. |
| Berg et al. (2022) | [Transportation Research Board record](https://trid.trb.org/View/1909441): 101st Annual Meeting, Washington, DC, paper TRBAM-22-02127, all three authors. |
| Lopez et al. (2018) | [SUMO's official reference and BibTeX](https://sumo.dlr.de/docs/Publications.html#citing_sumo): complete ten-author list, author order, conference title, pages, and DOI. Used the project's citation rather than the differing author order in Crossref's deposit. |
| Smith et al. (2020) | [National Transportation Library record](https://rosap.ntl.bts.gov/view/dot/44136) and [DataCite metadata](https://api.datacite.org/dois/10.21949/1518740): three personal authors, Volpe publisher, dataset/software resource, DOI. The former "John, A" author was an erroneous fragment of the institution name. |
| Real-Twin (2025) | [DOE CODE 147051](https://www.osti.gov/doecode/biblio/147051): software title, six developers, June 2, 2025, and DOI `10.11578/dc.20250602.3`. Removed the unsupported journal/page fields. |
| Other DOI-bearing papers | Checked the publisher-deposited Crossref metadata for the Halbach, Schrader, Zhang, WSC, Lu, EV charging, Singh, and Udomsilp entries. The Singh volume 6 article has publication year 2018; its existing citation key is retained. [arXiv](https://arxiv.org/abs/2609.01676) confirms Sim2Signal's title, authors, year, and version 2. |

The historical PyPI download count and research-impact claims were retained, not recomputed or expanded in this editorial revision.

## Author confirmation required

The existing paper metadata has not been changed. The submitting author must confirm the complete list, order, name forms, affiliations, and ORCIDs before the final release/archive metadata is published.

| Author, in current order | Current affiliation | Current ORCID |
| --- | --- | --- |
| Xiangyong Luo | Oak Ridge National Laboratory, United States | 0009-0003-1290-9983 |
| Yiran Zhang | University of Washington, Seattle, WA, United States | 0000-0002-7392-8841 |
| Xuesong (Simon) Zhou | Arizona State University, Tempe, AZ, United States | 0000-0002-9963-5369 |

ORCID checksum validity and corroborating publication records do not establish the authors' approval of the final author list or current affiliations. Confirm whether the ORNL affiliation should also include Oak Ridge, TN, and any department or division names.

The current paper title is **utdf2gmns: A Python Package for Mobility Simulation from UTDF to SUMO**. The review issue uses a different title. The archive must match the final paper title, author list, order, and ORCIDs. `CITATION.cff` intentionally points to the separately published WSC paper and should not be copied as the JOSS archive author list.

## Release and archive preparation

These items remain open; this revision does not claim a new release or archive DOI.

1. After the author metadata is confirmed, choose the final version and update the package/version fields consistently. A proposed next version is `1.2.6`, following package version `1.2.5` and the existing GitHub release tag `v.1.2.5`.
2. Create a GitHub release from the corrected `joss` commit, including the review fixes through PR #19 and this editorial revision. Confirm that the release target contains the checked tutorial dataset. The unchanged Python wheel/sdist distribution boundary remains documented.
3. Archive that exact release with Zenodo or another accepted archival service. Use the confirmed paper title and three-author metadata above, resource type software, and **MIT** license, matching the repository's `LICENSE`. Reserve or obtain the DOI from the archival service; do not invent one or reuse the WSC paper DOI.
4. Post the released version, immutable tag/commit, and archive DOI to JOSS review #10619. The editor can then update the review's version and archive fields and recommend acceptance.

Suggested release notes:

> Incorporates the JOSS review corrections to dependency and platform guidance, conversion-method documentation, software-design discussion, and CI validation, followed by the final manuscript and reference corrections. Clarifies how to obtain and run the Bullhead City tutorial dataset. Preserves conversion algorithms and output schemas. The core tutorial and optional SUMO conversion were verified; existing unsafe-green warnings at intersections 78, 84, and 98 still require signal-plan validation.
