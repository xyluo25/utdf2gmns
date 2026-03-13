'''
##############################################################
# Created Date: Thursday, March 12th 2026
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''


from xml.dom import minidom
import xml.etree.ElementTree as ET  # Use ElementTree for XML generation
import re
import copy
from datetime import datetime
import pandas as pd

from utdf2gmns.func_lib.gmns.geocoding_Links import cvt_lonlat_to_utm
from utdf2gmns.func_lib.utdf.cvt_utdf_lane_df_to_dict import cvt_lane_df_to_dict
from utdf2gmns.func_lib.gmns.geocoding_Links import cvt_link_df_to_dict


def xml_prettify(element: str) -> str:
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(element, 'utf-8')
    re_parsed = minidom.parseString(rough_string)
    return re_parsed.toprettyxml(indent="    ")


def cvt_feet_to_meters(feet: float) -> float:
    """Convert feet to meters."""
    return feet * 0.3048


def cvt_mph_to_mps(mph: float) -> float:
    """Convert miles per hour to meters per second."""
    return mph * 0.44704


def cvt_kmh_to_mps(kmh: float) -> float:
    """Convert kilometers per hour to meters per second."""
    return kmh / 3.6


def generate_lane_lookup_dict(utdf_dict: dict, net_unit: str) -> dict:
    """Generate the .lane.xml file.
                     int_id
                    ____|____ _____  __ ...
                   |    |    |     |
                   NB   SB   EB    WB  NE NW SE SW
              __ __|__   |
    --->     |  |  |  |  ...
             R  T  L  U
    lane index from 0 to more...

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        net_unit (str): The unit of the network (e.g., "feet", "meters").

    Note:
        SUMO to GMNS direction mapping:
        dir_type = {"s": "thru",
                    "t": "uturn",
                    "l": "left",
                    "r": "right",
                    "L": "partially left",
                    "R": "partially right",
                    "invalid": "invalid"}

    Raises:
        ValueError: Could not get Lane data from utdf_dict.

    Example:
        >>> from utdf2gmns.func_lib import generate_lane_lookup_dict
        >>> lane_lookup_dict = generate_lane_lookup_dict(utdf_dict, net_unit="feet")
        >>> # This will generate a lane lookup dictionary based on the provided UTDF Lane data.
        >>> print(lane_lookup_dict)
        {'1_2_0': {'id': '1_2_0', 'index': 0, 'length': '30.48', 'speed': '13.4112', 'volume': 100, ...}, ...}

    Returns:
        dict: A dictionary containing lane information for each intersection.
    """

    # Extract network unit: whether it's feet / mph or meters / km/h
    if "feet" in net_unit:
        unit_distance = "feet"
        unit_speed = "mph"
    elif "meters" in net_unit:
        unit_distance = "meters"
        unit_speed = "km/h"
    else:
        print(f"  Warning:Unknown distance and speed unit for Edge generation: {net_unit}. "
              "Defaulting to meters and km/h.")
        unit_distance = "meters"
        unit_speed = "km/h"

    cvt_unit_speed = {
        "mph": cvt_mph_to_mps,
        "km/h": cvt_kmh_to_mps,
    }
    cvt_unit_distance = {
        "feet": cvt_feet_to_meters,
        "meters": lambda x: x,
    }

    lanes_df = utdf_dict.get("Lanes")

    if lanes_df is None:
        raise ValueError("Could not get Lane data from utdf_dict.")

    # Convert lanes DataFrame to dictionary
    network_lanes = cvt_lane_df_to_dict(lanes_df)

    mvt_group_base = {
        "NB": {},  # {"NBL": {},"NBT": {}, "NBR": {},"NBU": {}, ...},
        "SB": {},
        "EB": {},
        "WB": {},
        "NE": {},
        "NW": {},
        "SE": {},
        "SW": {},
    }

    mvt_type_base = {
        "L": [],
        "T": [],
        "R": [],
        "U": [],
    }

    # Store lane information for each intersection
    lane_lookup_dict = {}

    # create link lookup dictionary: f{"{from_node}_{to_node}": "num_lanes"}
    link_lookup_dict = generate_link_lookup_dict(utdf_dict)

    # Loop through each intersection, mvt group, lane and connection
    for int_id, mvt_lanes in network_lanes.items():
        # e.g.: "1",  {"NBT": {}, "NBL": {}, "NBU": {}, "NBR": {}, ...}

        # Reset mvt_group for each intersection
        mvt_group = copy.deepcopy(mvt_group_base)

        # Group movement under each direction: NE, NW, SE, SW, NB, SB, EB, WB
        # mvt_group = {"NB": {"NBL": {}, "NBT": {}, "NBR": {}, "NBU": {}, ...},
        for each_mvt in mvt_lanes.keys():
            first_two_char = each_mvt[:2]
            if first_two_char in mvt_group:
                mvt_group[first_two_char][each_mvt] = mvt_lanes[each_mvt]

        # add movement into mvt_type dictionary
        for mvt_name, each_mvt_group in mvt_group.items():
            # mvt_name: NB, SB, EB, WB, NE, NW, SE, SW
            # each_mvt_group: {"NBL": {}, "NBT": {}, "NBR": {}, "NBU": {}, ...}

            # Reset mvt_type for each intersection
            mvt_type = copy.deepcopy(mvt_type_base)

            # check if each_mvt_group is not empty, skip empty group
            if not each_mvt_group:
                continue

            for mvt_turn, mvt_turn_info in each_mvt_group.items():
                # mvt_turn: NBL, NBT, NBR, NBU, ...
                # mvt_turn_info: {"Up Bode": "", "Dest Node": "", "Lanes": "", ...}

                # Extract relevant information from mvt_turn_info
                lane_mvt_info = {"up_node": mvt_turn_info.get("Up Node"),
                                 "dest_node": mvt_turn_info.get("Dest Node"),
                                 "lanes": mvt_turn_info.get("Lanes"),
                                 "shared": mvt_turn_info.get("Shared"),
                                 "storage": mvt_turn_info.get("Storage"),
                                 "taper": mvt_turn_info.get("Taper"),
                                 "speed": mvt_turn_info.get("Speed"),
                                 "volume": mvt_turn_info.get("Volume"),
                                 "distance": mvt_turn_info.get("Distance"),
                                 "num_detects": mvt_turn_info.get("numDetects"),
                                 }

                if "R" in mvt_turn:
                    mvt_type["R"].append(lane_mvt_info)
                elif "T" in mvt_turn:
                    mvt_type["T"].append(lane_mvt_info)
                elif "L" in mvt_turn:
                    mvt_type["L"].append(lane_mvt_info)
                elif "U" in mvt_turn:
                    mvt_type["U"].append(lane_mvt_info)
                else:
                    print(
                        f"Warning: Unknown movement type {mvt_turn} in node: {int_id}.")

            # Ordering lane index from the sequence of Right -> Through -> Left -> U-Turn  (SUMO)
            # Ordering lane index from the sequence of Through -> Right -> Left -> U-Turn  (GMNS)
            # For each mvt_name: NB, SB, EB, WB, NE, NW, SE, SW
            lane_index = 1
            lane_index_left = -1

            # Add Through lanes
            if mvt_type["T"]:
                for through in mvt_type["T"]:
                    num_lanes = through.get("lanes")

                    up_node = through.get("up_node")
                    dest_node = through.get("dest_node")
                    shared = through.get("shared")
                    storage = through.get("storage")
                    # taper = through.get("taper")
                    speed = through.get("speed")
                    volume = through.get("volume")
                    distance = through.get("distance")
                    num_detects = through.get("num_detects")

                    if int(num_lanes) > 0:
                        for _ in range(int(num_lanes)):
                            if storage:
                                storage = re.findall(r"\d+", str(storage))[0]
                                lane_length = f"{cvt_unit_distance[unit_distance](float(storage))}"
                            elif distance:
                                distance = re.findall(
                                    r"\d+", str(distance))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(distance))}"
                            else:
                                # use length from link lookup dictionary
                                lane_length = f"{link_lookup_dict[f'{up_node}_{int_id}']['length']}"
                                lane_length = re.findall(
                                    # Extract digit
                                    r"\d+", str(lane_length))[0]
                                lane_length = cvt_unit_distance[unit_distance](
                                    float(lane_length))

                            if speed:
                                speed = re.findall(
                                    r"\d+", str(speed))[0]  # Extract digit
                                lane_speed = f"{cvt_unit_speed[unit_speed](float(speed))}"
                            else:
                                # use speed from link lookup dictionary
                                lane_speed = f"{link_lookup_dict[f'{up_node}_{int_id}']['speed']}"
                                lane_speed = re.findall(
                                    # Extract digit
                                    r"\d+", str(lane_speed))[0]
                                lane_speed = cvt_unit_speed[unit_speed](
                                    float(lane_speed))

                            lane_lookup_dict[f"{up_node}_{int_id}_{lane_index}"] = {
                                "lane_id": f"{up_node}_{int_id}_{lane_index}",
                                "link_id": f"{up_node}_{int_id}",
                                "lane_num": lane_index_left,
                                f"length_{unit_distance}": lane_length,
                                f"speed_{unit_speed}": lane_speed,
                                "volume": volume,
                                "numDetects": num_detects,
                                "type": "thru",
                                "shared": shared,
                                "up_node": up_node,
                                "dest_node": dest_node,
                                "mvmt_id": f"{up_node}_{int_id}_{dest_node}",
                            }

                            lane_index += 1

            # Add Right Turn lanes
            if mvt_type["R"]:
                for right_turn in mvt_type["R"]:
                    num_lanes = right_turn.get("lanes")

                    up_node = right_turn.get("up_node")
                    dest_node = right_turn.get("dest_node")
                    shared = right_turn.get("shared")
                    storage = right_turn.get("storage")
                    # taper = right_turn.get("taper")
                    speed = right_turn.get("speed")
                    volume = right_turn.get("volume")
                    distance = right_turn.get("distance")
                    num_detects = right_turn.get("num_detects")

                    if int(num_lanes) == 0:  # shared right turn lane
                        # Do not create lane for shared right turn lane
                        pass

                    elif int(num_lanes) > 0:  # protected right turn lane (right turn bay)
                        for _ in range(int(num_lanes)):
                            # Create lane for protected right turn bay
                            if storage:
                                storage = re.findall(r"\d+", str(storage))[0]
                                lane_length = f"{cvt_unit_distance[unit_distance](float(storage))}"
                            elif distance:
                                distance = re.findall(
                                    r"\d+", str(distance))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(distance))}"
                            else:
                                # use length from link lookup dictionary
                                lane_length = f"{link_lookup_dict[f'{up_node}_{int_id}']['length']}"
                                lane_length = re.findall(
                                    # Extract digit
                                    r"\d+", str(lane_length))[0]
                                lane_length = cvt_unit_distance[unit_distance](
                                    float(lane_length))

                            if speed:
                                speed = re.findall(
                                    r"\d+", str(speed))[0]  # Extract digit
                                lane_speed = f"{cvt_unit_speed[unit_speed](float(speed))}"
                            else:
                                # use speed from link lookup dictionary
                                lane_speed = f"{link_lookup_dict[f'{up_node}_{int_id}']['speed']}"
                                lane_speed = re.findall(
                                    # Extract digit
                                    r"\d+", str(lane_speed))[0]
                                lane_speed = cvt_unit_speed[unit_speed](
                                    float(lane_speed))

                            lane_lookup_dict[f"{up_node}_{int_id}_{lane_index}"] = {
                                "lane_id": f"{up_node}_{int_id}_{lane_index}",
                                "link_id": f"{up_node}_{int_id}",
                                "lane_num": lane_index_left,
                                f"length_{unit_distance}": lane_length,
                                f"speed_{unit_speed}": lane_speed,
                                "volume": volume,
                                "numDetects": num_detects,
                                "type": "right",
                                "shared": shared,
                                "up_node": up_node,
                                "dest_node": dest_node,
                                "mvmt_id": f"{up_node}_{int_id}_{dest_node}",
                            }

                            lane_index += 1

            # Add Left Turn lanes
            if mvt_type["L"]:
                for left_turn in mvt_type["L"]:
                    num_lanes = left_turn.get("lanes")

                    up_node = left_turn.get("up_node")
                    dest_node = left_turn.get("dest_node")
                    shared = left_turn.get("shared")
                    storage = left_turn.get("storage")
                    # taper = left_turn.get("taper")
                    speed = left_turn.get("speed")
                    volume = left_turn.get("volume")
                    distance = left_turn.get("distance")
                    num_detects = left_turn.get("num_detects")

                    if int(num_lanes) == 0:  # shared left turn lane
                        # Do not create lane for shared left turn lane
                        pass

                    elif int(num_lanes) > 0:  # protected left turn lane (left turn bay)
                        # reverse order for left turn lane
                        for left_turn_index in range(int(num_lanes))[::-1]:
                            # Create lane for protected left turn lane
                            if storage:
                                storage = re.findall(r"\d+", str(storage))[0]
                                lane_length = f"{cvt_unit_distance[unit_distance](float(storage))}"
                            elif distance:
                                distance = re.findall(
                                    r"\d+", str(distance))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(distance))}"
                            else:
                                # use length from link lookup dictionary
                                lane_length = f"{link_lookup_dict[f'{up_node}_{int_id}']['length']}"
                                lane_length = re.findall(
                                    # Extract digit
                                    r"\d+", str(lane_length))[0]
                                lane_length = cvt_unit_distance[unit_distance](
                                    float(lane_length))

                            if speed:
                                speed = re.findall(
                                    r"\d+", str(speed))[0]  # Extract digit
                                lane_speed = f"{cvt_unit_speed[unit_speed](float(speed))}"
                            else:
                                # use speed from link lookup dictionary
                                lane_speed = f"{link_lookup_dict[f'{up_node}_{int_id}']['speed']}"
                                lane_speed = re.findall(
                                    # Extract digit
                                    r"\d+", str(lane_speed))[0]
                                lane_speed = cvt_unit_speed[unit_speed](
                                    float(lane_speed))

                            lane_lookup_dict[f"{up_node}_{int_id}_{lane_index_left}"] = {
                                "lane_id": f"{up_node}_{int_id}_{lane_index_left}",
                                "link_id": f"{up_node}_{int_id}",
                                "lane_num": lane_index_left,
                                f"length_{unit_distance}": lane_length,
                                f"speed_{unit_speed}": lane_speed,
                                "volume": volume,
                                "numDetects": num_detects,
                                "type": "left",
                                "shared": shared,
                                "up_node": up_node,
                                "dest_node": dest_node,
                                "mvmt_id": f"{up_node}_{int_id}_{dest_node}",
                            }

                            lane_index_left -= 1

            # Add U-Turn lanes
            if mvt_type["U"]:
                for u_turn in mvt_type["U"]:
                    num_lanes = u_turn.get("lanes")

                    up_node = u_turn.get("up_node")
                    # dest_node = u_turn.get("dest_node")
                    # shared = u_turn.get("shared")
                    storage = u_turn.get("storage")
                    # taper = u_turn.get("taper")
                    speed = u_turn.get("speed")
                    volume = u_turn.get("volume")
                    distance = u_turn.get("distance")
                    num_detects = u_turn.get("num_detects")

                    if int(num_lanes) == 0:  # shared U-turn lane
                        # Do not create lane for shared U-turn lane
                        pass

                    elif int(num_lanes) > 0:  # protected U-turn lane (U-turn bay)
                        for u_turn_index in range(int(num_lanes))[::-1]:
                            if storage:
                                storage = re.findall(
                                    r"\d+", str(storage))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(storage))}"
                            elif distance:
                                distance = re.findall(
                                    r"\d+", str(distance))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(distance))}"
                            else:
                                # use length from link lookup dictionary
                                lane_length = f"{link_lookup_dict[f'{up_node}_{int_id}']['length']}"
                                lane_length = re.findall(
                                    # Extract digit
                                    r"\d+", str(lane_length))[0]
                                lane_length = cvt_unit_distance[unit_distance](
                                    float(lane_length))

                            if speed:
                                speed = re.findall(
                                    r"\d+", str(speed))[0]  # Extract digit
                                lane_speed = f"{cvt_unit_speed[unit_speed](float(speed))}"
                            else:
                                # use speed from link lookup dictionary
                                lane_speed = f"{link_lookup_dict[f'{up_node}_{int_id}']['speed']}"
                                lane_speed = re.findall(
                                    # Extract digit
                                    r"\d+", str(lane_speed))[0]
                                lane_speed = cvt_unit_speed[unit_speed](
                                    float(lane_speed))

                            lane_lookup_dict[f"{up_node}_{int_id}_{lane_index_left}"] = {
                                "lane_id": f"{up_node}_{int_id}_{lane_index_left}",
                                "link_id": f"{up_node}_{int_id}",
                                "lane_num": lane_index_left,
                                f"length_{unit_distance}": lane_length,
                                f"speed_{unit_speed}": lane_speed,
                                "volume": volume,
                                "numDetects": num_detects,
                                "type": "uturn",
                                "shared": shared,
                                "up_node": up_node,
                                "dest_node": dest_node,
                                "mvmt_id": f"{up_node}_{int_id}_{dest_node}",
                            }

                            lane_index_left -= 1

    return lane_lookup_dict


def generate_link_lookup_dict(utdf_dict: dict) -> dict:
    """Generate a lookup dictionary for edges.

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.

    Raises:
        ValueError: UTDF Links data are required in utdf_dict.

    Example:
        >>> from utdf2gmns.func_lib import generate_link_lookup_dict
        >>> edge_lookup_dict = generate_link_lookup_dict(utdf_dict)
        >>> # This will generate a lookup dictionary for edges based on the provided UTDF Links data.
        >>> print(edge_lookup_dict)  # {"edge_id": "num_lanes"}
        {'1_2': '2', '2_3': '2', ...}

    Returns:
        dict: A dictionary containing edge information for each intersection.
    """
    link_df = utdf_dict.get("Links")

    if link_df is None:
        raise ValueError("UTDF Links data are required in utdf_dict.")

    # Convert links DataFrame to dictionary
    network_links = cvt_link_df_to_dict(link_df)

    # Create a lookup dictionary for edges
    edge_lookup_dict = {}
    for int_id, direction_links in network_links.items():
        for direction in direction_links:
            num_lanes = direction_links[direction].get(
                "Lanes")  # Default lanes
            length = direction_links[direction].get("Distance")
            speed = direction_links[direction].get("Speed")

            up_node = direction_links[direction]["Up ID"]
            edge_lookup_dict[f"{up_node}_{int_id}"] = {
                "num_lanes": num_lanes,
                "length": length,
                "speed": speed,
            }
    return edge_lookup_dict


def generate_gmns_lane(utdf_dict: dict, filename: str = "lane.csv", net_unit: str = "feet") -> bool:
    """Generate the lane.csv file in GMNS Standard.

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        filename (str): The name of the output lane CSV file (lane.csv).
        net_unit (str): The unit of measurement for the network data.

    Raises:
        ValueError: Could not get Lane data from utdf_dict.

    Example:
        >>> from utdf2gmns.func_lib import generate_gmns_lane
        >>> generate_gmns_lane(utdf_dict, filename="lane.csv")
        >>> # This will generate a lane.csv file in the current directory.
        True
    Returns:
        bool: True if the CSV file is generated successfully, False otherwise.
    """
    lanes_dict = generate_lane_lookup_dict(utdf_dict, net_unit=net_unit)
    df_lane = pd.DataFrame(lanes_dict.values())

    # exclude mvmt_id, up_node, dest_node columns in the output lane.csv
    exlude_columns = ["mvmt_id", "shared"]  # "up_node", "dest_node"
    df_lane = df_lane.drop(columns=exlude_columns, errors='ignore')
    df_lane.to_csv(filename, index=False)
    return True


def generate_gmns_movement(utdf_dict: dict, filename: str = "movement.csv", net_unit: str = "feet") -> bool:
    """Generate the movement.csv file in GMNS Standard.
                     int_id
                    ____|____ _____  __ ...
                   |    |    |     |
                   NB   SB   EB    WB  NE NW SE SW
              __ __|__   |
             |  |  |  |  ...
             R  T  L  U
    lane index from 0 to more (right most lane index is 0)...

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        filename (str): The name of the output movement CSV file (movement.csv).

    Raises:
        ValueError: Could not get Lane data from utdf_dict.

    Example:
        >>> from utdf2gmns.func_lib import generate_gmns_movement
        >>> generate_gmns_movement(utdf_dict, filename="movement.csv")
        >>> # This will generate a movement.csv file in the current directory.
        True

    Returns:
        bool: True if the CSV file is generated successfully, False otherwise.
    """

    lanes_df = utdf_dict.get("Lanes")

    if lanes_df is None:
        raise ValueError("Could not get Lane data from utdf_dict.")

    # Convert lanes DataFrame to dictionary
    network_lanes = cvt_lane_df_to_dict(lanes_df)

    mvt_group_base = {
        "NB": {},  # {"NBL": {},"NBT": {}, "NBR": {},"NBU": {}, ...},
        "SB": {},
        "EB": {},
        "WB": {},
        "NE": {},
        "NW": {},
        "SE": {},
        "SW": {},
    }

    mvt_type_base = {
        "L": [],
        "T": [],
        "R": [],
        "U": [],
    }

    # create link lookup dictionary: f{"{from_node}_{to_node}": "num_lanes"}
    link_lookup_dict = generate_link_lookup_dict(utdf_dict)

    def update_lane_index(lane_index: str, edge_id: str, link_lookup_dict: dict) -> str:
        """Update lane index based on the link lookup dictionary."""

        lane_index_integer = int(lane_index)
        edge_lanes = link_lookup_dict.get(edge_id)["num_lanes"]
        # extract digit group from edge_lanes
        edge_lanes = re.findall(r"\d+", str(edge_lanes))[0]  # Extract digit
        edge_lanes = int(edge_lanes)

        if lane_index_integer >= edge_lanes:
            lane_index_integer = edge_lanes - 1

        if lane_index_integer < 0:
            lane_index_integer = 0

        return f"{lane_index_integer}"

    # create connection xml
    root_con = ET.Element("connections")

    # Loop through each intersection, mvt group, lane and connection
    for int_id, mvt_lanes in network_lanes.items():
        # e.g.: "1",  {"NBT": {}, "NBL": {}, "NBU": {}, "NBR": {}, ...}

        # Reset mvt_group and mvt_type for each intersection
        # Reset mvt_group for each intersection
        mvt_group = copy.deepcopy(mvt_group_base)

        # Group movement under each direction: NE, NW, SE, SW, NB, SB, EB, WB
        # mvt_group = {"NB": {"NBL": {}, "NBT": {}, "NBR": {}, "NBU": {}, ...},
        for each_mvt in mvt_lanes.keys():
            first_two_char = each_mvt[:2]
            if first_two_char in mvt_group:
                mvt_group[first_two_char][each_mvt] = mvt_lanes[each_mvt]

        # add movement into mvt_type dictionary
        for mvt_name, each_mvt_group in mvt_group.items():
            # mvt_name: NB, SB, EB, WB, NE, NW, SE, SW
            # each_mvt_group: {"NBL": {}, "NBT": {}, "NBR": {}, "NBU": {}, ...}

            # Reset mvt_type for each intersection
            mvt_type = copy.deepcopy(mvt_type_base)

            # check if each_mvt_group is not empty, skip empty group
            if not each_mvt_group:
                continue

            for mvt_turn, mvt_turn_info in each_mvt_group.items():
                # mvt_turn: NBL, NBT, NBR, NBU, ...
                # mvt_turn_info: {"Up Bode": "", "Dest Node": "", "Lanes": "", ...}

                # Extract relevant information from mvt_turn_info
                lane_mvt_info = {"up_node": mvt_turn_info.get("Up Node"),
                                 "dest_node": mvt_turn_info.get("Dest Node"),
                                 "lanes": mvt_turn_info.get("Lanes"),
                                 "shared": mvt_turn_info.get("Shared"),
                                 "storage": mvt_turn_info.get("Storage"),
                                 "taper": mvt_turn_info.get("Taper"),
                                 "speed": mvt_turn_info.get("Speed"),
                                 "volume": mvt_turn_info.get("Volume"),
                                 "distance": mvt_turn_info.get("Distance"),
                                 "num_detects": mvt_turn_info.get("numDetects"),
                                 }

                if "R" in mvt_turn:
                    mvt_type["R"].append(lane_mvt_info)
                elif "T" in mvt_turn:
                    mvt_type["T"].append(lane_mvt_info)
                elif "L" in mvt_turn:
                    mvt_type["L"].append(lane_mvt_info)
                elif "U" in mvt_turn:
                    mvt_type["U"].append(lane_mvt_info)
                else:
                    print(
                        f"Warning: Unknown movement type {mvt_turn} in node: {int_id}.")

            # Ordering lane index from the sequence of Right -> Through -> Left -> U-Turn
            # For each mvt_name: NB, SB, EB, WB, NE, NW, SE, SW
            lane_index = 0

            # Add Right Turn lanes
            if mvt_type["R"]:
                for right_turn in mvt_type["R"]:
                    num_lanes = right_turn.get("lanes")

                    up_node = right_turn.get("up_node")
                    dest_node = right_turn.get("dest_node")

                    if int(num_lanes) == 0:  # shared right turn lane
                        # Create connection for shared right turn lane
                        connection = ET.SubElement(root_con, "connection")
                        connection.set("from", f"{up_node}_{int_id}")
                        connection.set("to", f"{int_id}_{dest_node}")
                        connection.set("fromLane",
                                       update_lane_index(f"{lane_index}", f"{up_node}_{int_id}", link_lookup_dict))
                        connection.set("toLane",
                                       update_lane_index(f"{lane_index}", f"{int_id}_{dest_node}", link_lookup_dict))
                        connection.set("dir", "r")  # right turn
                        # connection.set("state", "o")  #

                    elif int(num_lanes) > 0:  # protected right turn lane (right turn bay)
                        for _ in range(int(num_lanes)):
                            # Create connection for protected right turn lane
                            connection = ET.SubElement(root_con, "connection")
                            connection.set("from", f"{up_node}_{int_id}")
                            connection.set("to", f"{int_id}_{dest_node}")
                            connection.set("fromLane",
                                           update_lane_index(f"{lane_index}",
                                                             f"{up_node}_{int_id}",
                                                             link_lookup_dict))
                            connection.set("toLane",
                                           update_lane_index(f"{lane_index}",
                                                             f"{int_id}_{dest_node}",
                                                             link_lookup_dict))
                            connection.set("dir", "r")  # right turn
                            # connection.set("state", "o")

                            lane_index += 1

            # Add Through lanes
            if mvt_type["T"]:
                for through in mvt_type["T"]:
                    num_lanes = through.get("lanes")

                    up_node = through.get("up_node")
                    dest_node = through.get("dest_node")

                    if int(num_lanes) > 0:
                        for through_index in range(int(num_lanes)):
                            # create connection for through lane
                            connection = ET.SubElement(root_con, "connection")
                            connection.set("from", f"{up_node}_{int_id}")
                            connection.set("to", f"{int_id}_{dest_node}")
                            # connection.set("fromLane", str(lane_index))
                            # connection.set("toLane", str(through_index))

                            connection.set("fromLane",
                                           update_lane_index(f"{lane_index}",
                                                             f"{up_node}_{int_id}",
                                                             link_lookup_dict))
                            connection.set("toLane",
                                           update_lane_index(f"{through_index}",
                                                             f"{int_id}_{dest_node}",
                                                             link_lookup_dict))
                            connection.set("dir", "s")  # straight lane
                            # connection.set("state", "M")  # open lane

                            lane_index += 1

            # Add Left Turn lanes
            if mvt_type["L"]:
                for left_turn in mvt_type["L"]:
                    num_lanes = left_turn.get("lanes")

                    up_node = left_turn.get("up_node")
                    dest_node = left_turn.get("dest_node")

                    if int(num_lanes) == 0:  # shared left turn lane
                        # Create connection for shared left turn lane
                        connection = ET.SubElement(root_con, "connection")
                        connection.set("from", f"{up_node}_{int_id}")
                        connection.set("to", f"{int_id}_{dest_node}")
                        # connection.set("fromLane", str(lane_index))

                        connection.set("fromLane",
                                       update_lane_index(f"{lane_index}",
                                                         f"{up_node}_{int_id}",
                                                         link_lookup_dict))

                        num_lanes_for_to_link = link_lookup_dict.get(
                            f"{int_id}_{dest_node}")["num_lanes"]
                        # extract digit group from num_lanes_for_to_link
                        num_lanes_for_to_link = re.findall(
                            # Extract digit
                            r"\d+", str(num_lanes_for_to_link))[0]

                        # to innermost lane
                        to_lane_val = int(num_lanes_for_to_link) - 1
                        if to_lane_val < 0:
                            to_lane_val = 0
                        connection.set("toLane", str(to_lane_val))

                        connection.set("dir", "l")  # left turn
                        # connection.set("state", "o")  #

                    elif int(num_lanes) > 0:  # protected left turn lane (left turn bay)
                        # reverse order for left turn lane
                        for left_turn_index in range(int(num_lanes))[::-1]:
                            # Create connection for protected left turn lane
                            connection = ET.SubElement(root_con, "connection")
                            connection.set("from", f"{up_node}_{int_id}")
                            connection.set("to", f"{int_id}_{dest_node}")
                            # connection.set("fromLane", str(lane_index))
                            connection.set("fromLane",
                                           update_lane_index(f"{lane_index}",
                                                             f"{up_node}_{int_id}",
                                                             link_lookup_dict))

                            num_lanes_for_to_link = link_lookup_dict.get(
                                f"{int_id}_{dest_node}")["num_lanes"]

                            # extract digit group from num_lanes_for_to_link
                            num_lanes_for_to_link = re.findall(
                                # Extract digit
                                r"\d+", str(num_lanes_for_to_link))[0]

                            to_lane_val = int(
                                num_lanes_for_to_link) - left_turn_index - 1
                            if to_lane_val < 0:
                                to_lane_val = 0
                            connection.set("toLane", str(to_lane_val))
                            # connection.set("toLane", f"{int(num_lanes_for_to_link) - left_turn_index - 1}")
                            connection.set("dir", "l")
                            # connection.set("state", "o")  #

                            lane_index += 1

            # Add U-Turn lanes
            if mvt_type["U"]:
                for u_turn in mvt_type["U"]:
                    num_lanes = u_turn.get("lanes")

                    up_node = u_turn.get("up_node")
                    dest_node = u_turn.get("dest_node")

                    if int(num_lanes) == 0:  # shared U-turn lane
                        # Create connection for shared U-turn lane
                        connection = ET.SubElement(root_con, "connection")
                        connection.set("from", f"{up_node}_{int_id}")
                        connection.set("to", f"{int_id}_{dest_node}")

                        from_lane_val = lane_index - 1
                        if from_lane_val < 0:
                            from_lane_val = 0
                        connection.set("fromLane", str(from_lane_val))

                        num_lanes_for_to_link = link_lookup_dict.get(
                            f"{int_id}_{dest_node}")["num_lanes"]
                        # extract digit group from num_lanes_for_to_link
                        num_lanes_for_to_link = re.findall(
                            # Extract digit
                            r"\d+", str(num_lanes_for_to_link))[0]

                        # to innermost lane
                        to_lane_val = int(num_lanes_for_to_link) - 1
                        if to_lane_val < 0:
                            to_lane_val = 0
                        connection.set("toLane", str(to_lane_val))
                        # connection.set("toLane", f"{int(num_lanes_for_to_link) - 1}")  # to innermost lane
                        connection.set("dir", "t")  # U-turn
                        # connection.set("state", "o")  #

                    elif int(num_lanes) > 0:  # protected U-turn lane (U-turn bay)
                        for u_turn_index in range(int(num_lanes))[::-1]:
                            # Create connection for protected U-turn lane
                            connection = ET.SubElement(root_con, "connection")
                            connection.set("from", f"{up_node}_{int_id}")
                            connection.set("to", f"{int_id}_{dest_node}")

                            from_lane_val = lane_index - 1
                            if from_lane_val < 0:
                                from_lane_val = 0
                            connection.set("fromLane", str(from_lane_val))

                            num_lanes_for_to_link = link_lookup_dict.get(
                                f"{int_id}_{dest_node}")["num_lanes"]
                            # extract digit group from num_lanes_for_to_link
                            num_lanes_for_to_link = re.findall(
                                # Extract digit
                                r"\d+", str(num_lanes_for_to_link))[0]

                            to_lane_val = int(
                                num_lanes_for_to_link) - u_turn_index - 1
                            if to_lane_val < 0:
                                to_lane_val = 0
                            connection.set("toLane", str(to_lane_val))
                            # connection.set("toLane", f"{int(num_lanes_for_to_link) - u_turn_index - 1}")
                            connection.set("dir", "t")

                            lane_index += 1

    # loop through each connection and get attribute value and write into csv file
    movement_dict = {}
    for connection in root_con.findall("connection"):
        # e.g., "1_2_3" for movement from node 1 to node 2 with destination node 3
        mvmt_id = connection.get("from").split("_")[0] + "_" + connection.get("to")
        dir_type = {"s": "thru",
                    "t": "uturn",
                    "l": "left",
                    "r": "right",
                    "L": "partially left",
                    "R": "partially right",
                    "invalid": "invalid"}
        if mvmt_id not in movement_dict:
            movement_dict[mvmt_id] = {
                "mvmt_id": mvmt_id,
                "node_id": connection.get("to").split("_")[0],
                "ib_link_id": connection.get("from"),
                "ob_link_id": connection.get("to"),
                "type": dir_type.get(connection.get("dir"), "invalid"),
                "num_lanes": 1,
            }
        else:
            movement_dict[mvmt_id]["num_lanes"] += 1

    # Convert movement_dict to DataFrame
    df_movement = pd.DataFrame(movement_dict.values())

    # Collapse lane records to one row per movement key before merge.
    df_lane = pd.DataFrame(generate_lane_lookup_dict(utdf_dict, net_unit=net_unit).values())
    df_lane = df_lane[["mvmt_id", "type", "volume"]]
    df_lane = df_lane.groupby(["mvmt_id", "type"], as_index=False)["volume"].first()
    df_movement = df_movement.merge(df_lane, on=["mvmt_id", "type"], how="left", validate="one_to_one")

    # fill volume NaN with 0
    df_movement["volume"] = df_movement["volume"].fillna(0)

    df_movement.to_csv(filename, index=False)

    return True
