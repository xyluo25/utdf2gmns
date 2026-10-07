============
Installation
============

Requirements
============

utdf2gmns supports Python 3.10 through 3.13.

Default installation
====================

Install the latest stable release from PyPI_ with pip_:

.. code-block:: console

    python -m pip install utdf2gmns

The default installation includes the runtime dependencies declared in
requirements.txt: geocoder, GeoPandas, geopy, pandas, pyproj, pyufunc,
Shapely, and sumolib.

Optional dependency groups
==========================

Quote package specifications containing square brackets so the command works
consistently across shells.

Extended data and visualization dependencies
--------------------------------------------

The base extra installs the complete optional data and visualization stack,
including Matplotlib and Kepler.gl:

.. code-block:: console

    python -m pip install "utdf2gmns[base]"

The latest stable Kepler.gl release still imports pkg_resources, which
Setuptools 82 removed. The base extra therefore applies a temporary
Setuptools version constraint automatically; no separate compatibility
command is required.

Sigma-X intersection visualization
----------------------------------

Install the Sigma-X Python dependency with:

.. code-block:: console

    python -m pip install "utdf2gmns[sigma-x]"

Sigma-X requires desktop Microsoft Excel and is supported only on Windows and
macOS. The platform marker intentionally skips xlwings on Linux. Calling the
Sigma-X workflow on an unsupported platform prints an explanatory message and
returns False.

Testing and documentation
-------------------------

Install the test and documentation tools with:

.. code-block:: console

    python -m pip install "utdf2gmns[test]"

All optional dependencies
-------------------------

Install all package extras with:

.. code-block:: console

    python -m pip install "utdf2gmns[all]"

The all extra combines base, sigma-x, and test. Platform markers still apply,
so Linux does not install the desktop Excel integration.

Editable source installation
============================

From a repository checkout, install the project and the desired extras in
editable mode:

.. code-block:: console

    python -m pip install -e .
    python -m pip install -e ".[base]"
    python -m pip install -e ".[sigma-x]"

External applications
=====================

Some optional workflows require applications that pip does not install:

* **SUMO conversion:** Install SUMO separately and add its bin directory,
  containing the netconvert executable, to the system PATH before calling
  the SUMO conversion workflow.
* **Sigma-X visualization:** Install desktop Microsoft Excel and use Windows
  or macOS.

.. _PyPI: https://pypi.org/project/utdf2gmns
.. _pip: https://packaging.python.org/key_projects/#pip
