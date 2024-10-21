'''
##############################################################
# Created Date: Friday, October 18th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

import math
from shapely.geometry import Polygon
from pyproj import Transformer
import pandas as pd

# Define projection for converting lat/lon to a planar system (e.g., UTM or Mercator)
proj_wgs84 = Transformer.from_crs(
    "EPSG:32633", "EPSG:4326", always_xy=True)  # UTM to WGS84

# UTM projection (you can adjust the zone)
proj_utm = Transformer.from_crs(
    "EPSG:4326", "EPSG:32633", always_xy=True)  # WGS84 to UTM (zone 33N)


def project_to_utm(lon, lat):
    """Convert latitude and longitude to UTM coordinates."""
    return proj_utm.transform(lon, lat)


def project_to_latlon(x, y):
    """Convert UTM coordinates back to latitude and longitude."""
    return proj_wgs84.transform(x, y)


def create_line_polygon_points(lon1: float, lat1: float, lon2: float, lat2: float,
                               width: float, unit: str = "meters") -> list:
    """Create a line polygon points based on the width of the line.
    The polygon is to the right of the directional line.
    Start point is lon1, lat1 and end point is lon2, lat2.

    Args:
        lon1 (float): start longitude
        lat1 (float): start latitude
        lon2 (float): end longitude
        lat2 (float): end latitude
        width (float): width of the line
        unit (str): the unit of the width. Defaults to "meters".

    Raises:
        Exception: unit must be either feet or meters.

    Returns:
        tuple: the polygon points
    """

    # Check if the unit is valid
    if "feet" in unit:
        unit = "feet"
    elif "meters" in unit:
        unit = "meters"
    else:
        raise Exception("unit must be either feet or meters.")

    # Project the coordinates to UTM
    utm_coord1 = project_to_utm(*[lon1, lat1])
    utm_coord2 = project_to_utm(*[lon2, lat2])

    # Convert width to meters if needed
    if unit == "feet":
        width = float(width) * 0.3048  # Convert feet to meters

    # Calculate the direction of the original line in UTM coordinates
    x1, y1 = utm_coord1
    x2, y2 = utm_coord2
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx**2 + dy**2)
    direction = (dx / length, dy / length)

    # Perpendicular direction to offset the polygon
    perp_direction = (-direction[1], direction[0])  # Perpendicular vector

    offset = (perp_direction[0] * width, perp_direction[1] * width)

    # Calculate the four corner points of the polygon
    # Offset both start and end coordinates to the right
    corner1 = (x1, y1)
    corner2 = (x2, y2)
    corner3 = (x2 + offset[0], y2 + offset[1])
    corner4 = (x1 + offset[0], y1 + offset[1])

    # Project the UTM coordinates back to lat/lon
    corner1_latlon = project_to_latlon(*corner1)
    corner2_latlon = project_to_latlon(*corner2)
    corner3_latlon = project_to_latlon(*corner3)
    corner4_latlon = project_to_latlon(*corner4)

    # directional from start to end
    return [corner1_latlon, corner2_latlon, corner3_latlon, corner4_latlon]


def create_line_polygon(lon1: float, lat1: float, lon2: float, lat2: float,
                        num_lanes: int, width: float, unit: str = "meters") -> Polygon:
    """Create a line polygons based on the width of the line and number of lanes.
    The polygon is to the right of the directional line, each lane is exactly next to the previous one.

    Args:
        lon1 (float): start longitude
        lat1 (float): start latitude
        lon2 (float): end longitude
        lat2 (float): end latitude
        num_lanes (int): number of lanes
        width (float): width of the line
        unit (str): the unit of the width. Defaults to "meters".

    Returns:
        Polygon: the line polygon
    """
    lane_points = {}

    for i in range(num_lanes - 1, -1, -1):
        # reverse order as index 0 is the rightmost lane
        # calculate four corners of the lane
        corner_coords = create_line_polygon_points(lon1, lat1, lon2, lat2, width, unit)

        # add the lane points to the list
        lane_points[i] = corner_coords

        # update the start and end points for the next lane
        lon1 = corner_coords[3][0]
        lat1 = corner_coords[3][1]
        lon2 = corner_coords[2][0]
        lat2 = corner_coords[2][1]

    # return lane polygons as a dictionary
    return {key: Polygon(value + [value[0]]) for key, value in lane_points.items()}


def reformat_link_dataframe_to_dict(df_link: pd.DataFrame) -> dict:
    """Reformat the UTDF link dataframe to a dictionary of links with intersection id as keys

    Args:
        df_link (pd.DataFrame): UTDF link dataframe

    Returns:
        dict: a dictionary of links with keys are intersection ids and values are link data
    """

    # get unique intersection id
    intersection_id_list = list(df_link["INTID"].unique())

    # convert utdf_link dataframe to dictionary
    link_dict = {}
    for intersection_id in intersection_id_list:
        df_link_int_id = df_link[df_link["INTID"] == intersection_id]

        df_link_int_id.set_index("RECORDNAME", inplace=True)
        del df_link_int_id["INTID"]

        # select columns with Up ID not empty
        col_selection = df_link_int_id.columns[df_link_int_id.loc["Up ID"] != '']
        df_link_int_id = df_link_int_id[col_selection]

        link_dict[intersection_id] = df_link_int_id.to_dict("dict")

    return link_dict


def generate_links(df_link: pd.DataFrame, df_node: pd.DataFrame,
                   default_link_width: float, unit: str = "feet") -> dict:
    """Generate links from UTDF link data

    Args:
        df_link (pd.DataFrame): UTDF link data

    Returns:
        dict: a dictionary of links with keys are link ids and values are link polygon in wkt format
    """

    # extract intersection coordinates from df_node
    int_coords = {}
    for i in range(len(df_node)):
        int_id = df_node.loc[i, "INTID"]
        int_coords[int_id] = [df_node.loc[i, "x_coord"], df_node.loc[i, "y_coord"]]

    # extract link data from df_link
    int_links = reformat_link_dataframe_to_dict(df_link)

    # generate links
    links = {}

    for int_id in int_links:
        start_int = int_id
        start_x, start_y = int_coords[start_int]

        start_connections = int_links[int_id]
        for each_dir in start_connections:
            dest_int_dict = start_connections[each_dir]
            dest_int = dest_int_dict["Up ID"]

            dest_x, dest_y = int_coords[dest_int]
            num_lanes_str = dest_int_dict["Lanes"]
            if not num_lanes_str.isdigit():
                num_lanes_str = ''.join([char for char in num_lanes_str if char.isdigit()])
            num_lanes = int(num_lanes_str) if num_lanes_str else 1

            # remove keys "Up ID" and "Lanes"
            dest_int_dict.pop("Up ID")
            dest_int_dict.pop("Lanes")

            start_dest_links = create_line_polygon(start_x, start_y, dest_x, dest_y,
                                                   num_lanes, default_link_width, unit=unit)

            for i, link in start_dest_links.items():
                dest_int_dict["geometry"] = link
                links[f"{start_int}_{dest_int}_{i}"] = dest_int_dict
    return links
