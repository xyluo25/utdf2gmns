'''
##############################################################
# Created Date: Sunday, April 6th 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

import xml.etree.ElementTree as ET
import math

from utdf2gmns.func_lib.sumo.gmns2sumo import generate_net_lane_lookup_dict
from utdf2gmns.util_lib.pkg_utils import point_coord_on_line_2dim, point_coord_on_line_lonlat


def point_coord_on_line_2dim(x1: float, y1: float, x2: float, y2: float, distance: float) -> tuple:
    """Given a starting point (x1, y1) and an ending point (x2, y2) in 2D space,
    return the coordinates of the point at a given distance from the starting point.

    Args:
        x1 (float): x-coordinate of the starting point.
        y1 (float): y-coordinate of the starting point.
        x2 (float): x-coordinate of the ending point.
        y2 (float): y-coordinate of the ending point.
        distance (float): The distance from the starting point.

    Returns:
        tuple: A tuple containing the x and y coordinates of the point at the given distance.
    """
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx**2 + dy**2)
    if length == 0:
        return x1, y1
    ratio = distance / length
    x = x1 + ratio * dx
    y = y1 + ratio * dy
    return (x, y)


def point_coord_on_line_lonlat(lon1: float, lat1: float, lon2: float, lat2: float, distance: float) -> tuple:
    """
    Given a start point (lon1, lat1) and end point (lon2, lat2),
    return the longitude/latitude of the point at `distance` meters
    from the start, following the great circle path.

    Args:
        lon1 (float): Longitude of the starting point in degrees.
        lat1 (float): Latitude of the starting point in degrees.
        lon2 (float): Longitude of the ending point in degrees.
        lat2 (float): Latitude of the ending point in degrees.
        distance (float): Distance from the start point, in meters.

    Returns:
        (lon, lat): Tuple of longitude and latitude in degrees.
    """
    # Convert to radians
    φ1 = math.radians(lat1)
    λ1 = math.radians(lon1)
    φ2 = math.radians(lat2)
    λ2 = math.radians(lon2)

    # Earth radius (mean)
    R = 6_371_000.0

    # Compute the great-circle distance between start and end
    Δφ = φ2 - φ1
    Δλ = λ2 - λ1
    a = math.sin(Δφ / 2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2)**2
    sig = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    if sig == 0 or distance == 0:
        # coincident points or zero distance
        return lon1, lat1

    # Initial bearing from point 1 to point 2
    θ = math.atan2(
        math.sin(Δλ) * math.cos(φ2),
        math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(Δλ))

    # Angular distance along the great circle
    δ = distance / R

    # Compute the new point
    φ3 = math.asin(math.sin(φ1) * math.cos(δ) + math.cos(φ1) * math.sin(δ) * math.cos(θ))
    λ3 = λ1 + math.atan2(math.sin(θ) * math.sin(δ) * math.cos(φ1),
                         math.cos(δ) - math.sin(φ1) * math.sin(φ3))

    # Normalize lon to −180…+180°
    lon3 = (math.degrees(λ3) + 540) % 360 - 180
    lat3 = math.degrees(φ3)

    return (lon3, lat3)


def update_turn_bay_length(net_fname: str, utdf_dict: dict, net_unit: str) -> True:
    """
    Update the turn bay length in the SUMO network file based on the UTDf data.

    Parameters:
        net_fname (str): The path to the SUMO network file.
        utdf_dict (dict): A dictionary containing UTDf data.

    Returns:
        True if the operation is successful.
    """
    # Load the SUMO network file
    tree = ET.parse(net_fname)
    root = tree.getroot()

    # get lane data
    lane_lookup_dict = generate_net_lane_lookup_dict(utdf_dict, net_unit)

    # Iterate through each edge in the network
    edges = root.findall("edge")

    # Iterate through each edge in the network
    for edge in edges:
        # Get the edge ID
        edge_id = edge.get("id")

        if edge_id.startswith(":"):
            # skip internal edges in the network
            continue

        # loop through lanes in each edge (from net.xml)
        for lane in edge.findall("lane"):
            # get lane index from net.xml: rightmost lane is 0
            lane_id = lane.get("id")

            # get lane info from lane_lookup_dict (from utdf_dict)
            lane_lookup = lane_lookup_dict.get(lane_id)

            if not lane_lookup:
                # if lane_lookup is None, skip this lane
                continue

            lane_dir = lane_lookup.get("dir")

            # if it's the turn bay, update the length in shape
            if lane_dir in ["l", "r"]:
                lane_length_real = lane_lookup.get("length")

                # get coordinates of the lane shape
                lane_shape = lane.get("shape")
                start_coord, end_coord = lane_shape.split(" ")
                start_x, start_y = start_coord.split(",")
                end_x, end_y = end_coord.split(",")

                middle_x, middle_y = point_coord_on_line_2dim(float(end_x),
                                                              float(end_y),
                                                              float(start_x),
                                                              float(start_y),
                                                              float(lane_length_real))

                # update the shape of the lane
                lane.set("shape", f"{middle_x},{middle_y} {end_x},{end_y}")

    # Save the updated network file
    tree.write(net_fname)
    return True
