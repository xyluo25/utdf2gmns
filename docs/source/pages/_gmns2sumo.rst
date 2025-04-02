===================
GMNS To SUMO Format
===================

Convert GMNS format files (from :ref:`UTDF To GMNS Format`) to SUMO format.

.. code-block:: python
    :linenos:
    :emphasize-lines: 14

    import utdf2gmns as ug

    if __name__ == "__main__":

        region_name = " Bullhead City, AZ"
        path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"

        net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name, verbose=False)

        net.geocode_utdf_intersections(single_intersection_coord={}, dist_threshold=0.01)

        net.create_gmns_links(is_link_polygon=False)

        net.utdf_to_sumo(sumo_name="", show_warning_message=True, disable_U_turn=True)


The generated SUMO network files are saved in the same directory as the input UTDF file. Simulation in SUMO (Example Below):

.. image:: ../_static/sumo_network_sim.gif
    :width: 100%
    :alt: GMNS to SUMO network simulation
