============
Installation
============

You can install the latest stable release of the package at `PyPI`_ using `pip`_:

.. code-block:: python
    :linenos:

    pip install utdf2gmns

By running the command above, the utdf2gmns package along with required dependency packages
(`pandas`_, `pyufunc`_) will be installed to your computer (if they have not been installed yet).

.. note::
    You can also choose to install packages based on your needs. Below are the optional dependencies that can be included during installation.

.. code-block:: python
    :linenos:

    pip install utdf2gmns[base]

.. code-block:: python
    :linenos:

    pip install utdf2gmns[test]  # including test dependencies (pytest, coverage)

.. code-block:: python
    :linenos:

    pip install utdf2gmns[all]  # including all optional dependencies, including test dependencies and visualization dependencies (matplotlib, keplergl)

⚡⚡If you don't know what's best for your, the default :ref:`Installation` should work for most users.

⚡⚡By the way, the utdf2gmns package will also install the required dependencies automatically when you run functions that require them.


.. _`PyPI`: https://pypi.org/project/osm2gmns
.. _`pip`: https://packaging.python.org/key_projects/#pip
.. _`pyufunc`: https://github.com/xyluo25/pyufunc
.. _`pandas`: https://pandas.pydata.org/
