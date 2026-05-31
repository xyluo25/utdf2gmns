"""Regression tests for SUMO signal mapping from UTDF phases."""

import pandas as pd

from utdf2gmns.func_lib.sumo.signal_mapping import create_SignalTimingPlan
from utdf2gmns.func_lib.sumo.signal_intersections import (
    parse_lane,
    parse_signal_control,
)
from utdf2gmns.func_lib.sumo.update_sumo_signal_from_utdf import (
    _build_inbound_direction_mapping_from_lanes,
    _build_movement_lookup_from_lanes,
    _build_signal_controller_mapping,
    _select_movement_name_for_sumo_connection,
)
from utdf2gmns.func_lib.utdf.cvt_utdf_lane_df_to_dict import cvt_lane_df_to_dict


def _blank_lane_row(record_name: str, intersection_id: str) -> dict[str, str]:
    """Create one UTDF Lanes row with the movement columns used in this test."""
    return {
        "RECORDNAME": record_name,
        "INTID": intersection_id,
        "NBL": "",
        "NBT": "",
        "NBR": "",
        "SBL": "",
        "SBT": "",
        "SBR": "",
        "EBL": "",
        "EBT": "",
        "EBR": "",
        "EBR2": "",
        "WBL": "",
        "WBT": "",
        "WBR": "",
    }


def _build_lane_mapping_dict() -> dict:
    """Build UTDF lane data with one zero-lane inbound and three active inbounds."""
    lane_rows = []
    values_by_record = {
        "Up Node": {
            "NBL": "5291",
            "NBT": "5291",
            "NBR": "5291",
            "SBL": "5277",
            "SBT": "5277",
            "SBR": "5277",
            "EBL": "102",
            "EBT": "102",
            "EBR": "102",
            "WBL": "303",
            "WBT": "303",
            "WBR": "303",
        },
        "Dest Node": {
            "NBL": "102",
            "NBT": "5277",
            "NBR": "303",
            "SBL": "303",
            "SBT": "5291",
            "SBR": "102",
            "EBL": "5277",
            "EBT": "303",
            "EBR": "5291",
            "WBL": "5291",
            "WBT": "102",
            "WBR": "5277",
        },
        "Lanes": {
            "NBL": "0",
            "NBT": "0",
            "NBR": "0",
            "SBL": "1",
            "SBT": "2",
            "SBR": "1",
            "EBL": "0",
            "EBT": "5",
            "EBR": "1",
            "WBL": "2",
            "WBT": "3",
            "WBR": "0",
        },
    }

    for record_name, movement_values in values_by_record.items():
        row = _blank_lane_row(record_name, "103")
        row.update(movement_values)
        lane_rows.append(row)

    return cvt_lane_df_to_dict(pd.DataFrame(lane_rows))


def test_signal_mapping_uses_utdf_up_nodes_for_turn_bay_edges():
    """Inbound signal directions should come from UTDF Up Node values first."""
    network_lanes = _build_lane_mapping_dict()
    inbound_edges = [
        "102_103_bay",
        "303_103",
        "5277_103_bay",
        "5291_103",
    ]

    mapping, lane_directions = _build_inbound_direction_mapping_from_lanes(
        network_lanes,
        "103",
        inbound_edges,
    )

    assert mapping == {
        "102_103_bay": "EB",
        "303_103": "WB",
        "5277_103_bay": "SB",
        "5291_103": "NB",
    }
    assert "NBT" in lane_directions
    assert "WBL" in lane_directions


def test_protected_left_signal_stays_green_with_no_phase_inbound():
    """A zero-lane/no-phase inbound should not make protected left timing fail."""
    utdf_signal = {
        "D1": {
            "MinGreen": "5",
            "MaxGreen": "30",
            "Yellow": "4",
            "AllRed": "2",
            "protected": ["WBL"],
        },
        "brp_info": {
            "1": {
                "1": ["D1"],
            },
        },
    }
    sumo_signal = {
        "0": {
            "dir": "l",
            "sumo_dir": "l",
            "fromEdge": "303_103",
            "synchro_dir": "WBL",
        },
        "1": {
            "dir": "s",
            "sumo_dir": "s",
            "fromEdge": "5291_103",
            "synchro_dir": "NBT",
        },
    }

    timing_plan = create_SignalTimingPlan(utdf_signal, sumo_signal)

    assert timing_plan
    assert any(phase["state"][0] == "G" for phase in timing_plan)


def test_signal_mapping_uses_dest_node_before_sumo_turn_dir():
    """Destination node should correct ambiguous SUMO turn directions."""
    network_lanes = _build_lane_mapping_dict()
    movement_lookup = _build_movement_lookup_from_lanes(network_lanes, "103")
    sumo_movement = {
        "fromEdge": "5291_103",
        "toEdge": "103_5277",
        "dir": "L",
    }

    movement_name = _select_movement_name_for_sumo_connection(
        movement_lookup,
        "103",
        sumo_movement,
        "NB",
    )

    assert movement_name == "NBT"


def test_uncontrolled_right_turn_gets_permissive_green():
    """UTDF phase value -1 means the movement is uncontrolled, not always red."""
    utdf_signal = {
        "D1": {
            "MinGreen": "5",
            "MaxGreen": "30",
            "Yellow": "4",
            "AllRed": "2",
            "protected": ["NBT"],
        },
        "brp_info": {
            "1": {
                "1": ["D1"],
            },
        },
    }
    sumo_signal = {
        "0": {
            "dir": "r",
            "sumo_dir": "r",
            "fromEdge": "2_1",
            "synchro_dir": "NBR",
            "uncontrolled": True,
        },
        "1": {
            "dir": "s",
            "sumo_dir": "s",
            "fromEdge": "2_1",
            "synchro_dir": "NBT",
        },
    }

    timing_plan = create_SignalTimingPlan(utdf_signal, sumo_signal)

    assert timing_plan
    assert all(
        phase["state"][0] == "g"
        for phase in timing_plan
        if phase.get("minDur") is not None
    )


def test_missing_right_turn_variant_inherits_same_turn_phase():
    """A no-phase R2 movement should inherit a usable same-bound right phase."""
    lane_rows = []
    values_by_record = {
        "Up Node": {
            "EBL": "539",
            "EBR": "539",
            "EBR2": "539",
        },
        "Dest Node": {
            "EBL": "49",
            "EBR": "519",
            "EBR2": "63",
        },
        "Lanes": {
            "EBL": "1",
            "EBR": "1",
            "EBR2": "0",
        },
        "Volume": {
            "EBL": "0",
            "EBR": "10",
            "EBR2": "2",
        },
        "Phase1": {
            "EBR": "6",
        },
        "PermPhase1": {
            "EBL": "6",
        },
    }
    for record_name, movement_values in values_by_record.items():
        row = _blank_lane_row(record_name, "517")
        row.update(movement_values)
        lane_rows.append(row)

    lane_info = parse_lane(pd.DataFrame(lane_rows), "517")

    assert "EBR2" in lane_info["phases"]["D6"]["permitted"]


def test_timeplans_node_rows_map_child_signal_to_controller():
    """UTDF Node 0..7 rows should assign child nodes to one controller."""
    timeplans = pd.DataFrame([
        {"INTID": "100", "RECORDNAME": "Control Type", "DATA": "3"},
        {"INTID": "100", "RECORDNAME": "Offset", "DATA": "12"},
        {"INTID": "100", "RECORDNAME": "Node 0", "DATA": "100"},
        {"INTID": "100", "RECORDNAME": "Node 1", "DATA": "200"},
        {"INTID": "100", "RECORDNAME": "Node 2", "DATA": "0"},
    ])

    controller_mapping = _build_signal_controller_mapping(
        timeplans,
        sumo_signal_ids={"100", "200", "300"},
    )

    assert controller_mapping == {
        "100": "100",
        "200": "100",
    }


def test_shared_controller_uses_controller_phase_and_local_lanes():
    """Child nodes should use controller timing with their own lane phases."""
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

    signal_control = parse_signal_control(
        pd.DataFrame(phase_rows),
        pd.DataFrame(lane_rows),
        int_id="100",
        lane_int_id="200",
    )

    assert signal_control["D1"]["MinGreen"] == "5"
    assert signal_control["D1"]["protected"] == ["NBT"]


def test_right_turn_on_red_gets_permissive_signal_state():
    """Allow RTOR should give a right turn permissive service outside its phase."""
    utdf_signal = {
        "D1": {
            "MinGreen": "5",
            "MaxGreen": "30",
            "Yellow": "4",
            "AllRed": "2",
            "protected": ["NBT"],
        },
        "brp_info": {
            "1": {
                "1": ["D1"],
            },
        },
    }
    sumo_signal = {
        "0": {
            "dir": "r",
            "sumo_dir": "r",
            "fromEdge": "2_1",
            "synchro_dir": "NBR",
            "rtor_allowed": True,
        },
        "1": {
            "dir": "s",
            "sumo_dir": "s",
            "fromEdge": "2_1",
            "synchro_dir": "NBT",
        },
    }

    timing_plan = create_SignalTimingPlan(utdf_signal, sumo_signal)

    assert timing_plan
    assert any(phase["state"][0] == "g" for phase in timing_plan)


def test_static_signal_sequence_uses_utdf_start_end_overlap():
    """Static NEMA timing should skip phase pairs that never overlap in UTDF."""
    utdf_signal = {
        "D3": {
            "MinGreen": "5",
            "MaxGreen": "25",
            "Yellow": "3",
            "AllRed": "1",
            "Start": "62",
            "End": "89",
            "protected": ["NBL"],
        },
        "D4": {
            "MinGreen": "5",
            "MaxGreen": "35",
            "Yellow": "4.5",
            "AllRed": "1.5",
            "Start": "21",
            "End": "62",
            "protected": ["SBT"],
        },
        "D7": {
            "MinGreen": "5",
            "MaxGreen": "6",
            "Yellow": "3",
            "AllRed": "1",
            "Start": "21",
            "End": "31",
            "protected": ["SBL"],
        },
        "D8": {
            "MinGreen": "5",
            "MaxGreen": "52",
            "Yellow": "4.5",
            "AllRed": "1.5",
            "Start": "31",
            "End": "89",
            "protected": ["NBT"],
        },
        "brp_info": {
            "1": {
                "1": ["D4", "D3"],
                "2": ["D7", "D8"],
            },
        },
    }
    sumo_signal = {
        "0": {
            "dir": "s",
            "sumo_dir": "s",
            "fromEdge": "7_10",
            "synchro_dir": "SBT",
            "signal_dir": "SBT",
        },
    }

    timing_plan = create_SignalTimingPlan(
        utdf_signal,
        sumo_signal,
        cycle_length=110,
    )
    green_phase_names = {
        phase["name"]
        for phase in timing_plan
        if phase.get("minDur") is not None
    }

    assert "(D4,D8)" in green_phase_names
    assert "(D3,D7)" not in green_phase_names


def test_utdf_actuated_control_uses_static_sumo_program(tmp_path):
    """UTDF actuated plans should not become SUMO min-green-only programs."""
    from utdf2gmns.func_lib.sumo.read_sumo import ReadSUMO

    net_file = tmp_path / "tiny.net.xml"
    net_file.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<net>
    <tlLogic id="1" type="static" programID="0" offset="0">
        <phase duration="1" state="r"/>
    </tlLogic>
</net>
""",
        encoding="utf-8",
    )
    sumo_net = ReadSUMO(str(net_file))
    timing_plan = [{
        "name": "D2",
        "minDur": 5.0,
        "maxDur": 30.0,
        "next": 0,
        "state": "G",
    }]

    sumo_net.replace_tl_logic_xml("1", timing_plan, {}, "static", 0)
    sumo_net.write_xml()

    output_text = net_file.read_text(encoding="utf-8")
    assert 'type="static"' in output_text
    assert 'duration="30.0"' in output_text
