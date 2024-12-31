'''
##############################################################
# Created Date: Thursday, October 17th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

import pandas as pd
from geopy import distance


def calculate_new_coordinates_from_offsets(base_lon: float,
                                           base_lat: float,
                                           x_offset: float,
                                           y_offset: float,
                                           unit: str) -> tuple:
    """
    Calculate the new point's coordinates given offsets in unit.

    Args:
        base_lon (float): the base longitude
        base_lat (float): the base latitude
        x_offset (float): the offset in x direction
        y_offset (float): the offset in y direction
        unit (str): the unit of the offsets, e.g., "feet" or "meter"
    """

    # Convert offsets to meters (1 foot = 0.3048 meters)
    if "feet" in unit:
        x_m = x_offset * 0.3048
        y_m = y_offset * 0.3048
    elif "meter" in unit:
        x_m = x_offset
        y_m = y_offset
    else:
        raise Exception("unit must be either feet or meter.")

    # Calculate the distance and bearing for y_offset (North/South)
    if y_m != 0:
        bearing_y = 0 if y_m > 0 else 180
        distance_y = abs(y_m)
        origin = (base_lat, base_lon)
        new_point_y = distance.distance(
            meters=distance_y).destination(origin, bearing_y)
    else:
        new_point_y = (base_lat, base_lon)

    # Calculate the distance and bearing for x_offset (East/West)
    if x_m != 0:
        bearing_x = 90 if x_m > 0 else 270
        distance_x = abs(x_m)
        new_point = distance.distance(
            meters=distance_x).destination(new_point_y, bearing_x)
    else:
        new_point = new_point_y

    if isinstance(new_point, tuple):
        return (new_point[1], new_point[0])

    return (new_point.longitude, new_point.latitude)


def update_node_from_one_intersection(single_int: dict, df_node: pd.DataFrame, unit: str) -> dict:
    """
    Update node coordinates from a single intersection data.

    Args:
        single_int (dict): a dictionary of a single intersection data,
            eg. {"INTID": 1, "x_coord": 0, "y_coord": 0}
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

    df_node.set_index("INTID", inplace=True, drop=False)

    return df_node.to_dict("index")
