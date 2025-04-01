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

    pip install utdf2gmns[all]

.. code-block:: python
    :linenos:

    pip install utdf2gmns[test]  # including test dependencies (pytest, coverage)

.. code-block:: python
    :linenos:

    pip install utdf2gmns[vis]  # including visualization dependencies (matplotlib, keplergl)

.. code-block:: python
    :linenos:

    pip install utdf2gmns[sumo]  # including SUMO dependencies (traci, sumollib)

⚡⚡If you don't know what's best for your, the default :ref:`Installation` should work for most users.

⚡⚡By the way, the utdf2gmns package will also install the required dependencies automatically when you run functions that require them.


=================
Quick Start Guide
=================

.. note::
    - This quick start guide assumes you have a valid UTDF file and the required dependencies installed.
    - The following example uses a sample UTDF file from the Bullhead City, AZ dataset. You can replace it with your own UTDF file as needed.
    - The example below uses automatic geocoding by default. You can choose to geocode automatically ::ref:: `automatic_geociding` or manually ::ref::  `manual_geocoding` as per your requirement.

.. code-block:: python
    :linenos:

    import utdf2gmns as ug


    if __name__ == "__main__":

        region_name = " Bullhead City, AZ"
        path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"

        # Step 1: Initialize the UTDF2GMNS
        net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name, verbose=False)

        # (Optional) Sigma-X engine generate each signal intersection with visualization
        # net.utdf_to_gmns_signal_ints()

        # Step 2: Geocode intersection
        #   if user manually provide single intersection coordinate, such as:
        #   single_coord={"INTID": "1", "x_coord": -114.568, "y_coord": 35.155}
        #   Intersections will geocoded base on this point (Recommended Method)
        net.geocode_utdf_intersections(single_intersection_coord={}, dist_threshold=0.01)

        # Step 3: create network links: user can generate polygon-link or line-link
        net.create_gmns_links(is_link_polygon=False)

        # Step 4: convert UTDF network to GMNS format (csv)
        net.utdf_to_gmns(incl_utdf=True)

        # Step 5 (optional): convert UTDF network to SUMO
        net.utdf_to_sumo(sumo_name="", show_warning_message=True)

        # Step 6 (optional): visualize the network
        # net_map = ug.plot_net_keplergl(net, save_fig=True, fig_name="Bullhead_City.html")


.. _`PyPI`: https://pypi.org/project/osm2gmns
.. _`pip`: https://packaging.python.org/key_projects/#pip
.. _`pandas`: https://pandas.pydata.org/
.. _`pyufunc`: https://github.com/xyluo25/pyufunc
.. _`traci`: https://github.com/osmcode/pyosmium
.. _`Requests`: https://github.com/numpy/numpy

.. _`matplotlib`: https://matplotlib.org/
.. _`networkx`: https://networkx.org/
.. _`PyYAML`: https://pyyaml.org/
.. _`our repository`: https://github.com/xyluo25/utdf2gmns
.. _`osmium github homepage`: https://github.com/xyluo25/utdf2gmns
.. _`SUMO`: https://sumo.dlr.de/docs/index.html
.. _`Aimsun`: https://www.aimsun.com/
.. _YAML: https://en.wikipedia.org/wiki/YAML
