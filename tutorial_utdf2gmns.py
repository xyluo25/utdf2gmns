# -*- coding:utf-8 -*-
##############################################################
# Created Date: Friday, June 23rd 2023
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################

import utdf2gmns as ug


if __name__ == "__main__":

    region_name = " Tempe, AZ"
    path_utdf = r"C:\Users\xyluo25\Desktop\pytes\data_Tempe_network\UTDF.csv"

    # Step 1: Initialize the UTDF2GMNS
    net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name, verbose=False)

    # Step 2: Geocode intersection
    #   if user manually provide single intersection coordinate, such as:
    # single_coord = {"INTID": "1", "x_coord": -111.963073214095, "y_coord": 33.3545737884511}
    # net.geocode_utdf_intersections(single_intersection_coord=single_coord)
    #   Intersections will geocoded base on this point (Recommended Method)
    net.geocode_utdf_intersections(single_intersection_coord={}, dist_threshold=0.01)

    # Step 3: convert UTDF network to GMNS format (csv)
    net.utdf_to_gmns(incl_utdf=True)

    # Step 4 (optional): convert UTDF network to SUMO
    net.utdf_to_sumo(sim_name="", show_warning_message=True, disable_U_turn=True, sim_duration=7200)

    # Step 5 (optional): visualize the network
    # # visualize in matplotlib (png) and kepler.gl (html)
    net_map = ug.plot_net_mpl(net, save_fig=True, fig_name="Bullhead_City.png")
    net_map = ug.plot_net_keplergl(net, save_fig=True, fig_name="Bullhead_City.html")

    # Step 6: Sigma-X visualize signalized intersection
    # net.utdf_to_gmns_signal_ints()
