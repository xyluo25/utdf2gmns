
======================================
Sigma-x Engine Visualize Intersections
======================================

`utdf2gmns` package provides a method to visualize intersections using the Sigma-x engine. This is an optional step and can be used to generate a visual representation of the intersections.

.. code-block:: python
    :linenos:
    :emphasize-lines: 6, 9

    import utdf2gmns as ug


        if __name__ == "__main__":

            path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"

            # Step 1: Initialize the UTDF2GMNS
            net = ug.UTDF2GMNS(utdf_filename=path_utdf, verbose=False)

            net.utdf_to_gmns_signal_ints()  # This will generate the Sigma-x engine visualization for intersections

This will save visualization file for each intersection in the current working directory. You can open these files to perform additional analysis.


Signalized Intersection Overview Chart
======================================
.. image:: ../_static/int_overview.png
    :width: 600
    :alt: Signalized Intersection Overview Chart


Phasing Chart / Table
=====================

.. image:: ../_static/int_phasing_table.png
    :width: 600
    :alt: Phasing Table

.. image:: ../_static/int_phasing_chart.png
    :width: 600
    :alt: Phasing Chart


Turning Volumes (VPH) Chart
===========================

.. image:: ../_static/int_turning_volumns.png
    :width: 600
    :alt: Turning Volumes Chart


Phase Designation (Phase No) Chart
==================================

.. image:: ../_static/int_phase_designation.png
    :width: 600
    :alt: Phase Designation Chart


Number of Lanes Chart
=====================

.. image:: ../_static/int_num_lanes.png
    :width: 600
    :alt: Number of Lanes Chart


Split Durations (Seconds) Chart
===============================

.. image:: ../_static/int_split_duration.png
    :width: 600
    :alt: Split Durations Chart


Movement Capacity (VPH) Chart
=============================

.. image:: ../_static/int_movement_capacity.png
    :width: 600
    :alt: Movement Capacity Chart


V/C Ratio Chart
===============

.. image:: ../_static/int_v_c_ratio.png
    :width: 600
    :alt: V/C Ratio Chart


Control Delay (Seconds) Chart
=============================

.. image:: ../_static/int_control_delay.png
    :width: 600
    :alt: Control Delay Chart


Intersection Level of Service (LOS) Chart
=========================================

.. image:: ../_static/int_level_of_service.png
    :width: 600
    :alt: Intersection Level of Service (LOS) Chart
