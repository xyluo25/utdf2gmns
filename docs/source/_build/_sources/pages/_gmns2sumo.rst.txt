===================
GMNS To SUMO Format
===================

Convert GMNS format files (from :ref:`UTDF To GMNS Format`) to SUMO format.

.. important::

    SUMO is an external application and is not installed by pip. Install SUMO
    and add its bin directory, containing the netconvert executable, to the
    system PATH before running this workflow.

.. code-block:: python
    :linenos:
    :emphasize-lines: 15

    import utdf2gmns as ug

    if __name__ == "__main__":

        region_name = " Bullhead City, AZ"
        path_utdf = "datasets/data_bullhead_seg4/UTDF.csv"

        net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name, verbose=False)

        single_coord = {"INTID": "39", "x_coord": -114.59807666698381, "y_coord": 35.02605198650903}
        net.geocode_utdf_intersections(single_intersection_coord=single_coord)

        net.create_gmns_links(is_link_polygon=False)

        net.utdf_to_sumo(sim_name="", show_warning_message=True, remove_U_turn=True)


By default, the generated SUMO network files are saved in an utdf_to_sumo
subdirectory beside the input UTDF file. The resulting configuration can be
opened with sumo-gui.

.. image:: ../_static/sumo_network_sim.gif
    :width: 100%
    :alt: GMNS to SUMO network simulation
