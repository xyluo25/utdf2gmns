"""Regression tests for SUMO turn-bay edge splitting."""

import xml.etree.ElementTree as ET

import pandas as pd

from utdf2gmns.func_lib.gmns.geocoding_Nodes import calculate_new_coordinates_from_offsets
from utdf2gmns.func_lib.sumo.gmns2sumo import (
    generate_net_link_lookup_dict,
    generate_sumo_connection_xml,
    generate_sumo_edg_xml,
    generate_sumo_flow_xml,
    generate_sumo_loop_detector_add_xml,
    generate_sumo_network_route_xml,
    generate_sumo_nod_xml,
)


def _blank_link_row(record_name: str, intersection_id: str) -> dict[str, str]:
    """Create one UTDF Links row with the standard direction columns."""
    return {
        "RECORDNAME": record_name,
        "INTID": intersection_id,
        "NB": "",
        "SB": "",
        "EB": "",
        "WB": "",
        "NE": "",
        "NW": "",
        "SE": "",
        "SW": "",
    }


def _blank_lane_row(record_name: str, intersection_id: str) -> dict[str, str]:
    """Create one UTDF Lanes row with the movement columns used in this test."""
    return {
        "RECORDNAME": record_name,
        "INTID": intersection_id,
        "NBR": "",
        "NBT": "",
        "NBL": "",
        "SBR": "",
        "SBT": "",
        "SBL": "",
    }


def _parse_sumo_shape(shape_text: str | None) -> list[tuple[float, float]]:
    """Parse a SUMO shape attribute into longitude/latitude points."""
    assert shape_text is not None
    return [
        tuple(float(value) for value in point_text.split(",")[:2])
        for point_text in shape_text.split()
    ]


def _build_turn_bay_utdf_dict() -> dict:
    """Build a small UTDF-like dictionary with turn bays on source and target links."""
    link_rows = []

    for record_name, value in {
        "Up ID": "2",
        "Lanes": "5",
        "Distance": "1000",
        "Speed": "35",
    }.items():
        row = _blank_link_row(record_name, "1")
        row["NB"] = value
        link_rows.append(row)

    for record_name, value in {
        "Up ID": "1",
        "Lanes": "5",
        "Distance": "1000",
        "Speed": "35",
    }.items():
        row = _blank_link_row(record_name, "3")
        row["NB"] = value
        link_rows.append(row)

    lane_rows = []
    int_1_values = {
        "Up Node": {"NBR": "2", "NBT": "2", "NBL": "2"},
        "Dest Node": {"NBR": "3", "NBT": "3", "NBL": "3"},
        "Lanes": {"NBR": "1", "NBT": "3", "NBL": "1"},
        "Storage": {"NBR": "100", "NBL": "100"},
        "Taper": {"NBR": "25", "NBL": "25"},
        "Speed": {"NBR": "35", "NBT": "35", "NBL": "35"},
        "Volume": {"NBR": "100", "NBT": "200", "NBL": "50"},
        "numDetects": {"NBR": "1"},
    }
    for record_name, movement_values in int_1_values.items():
        row = _blank_lane_row(record_name, "1")
        row.update(movement_values)
        lane_rows.append(row)

    int_3_values = {
        "Up Node": {"SBR": "1", "SBT": "1", "SBL": "1"},
        "Dest Node": {"SBR": "6", "SBT": "7", "SBL": "8"},
        "Lanes": {"SBR": "1", "SBT": "3", "SBL": "1"},
        "Storage": {"SBR": "100", "SBL": "100"},
        "Taper": {"SBR": "25", "SBL": "25"},
        "Speed": {"SBR": "35", "SBT": "35", "SBL": "35"},
        "Volume": {"SBR": "0", "SBT": "0", "SBL": "0"},
        "numDetects": {},
    }
    for record_name, movement_values in int_3_values.items():
        row = _blank_lane_row(record_name, "3")
        row.update(movement_values)
        lane_rows.append(row)

    return {
        "Links": pd.DataFrame(link_rows),
        "Lanes": pd.DataFrame(lane_rows),
        "network_nodes": {
            "1": {"x_coord": -111.0000, "y_coord": 33.0000, "TYPE_DESC": "Signalized"},
            "2": {"x_coord": -111.0100, "y_coord": 33.0000, "TYPE_DESC": "Signalized"},
            "3": {"x_coord": -111.0000, "y_coord": 33.0100, "TYPE_DESC": "Signalized"},
        },
    }


def _build_network_flow_utdf_dict(second_intersection_volume: str = "100") -> dict:
    """Build a three-intersection chain for network-level route tests."""
    link_rows = []
    for intersection_id, up_node in [("1", "2"), ("3", "1"), ("4", "3")]:
        for record_name, value in {
            "Up ID": up_node,
            "Lanes": "2",
            "Distance": "1000",
            "Speed": "35",
        }.items():
            row = _blank_link_row(record_name, intersection_id)
            row["NB"] = value
            link_rows.append(row)

    lane_rows = []
    for intersection_id, up_node, dest_node in [("1", "2", "3"), ("3", "1", "4")]:
        movement_values = {
            "Up Node": {"NBT": up_node},
            "Dest Node": {"NBT": dest_node},
            "Lanes": {"NBT": "2"},
            "Speed": {"NBT": "35"},
            "Volume": {
                "NBT": "100" if intersection_id == "1" else second_intersection_volume,
            },
        }
        for record_name, values_by_movement in movement_values.items():
            row = _blank_lane_row(record_name, intersection_id)
            row.update(values_by_movement)
            lane_rows.append(row)

    return {
        "Links": pd.DataFrame(link_rows),
        "Lanes": pd.DataFrame(lane_rows),
        "network_nodes": {
            "1": {"x_coord": -111.0000, "y_coord": 33.0000, "TYPE_DESC": "Signalized"},
            "2": {"x_coord": -111.0100, "y_coord": 33.0000, "TYPE_DESC": "Signalized"},
            "3": {"x_coord": -111.0000, "y_coord": 33.0100, "TYPE_DESC": "Signalized"},
            "4": {"x_coord": -111.0000, "y_coord": 33.0200, "TYPE_DESC": "Signalized"},
        },
    }


def _build_merge_distribution_utdf_dict() -> dict:
    """Build a five-lane source movement that merges into three receiving lanes."""
    link_rows = []
    for intersection_id, up_node, lane_count in [
        ("1", "2", "5"),
        ("3", "1", "3"),
    ]:
        for record_name, value in {
            "Up ID": up_node,
            "Lanes": lane_count,
            "Distance": "1000",
            "Speed": "35",
        }.items():
            row = _blank_link_row(record_name, intersection_id)
            row["NB"] = value
            link_rows.append(row)

    lane_rows = []
    for record_name, values_by_movement in {
        "Up Node": {"NBT": "2"},
        "Dest Node": {"NBT": "3"},
        "Lanes": {"NBT": "5"},
        "Volume": {"NBT": "500"},
    }.items():
        row = _blank_lane_row(record_name, "1")
        row.update(values_by_movement)
        lane_rows.append(row)

    return {
        "Links": pd.DataFrame(link_rows),
        "Lanes": pd.DataFrame(lane_rows),
        "network_nodes": {
            "1": {"x_coord": -111.0000, "y_coord": 33.0000, "TYPE_DESC": "Signalized"},
            "2": {"x_coord": -111.0100, "y_coord": 33.0000, "TYPE_DESC": "External Node"},
            "3": {"x_coord": -111.0000, "y_coord": 33.0100, "TYPE_DESC": "External Node"},
        },
    }


def _build_internal_endpoint_network_utdf_dict(first_volume: str,
                                               second_volume: str) -> dict:
    """Build a chain where one intersection movement is an uncounted connector."""
    link_rows = []
    for intersection_id, up_node in [("1", "0"), ("2", "1"), ("3", "2")]:
        for record_name, value in {
            "Up ID": up_node,
            "Lanes": "1",
            "Distance": "500",
            "Speed": "30",
        }.items():
            row = _blank_link_row(record_name, intersection_id)
            row["NB"] = value
            link_rows.append(row)

    lane_rows = []
    movement_values_by_intersection = {
        "1": {
            "Up Node": {"NBT": "0"},
            "Dest Node": {"NBT": "2"},
            "Lanes": {"NBT": "1"},
            "Speed": {"NBT": "30"},
            "Volume": {"NBT": first_volume},
        },
        "2": {
            "Up Node": {"NBT": "1"},
            "Dest Node": {"NBT": "3"},
            "Lanes": {"NBT": "1"},
            "Speed": {"NBT": "30"},
            "Volume": {"NBT": second_volume},
        },
    }
    for intersection_id, movement_values in movement_values_by_intersection.items():
        for record_name, values_by_movement in movement_values.items():
            row = _blank_lane_row(record_name, intersection_id)
            row.update(values_by_movement)
            lane_rows.append(row)

    return {
        "Links": pd.DataFrame(link_rows),
        "Lanes": pd.DataFrame(lane_rows),
        "network_nodes": {
            "0": {"x_coord": -111.0200, "y_coord": 33.0000, "TYPE_DESC": "External Node"},
            "1": {"x_coord": -111.0100, "y_coord": 33.0000, "TYPE_DESC": "Bend"},
            "2": {"x_coord": -111.0000, "y_coord": 33.0000, "TYPE_DESC": "Bend"},
            "3": {"x_coord": -110.9900, "y_coord": 33.0000, "TYPE_DESC": "External Node"},
        },
    }


def _build_one_way_utdf_dict() -> dict:
    """Build a one-way approach with a zero-lane reverse placeholder."""
    link_rows = []

    def add_link(intersection_id: str, direction: str, up_node: str,
                 lane_count: str) -> None:
        """Add one Links direction record to the test UTDF table."""
        for record_name, value in {
            "Up ID": up_node,
            "Lanes": lane_count,
            "Distance": "1000",
            "Speed": "35",
        }.items():
            row = _blank_link_row(record_name, intersection_id)
            row[direction] = value
            link_rows.append(row)

    add_link("1", "NB", "2", "2")
    add_link("2", "SB", "1", "0")
    add_link("3", "NB", "1", "2")
    add_link("4", "NB", "1", "1")

    lane_rows = []
    int_1_values = {
        "Up Node": {"NBT": "2", "NBR": "2"},
        "Dest Node": {"NBT": "3", "NBR": "4"},
        "Lanes": {"NBT": "2", "NBR": "0"},
        "Speed": {"NBT": "35", "NBR": "35"},
        "Volume": {"NBT": "100", "NBR": "15"},
    }
    for record_name, movement_values in int_1_values.items():
        row = _blank_lane_row(record_name, "1")
        row.update(movement_values)
        lane_rows.append(row)

    int_2_placeholder_values = {
        "Up Node": {"SBT": "1"},
        "Dest Node": {"SBT": "5"},
        "Lanes": {"SBT": "0"},
        "Volume": {"SBT": "0"},
    }
    for record_name, movement_values in int_2_placeholder_values.items():
        row = _blank_lane_row(record_name, "2")
        row.update(movement_values)
        lane_rows.append(row)

    return {
        "Links": pd.DataFrame(link_rows),
        "Lanes": pd.DataFrame(lane_rows),
        "network_nodes": {
            "1": {"x_coord": -111.0000, "y_coord": 33.0000, "TYPE_DESC": "Signalized"},
            "2": {"x_coord": -111.0100, "y_coord": 33.0000, "TYPE_DESC": "Signalized"},
            "3": {"x_coord": -111.0000, "y_coord": 33.0100, "TYPE_DESC": "Signalized"},
            "4": {"x_coord": -111.0000, "y_coord": 32.9900, "TYPE_DESC": "Signalized"},
        },
    }


def _build_signal_approach_without_target_utdf_dict() -> dict:
    """Build a signalized approach whose only movement has no downstream edge."""
    link_rows = []
    for record_name, value in {
        "Up ID": "2",
        "Lanes": "1",
        "Distance": "500",
        "Speed": "30",
    }.items():
        row = _blank_link_row(record_name, "1")
        row["NB"] = value
        link_rows.append(row)

    lane_rows = []
    for record_name, movement_values in {
        "Up Node": {"NBT": "2"},
        "Dest Node": {"NBT": "9"},
        "Lanes": {"NBT": "1"},
        "Volume": {"NBT": "0"},
    }.items():
        row = _blank_lane_row(record_name, "1")
        row.update(movement_values)
        lane_rows.append(row)

    return {
        "Links": pd.DataFrame(link_rows),
        "Lanes": pd.DataFrame(lane_rows),
        "Timeplans": pd.DataFrame([{
            "INTID": "1",
            "RECORDNAME": "Control Type",
            "DATA": "0",
        }]),
        "network_nodes": {
            "1": {"x_coord": -111.0000, "y_coord": 33.0000, "TYPE_DESC": "Signalized"},
            "2": {"x_coord": -111.0100, "y_coord": 33.0000, "TYPE_DESC": "External Node"},
        },
    }


def _build_curved_link_utdf_dict() -> dict:
    """Build a link with a UTDF curve point in the Links table."""
    link_rows = []
    for record_name, value in {
        "Up ID": "2",
        "Lanes": "1",
        "Distance": "1000",
        "Speed": "35",
        "Curve Pt X": "500",
        "Curve Pt Y": "250",
    }.items():
        row = _blank_link_row(record_name, "1")
        row["NB"] = value
        link_rows.append(row)

    base_lon = -111.0
    base_lat = 33.0
    upstream_lon, upstream_lat = calculate_new_coordinates_from_offsets(
        base_lon,
        base_lat,
        1000,
        0,
        "feet",
    )
    return {
        "Links": pd.DataFrame(link_rows),
        "network_nodes": {
            "1": {
                "x_coord": base_lon,
                "y_coord": base_lat,
                "TYPE_DESC": "Signalized",
                "X": "0",
                "Y": "0",
            },
            "2": {
                "x_coord": upstream_lon,
                "y_coord": upstream_lat,
                "TYPE_DESC": "External Node",
                "X": "1000",
                "Y": "0",
            },
        },
    }


def _build_bidirectional_curved_link_utdf_dict() -> dict:
    """Build a bidirectional link where each direction stores one curve point."""
    link_rows = []
    for record_name, value in {
        "Up ID": "2",
        "Lanes": "2",
        "Distance": "1000",
        "Speed": "35",
        "Curve Pt X": "400",
        "Curve Pt Y": "250",
    }.items():
        row = _blank_link_row(record_name, "1")
        row["NB"] = value
        link_rows.append(row)

    for record_name, value in {
        "Up ID": "1",
        "Lanes": "2",
        "Distance": "1000",
        "Speed": "35",
        "Curve Pt X": "600",
        "Curve Pt Y": "250",
    }.items():
        row = _blank_link_row(record_name, "2")
        row["SB"] = value
        link_rows.append(row)

    base_lon = -111.0
    base_lat = 33.0
    upstream_lon, upstream_lat = calculate_new_coordinates_from_offsets(
        base_lon,
        base_lat,
        1000,
        0,
        "feet",
    )
    return {
        "Links": pd.DataFrame(link_rows),
        "network_nodes": {
            "1": {
                "x_coord": base_lon,
                "y_coord": base_lat,
                "TYPE_DESC": "Signalized",
                "X": "0",
                "Y": "0",
            },
            "2": {
                "x_coord": upstream_lon,
                "y_coord": upstream_lat,
                "TYPE_DESC": "External Node",
                "X": "1000",
                "Y": "0",
            },
        },
    }


def _build_z_shaped_curve_utdf_dict() -> dict:
    """Build curve-point data that would create an unrealistic Z-shaped link."""
    link_rows = []
    for record_name, value in {
        "Up ID": "2",
        "Lanes": "2",
        "Distance": "1000",
        "Speed": "35",
        "Curve Pt X": "900",
        "Curve Pt Y": "-200",
    }.items():
        row = _blank_link_row(record_name, "1")
        row["NB"] = value
        link_rows.append(row)

    for record_name, value in {
        "Up ID": "1",
        "Lanes": "2",
        "Distance": "1000",
        "Speed": "35",
        "Curve Pt X": "400",
        "Curve Pt Y": "200",
    }.items():
        row = _blank_link_row(record_name, "2")
        row["SB"] = value
        link_rows.append(row)

    base_lon = -111.0
    base_lat = 33.0
    end_lon, end_lat = calculate_new_coordinates_from_offsets(
        base_lon,
        base_lat,
        1000,
        0,
        "feet",
    )
    return {
        "Links": pd.DataFrame(link_rows),
        "network_nodes": {
            "1": {
                "x_coord": end_lon,
                "y_coord": end_lat,
                "TYPE_DESC": "Signalized",
                "X": "1000",
                "Y": "0",
            },
            "2": {
                "x_coord": base_lon,
                "y_coord": base_lat,
                "TYPE_DESC": "External Node",
                "X": "0",
                "Y": "0",
            },
        },
    }


def _movement_volume_by_main_edge_pair(route_file) -> dict[tuple[str, str], int]:
    """Aggregate generated route flows back to main-edge movement counts."""
    route_root = ET.parse(route_file).getroot()
    routes_by_id = {
        route.get("id"): (route.get("edges") or "").split()
        for route in route_root.findall("route")
    }
    movement_volumes: dict[tuple[str, str], int] = {}

    for flow in route_root.findall("flow"):
        route_edges = routes_by_id[flow.get("route")]
        main_edges = [
            edge_id for edge_id in route_edges
            if not edge_id.endswith("_bay")
        ]
        flow_volume = int(flow.get("number"))
        for source_edge_id, target_edge_id in zip(main_edges, main_edges[1:]):
            movement_key = (source_edge_id, target_edge_id)
            movement_volumes[movement_key] = (
                movement_volumes.get(movement_key, 0) + flow_volume
            )

    return movement_volumes


def test_turn_bay_edges_are_split_and_turns_target_straight_lanes(tmp_path):
    """Turn bays should be short stop-line edges, not extra lanes on the full link."""
    utdf_dict = _build_turn_bay_utdf_dict()
    node_file = tmp_path / "network.nod.xml"
    edge_file = tmp_path / "network.edg.xml"
    connection_file = tmp_path / "network.con.xml"

    generate_sumo_nod_xml(utdf_dict, str(node_file), "feet, mph")
    generate_sumo_edg_xml(utdf_dict, "feet, mph", str(edge_file))
    generate_sumo_connection_xml(utdf_dict, str(connection_file), "feet, mph")

    node_by_id = {
        node.get("id"): node
        for node in ET.parse(node_file).getroot()
    }
    node_ids = set(node_by_id)
    assert "2_1_bay_node" in node_ids
    assert "1_3_bay_node" in node_ids
    assert node_by_id["2_1_bay_node"].get("type") == "unregulated"

    edge_by_id = {
        edge.get("id"): edge
        for edge in ET.parse(edge_file).getroot().findall("edge")
    }
    assert edge_by_id["2_1"].get("numLanes") == "3"
    assert edge_by_id["2_1"].get("to") == "2_1_bay_node"
    assert edge_by_id["2_1_bay"].get("numLanes") == "5"
    assert edge_by_id["1_3"].get("numLanes") == "3"
    assert edge_by_id["1_3"].get("to") == "1_3_bay_node"

    connections = ET.parse(connection_file).getroot().findall("connection")
    right_turn_connections = [
        connection for connection in connections
        if connection.get("from") == "2_1_bay"
        and connection.get("to") == "1_3"
        and connection.get("dir") == "r"
    ]
    assert len(right_turn_connections) == 1
    assert right_turn_connections[0].get("toLane") == "0"

    diverge_to_lanes = {
        connection.get("toLane")
        for connection in connections
        if connection.get("from") == "2_1" and connection.get("to") == "2_1_bay"
    }
    assert diverge_to_lanes == {"0", "1", "2", "3", "4"}
    bay_connections = [
        connection for connection in connections
        if connection.get("from") == "2_1" and connection.get("to") == "2_1_bay"
    ]
    assert all(connection.get("pass") == "true" for connection in bay_connections)
    assert all(connection.get("uncontrolled") == "true" for connection in bay_connections)


def test_flows_and_detectors_use_split_edge_ids(tmp_path):
    """Flows start on main edges while stop-line detectors use bay-edge lane ids."""
    utdf_dict = _build_turn_bay_utdf_dict()
    flow_file = tmp_path / "network.flow.xml"
    add_file = tmp_path / "network.add.xml"

    generate_sumo_flow_xml(
        utdf_dict,
        str(flow_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )
    generate_sumo_loop_detector_add_xml(
        utdf_dict,
        "feet, mph",
        add_fname=str(add_file),
        sim_output_fname="detectors.xml",
    )

    flows = ET.parse(flow_file).getroot().findall("flow")
    right_turn_flow = next(flow for flow in flows if flow.get("id") == "2_3")
    assert right_turn_flow.get("from") == "2_1"
    assert right_turn_flow.get("to") == "1_3"

    detectors = ET.parse(add_file).getroot().findall("inductionLoop")
    assert detectors[0].get("lane") == "2_1_bay_0"


def test_network_route_flow_uses_turn_bay_edges(tmp_path):
    """Network-level route flows should include short stop-line bay edges."""
    utdf_dict = _build_turn_bay_utdf_dict()
    network_route_file = tmp_path / "network.rou.xml"

    generate_sumo_network_route_xml(
        utdf_dict,
        str(network_route_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )

    route_root = ET.parse(network_route_file).getroot()
    route_edges = [
        route.get("edges")
        for route in route_root.findall("route")
    ]
    flow = route_root.find("flow")
    assert "2_1 2_1_bay 1_3" in route_edges
    assert flow is not None
    assert flow.get("number") == "350"


def test_network_route_flow_extends_across_multiple_intersections(tmp_path):
    """Network-level route flows should combine local turning counts into paths."""
    utdf_dict = _build_network_flow_utdf_dict()
    intersection_flow_file = tmp_path / "network.flow.xml"
    network_route_file = tmp_path / "network.rou.xml"

    generate_sumo_flow_xml(
        utdf_dict,
        str(intersection_flow_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )
    generate_sumo_network_route_xml(
        utdf_dict,
        str(network_route_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )

    intersection_flows = ET.parse(intersection_flow_file).getroot().findall("flow")
    intersection_pairs = {
        (flow.get("from"), flow.get("to"))
        for flow in intersection_flows
    }
    assert ("2_1", "1_3") in intersection_pairs
    assert ("1_3", "3_4") in intersection_pairs

    route_root = ET.parse(network_route_file).getroot()
    routes_by_id = {
        route.get("id"): route.get("edges")
        for route in route_root.findall("route")
    }
    network_flow = route_root.find("flow")
    assert network_flow is not None
    assert network_flow.get("number") == "100"
    assert network_flow.get("departLane") == "best"
    assert network_flow.get("departSpeed") == "max"
    assert network_flow.get("departPos") == "random_free"
    assert routes_by_id[network_flow.get("route")] == "2_1 1_3 3_4"


def test_network_route_flow_does_not_overload_internal_imbalance(tmp_path):
    """Network-level routes should not create vehicles at an internal imbalance."""
    utdf_dict = _build_network_flow_utdf_dict(second_intersection_volume="70")
    network_route_file = tmp_path / "network.rou.xml"

    generate_sumo_network_route_xml(
        utdf_dict,
        str(network_route_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )

    movement_volumes = _movement_volume_by_main_edge_pair(network_route_file)
    assert movement_volumes[("2_1", "1_3")] == 70
    assert movement_volumes[("1_3", "3_4")] == 70

    route_root = ET.parse(network_route_file).getroot()
    total_departing_vehicles = sum(
        int(flow.get("number"))
        for flow in route_root.findall("flow")
    )
    assert total_departing_vehicles == 70


def test_network_route_flow_does_not_start_on_internal_connector(tmp_path):
    """Network-level routes should enter from a boundary even when the first count is internal."""
    utdf_dict = _build_internal_endpoint_network_utdf_dict(
        first_volume="0",
        second_volume="100",
    )
    network_route_file = tmp_path / "network.rou.xml"

    generate_sumo_network_route_xml(
        utdf_dict,
        str(network_route_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )

    route_root = ET.parse(network_route_file).getroot()
    route = route_root.find("route")
    flow = route_root.find("flow")
    assert route is not None
    assert flow is not None
    assert route.get("edges") == "0_1 1_2 2_3"
    assert flow.get("number") == "100"


def test_network_route_flow_does_not_end_on_internal_connector(tmp_path):
    """Network-level routes should continue to a boundary after the last counted movement."""
    utdf_dict = _build_internal_endpoint_network_utdf_dict(
        first_volume="100",
        second_volume="0",
    )
    network_route_file = tmp_path / "network.rou.xml"

    generate_sumo_network_route_xml(
        utdf_dict,
        str(network_route_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )

    route_root = ET.parse(network_route_file).getroot()
    route = route_root.find("route")
    flow = route_root.find("flow")
    assert route is not None
    assert flow is not None
    assert route.get("edges") == "0_1 1_2 2_3"
    assert flow.get("number") == "100"


def test_network_route_flow_does_not_use_zero_count_signal_connector(tmp_path):
    """Signalized zero-count movements should not carry connector-only traffic."""
    utdf_dict = _build_internal_endpoint_network_utdf_dict(
        first_volume="0",
        second_volume="100",
    )
    utdf_dict["network_nodes"]["1"]["TYPE_DESC"] = "Signalized"
    network_route_file = tmp_path / "network.rou.xml"

    generate_sumo_network_route_xml(
        utdf_dict,
        str(network_route_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )

    route_root = ET.parse(network_route_file).getroot()
    assert route_root.findall("route") == []
    assert route_root.findall("flow") == []


def test_zero_lane_reverse_link_does_not_create_one_way_lane(tmp_path):
    """A zero-lane reverse placeholder should not become a SUMO one-lane edge."""
    utdf_dict = _build_one_way_utdf_dict()
    edge_file = tmp_path / "network.edg.xml"
    connection_file = tmp_path / "network.con.xml"

    link_lookup = generate_net_link_lookup_dict(utdf_dict)
    generate_sumo_edg_xml(utdf_dict, "feet, mph", str(edge_file))
    generate_sumo_connection_xml(utdf_dict, str(connection_file), "feet, mph")

    edge_ids = {
        edge.get("id")
        for edge in ET.parse(edge_file).getroot().findall("edge")
    }
    assert "2_1" in edge_ids
    assert "1_2" not in link_lookup
    assert "1_2" not in edge_ids

    connections = ET.parse(connection_file).getroot().findall("connection")
    assert all(
        connection.get("from") != "1_2" and connection.get("to") != "1_2"
        for connection in connections
    )


def test_zero_lane_shared_turn_with_count_stays_connected(tmp_path):
    """A shared turn with positive volume should use the through lane, not disappear."""
    utdf_dict = _build_one_way_utdf_dict()
    edge_file = tmp_path / "network.edg.xml"
    connection_file = tmp_path / "network.con.xml"
    flow_file = tmp_path / "network.flow.xml"

    generate_sumo_edg_xml(utdf_dict, "feet, mph", str(edge_file))
    generate_sumo_connection_xml(utdf_dict, str(connection_file), "feet, mph")
    generate_sumo_flow_xml(
        utdf_dict,
        str(flow_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )

    edge_by_id = {
        edge.get("id"): edge
        for edge in ET.parse(edge_file).getroot().findall("edge")
    }
    assert edge_by_id["2_1"].get("numLanes") == "2"

    connections = ET.parse(connection_file).getroot().findall("connection")
    right_turn_connections = [
        connection for connection in connections
        if connection.get("from") == "2_1"
        and connection.get("to") == "1_4"
        and connection.get("dir") == "r"
    ]
    assert len(right_turn_connections) == 1
    assert right_turn_connections[0].get("fromLane") == "0"

    right_turn_flow = next(
        flow for flow in ET.parse(flow_file).getroot().findall("flow")
        if flow.get("id") == "2_4"
    )
    assert right_turn_flow.get("from") == "2_1"
    assert right_turn_flow.get("to") == "1_4"
    assert right_turn_flow.get("number") == "15"
    assert right_turn_flow.get("departLane") == "best"


def test_lane_group_flow_is_used_when_volume_is_missing(tmp_path):
    """Lane Group Flow should be a fallback count source for SUMO flows."""
    utdf_dict = _build_one_way_utdf_dict()
    lane_df = utdf_dict["Lanes"].copy()
    lane_df.loc[
        (lane_df["INTID"] == "1") & (lane_df["RECORDNAME"] == "Volume"),
        ["NBT", "NBR"],
    ] = "0"
    lane_group_flow_row = _blank_lane_row("Lane Group Flow", "1")
    lane_group_flow_row.update({
        "NBT": "42",
        "NBR": "15",
    })
    utdf_dict["Lanes"] = pd.concat(
        [lane_df, pd.DataFrame([lane_group_flow_row])],
        ignore_index=True,
    )
    flow_file = tmp_path / "network.flow.xml"

    generate_sumo_flow_xml(
        utdf_dict,
        str(flow_file),
        begin=0,
        end=3600,
        net_unit="feet, mph",
    )

    flows_by_id = {
        flow.get("id"): flow
        for flow in ET.parse(flow_file).getroot().findall("flow")
    }
    assert flows_by_id["2_3"].get("number") == "42"
    assert flows_by_id["2_4"].get("number") == "15"


def test_connection_merges_source_lanes_evenly_to_receiving_lanes(tmp_path):
    """A wide source movement should not clamp all extra lanes to one target lane."""
    utdf_dict = _build_merge_distribution_utdf_dict()
    connection_file = tmp_path / "network.con.xml"

    generate_sumo_connection_xml(utdf_dict, str(connection_file), "feet, mph")

    through_connections = [
        connection for connection in ET.parse(connection_file).getroot().findall("connection")
        if connection.get("from") == "2_1"
        and connection.get("to") == "1_3"
        and connection.get("dir") == "s"
    ]
    target_lanes_by_source_lane = {
        connection.get("fromLane"): connection.get("toLane")
        for connection in through_connections
    }
    assert target_lanes_by_source_lane == {
        "0": "0",
        "1": "0",
        "2": "1",
        "3": "1",
        "4": "2",
    }


def test_connection_uses_utdf_turning_speed(tmp_path):
    """UTDF Turning Speed should become the SUMO connection speed."""
    utdf_dict = _build_turn_bay_utdf_dict()
    turning_speed_row = _blank_lane_row("Turning Speed", "1")
    turning_speed_row["NBR"] = "9"
    utdf_dict["Lanes"] = pd.concat(
        [utdf_dict["Lanes"], pd.DataFrame([turning_speed_row])],
        ignore_index=True,
    )
    connection_file = tmp_path / "network.con.xml"

    generate_sumo_connection_xml(utdf_dict, str(connection_file), "feet, mph")

    right_turn_connection = next(
        connection for connection in ET.parse(connection_file).getroot().findall("connection")
        if connection.get("from") == "2_1_bay"
        and connection.get("to") == "1_3"
        and connection.get("dir") == "r"
    )
    assert right_turn_connection.get("speed") == "4.02336"


def test_turn_bay_uses_utdf_storage_lane_count(tmp_path):
    """StLanes should control the number of lanes in the short turn bay."""
    utdf_dict = _build_turn_bay_utdf_dict()
    storage_lane_row = _blank_lane_row("StLanes", "1")
    storage_lane_row["NBR"] = "2"
    utdf_dict["Lanes"] = pd.concat(
        [utdf_dict["Lanes"], pd.DataFrame([storage_lane_row])],
        ignore_index=True,
    )
    edge_file = tmp_path / "network.edg.xml"
    connection_file = tmp_path / "network.con.xml"

    generate_sumo_edg_xml(utdf_dict, "feet, mph", str(edge_file))
    generate_sumo_connection_xml(utdf_dict, str(connection_file), "feet, mph")

    edge_by_id = {
        edge.get("id"): edge
        for edge in ET.parse(edge_file).getroot().findall("edge")
    }
    assert edge_by_id["2_1_bay"].get("numLanes") == "6"

    right_turn_connections = [
        connection for connection in ET.parse(connection_file).getroot().findall("connection")
        if connection.get("from") == "2_1_bay"
        and connection.get("to") == "1_3"
        and connection.get("dir") == "r"
    ]
    assert len(right_turn_connections) == 2


def test_turn_bay_keeps_lane_group_count_when_storage_is_smaller(tmp_path):
    """UTDF Lanes should remain the stop-line count when StLanes is smaller."""
    utdf_dict = _build_turn_bay_utdf_dict()
    lane_mask = utdf_dict["Lanes"]["RECORDNAME"] == "Lanes"
    utdf_dict["Lanes"].loc[lane_mask, "NBR"] = "2"
    storage_lane_row = _blank_lane_row("StLanes", "1")
    storage_lane_row["NBR"] = "1"
    utdf_dict["Lanes"] = pd.concat(
        [utdf_dict["Lanes"], pd.DataFrame([storage_lane_row])],
        ignore_index=True,
    )
    connection_file = tmp_path / "network.con.xml"

    generate_sumo_connection_xml(utdf_dict, str(connection_file), "feet, mph")

    right_turn_connections = [
        connection for connection in ET.parse(connection_file).getroot().findall("connection")
        if connection.get("from") == "2_1_bay"
        and connection.get("to") == "1_3"
        and connection.get("dir") == "r"
    ]
    assert len(right_turn_connections) == 2


def test_turn_bay_split_uses_clamped_coordinate_geometry(tmp_path):
    """Oversized storage lengths should not create near-zero split edges."""
    utdf_dict = _build_turn_bay_utdf_dict()
    utdf_dict["network_nodes"]["2"]["x_coord"] = -111.00025
    edge_file = tmp_path / "network.edg.xml"

    generate_sumo_edg_xml(utdf_dict, "feet, mph", str(edge_file))

    edge_by_id = {
        edge.get("id"): edge
        for edge in ET.parse(edge_file).getroot().findall("edge")
    }
    lane_lengths = [
        float(lane.get("length"))
        for lane in edge_by_id["2_1"].findall("lane")
    ]

    assert "2_1_bay" not in edge_by_id
    assert min(lane_lengths) >= 20


def test_signalized_approach_without_target_edge_is_not_guessed(tmp_path):
    """Signalized approaches need a representable UTDF movement before being written."""
    utdf_dict = _build_signal_approach_without_target_utdf_dict()
    edge_file = tmp_path / "network.edg.xml"

    generate_sumo_edg_xml(utdf_dict, "feet, mph", str(edge_file))

    edge_ids = {
        edge.get("id")
        for edge in ET.parse(edge_file).getroot().findall("edge")
    }
    assert "2_1" not in edge_ids


def test_link_curve_point_is_written_to_sumo_edge_shape(tmp_path):
    """When UTDF provides a curve point, the SUMO edge shape should use it."""
    utdf_dict = _build_curved_link_utdf_dict()
    edge_file = tmp_path / "network.edg.xml"

    generate_sumo_edg_xml(utdf_dict, "feet, mph", str(edge_file))

    edge = ET.parse(edge_file).getroot().find("edge")
    shape = edge.get("shape")
    assert shape is not None
    assert len(shape.split()) == 3


def test_bidirectional_link_shape_uses_both_utdf_curve_points(tmp_path):
    """Use both UTDF curve points so opposite directions share one centerline."""
    utdf_dict = _build_bidirectional_curved_link_utdf_dict()
    edge_file = tmp_path / "network.edg.xml"

    generate_sumo_edg_xml(utdf_dict, "feet, mph", str(edge_file))

    root = ET.parse(edge_file).getroot()
    forward_shape = _parse_sumo_shape(root.find("edge[@id='2_1']").get("shape"))
    reverse_shape = _parse_sumo_shape(root.find("edge[@id='1_2']").get("shape"))

    assert len(forward_shape) == 4
    assert len(reverse_shape) == 4
    assert forward_shape == list(reversed(reverse_shape))


def test_unrealistic_z_curve_falls_back_to_single_curve_point(tmp_path):
    """Do not write sharp Z-shaped SUMO links from incompatible curve points."""
    utdf_dict = _build_z_shaped_curve_utdf_dict()
    edge_file = tmp_path / "network.edg.xml"

    generate_sumo_edg_xml(utdf_dict, "feet, mph", str(edge_file))

    root = ET.parse(edge_file).getroot()
    forward_shape = _parse_sumo_shape(root.find("edge[@id='2_1']").get("shape"))
    reverse_shape = _parse_sumo_shape(root.find("edge[@id='1_2']").get("shape"))

    assert len(forward_shape) == 3
    assert len(reverse_shape) == 3
