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
import xml.etree.ElementTree as ET

import sumolib
from sumolib.net import Net, TLS, TLSProgram, Phase, EdgeType
from sumolib.net.node import Node
from sumolib.net.edge import Edge
from sumolib.net.lane import Lane
from sumolib.net.roundabout import Roundabout
from sumolib.net.connection import Connection
from sumolib.net.netshiftadaptor import NetShiftAdaptor

from utdf2gmns.func_lib.geocoding_Links import cvt_utm_to_lonlat, cvt_lonlat_to_utm


def gererate_sumo_network() -> Net:
    pass


def generate_sumo_nodes(network_nodes: dict, filename="network.nod.xml") -> list:
    """Create SUMO node XML file."""
    nodes = []
    for node_id, node in network_nodes.items():
        sumo_node = sumolib.net.node.Node(id=node_id,
                                          x=node["X"],
                                          y=node["Y"])
        nodes.append(sumo_node)
    return nodes


def generate_sumo_edges(network_edges: dict, filename="network.edg.xml") -> list:
    """Create SUMO edge XML file."""
    edges = []
    for int_id, edges in network_edges.items():
        start_node = int_id

        for edge in edges:
            sumo_edge = sumolib.net.edge.Edge(
                id=f"{start_node}_{edges[edge]['Up ID']}",
                fromN=start_node,
                toN=edges[edge]["Up ID"],
                numLanes=edges[edge]["Lanes"],
                prio="-1",
                function="normal"
            )
            edges.append(sumo_edge)
    return edges


def xml_prettify(element):
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(element, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="    ")


def generate_nod_xml(network_nodes: dict, filename="network.nod.xml") -> None:
    """Generate the .nod.xml file."""

    root = ET.Element("nodes")
    for node_id, node in network_nodes.items():
        node_elem = ET.SubElement(root, "node")
        node_elem.set("id", str(node_id))

        # Convert lonlat to UTM
        utm_x, utm_y, zone, hemi = cvt_lonlat_to_utm(node["x_coord"], node["y_coord"])

        node_elem.set("x", str(utm_x))
        node_elem.set("y", str(utm_y))

        node_type_description = node.get("TYPE_DESC")
        if node_type_description == "Signalized":
            node_elem.set("type", "traffic_light")  # Default type

    xml_str = xml_prettify(root)
    with open(filename, "w") as f:
        f.write(xml_str)

    return None


def generate_edg_xml(network_links: dict, filename="network.edg.xml") -> None:
    """Generate the .edg.xml file."""

    root = ET.Element("edges")
    for int_id, direction_links in network_links.items():
        for direction in direction_links:
            link = direction_links[direction]
            start_node = int_id
            end_node = link["Up ID"]

            edge_elem = ET.SubElement(root, "edge")
            edge_elem.set("id", f"{start_node}_{end_node}")
            edge_elem.set("from", str(start_node))
            edge_elem.set("to", str(end_node))

            # define number of lanes for the edge
            num_lanes = link.get("Lanes", "2")  # Default lanes
            if num_lanes == "0":
                num_lanes = "2"
            if len(num_lanes) > 1:
                num_lanes = num_lanes[-1]

            edge_elem.set("numLanes", str(num_lanes))  # Default lanes

            # check if speed is provided
            if link.get("Speed", None):
                edge_elem.set("speed", str(link.get("Speed")))

    xml_str = xml_prettify(root)
    with open(filename, "w") as f:
        f.write(xml_str)
    return None
