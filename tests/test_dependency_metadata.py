from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_keplergl_extra_constrains_setuptools():
    """Keep stable Kepler.gl compatible with its pkg_resources dependency."""
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    optional_dependencies = pyproject.split(
        "[project.optional-dependencies]", maxsplit=1
    )[1].split("[project.urls]", maxsplit=1)[0]

    assert '"keplergl"' in optional_dependencies
    assert '"setuptools<82"' in optional_dependencies


def test_readthedocs_keplergl_constrains_setuptools():
    """Use the same compatibility constraint in documentation builds."""
    requirements = {
        line.split("#", maxsplit=1)[0].strip()
        for line in (PROJECT_ROOT / "requirements_readthedocs.txt")
        .read_text(encoding="utf-8")
        .splitlines()
    }

    assert "keplergl" in requirements
    assert "setuptools<82" in requirements
