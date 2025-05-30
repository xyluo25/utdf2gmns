'''
##############################################################
# Created Date: Sunday, October 20th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

# SUMO network specification: https://sumo.dlr.de/docs/Networks/SUMO_Road_Networks.html#network_format
# SUMO network plain xml format: https://sumo.dlr.de/docs/Networks/PlainXML.html

# SUMO-GUI Specification: https://sumo.dlr.de/docs/sumo-gui.html#interaction_with_the_view
# SUMO netedit specification: https://sumo.dlr.de/docs/Netedit/index.html#processing_menu_options


from xml.dom import minidom
import xml.etree.ElementTree as ET  # Use ElementTree for XML generation
import re
import copy
from datetime import datetime

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


def generate_sumo_nod_xml(utdf_dict: dict, filename: str = "network.nod.xml") -> bool:
    """Generate the .nod.xml file.

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        filename (str): The name of the output node XML file (.nod.xml).

    Example:
        >>> from utdf2gmns.func_lib import generate_sumo_nod_xml
        >>> generate_sumo_nod_xml(utdf_dict, filename="network.nod.xml")
        >>> # This will generate a network.nod.xml file in the current directory.
        True

    Raises:
        ValueError: No network_nodes found, please run geocode_utdf_intersections() first.

    Returns:
        bool: True if the XML file is generated successfully, False otherwise.
    """

    network_nodes = utdf_dict.get("network_nodes")

    # TDD
    if network_nodes is None:
        raise ValueError("No network_nodes found, please run geocode_utdf_intersections() first.")

    root = ET.Element("nodes")
    for node_id, node in network_nodes.items():
        node_elem = ET.SubElement(root, "node")
        node_elem.set("id", str(node_id))

        # Convert lonlat to UTM
        utm_x, utm_y, zone, hemi = cvt_lonlat_to_utm(node["x_coord"], node["y_coord"])

        # Convert lon and lat to UTM coordinates
        # node_elem.set("x", str(utm_x))
        # node_elem.set("y", str(utm_y))

        # Use real-world coordinates for SUMO and then use --proj.utm to convert to UTM
        node_elem.set("x", str(node["x_coord"]))
        node_elem.set("y", str(node["y_coord"]))

        node_type_description = node.get("TYPE_DESC")
        if node_type_description == "Signalized":
            node_elem.set("type", "traffic_light")  # Default type

    xml_str = xml_prettify(root)
    with open(filename, "w") as f:
        f.write(xml_str)

    return True


def generate_net_lane_lookup_dict(utdf_dict: dict, net_unit: str) -> dict:
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

    Raises:
        ValueError: Could not get Lane data from utdf_dict.

    Example:
        >>> from utdf2gmns.func_lib import generate_net_lane_lookup_dict
        >>> lane_lookup_dict = generate_net_lane_lookup_dict(utdf_dict, net_unit="feet")
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

    network_lanes = cvt_lane_df_to_dict(lanes_df)  # Convert lanes DataFrame to dictionary

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
    link_lookup_dict = generate_net_link_lookup_dict(utdf_dict)

    # Loop through each intersection, mvt group, lane and connection
    for int_id, mvt_lanes in network_lanes.items():
        # e.g.: "1",  {"NBT": {}, "NBL": {}, "NBU": {}, "NBR": {}, ...}

        mvt_group = copy.deepcopy(mvt_group_base)  # Reset mvt_group for each intersection

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

            mvt_type = copy.deepcopy(mvt_type_base)  # Reset mvt_type for each intersection

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
                    print(f"Warning: Unknown movement type {mvt_turn} in node: {int_id}.")

            # Ordering lane index from the sequence of Right -> Through -> Left -> U-Turn
            # For each mvt_name: NB, SB, EB, WB, NE, NW, SE, SW
            lane_index = 0

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
                                distance = re.findall(r"\d+", str(distance))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(distance))}"
                            else:
                                # use length from link lookup dictionary
                                lane_length = f"{link_lookup_dict[f'{up_node}_{int_id}']['length']}"
                                lane_length = re.findall(r"\d+", str(lane_length))[0]  # Extract digit
                                lane_length = cvt_unit_distance[unit_distance](float(lane_length))

                            if speed:
                                speed = re.findall(r"\d+", str(speed))[0]  # Extract digit
                                lane_speed = f"{cvt_unit_speed[unit_speed](float(speed))}"
                            else:
                                # use speed from link lookup dictionary
                                lane_speed = f"{link_lookup_dict[f'{up_node}_{int_id}']['speed']}"
                                lane_speed = re.findall(r"\d+", str(lane_speed))[0]  # Extract digit
                                lane_speed = cvt_unit_speed[unit_speed](float(lane_speed))

                            lane_lookup_dict[f"{up_node}_{int_id}_{lane_index}"] = {
                                "id": f"{up_node}_{int_id}_{lane_index}",
                                "index": lane_index,
                                "length": lane_length,
                                "speed": lane_speed,
                                "volume": volume,
                                "numDetects": num_detects,
                                "dir": "r",
                                "shared": shared,
                                "up_node": up_node,
                                "dest_node": dest_node,
                            }

                            lane_index += 1

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
                                distance = re.findall(r"\d+", str(distance))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(distance))}"
                            else:
                                # use length from link lookup dictionary
                                lane_length = f"{link_lookup_dict[f'{up_node}_{int_id}']['length']}"
                                lane_length = re.findall(r"\d+", str(lane_length))[0]  # Extract digit
                                lane_length = cvt_unit_distance[unit_distance](float(lane_length))

                            if speed:
                                speed = re.findall(r"\d+", str(speed))[0]  # Extract digit
                                lane_speed = f"{cvt_unit_speed[unit_speed](float(speed))}"
                            else:
                                # use speed from link lookup dictionary
                                lane_speed = f"{link_lookup_dict[f'{up_node}_{int_id}']['speed']}"
                                lane_speed = re.findall(r"\d+", str(lane_speed))[0]  # Extract digit
                                lane_speed = cvt_unit_speed[unit_speed](float(lane_speed))

                            lane_lookup_dict[f"{up_node}_{int_id}_{lane_index}"] = {
                                "id": f"{up_node}_{int_id}_{lane_index}",
                                "index": lane_index,
                                "length": lane_length,
                                "speed": lane_speed,
                                "volume": volume,
                                "numDetects": num_detects,
                                "dir": "s",
                                "shared": shared,
                                "up_node": up_node,
                                "dest_node": dest_node,
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
                        for left_turn_index in range(int(num_lanes))[::-1]:  # reverse order for left turn lane
                            # Create lane for protected left turn lane
                            if storage:
                                storage = re.findall(r"\d+", str(storage))[0]
                                lane_length = f"{cvt_unit_distance[unit_distance](float(storage))}"
                            elif distance:
                                distance = re.findall(r"\d+", str(distance))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(distance))}"
                            else:
                                # use length from link lookup dictionary
                                lane_length = f"{link_lookup_dict[f'{up_node}_{int_id}']['length']}"
                                lane_length = re.findall(r"\d+", str(lane_length))[0]  # Extract digit
                                lane_length = cvt_unit_distance[unit_distance](float(lane_length))

                            if speed:
                                speed = re.findall(r"\d+", str(speed))[0]  # Extract digit
                                lane_speed = f"{cvt_unit_speed[unit_speed](float(speed))}"
                            else:
                                # use speed from link lookup dictionary
                                lane_speed = f"{link_lookup_dict[f'{up_node}_{int_id}']['speed']}"
                                lane_speed = re.findall(r"\d+", str(lane_speed))[0]  # Extract digit
                                lane_speed = cvt_unit_speed[unit_speed](float(lane_speed))

                            lane_lookup_dict[f"{up_node}_{int_id}_{lane_index}"] = {
                                "id": f"{up_node}_{int_id}_{lane_index}",
                                "index": lane_index,
                                "length": lane_length,
                                "speed": lane_speed,
                                "volume": volume,
                                "numDetects": num_detects,
                                "dir": "l",
                                "shared": shared,
                                "up_node": up_node,
                                "dest_node": dest_node,
                            }

                            lane_index += 1

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
                                storage = re.findall(r"\d+", str(storage))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(storage))}"
                            elif distance:
                                distance = re.findall(r"\d+", str(distance))[0]  # Extract digit
                                lane_length = f"{cvt_unit_distance[unit_distance](float(distance))}"
                            else:
                                # use length from link lookup dictionary
                                lane_length = f"{link_lookup_dict[f'{up_node}_{int_id}']['length']}"
                                lane_length = re.findall(r"\d+", str(lane_length))[0]  # Extract digit
                                lane_length = cvt_unit_distance[unit_distance](float(lane_length))

                            if speed:
                                speed = re.findall(r"\d+", str(speed))[0]  # Extract digit
                                lane_speed = f"{cvt_unit_speed[unit_speed](float(speed))}"
                            else:
                                # use speed from link lookup dictionary
                                lane_speed = f"{link_lookup_dict[f'{up_node}_{int_id}']['speed']}"
                                lane_speed = re.findall(r"\d+", str(lane_speed))[0]  # Extract digit
                                lane_speed = cvt_unit_speed[unit_speed](float(lane_speed))

                            lane_lookup_dict[f"{up_node}_{int_id}_{lane_index}"] = {
                                "id": f"{up_node}_{int_id}_{lane_index}",
                                "index": lane_index,
                                "length": lane_length,
                                "speed": lane_speed,
                                "volume": volume,
                                "numDetects": num_detects,
                                "dir": "t",
                                "shared": shared,
                                "up_node": up_node,
                                "dest_node": dest_node,
                            }

                            lane_index += 1

    return lane_lookup_dict


def generate_sumo_connection_xml(utdf_dict: dict, filename: str = "network.con.xml") -> bool:
    """Generate the .lane.xml file.
                     int_id
                    ____|____ _____  __ ...
                   |    |    |     |
                   NB   SB   EB    WB  NE NW SE SW
              __ __|__   |
             |  |  |  |  ...
             R  T  L  U
    lane index from 0 to more...

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        filename (str): The name of the output connection XML file (.con.xml).

    Raises:
        ValueError: Could not get Lane data from utdf_dict.

    Example:
        >>> from utdf2gmns.func_lib import generate_sumo_connection_xml
        >>> generate_sumo_connection_xml(utdf_dict, filename="network.con.xml")
        >>> # This will generate a network.con.xml file in the current directory.
        True

    Returns:
        bool: True if the XML file is generated successfully, False otherwise.
    """

    lanes_df = utdf_dict.get("Lanes")

    if lanes_df is None:
        raise ValueError("Could not get Lane data from utdf_dict.")

    network_lanes = cvt_lane_df_to_dict(lanes_df)  # Convert lanes DataFrame to dictionary

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
    link_lookup_dict = generate_net_link_lookup_dict(utdf_dict)

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
        mvt_group = copy.deepcopy(mvt_group_base)  # Reset mvt_group for each intersection

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

            mvt_type = copy.deepcopy(mvt_type_base)  # Reset mvt_type for each intersection

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
                    print(f"Warning: Unknown movement type {mvt_turn} in node: {int_id}.")

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

                        num_lanes_for_to_link = link_lookup_dict.get(f"{int_id}_{dest_node}")["num_lanes"]
                        # extract digit group from num_lanes_for_to_link
                        num_lanes_for_to_link = re.findall(r"\d+", str(num_lanes_for_to_link))[0]  # Extract digit

                        to_lane_val = int(num_lanes_for_to_link) - 1  # to innermost lane
                        if to_lane_val < 0:
                            to_lane_val = 0
                        connection.set("toLane", str(to_lane_val))

                        connection.set("dir", "l")  # left turn
                        # connection.set("state", "o")  #

                    elif int(num_lanes) > 0:  # protected left turn lane (left turn bay)
                        for left_turn_index in range(int(num_lanes))[::-1]:  # reverse order for left turn lane
                            # Create connection for protected left turn lane
                            connection = ET.SubElement(root_con, "connection")
                            connection.set("from", f"{up_node}_{int_id}")
                            connection.set("to", f"{int_id}_{dest_node}")
                            # connection.set("fromLane", str(lane_index))
                            connection.set("fromLane",
                                           update_lane_index(f"{lane_index}",
                                                             f"{up_node}_{int_id}",
                                                             link_lookup_dict))

                            num_lanes_for_to_link = link_lookup_dict.get(f"{int_id}_{dest_node}")["num_lanes"]

                            # extract digit group from num_lanes_for_to_link
                            num_lanes_for_to_link = re.findall(r"\d+", str(num_lanes_for_to_link))[0]  # Extract digit

                            to_lane_val = int(num_lanes_for_to_link) - left_turn_index - 1
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

                        num_lanes_for_to_link = link_lookup_dict.get(f"{int_id}_{dest_node}")["num_lanes"]
                        # extract digit group from num_lanes_for_to_link
                        num_lanes_for_to_link = re.findall(r"\d+", str(num_lanes_for_to_link))[0]  # Extract digit

                        to_lane_val = int(num_lanes_for_to_link) - 1  # to innermost lane
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

                            num_lanes_for_to_link = link_lookup_dict.get(f"{int_id}_{dest_node}")["num_lanes"]
                            # extract digit group from num_lanes_for_to_link
                            num_lanes_for_to_link = re.findall(r"\d+", str(num_lanes_for_to_link))[0]  # Extract digit

                            to_lane_val = int(num_lanes_for_to_link) - u_turn_index - 1
                            if to_lane_val < 0:
                                to_lane_val = 0
                            connection.set("toLane", str(to_lane_val))
                            # connection.set("toLane", f"{int(num_lanes_for_to_link) - u_turn_index - 1}")
                            connection.set("dir", "t")

                            lane_index += 1

    xml_str = xml_prettify(root_con)
    with open(filename, "w") as f:
        f.write(xml_str)

    return True


def generate_sumo_edg_xml(utdf_dict: dict, net_unit: str, filename: str = "network.edg.xml") -> bool:
    """Generate the .edg.xml file.

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        net_unit (str): The unit of the network (e.g., "feet", "meters").
        filename (str): The name of the output edge XML file (.edg.xml).

    Raises:
        ValueError: UTDF Links and Lanes data are required.

    Example:
        >>> from utdf2gmns.func_lib import generate_sumo_edg_xml
        >>> generate_sumo_edg_xml(utdf_dict, net_unit="feet", filename="network.edg.xml")
        >>> # This will generate a network.edg.xml file in the current directory.
        True

    Returns:
        bool: True if the XML file is generated successfully, False otherwise.
    """

    links_df = utdf_dict.get("Links")

    if links_df is None:
        raise ValueError("UTDF Links and Lanes data are required. ")

    network_links = cvt_link_df_to_dict(links_df)

    lane_lookup_dict = generate_net_lane_lookup_dict(utdf_dict, net_unit)

    if "feet" in net_unit:
        unit_speed = "mph"
        unit_distance = "feet"
    elif "meters" in net_unit:
        unit_speed = "km/h"
        unit_distance = "meters"
    else:
        print(f"  Warning:Unknown distance and speed unit for Edge generation: {net_unit}. "
              "Defaulting to meters and km/h.")
        unit_speed = "km/h"
        unit_distance = "meters"

    cvt_unit_speed = {
        "mph": cvt_mph_to_mps,
        "km/h": cvt_kmh_to_mps,
    }
    cvt_unit_distance = {
        "feet": cvt_feet_to_meters,
        "meters": lambda x: x,
    }

    root = ET.Element("edges")
    for int_id, direction_links in network_links.items():
        for direction in direction_links:
            link = direction_links[direction]
            up_node = link["Up ID"]

            edge_elem = ET.SubElement(root, "edge")

            edge_id = f"{up_node}_{int_id}"
            edge_elem.set("id", f"{edge_id}")
            edge_elem.set("from", str(up_node))
            edge_elem.set("to", str(int_id))

            # define number of lanes for the edge
            num_lanes = link.get("Lanes")
            if num_lanes:
                num_lanes_lst = re.findall(r"\d+", str(num_lanes))  # Extract digit group

                if len(num_lanes_lst) == 1:  # only one group of digits
                    num_lanes = int(num_lanes_lst[0])

                    if (num_lanes) > 0:
                        edge_elem.set("numLanes", str(num_lanes))  # Default lanes
                    elif num_lanes == 0:  # one-way street
                        pass

            # check if speed is provided
            if link.get("Speed", None):
                link_speed = link["Speed"]
                link_speed = re.findall(r"\d+", str(link_speed))[0]  # Extract digit group
                speed_in_meter_per_second = cvt_unit_speed[unit_speed](float(link_speed))
                edge_elem.set("speed", str(speed_in_meter_per_second))

            # check if length is provided
            if link.get("Distance", None):
                link_dist = link["Distance"]
                link_dist = re.findall(r"\d+", str(link_dist))[0]  # Extract digit group
                length_in_meter = cvt_unit_distance[unit_distance](float(link_dist))

            # Add lane for each edge
            for lane_id in lane_lookup_dict.keys():
                if lane_id.startswith(f"{edge_id}_"):
                    lane_info = lane_lookup_dict[lane_id]

                    # get the lane direction
                    # lane_dir = lane_info.get("dir")
                    # if lane_dir in ["r", "l", "t"]:
                    #     continue

                    lane_elem = ET.SubElement(edge_elem, "lane")

                    # lane_elem.set("id", f"edge{lane_info["id"]}")
                    lane_elem.set("index", str(lane_info["index"]))

                    if float(lane_info["length"]) > 0:
                        lane_elem.set("length", str(lane_info["length"]))
                    else:
                        lane_elem.set("length", str(length_in_meter))

                    if float(lane_info["speed"]) > 0:
                        lane_elem.set("speed", str(lane_info["speed"]))
                    else:
                        lane_elem.set("speed", str(speed_in_meter_per_second))

    xml_str = xml_prettify(root)
    with open(filename, "w") as f:
        f.write(xml_str)
    return True


def generate_net_link_lookup_dict(utdf_dict: dict) -> dict:
    """Generate a lookup dictionary for edges.

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.

    Raises:
        ValueError: UTDF Links data are required in utdf_dict.

    Example:
        >>> from utdf2gmns.func_lib import generate_net_link_lookup_dict
        >>> edge_lookup_dict = generate_net_link_lookup_dict(utdf_dict)
        >>> # This will generate a lookup dictionary for edges based on the provided UTDF Links data.
        >>> print(edge_lookup_dict)  # {"edge_id": "num_lanes"}
        {'1_2': '2', '2_3': '2', ...}

    Returns:
        dict: A dictionary containing edge information for each intersection.
    """
    link_df = utdf_dict.get("Links")

    if link_df is None:
        raise ValueError("UTDF Links data are required in utdf_dict.")

    network_links = cvt_link_df_to_dict(link_df)  # Convert links DataFrame to dictionary

    # Create a lookup dictionary for edges
    edge_lookup_dict = {}
    for int_id, direction_links in network_links.items():
        for direction in direction_links:
            num_lanes = direction_links[direction].get("Lanes")  # Default lanes
            length = direction_links[direction].get("Distance")
            speed = direction_links[direction].get("Speed")

            up_node = direction_links[direction]["Up ID"]
            edge_lookup_dict[f"{up_node}_{int_id}"] = {
                "num_lanes": num_lanes,
                "length": length,
                "speed": speed,
            }
    return edge_lookup_dict


def generate_sumo_flow_xml(utdf_dict: dict, fname: str = "network.flow.xml", **kwargs) -> bool:
    """Generate the .flow.xml file.

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        fname (str): The name of the output flow XML file (.flow.xml).
        **kwargs: Additional arguments for begin and end time.
            begin (int): The start time for the flow.
            end (int): The end time for the flow.

    Raises:
        ValueError: UTDF Lanes data are required.

    Example:
        >>> from utdf2gmns.func_lib import generate_sumo_flow_xml
        >>> generate_sumo_flow_xml(utdf_dict, fname="network.flow.xml", begin=0, end=3600)
        >>> # This will generate a network.flow.xml file in the current directory.
        True

    Returns:
        bool: True if the XML file is generated successfully, False otherwise.
    """

    lane_df = utdf_dict.get("Lanes")
    if lane_df is None:
        raise ValueError("UTDF Lanes data are required. ")

    network_lanes = cvt_lane_df_to_dict(lane_df)  # Convert lanes DataFrame to dictionary

    root = ET.Element("routes")
    ET.SubElement(root, "vType", id="car", type="passenger")

    # check if begin and end time is provided
    begin_time = kwargs.get("begin")
    end_time = kwargs.get("end")

    flow_id_lst = []
    for int_id, direction_lanes in network_lanes.items():
        for direction in direction_lanes:

            # check whether the node have valid Up Node and Dest Node with volume greater than 0
            up_node = direction_lanes[direction].get("Up Node")
            dest_node = direction_lanes[direction].get("Dest Node")
            volume = direction_lanes[direction].get("Volume", None)

            flow_id = f"{up_node}_{dest_node}"

            try:
                volume = int(volume) if volume is not None else None
            except (ValueError, TypeError):
                volume = None

            if up_node and dest_node and volume and volume > 0:

                # add additional check for lanes
                num_lanes = direction_lanes[direction].get("Lanes")
                num_lanes = re.findall(r"\d+", str(num_lanes))[0]  # Extract digit group
                num_lanes = int(num_lanes)
                if num_lanes <= 0:
                    # Skip if no lanes are available
                    continue

                # avoid duplicate flow id in the flow file
                if flow_id not in flow_id_lst:
                    flow_id_lst.append(flow_id)
                    flow_elem = ET.SubElement(root, "flow")
                    flow_elem.set("id", f"{up_node}_{dest_node}")
                    flow_elem.set("from", f"{up_node}_{int_id}")
                    flow_elem.set("to", f"{int_id}_{dest_node}")
                    flow_elem.set("number", f"{volume}")
                    flow_elem.set("type", "car")
                    if begin_time:
                        flow_elem.set("begin", f"{int(begin_time)}")
                    if end_time:
                        flow_elem.set("end", f"{int(end_time)}")

    xml_str = xml_prettify(root)
    with open(fname, "w") as f:
        f.write(xml_str)
    return True


def generate_turn_bay_node_edge_con(up_node: str,
                                    int_node: str,
                                    length: str,
                                    speed: str,
                                    nod_fname: str = "network.nod.xml",
                                    edge_fname: str = "network.edg.xml",
                                    con_fname: str = "network.con.xml",
                                    **kwargs) -> bool:
    """Create dummy node and edge for turn bay"""

    # Step 1: Get coordinates of up_node and int_id from the node file.

    # Step 2: Generate dummy node id and calculate its coordinate.
    # The dummy node is bay_len away from int_id along the line from int_id toward up_node.

    # Step 3: Open node_fname (.nod.xml) and add the dummy node.

    # Step 4: Add the bay edge into the edge file.
    # Create a new edge that represents the bay.

    # Define the lane for this edge.
    # The lane goes from the dummy node coordinate to int_id's coordinate.

    # Step 5: Add connections to the connection file.
    # Connection from the bay edge to int_id.

    # Connection from int_id to dest_node.
    pass


def generate_sumo_loop_detector_add_xml(utdf_dict: dict, net_unit: str, detector_type: str = "E1",
                                        add_fname: str = "network.add.xml", sim_output_fname: str = "") -> bool:
    """""Generate the .add.xml file for SUMO and add loop detectors for each lane that has a detector.

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        net_unit (str): The unit of the network (e.g., "feet", "meters").
        detector_type (str): The type of detector to be added. Defaults to "E1".
            Accepted type: E1: Inductive loop detector, E2: Lane area detector, E0: Instant induction loops.

        fname (str, optional): SUMO additional file. Defaults to "network.add.xml".
        sim_output_fname (str): The output file name to record loop detectors data in simulation.
            the output file name in default is: output_loop_detector_YYYYMMDDHHMM.xml

    See Also:
        For different detector types, please refer to the SUMO documentation:
            https://sumo.dlr.de/docs/Simulation/Output/#simulated_detectors

        E1: Inductive loop detector
            https://sumo.dlr.de/docs/Simulation/Output/Induction_Loops_Detectors_%28E1%29.html

        E2: Lane area detector,
            https://sumo.dlr.de/docs/Simulation/Output/Lanearea_Detectors_%28E2%29.html

        E0: Instant induction loops,
            https://sumo.dlr.de/docs/Simulation/Output/Instantaneous_Induction_Loops_Detectors.html
    """

    # get lane_lookup_dict from utdf_dict and net_unit
    lane_lookup_dict = generate_net_lane_lookup_dict(utdf_dict, net_unit)

    # get detector tag
    if detector_type == "E1":
        detector_tag = "inductionLoop"
    elif detector_type == "E2":
        detector_tag = "laneAreaDetector"
    elif detector_type == "E0":
        detector_tag = "instantInductionLoop"
    else:
        raise ValueError(f"Unknown detector type: {detector_type}. Accepted types are E1, E2, E0.")

    add_elem = ET.Element("additional")

    if not str(add_fname).endswith(".add.xml"):
        add_fname = f"{add_fname}.add.xml"

    if sim_output_fname:
        if not str(sim_output_fname).endswith(".xml"):
            sim_output_fname = f"{sim_output_fname}.xml"
    else:
        sim_output_fname = f"output_loop_detector_{datetime.now().strftime(r'%Y%m%d%H%M')}.xml"

    for lane_id, lane_info in lane_lookup_dict.items():
        # Check if the lane has a detector, num_detectors not None
        if lane_info.get("numDetects"):
            # Create the detector element
            detector = ET.SubElement(add_elem, detector_tag)
            detector.set("id", f"{lane_id}_detector")
            detector.set("lane", f"{lane_id}")
            detector.set("pos", "-8")  # must assigned, backward of the lane
            detector.set("friendlyPos", "true")
            # detector.set("vTypes", "")
            detector.set("file", f"{sim_output_fname}")  # output file name

            # Add the detector to the root element
            root = ET.Element("additional")
            root.append(detector)

    xml_str = xml_prettify(add_elem)
    with open(add_fname, "w") as f:
        f.write(xml_str)
    return True
