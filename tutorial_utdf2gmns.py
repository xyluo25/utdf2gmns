# -*- coding:utf-8 -*-
##############################################################
# Created Date: Friday, June 23rd 2023
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################

import utdf2gmns as ug


if __name__ == "__main__":

    region_name = " Bullhead City, AZ"
    path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"

    # Step 1: Initialize the UTDF2GMNS
    net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name)

    # Step 2: Geocode intersection
    #   if user manually provide single intersection coordinate, such as:
    #   single_coord={"INTID": "1", "x_coord": -114.568, "y_coord": 35.155}
    #   Intersections will geocoded base on this point (Recommended Method)
    net.geocode_intersections(single_coord={}, dist_threshold=0.01)

    # Step 3: create network links: user can genrate polygon-link or line-link
    net.create_network(is_link_polygon=False)

    # Step 4: create signal intesection control
    net.create_signal_control()

    # Step 5: convert UTDF network to GMNS format (csv)
    net.utdf_to_gmns(incl_utdf=True)

    # Step 6 (optional): convert UTDF netowrk to SUMO
    net.utdf_to_sumo(sumo_name="", show_warning_message=False)
