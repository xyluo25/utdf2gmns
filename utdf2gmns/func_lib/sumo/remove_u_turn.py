'''
##############################################################
# Created Date: Friday, February 7th 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

import xml.etree.ElementTree as ET


def remove_sumo_U_turn(path_net: str) -> bool:
    """ Remove U-turns in the SUMO network."""

    # check if path is a string and ends with .net.xml
    if not isinstance(path_net, str):
        raise ValueError("path_net must be a string")
    if not path_net.endswith(".net.xml"):
        raise ValueError("path_net must end with .net.xml")

    # open the xml file and find all connections
    with open(path_net, 'r') as f:
        tree = ET.parse(f)

    root = tree.getroot()
    connections = root.findall("connection")

    # loop through all connections
    for connection in connections:
        from_edge = connection.get('from')
        to_edge = connection.get('to')

        if from_edge == to_edge:
            # change the dir attribute to "invalid" if the connection is a U-turn'
            connection.attrib['dir'] = "invalid"
            # directly remove the connection if it is a U-turn
            # root.remove(connection)

        if from_edge == "_".join(to_edge.split("_")[::-1]):
            connection.attrib["dir"] = "invalid"

            # directly remove the connection if it is a U-turn
            # root.remove(connection)

    # write the modified xml to the file
    tree.write(path_net, encoding='utf-8', xml_declaration=True)
    print("  :U-turns removed from the SUMO network")
    return True