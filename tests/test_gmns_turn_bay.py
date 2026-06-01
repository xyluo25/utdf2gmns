"""Regression tests for GMNS turn-bay export consistency."""

import json

import pandas as pd
from shapely import wkt

from utdf2gmns import UTDF2GMNS
from utdf2gmns.func_lib.gmns.generate_lane_movement import (
    generate_gmns_lane,
    generate_gmns_link,
    generate_gmns_movement,
    generate_gmns_node,
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


def test_gmns_export_uses_sumo_turn_bay_topology(tmp_path):
    """GMNS node/link/lane/movement files should match SUMO turn-bay splits."""
    utdf_dict = _build_turn_bay_utdf_dict()
    node_file = tmp_path / "node.csv"
    link_file = tmp_path / "link.csv"
    lane_file = tmp_path / "lane.csv"
    movement_file = tmp_path / "movement.csv"

    generate_gmns_node(utdf_dict, str(node_file), net_unit="feet, mph")
    generate_gmns_link(utdf_dict, str(link_file), net_unit="feet, mph")
    generate_gmns_lane(utdf_dict, str(lane_file), net_unit="feet, mph")
    generate_gmns_movement(utdf_dict, str(movement_file), net_unit="feet, mph")

    nodes = pd.read_csv(node_file, dtype={"node_id": "string", "INTID": "string"})
    node_ids = set(nodes["node_id"].astype(str))
    assert "2_1_bay_node" in node_ids
    assert nodes["node_id"].equals(nodes["INTID"])

    links = pd.read_csv(link_file).set_index("link_id")
    assert set(links["from_node_id"].astype(str)).issubset(node_ids)
    assert set(links["to_node_id"].astype(str)).issubset(node_ids)
    assert links.index.astype(str).is_unique
    assert links.loc["2_1", "to_node_id"] == "2_1_bay_node"
    assert links.loc["2_1", "lanes"] == 3
    assert links.loc["2_1_bay", "from_node_id"] == "2_1_bay_node"
    assert links.loc["2_1_bay", "lanes"] == 5

    lanes = pd.read_csv(lane_file).set_index("lane_id")
    assert lanes.index.astype(str).is_unique
    assert set(lanes["link_id"].astype(str)).issubset(set(links.index.astype(str)))
    assert len(lanes[lanes["link_id"] == "2_1"]) == 3
    assert len(lanes[lanes["link_id"] == "2_1_bay"]) == 5
    assert lanes.loc["2_1_bay_0", "type"] == "right"
    assert lanes.loc["2_1_bay_0", "movement_name"] == "NBR"
    assert links.loc["2_1_bay", "geometry"].startswith("POLYGON")
    assert lanes.loc["2_1_bay_0", "geometry"].startswith("POLYGON")
    assert lanes.loc["2_1_bay_0", "geometry"] != lanes.loc["2_1_bay_4", "geometry"]
    right_lane_polygon = wkt.loads(lanes.loc["2_1_bay_0", "geometry"])
    adjacent_lane_polygon = wkt.loads(lanes.loc["2_1_bay_1", "geometry"])
    assert right_lane_polygon.is_valid
    assert adjacent_lane_polygon.is_valid
    assert right_lane_polygon.area > 0
    assert adjacent_lane_polygon.area > 0
    assert right_lane_polygon.intersection(adjacent_lane_polygon).area < 1e-12

    movements = pd.read_csv(movement_file)
    source_connector = movements[
        (movements["movement_name"] == "TURN_BAY_CONNECTOR")
        & (movements["ib_link_id"] == "2_1")
    ].iloc[0]
    assert set(movements["node_id"].astype(str)).issubset(node_ids)
    assert set(movements["ib_link_id"].astype(str)).issubset(set(links.index.astype(str)))
    assert set(movements["ob_link_id"].astype(str)).issubset(set(links.index.astype(str)))
    assert source_connector["node_id"] == "2_1_bay_node"
    assert source_connector["control"] == "free"

    right_turn = movements[movements["movement_name"] == "NBR"].iloc[0]
    assert right_turn["ib_link_id"] == "2_1_bay"
    assert right_turn["ob_link_id"] == "1_3"
    assert right_turn["ob_lane_indices"] == "0"


def test_gmns_signal_control_uses_shared_controller_local_lanes(tmp_path):
    """GMNS signal.json source should match SUMO shared-controller mapping."""
    phase_rows = [
        {"RECORDNAME": "BRP", "INTID": "100", "D1": "11"},
        {"RECORDNAME": "MinGreen", "INTID": "100", "D1": "5"},
        {"RECORDNAME": "MaxGreen", "INTID": "100", "D1": "30"},
        {"RECORDNAME": "Yellow", "INTID": "100", "D1": "4"},
        {"RECORDNAME": "AllRed", "INTID": "100", "D1": "2"},
    ]
    lane_rows = []
    for record_name, movement_values in {
        "Up Node": {"NBT": "1"},
        "Dest Node": {"NBT": "3"},
        "Lanes": {"NBT": "1"},
        "Phase1": {"NBT": "1.0"},
    }.items():
        row = _blank_lane_row(record_name, "200")
        row.update(movement_values)
        lane_rows.append(row)

    net = UTDF2GMNS.__new__(UTDF2GMNS)
    net._utdf_dict = {
        "Phases": pd.DataFrame(phase_rows),
        "Lanes": pd.DataFrame(lane_rows),
        "Timeplans": pd.DataFrame([
            {"INTID": "100", "RECORDNAME": "Node 0", "DATA": "100"},
            {"INTID": "100", "RECORDNAME": "Node 1", "DATA": "200"},
        ]),
    }

    assert net.create_signal_control()
    assert net.network_signal_control["200"]["D1"]["MinGreen"] == "5"
    assert net.network_signal_control["200"]["D1"]["protected"] == ["NBT"]

    signal_file = tmp_path / "signal.json"
    with open(signal_file, "w", encoding="utf-8") as file:
        json.dump(net.network_signal_control, file)

    with open(signal_file, encoding="utf-8") as file:
        signal_control = json.load(file)
    assert all(isinstance(node_id, str) for node_id in signal_control)
