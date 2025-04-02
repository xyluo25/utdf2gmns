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
