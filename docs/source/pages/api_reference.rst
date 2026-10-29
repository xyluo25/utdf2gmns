=============
API Reference
=============

.. currentmodule:: utdf2gmns

UTDF2GMNS class
===============
.. autosummary::
   :toctree: api/

   UTDF2GMNS

Function Library: UTDF
======================
.. autosummary::
   :toctree: api/

   func_lib.read_UTDF
   func_lib.cvt_lane_df_to_dict

Function Library: GMNS
======================
.. autosummary::
   :toctree: api/

   func_lib.cvt_utdf_to_signal_intersection
   func_lib.cvt_link_df_to_dict

Function Library: SUMO
======================
.. autosummary::
   :toctree: api/

   func_lib.remove_sumo_U_turn
   func_lib.update_sumo_signal_from_utdf

Visualization
=============
.. autosummary::
   :toctree: api/

   func_lib.plot_net_mpl
   func_lib.plot_net_keplergl

Utility Functions
=================
.. autosummary::
   :toctree: api/

   util_lib.calculate_point2point_distance_in_km
   util_lib.time_unit_converter
   util_lib.time_str_to_seconds

Detailed conversion methods
===========================

The workflow starts with initialization and geocoding, then exports GMNS or
SUMO artifacts. The methods below document parameters and return values.
SUMO conversion requires the external SUMO installation; Sigma-X is optional
and requires desktop Microsoft Excel on Windows or macOS.

.. automethod:: UTDF2GMNS.geocode_utdf_intersections

.. automethod:: UTDF2GMNS.create_gmns_links

.. automethod:: UTDF2GMNS.create_signal_control

.. automethod:: UTDF2GMNS.utdf_to_gmns

.. automethod:: UTDF2GMNS.utdf_to_sumo

.. automethod:: UTDF2GMNS.utdf_to_gmns_signal_ints
