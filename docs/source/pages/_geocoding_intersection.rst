

=======================
Geocoding Intersections
=======================
There are two ways to geocode intersections in the UTDF2GMNS package
    - **Automatic Geocoding**: This method uses the `geocode_utdf_intersections` function to geocode intersections based on the provided UTDF data. The function will attempt to geocode all intersections in the dataset using a distance threshold.

    - **Manual Geocoding**: This method allows you to manually specify a single intersection coordinate using the `single_intersection_coord` parameter in the `geocode_utdf_intersections` function. This is recommended when you have a known coordinate for a specific intersection and want to ensure accuracy.


Automatic Geocoding
===================

.. note::
    - For automatic geocoding method, `region_name` must be specified when initializing the `UTDF2GMNS` class. This is used to identify the region for geocoding intersections.
    - The `dist_threshold` parameter can be adjusted based on your needs, default is **0.01 km (10 meters)**.

.. code-block:: python
    :linenos:
    :emphasize-lines: 6, 10

    import utdf2gmns as ug


    if __name__ == "__main__":

        region_name = " Bullhead City, AZ"
        path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"

        # Step 1: Initialize the UTDF2GMNS
        net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name, verbose=False)

        # Step 2: Geocode intersection using automatic geocoding method
        net.geocode_utdf_intersections(single_intersection_coord={}, dist_threshold=0.01)


Manual Geocoding
================

.. note::
    - For manual geocoding method, `region_name` is not required when initializing the `UTDF2GMNS` class.
    - The dist_threshold parameter will not be used when you provide a single intersection coordinate. The function will use the provided coordinate directly for geocoding.

.. code-block:: python
    :linenos:
    :emphasize-lines: 6, 9

    import utdf2gmns as ug


    if __name__ == "__main__":

        path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"

        # Step 1: Initialize the UTDF2GMNS
        net = ug.UTDF2GMNS(utdf_filename=path_utdf, verbose=False)

        # Step 2: Example of manual geocoding using the geocode_utdf_intersections method
        single_coord = {"INTID": "1", "x_coord": -114.568, "y_coord": 35.155}  # Example coordinates for a known intersection
        net.geocode_utdf_intersections(single_intersection_coord=single_coord, dist_threshold=0.01)

