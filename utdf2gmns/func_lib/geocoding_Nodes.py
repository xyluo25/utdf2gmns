'''
##############################################################
# Created Date: Thursday, October 17th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

import pandas as pd
import math


def calculate_new_coordinates_from_offsets(initial_longitude: float, initial_latitude: float,
                                           x_offset: float, y_offset: float, unit: str) -> tuple:

    EARTH_RADIUS = 6371.0088  # in kilometers

    # covert ft to km, 1 ft = 0.3048 m = 0.0003048 km
    if "feet" in unit:
        x_distance_km = x_offset * 0.0003048
        y_distance_km = y_offset * 0.0003048
    elif "meter" in unit:
        x_distance_km = x_offset * 0.001
        y_distance_km = y_offset * 0.001
    else:
        raise Exception("unit must be either feet or meter.")

    # covert lat and lng degree to km
    lat_rad = math.radians(initial_latitude)
    lat_km_per_degree = (2 * math.pi * EARTH_RADIUS) * math.cos(lat_rad) / 360
    lng_km_per_degree = (2 * math.pi * EARTH_RADIUS) * \
        math.cos(math.radians(initial_latitude)) / 360

    # calculate the lat and lng degree change with distance
    lat_change = y_distance_km / lat_km_per_degree
    lng_change = x_distance_km / lng_km_per_degree

    # calculate the new lat and lng
    new_lat = initial_latitude + lat_change
    new_lng = initial_longitude + lng_change

    return (new_lng, new_lat)


def update_node_from_one_intersection(single_int: dict, df_node: pd.DataFrame, unit: str) -> pd.DataFrame:
    """
    Update node coordinates from a single intersection data.

    Args:
        single_int (dict): a dictionary of a single intersection data
        df_node (pd.DataFrame): a dataframe of node data
        unit: the unit of the coordinates, e.g., "feet" or "meter"

    Returns:
        pd.DataFrame: a dataframe of node data with updated coordinates
    """

    # Copy the node dataframe
    df_node = df_node.copy(deep=True).reset_index(drop=True)

    # Add columns to the node dataframe
    df_node["x_coord"] = 0.0
    df_node["y_coord"] = 0.0
    df_node["INTID_base"] = 0
    df_node["TYPE_DESC"] = ""

    # Get the intersection ID and coordinates
    int_id = int(single_int["INTID"])
    int_x_coord = float(single_int["x_coord"])
    int_y_coord = float(single_int["y_coord"])

    # get intersection synchro x and y coordinates
    try:
        synchro_x = df_node[df_node["INTID"] == int_id]["X"].values[0]
        synchro_y = df_node[df_node["INTID"] == int_id]["Y"].values[0]
    except Exception:
        synchro_x = df_node[df_node["INTID"] == str(int_id)]["X"].values[0]
        synchro_y = df_node[df_node["INTID"] == str(int_id)]["Y"].values[0]

    # update the node coordinates
    for i in range(len(df_node)):
        node_id = df_node.loc[i, "INTID"]
        node_x = df_node.loc[i, "X"]
        node_y = df_node.loc[i, "Y"]

        # the offset from node to intersection
        x_offset = float(node_x) - float(synchro_x)
        y_offset = float(node_y) - float(synchro_y)

        # calculate the new coordinates
        x_coord, y_coord = calculate_new_coordinates_from_offsets(int_x_coord,
                                                                  int_y_coord,
                                                                  x_offset,
                                                                  y_offset,
                                                                  unit)
        # update the node dataframe
        df_node.loc[i, "INTID_base"] = 1 if int(int_id) == int(node_id) else 0
        df_node.loc[i, "x_coord"] = float(x_coord)
        df_node.loc[i, "y_coord"] = float(y_coord)

        # update Node Type
        node_type = {0: "Signalized", 1: "External Node",
                     2: "Bend", 3: "Unsignalized", 4: "Roundabout"}
        try:
            df_node.loc[i, "TYPE_DESC"] = node_type[int(df_node.loc[i, "TYPE"])]
        except Exception:
            continue
    return df_node