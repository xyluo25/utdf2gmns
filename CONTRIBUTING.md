# Contributing to utdf2gmns

Contributions to code, tests, documentation, examples, and validation with real UTDF datasets are welcome. The project maintainer reviews proposed changes and decides when they are ready to merge.

## Report a problem or request support

Search the [existing issues](https://github.com/xyluo25/utdf2gmns/issues) before opening a new report. Use the [issue forms](https://github.com/xyluo25/utdf2gmns/issues/new/choose) to report bugs, request features, suggest documentation changes, or ask a usage question.

For a bug report, include your operating system, Python and utdf2gmns versions, installation command, a minimal example, the full error traceback, and the expected behavior. Share a small UTDF input only when you have permission to publish it; remove confidential information and credentials. For conversion errors, identify the relevant intersection, movement, signal timing, units, and coordinate convention.

For larger changes, open an issue first to discuss the intended behavior and scope with the maintainer. Useful non-code contributions include installation testing, dataset validation, issue investigation, tutorials, and reviews of proposed changes.

## Set up a development environment

Use Python 3.10 or later in an isolated environment. Fork the repository on GitHub, clone your fork, and run these commands from the repository root:

```text
python -m venv .venv
```

Activate the environment:

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# Linux or macOS
source .venv/bin/activate
```

Install the local package and test dependencies:

```text
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
```

Optional workflows have additional requirements. SUMO conversion needs SUMO installed with its `netconvert` executable on `PATH`. Sigma-X needs desktop Microsoft Excel on Windows or macOS and the `sigma-x` extra. The `base` extra provides optional visualization dependencies. Follow the [README](README.md) and [documentation](https://utdf2gmns.readthedocs.io/en/latest/) when testing these workflows.

## Validate and submit a change

Keep changes focused and preserve existing public APIs and output schemas unless an agreed change requires otherwise. Describe inputs, outputs, units, and coordinate conventions clearly. Add a regression test for a bug fix when practical, and update relevant documentation and `CHANGELOG.md` when behavior changes.

Run the relevant tests, followed by the existing suite when practical:

```text
python -m pytest -q
git diff --check
```

Open a pull request against `main` for software or general documentation changes. For revisions to an active JOSS submission, use its paper branch (`joss`) and explain the review item being addressed. Link the related issue, describe the change and its purpose, list the checks performed, and state any workflows that could not be tested. The maintainer may request revisions before merging.

If generative AI assisted your contribution, identify the tool and the affected code or text in the pull request, and describe how you verified it. Contributors remain responsible for correctness, licensing, and the evidence behind their claims.
