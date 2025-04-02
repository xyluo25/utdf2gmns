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
from typing import TYPE_CHECKING

import pandas as pd
import pyufunc as pf

from utdf2gmns.func_lib.gmns.geocoding_Links import cvt_lonlat_to_utm

if TYPE_CHECKING:
    import sumolib
    from sumolib.net import Net


def generate_sumo_network() -> "Net":
    pass


@pf.requires("sumolib", verbose=False)
def generate_sumo_nodes(network_nodes: dict, filename: str = "network.nod.xml") -> list:
    """Create SUMO node XML file."""

    pf.import_package("sumolib", verbose=False)  # ensure sumolib is imported
    import sumolib  # ensure sumolib is imported

    nodes = []
    for node_id, node in network_nodes.items():
        sumo_node = sumolib.net.node.Node(id=node_id,
                                          x=node["X"],
                                          y=node["Y"])
        nodes.append(sumo_node)
    return nodes


@pf.requires("sumolib", verbose=False)
def generate_sumo_edges(network_edges: dict, filename: str = "network.edg.xml") -> list:
    """Create SUMO edge XML file."""
    pf.import_package("sumolib", verbose=False)  # ensure sumolib is imported
    import sumolib  # ensure sumolib is imported

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


def xml_prettify(element: str) -> str:
    """Return a pretty-printed XML string for the Element."""
    rough_string = ET.tostring(element, 'utf-8')
    re_parsed = minidom.parseString(rough_string)
    return re_parsed.toprettyxml(indent="    ")


def generate_sumo_nod_xml(network_nodes: dict, filename: str = "network.nod.xml") -> bool:
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

    return True


def generate_sumo_edg_xml(network_links: dict, filename: str = "network.edg.xml") -> bool:
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
    return True


def generate_sumo_flow_xml(network_lanes: dict, fname: str = "network.flow.xml", **kwargs) -> bool:
    """Generate the .flow.xml file."""
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