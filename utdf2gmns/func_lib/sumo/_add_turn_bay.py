'''
##############################################################
# Created Date: Sunday, April 6th 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

import xml.etree.ElementTree as ET
import math


def point_on_line(x1, y1, x2, y2, distance):
    """
    Given a starting point (x1, y1) and an ending point (x2, y2),
    return the coordinates of the point at a given distance from the starting point.
    """
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx**2 + dy**2)
    if length == 0:
        return x1, y1
    ratio = distance / length
    x = x1 + ratio * dx
    y = y1 + ratio * dy
    return x, y


def generate_turn_bay_node_edge_con(up_node, int_id, dest_node, bay_len, bay_speed, node_fname, edge_fname, con_fname):
    # Step 1: Get coordinates of up_node and int_id from the node file.
    node_tree = ET.parse(node_fname)
    node_root = node_tree.getroot()

    up_coords = None
    int_coords = None

    # Assuming each node element is of the form: <node id="..." x="..." y="..."/>
    for node in node_root.findall("node"):
        node_id = node.get("id")
        if node_id == up_node:
            up_coords = (float(node.get("x")), float(node.get("y")))
        if node_id == int_id:
            int_coords = (float(node.get("x")), float(node.get("y")))

    if up_coords is None or int_coords is None:
        raise ValueError(
            "Either up_node or int_id was not found in the node file.")

    # Step 2: Generate dummy node id and calculate its coordinate.
    # The dummy node is bay_len away from int_id along the line from int_id toward up_node.
    dummy_node = f"{int_id}_bay"
    dummy_x, dummy_y = point_on_line(
        int_coords[0], int_coords[1], up_coords[0], up_coords[1], bay_len)

    # Step 3: Open node_fname (.nod.xml) and add the dummy node.
    dummy_node_elem = ET.Element(
        "node", id=dummy_node, x=str(dummy_x), y=str(dummy_y))
    node_root.append(dummy_node_elem)
    node_tree.write(node_fname)

    # Step 4: Add the bay edge into the edge file.
    edge_tree = ET.parse(edge_fname)
    edge_root = edge_tree.getroot()

    # Create a new edge that represents the bay.
    bay_edge_id = f"{dummy_node}_{int_id}"
    edge_attrib = {
        "id": bay_edge_id,
        "from": dummy_node,
        "to": int_id,
        "numLanes": "1",
        "speed": str(bay_speed)
    }
    edge_elem = ET.Element("edge", edge_attrib)

    # Define the lane for this edge.
    # The lane goes from the dummy node coordinate to int_id's coordinate.
    lane_attrib = {
        "index": "0",
        "speed": str(bay_speed),
        "length": str(bay_len),
        "shape": f"{dummy_x},{dummy_y} {int_coords[0]},{int_coords[1]}"
    }
    lane_elem = ET.Element("lane", lane_attrib)
    edge_elem.append(lane_elem)
    edge_root.append(edge_elem)
    edge_tree.write(edge_fname)

    # Step 5: Add connections to the connection file.
    con_tree = ET.parse(con_fname)
    con_root = con_tree.getroot()

    # Connection from the bay edge to int_id.
    con1_attrib = {
        "from": bay_edge_id,
        "to": int_id,
        "fromLane": "0",
        "toLane": "0"
    }
    con1 = ET.Element("connection", con1_attrib)

    # Connection from int_id to dest_node.
    con2_attrib = {
        "from": int_id,
        "to": dest_node,
        "fromLane": "0",
        "toLane": "0"
    }
    con2 = ET.Element("connection", con2_attrib)

    con_root.append(con1)
    con_root.append(con2)
    con_tree.write(con_fname)
