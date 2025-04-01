
=====================
Read UTDF Format Data
=====================

The `UTDF2GMNS` class is designed to read UTDF format data and convert it into GMNS format. The following example demonstrates how to initialize the class with a UTDF file and read the data from it. This will load the UTDF file into a dictionary format, which can then be used to access various components of the network data.

The original UTDF format include the following keys:

.. list-table::
    :widths: 20, 80
    :header-rows: 1

    * - Key
      - Description
    * - Network
      - Overall network information, including ScenarioData, ScenarioTime, vehLength, PHF, Metrics, etc.
    * - Nodes
      - Intersections in the network, which includes INTID, x/y coordinates, and other attributes.
    * - Links
      - Links between intersections, which can be represented as either polygon or line links in GMNS format. Each link includes attributes such as LinkID, FromNode, ToNode, Length, etc.
    * - Lanes
      - Lanes associated with each link, which can be used to define the lane geometry and attributes in GMNS. Each lane includes attributes such as LaneID, LinkID, Width, etc.
    * - Timeplans
      - Time-based signal control plans for signalized intersections in the network. This includes the timing of each signal phase and the associated green times.
    * - Phases
      - Signal phases for each signalized intersection, which defines the signal timing and control for each approach at the intersection. Each phase includes attributes such as PhaseID, GreenTime, YellowTime, RedTime, etc.


load utdf data from UTDF2GMNS class
===================================

.. code-block:: python
    :linenos:
    :emphasize-lines: 5

    import utdf2gmns as ug

    if __name__ == "__main__":

    region_name = " Bullhead City, AZ"
    path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"

    net = net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name, verbose=False)

Then you can get UTDF data in a dictionary format from the initialized object. The keys in the dictionary correspond to the components of the UTDF data, such as **Network**, **Nodes**, **Links**, **Lanes**, **Timeplans**, and **Phases**. The values of these keys will be DataFrame objects (from `pandas`_) that contain the corresponding data from the UTDF file. You can access these components as follows:

.. code-block:: python
    :linenos:

    net._utdf_dict["Network"]

    # or view the node information (intersections)
    net._utdf_dict["Nodes"]

.. warning::

    - **region_name** is optional.

    * **region_name** is necessary for :ref:`Automatic Geocoding`. It can be any string that represents the region of the UTDF data (e.g., "Bullhead City, AZ").

    - **region_name** is not used for :ref:`Manual Geocoding`. In the manual mode, you can specify the coordinates directly using the **single_intersection_coord** parameter in the **geocode_utdf_intersections** function.


Load UTDF data from read_UTDF function
======================================

**If you just want to read the UTDF file without converting it to GMNS format, you can simply run the code**

.. code-block:: python
    :linenos:

    import utdf2gmns as ug

    path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"
    utdf_dict = ug.read_UTDF(path_utdf)

    # get all available keys in the utdf_dict
    print(utdf_dict.keys())

