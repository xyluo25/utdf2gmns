"""Regression tests for selective SUMO U-turn removal."""

import xml.etree.ElementTree as ET
from pathlib import Path

from utdf2gmns.func_lib.sumo.remove_u_turn import remove_sumo_U_turn


def _write_sumo_net(path_net: Path, edges: list[dict[str, str]],
                    connections: list[dict[str, str]]) -> None:
    """Write a minimal SUMO net.xml file for U-turn removal tests."""
    root = ET.Element("net")
    for edge_attributes in edges:
        ET.SubElement(root, "edge", edge_attributes)
    for connection_attributes in connections:
        ET.SubElement(root, "connection", connection_attributes)

    ET.ElementTree(root).write(path_net, encoding="utf-8", xml_declaration=True)


def _write_sumo_connections(path_con: Path,
                            connections: list[dict[str, str]]) -> None:
    """Write a minimal SUMO plain con.xml file."""
    root = ET.Element("connections")
    for connection_attributes in connections:
        ET.SubElement(root, "connection", connection_attributes)

    ET.ElementTree(root).write(path_con, encoding="utf-8", xml_declaration=True)


def _get_single_connection(path_net: Path) -> ET.Element:
    """Return the only connection in a minimal SUMO net.xml test file."""
    connections = ET.parse(path_net).getroot().findall("connection")
    assert len(connections) == 1
    return connections[0]


def _get_connections(path_net: Path) -> list[ET.Element]:
    """Return all connections in a minimal SUMO net.xml test file."""
    return ET.parse(path_net).getroot().findall("connection")


def test_remove_dead_end_turn_bay_u_turn_when_not_in_con_file(tmp_path):
    """SUMO-created dead-end U-turns should be deleted."""
    path_net = tmp_path / "network.net.xml"
    path_con = tmp_path / "network.con.xml"
    connection = {
        "from": "1_2_bay",
        "to": "2_1",
        "fromLane": "0",
        "toLane": "0",
        "dir": "t",
    }

    _write_sumo_net(
        path_net,
        edges=[
            {"id": "1_2_bay", "from": "1_2_bay_node", "to": "2"},
            {"id": "2_1", "from": "2", "to": "1"},
        ],
        connections=[
            {**connection, "via": ":2_0_0"},
            {"from": ":2_0", "to": "2_1", "fromLane": "0", "toLane": "0", "via": ":2_1_0"},
            {"from": ":2_1", "to": "2_1", "fromLane": "0", "toLane": "0"},
        ],
    )
    _write_sumo_connections(path_con, connections=[])

    remove_sumo_U_turn(str(path_net), rebuild_net=False)

    assert _get_connections(path_net) == []


def test_preserve_explicit_u_turn_from_con_file(tmp_path):
    """U-turns generated from UTDF lane movements should stay valid."""
    path_net = tmp_path / "network.net.xml"
    path_con = tmp_path / "network.con.xml"
    connection = {
        "from": "1_2_bay",
        "to": "2_1",
        "fromLane": "0",
        "toLane": "0",
        "dir": "t",
    }

    _write_sumo_net(
        path_net,
        edges=[
            {"id": "1_2_bay", "from": "1_2_bay_node", "to": "2"},
            {"id": "2_1", "from": "2", "to": "1"},
        ],
        connections=[connection],
    )
    _write_sumo_connections(path_con, connections=[connection])

    remove_sumo_U_turn(str(path_net), rebuild_net=False)

    assert _get_single_connection(path_net).get("dir") == "t"


def test_preserve_non_dead_end_u_turn_without_con_file(tmp_path):
    """A reverse-edge U-turn at a normal intersection should not be disabled."""
    path_net = tmp_path / "network.net.xml"
    path_con = tmp_path / "network.con.xml"
    connection = {
        "from": "1_2",
        "to": "2_1",
        "fromLane": "0",
        "toLane": "0",
        "dir": "t",
    }

    _write_sumo_net(
        path_net,
        edges=[
            {"id": "1_2", "from": "1", "to": "2"},
            {"id": "2_1", "from": "2", "to": "1"},
            {"id": "2_3", "from": "2", "to": "3"},
        ],
        connections=[connection],
    )
    _write_sumo_connections(path_con, connections=[])

    remove_sumo_U_turn(str(path_net), rebuild_net=False)

    assert _get_single_connection(path_net).get("dir") == "t"
