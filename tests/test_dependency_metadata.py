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


def test_setuptools_discovers_source_packages():
    """Keep Python source packages in built distributions."""
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    setuptools_config = pyproject.split("[tool.setuptools]", maxsplit=1)[1].split(
        "[[tool.uv.index]]", maxsplit=1
    )[0]

    assert "py-modules = []" not in setuptools_config
    assert "[tool.setuptools.packages.find]" in setuptools_config
    assert 'where = ["."]' in setuptools_config
    assert 'include = ["utdf2gmns*"]' in setuptools_config
