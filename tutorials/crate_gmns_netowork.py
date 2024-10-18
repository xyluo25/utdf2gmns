'''
##############################################################
# Created Date: Thursday, October 17th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

from __future__ import absolute_import
import utdf2gmns as ug


if __name__ == '__main__':
    utdf_fn = r"C:\Users\xyluo25\anaconda3_workspace\001_GitHub\utdf2gmns\datasets\Sedona\Sedona SR 89A 9-19-23 Optimized UTDF.csv"
    place_name = " Sedona, AZ"

    net = ug.UTDF2GMNS(utdf_fn, place_name)

    net.load_utdf()

    net.geocoding_intersections()

    # print(" update Nodes: ", net.utdf_dict["Nodes"])
    net.signalize_intersections()

    net.create_network()

    ug.plot_net(net)

    net.save_results_to_csv("./")