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
import math
from collections import deque
from datetime import datetime
from typing import Any

from utdf2gmns.func_lib.gmns.geocoding_Links import cvt_lonlat_to_utm, cvt_utm_to_lonlat
from utdf2gmns.func_lib.gmns.geocoding_Nodes import calculate_new_coordinates_from_offsets
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


TURN_TYPE_ORDER = ("R", "T", "L", "U")
TURN_TYPE_TO_SUMO_DIR = {
    "R": "r",
    "T": "s",
    "L": "l",
    "U": "t",
}
TURN_BAY_TYPES = {"R", "L", "U"}
BLANK_TEXT_VALUES = {"", "nan", "none", "null"}
MIN_TURN_BAY_SPLIT_EDGE_LENGTH_M = 30.0
MAX_REALISTIC_CURVE_TURN_DEGREES = 80.0
MAX_REALISTIC_Z_CURVE_TOTAL_DEGREES = 90.0
MAX_REALISTIC_SHAPE_LENGTH_RATIO = 1.35


def _is_blank(value: Any) -> bool:
    """Return True when a UTDF cell does not contain useful data."""
    if value is None:
        return True
    return str(value).strip().lower() in BLANK_TEXT_VALUES


def _normalize_node_id(value: Any) -> str:
    """Return a stable node id string from a UTDF cell value."""
    if _is_blank(value):
        return ""

    node_id = str(value).strip()
    try:
        numeric_node_id = float(node_id)
    except ValueError:
        return node_id

    if numeric_node_id.is_integer():
        return str(int(numeric_node_id))
    return node_id


def _extract_number(value: Any) -> float | None:
    """Extract the first number from a UTDF cell."""
    if _is_blank(value):
        return None

    number_matches = re.findall(r"-?\d+(?:\.\d+)?", str(value))
    if not number_matches:
        return None
    return float(number_matches[0])


def _extract_int(value: Any, default: int = 0) -> int:
    """Extract the first integer-like value from a UTDF cell."""
    number_value = _extract_number(value)
    if number_value is None:
        return default
    return int(number_value)


def _get_unit_labels(net_unit: str | None) -> tuple[str, str]:
    """Return distance and speed labels used by the current UTDF network."""
    if net_unit and "feet" in net_unit:
        return "feet", "mph"
    if net_unit and "meters" in net_unit:
        return "meters", "km/h"
    return "feet", "mph"


def _convert_distance_to_meters(value: Any, net_unit: str | None) -> float | None:
    """Convert a UTDF distance value into meters."""
    distance_value = _extract_number(value)
    if distance_value is None:
        return None

    unit_distance, _ = _get_unit_labels(net_unit)
    if unit_distance == "feet":
        return cvt_feet_to_meters(distance_value)
    return distance_value


def _convert_speed_to_mps(value: Any, net_unit: str | None) -> float | None:
    """Convert a UTDF speed value into meters per second."""
    speed_value = _extract_number(value)
    if speed_value is None:
        return None

    _, unit_speed = _get_unit_labels(net_unit)
    if unit_speed == "mph":
        return cvt_mph_to_mps(speed_value)
    return cvt_kmh_to_mps(speed_value)


def _get_movement_flow_volume(movement_info: dict) -> float | None:
    """Return the best UTDF turning count available for one lane group.

    ``Volume`` is the preferred source in the UTDF metadata. Some files store
    the same count-like demand in ``Lane Group Flow`` instead, so it is used as
    a fallback only when ``Volume`` is blank or non-positive.
    """
    for volume_field in ("Volume", "Lane Group Flow", "Lane_Group_Flow"):
        volume = _extract_number(movement_info.get(volume_field))
        if volume is not None and volume > 0:
            return volume
    return None


def _format_xml_number(value: float | int | None) -> str | None:
    """Format a number for XML while keeping the text compact."""
    if value is None:
        return None
    return f"{float(value):.6f}".rstrip("0").rstrip(".")


def _movement_turn_type(movement_name: str) -> str | None:
    """Return the movement type from a Synchro movement name such as NBL or EBR2."""
    movement_suffix = movement_name[2:]
    for turn_type in TURN_TYPE_ORDER:
        if turn_type in movement_suffix:
            return turn_type
    return None


def _get_turn_bay_length_meters(movement_info: dict, net_unit: str | None) -> float:
    """Return the lane-add/drop section length for a protected turn lane."""
    storage_length = _convert_distance_to_meters(movement_info.get("Storage"), net_unit) or 0.0
    taper_length = _convert_distance_to_meters(movement_info.get("Taper"), net_unit) or 0.0
    return storage_length + taper_length


def _get_turn_bay_lane_count(movement_info: dict, default_lane_count: int) -> int:
    """Return the UTDF storage-bay lane count when it is explicitly provided."""
    storage_lane_count = _extract_int(movement_info.get("StLanes"), default=0)
    if storage_lane_count > 0:
        return storage_lane_count
    return default_lane_count


def _extract_link_lane_count(link_info: dict) -> int:
    """Return the non-negative lane count from a normalized or raw Links record."""
    lane_value = link_info.get("num_lanes")
    if lane_value is None:
        lane_value = link_info.get("Lanes")
    return max(_extract_int(lane_value, default=0), 0)


def _movement_has_lane_or_demand(movement_info: dict) -> bool:
    """Return True when a lane-group record proves that an approach is real.

    UTDF exports can include an ``Up ID`` in ``Links`` for a geometric reverse
    direction even when there are no real lanes in that direction. A movement
    with lanes, positive demand, or lane-group flow is treated as evidence that
    the approach should remain in the SUMO network. Detector-only records are
    not enough because Synchro can export detectors for zero-lane, zero-count
    placeholders; turning those into connections gives SUMO signal links with
    no valid green.
    """
    if _extract_int(movement_info.get("Lanes"), default=0) > 0:
        return True
    for demand_field in ("Volume", "Lane Group Flow", "Lane_Group_Flow"):
        demand_value = _extract_number(movement_info.get(demand_field))
        if demand_value is not None and demand_value > 0:
            return True
    return False


def _collect_active_lane_approach_ids(utdf_dict: dict) -> set[str]:
    """Return edge ids that have real lane-group evidence in the UTDF Lanes table."""
    lanes_df = utdf_dict.get("Lanes")
    if lanes_df is None:
        return set()

    active_approach_ids: set[str] = set()
    network_lanes = cvt_lane_df_to_dict(lanes_df)
    for intersection_id, movement_lanes in network_lanes.items():
        intersection_node = _normalize_node_id(intersection_id)
        for movement_name, movement_info in movement_lanes.items():
            if _movement_turn_type(movement_name) is None:
                continue
            if not _movement_has_lane_or_demand(movement_info):
                continue

            up_node = _normalize_node_id(movement_info.get("Up Node"))
            if up_node:
                active_approach_ids.add(f"{up_node}_{intersection_node}")
    return active_approach_ids


def _collect_signalized_node_ids_from_timeplans(timeplans_df) -> set[str]:
    """Return all signalized node ids, including shared-controller child nodes."""
    if timeplans_df is None or "INTID" not in timeplans_df:
        return set()

    signalized_node_ids = {
        _normalize_node_id(intersection_id)
        for intersection_id in timeplans_df["INTID"].unique()
        if _normalize_node_id(intersection_id)
    }
    if "RECORDNAME" not in timeplans_df or "DATA" not in timeplans_df:
        return signalized_node_ids

    node_rows = timeplans_df[
        timeplans_df["RECORDNAME"].astype(str).str.strip().str.lower().str.startswith("node")
    ]
    for node_id in node_rows["DATA"]:
        normalized_node_id = _normalize_node_id(node_id)
        if normalized_node_id and normalized_node_id != "0":
            signalized_node_ids.add(normalized_node_id)

    return signalized_node_ids


def _create_empty_edge_profile(edge_id: str, link_info: dict, net_unit: str | None) -> dict:
    """Create the default SUMO approach profile for one directed UTDF link."""
    try:
        from_node, to_node = edge_id.split("_", 1)
    except ValueError:
        from_node = edge_id
        to_node = ""

    link_lane_count = _extract_link_lane_count(link_info)
    return {
        "edge_id": edge_id,
        "main_edge_id": edge_id,
        "stop_edge_id": edge_id,
        "bay_node_id": "",
        "from_node": from_node,
        "to_node": to_node,
        "link_lane_count": max(link_lane_count, 0),
        "length_m": _convert_distance_to_meters(link_info.get("length"), net_unit),
        "speed_mps": _convert_speed_to_mps(link_info.get("speed"), net_unit),
        "curve_pt_x": link_info.get("curve_pt_x"),
        "curve_pt_y": link_info.get("curve_pt_y"),
        "reverse_curve_pt_x": None,
        "reverse_curve_pt_y": None,
        "movements": [],
        "movements_by_type": {turn_type: [] for turn_type in TURN_TYPE_ORDER},
        "turn_lane_counts": {turn_type: 0 for turn_type in TURN_TYPE_ORDER},
        "turn_bay_lane_counts": {turn_type: 0 for turn_type in TURN_TYPE_ORDER},
        "turn_bay_length_m": 0.0,
        "has_turn_bay": False,
        "main_lane_count": 1,
        "stop_lane_count": 1,
        "stop_lane_slots": [],
        "through_stop_lane_indices": [],
        "through_main_lane_indices": [],
    }


def _rebuild_edge_profile_movement_summaries(profile: dict) -> None:
    """Recalculate movement groups and lane totals after filtering movements."""
    profile["movements_by_type"] = {turn_type: [] for turn_type in TURN_TYPE_ORDER}
    profile["turn_lane_counts"] = {turn_type: 0 for turn_type in TURN_TYPE_ORDER}
    profile["turn_bay_lane_counts"] = {turn_type: 0 for turn_type in TURN_TYPE_ORDER}
    profile["turn_bay_length_m"] = 0.0

    for movement in profile["movements"]:
        turn_type = movement["turn_type"]
        lane_count = movement["lane_count"]
        profile["movements_by_type"][turn_type].append(movement)
        profile["turn_lane_counts"][turn_type] += lane_count
        if movement["is_turn_bay"]:
            profile["turn_bay_lane_counts"][turn_type] += movement.get(
                "turn_bay_lane_count",
                lane_count,
            )
            profile["turn_bay_length_m"] = max(
                profile["turn_bay_length_m"],
                movement["turn_bay_length_m"],
            )


def _finalize_edge_profile(profile: dict) -> None:
    """Calculate lane counts and lane index maps for one SUMO approach profile."""
    positive_movement_lane_count = sum(profile["turn_lane_counts"].values())
    link_lane_count = profile["link_lane_count"]
    stop_lane_count = max(link_lane_count, positive_movement_lane_count, 1)

    turn_bay_lane_count = sum(profile["turn_bay_lane_counts"].values())
    through_lane_count = profile["turn_lane_counts"]["T"]
    main_lane_count = max(stop_lane_count - turn_bay_lane_count, through_lane_count, 1)
    stop_lane_count = max(stop_lane_count, main_lane_count + turn_bay_lane_count)

    profile["main_lane_count"] = main_lane_count
    profile["stop_lane_count"] = stop_lane_count
    profile["has_turn_bay"] = bool(
        turn_bay_lane_count > 0
        and profile["turn_bay_length_m"] > 0
        and main_lane_count < stop_lane_count
    )

    if profile["has_turn_bay"]:
        profile["stop_edge_id"] = f"{profile['edge_id']}_bay"
        profile["bay_node_id"] = f"{profile['edge_id']}_bay_node"

    for movement in profile["movements"]:
        movement["stop_lane_indices"] = []

    lane_slots = []
    for turn_type in TURN_TYPE_ORDER:
        for movement in profile["movements_by_type"][turn_type]:
            added_turn_bay_lane_count = 0
            if movement["is_turn_bay"]:
                added_turn_bay_lane_count = min(
                    movement.get("turn_bay_lane_count", movement["lane_count"]),
                    movement["lane_count"],
                )
            for lane_number in range(movement["lane_count"]):
                is_added_turn_bay_lane = False
                if movement["is_turn_bay"]:
                    if turn_type == "R":
                        is_added_turn_bay_lane = lane_number < added_turn_bay_lane_count
                    else:
                        is_added_turn_bay_lane = (
                            lane_number
                            >= movement["lane_count"] - added_turn_bay_lane_count
                        )

                stop_lane_index = len(lane_slots)
                movement["stop_lane_indices"].append(stop_lane_index)
                lane_slots.append({
                    "index": stop_lane_index,
                    "turn_type": turn_type,
                    "movement": movement,
                    "is_turn_bay": movement["is_turn_bay"],
                    "is_added_turn_bay_lane": is_added_turn_bay_lane,
                    "lane_number": lane_number,
                })

    while len(lane_slots) < stop_lane_count:
        lane_slots.append({
            "index": len(lane_slots),
            "turn_type": "T",
            "movement": None,
            "is_turn_bay": False,
            "is_added_turn_bay_lane": False,
            "lane_number": 0,
        })

    if len(lane_slots) > stop_lane_count:
        profile["stop_lane_count"] = len(lane_slots)

    added_turn_bay_lane_indices = [
        lane_slot["index"] for lane_slot in lane_slots
        if lane_slot["is_added_turn_bay_lane"]
    ]
    for lane_slot in lane_slots:
        if lane_slot["is_added_turn_bay_lane"]:
            if lane_slot["turn_type"] == "R":
                main_lane_index = 0
            else:
                main_lane_index = main_lane_count - 1
        else:
            added_lanes_to_the_right = sum(
                1 for lane_index in added_turn_bay_lane_indices
                if lane_index < lane_slot["index"]
            )
            main_lane_index = lane_slot["index"] - added_lanes_to_the_right

        lane_slot["main_lane_index"] = min(max(main_lane_index, 0), main_lane_count - 1)

    through_stop_lane_indices = [
        lane_slot["index"] for lane_slot in lane_slots
        if lane_slot["turn_type"] == "T"
    ]
    through_main_lane_indices = sorted({
        lane_slot["main_lane_index"] for lane_slot in lane_slots
        if lane_slot["turn_type"] == "T"
    })

    profile["stop_lane_slots"] = lane_slots
    profile["through_stop_lane_indices"] = through_stop_lane_indices or [0]
    profile["through_main_lane_indices"] = through_main_lane_indices or list(range(main_lane_count))


def _disable_turn_bay_split(profile: dict) -> None:
    """Keep stop-line lanes on the full edge when a separate bay edge is unsafe."""
    profile["has_turn_bay"] = False
    profile["stop_edge_id"] = profile["edge_id"]
    profile["bay_node_id"] = ""
    profile["main_lane_count"] = profile["stop_lane_count"]

    for lane_slot in profile["stop_lane_slots"]:
        lane_slot["main_lane_index"] = lane_slot["index"]

    profile["through_main_lane_indices"] = profile["through_stop_lane_indices"] or list(
        range(profile["main_lane_count"])
    )


def _profile_has_enough_turn_bay_geometry(profile: dict, network_nodes: dict | None,
                                          net_unit: str | None) -> bool:
    """Return True when a turn-bay split can create two usable SUMO edges."""
    if network_nodes is None:
        return True

    shape_length = _shape_length_meters(
        _get_profile_shape_points(profile, network_nodes, net_unit),
    )
    if shape_length is None:
        return True

    bay_length = min(profile["turn_bay_length_m"], shape_length)
    upstream_length = shape_length - bay_length
    return (
        bay_length >= MIN_TURN_BAY_SPLIT_EDGE_LENGTH_M
        and upstream_length >= MIN_TURN_BAY_SPLIT_EDGE_LENGTH_M
    )


def _build_sumo_edge_profile_dict(utdf_dict: dict, net_unit: str | None) -> dict:
    """Build lane profiles shared by SUMO node, edge, connection, flow, and detector writers."""
    link_lookup_dict = generate_net_link_lookup_dict(utdf_dict)
    edge_profiles = {
        edge_id: _create_empty_edge_profile(edge_id, link_info, net_unit)
        for edge_id, link_info in link_lookup_dict.items()
    }
    target_edge_ids: set[str] = set()

    lanes_df = utdf_dict.get("Lanes")
    if lanes_df is not None:
        network_lanes = cvt_lane_df_to_dict(lanes_df)
        for intersection_id, movement_lanes in network_lanes.items():
            intersection_node = _normalize_node_id(intersection_id)
            for movement_name, movement_info in movement_lanes.items():
                turn_type = _movement_turn_type(movement_name)
                if turn_type is None:
                    continue

                up_node = _normalize_node_id(movement_info.get("Up Node"))
                dest_node = _normalize_node_id(movement_info.get("Dest Node"))
                if not up_node:
                    continue

                if not _movement_has_lane_or_demand(movement_info):
                    continue

                base_lane_count = max(_extract_int(movement_info.get("Lanes"), default=0), 0)
                turn_bay_length_m = _get_turn_bay_length_meters(movement_info, net_unit)

                # UTDF ``Lanes`` is the full stop-line lane group count.
                # ``StLanes`` only tells how many of those lanes are added as
                # storage near the stop line, so it must not replace the lane
                # group count.
                lane_count = base_lane_count
                turn_bay_lane_count = 0
                if turn_type in TURN_BAY_TYPES and turn_bay_length_m > 0:
                    storage_lane_count = _get_turn_bay_lane_count(
                        movement_info,
                        base_lane_count,
                    )
                    lane_count = max(base_lane_count, storage_lane_count)
                    turn_bay_lane_count = min(storage_lane_count, lane_count)
                is_turn_bay = (
                    turn_type in TURN_BAY_TYPES
                    and lane_count > 0
                    and turn_bay_lane_count > 0
                    and turn_bay_length_m > 0
                )

                edge_id = f"{up_node}_{intersection_node}"
                profile = edge_profiles.setdefault(
                    edge_id,
                    _create_empty_edge_profile(edge_id, {}, net_unit),
                )
                movement = {
                    "movement_name": movement_name,
                    "turn_type": turn_type,
                    "up_node": up_node,
                    "intersection_node": intersection_node,
                    "dest_node": dest_node,
                    "lane_count": lane_count,
                    "volume": _get_movement_flow_volume(movement_info),
                    "num_detects": movement_info.get("numDetects"),
                    "speed_mps": _convert_speed_to_mps(movement_info.get("Speed"), net_unit),
                    "turning_speed_mps": _convert_speed_to_mps(
                        movement_info.get("Turning Speed"),
                        net_unit,
                    ),
                    "right_channeled": movement_info.get("Right Channeled"),
                    "allow_rtor": movement_info.get("Allow RTOR"),
                    "turn_bay_length_m": turn_bay_length_m,
                    "turn_bay_lane_count": turn_bay_lane_count,
                    "is_turn_bay": is_turn_bay,
                    "stop_lane_indices": [],
                }

                profile["movements"].append(movement)
                profile["movements_by_type"][turn_type].append(movement)
                if dest_node:
                    target_edge_ids.add(f"{intersection_node}_{dest_node}")
                profile["turn_lane_counts"][turn_type] += lane_count
                if is_turn_bay:
                    profile["turn_bay_lane_counts"][turn_type] += turn_bay_lane_count
                    profile["turn_bay_length_m"] = max(
                        profile["turn_bay_length_m"],
                        turn_bay_length_m,
                    )

    signalized_node_ids = _collect_signalized_node_ids_from_timeplans(
        utdf_dict.get("Timeplans"),
    )

    target_edge_ids = set()
    for profile in edge_profiles.values():
        valid_movements = []
        for movement in profile["movements"]:
            target_edge_id = f"{movement['intersection_node']}_{movement['dest_node']}"
            if movement["dest_node"] and target_edge_id in edge_profiles:
                valid_movements.append(movement)
                target_edge_ids.add(target_edge_id)
            elif profile["to_node"] not in signalized_node_ids:
                valid_movements.append(movement)
        if len(valid_movements) != len(profile["movements"]):
            profile["movements"] = valid_movements
            _rebuild_edge_profile_movement_summaries(profile)

    # A positive Links lane count without any active lane-group movement is not
    # enough to define signalized stop-line behavior. Keeping those approaches
    # lets netconvert invent turn links and signal states that do not exist in
    # UTDF. Receiving-only edges are kept only away from signalized stop lines,
    # where they can represent downstream exits rather than internal sinks.
    for edge_id, profile in list(edge_profiles.items()):
        if profile["movements"]:
            continue
        if profile["to_node"] in signalized_node_ids:
            del edge_profiles[edge_id]
            continue
        if edge_id in target_edge_ids:
            continue

    for profile in edge_profiles.values():
        reverse_edge_id = f"{profile['to_node']}_{profile['from_node']}"
        reverse_profile = edge_profiles.get(reverse_edge_id)
        if reverse_profile is None:
            continue
        profile["reverse_curve_pt_x"] = reverse_profile.get("curve_pt_x")
        profile["reverse_curve_pt_y"] = reverse_profile.get("curve_pt_y")

    for profile in edge_profiles.values():
        _finalize_edge_profile(profile)
        if profile["has_turn_bay"] and not _profile_has_enough_turn_bay_geometry(
                profile,
                utdf_dict.get("network_nodes"),
                net_unit):
            _disable_turn_bay_split(profile)

    return edge_profiles


def _get_network_node(network_nodes: dict, node_id: str) -> dict | None:
    """Find a node record regardless of whether its key is stored as text or a number."""
    if node_id in network_nodes:
        return network_nodes[node_id]
    try:
        numeric_node_id = int(node_id)
    except ValueError:
        return None
    return network_nodes.get(numeric_node_id)


def _format_shape_points(shape_points: list[tuple[float, float]] | None) -> str | None:
    """Return a SUMO shape string from longitude/latitude points."""
    if not shape_points:
        return None
    return " ".join(f"{lon:.12f},{lat:.12f}" for lon, lat in shape_points)


def _append_distinct_shape_point(shape_points: list[tuple[float, float]],
                                 point: tuple[float, float] | None) -> None:
    """Append a shape point unless it duplicates the previous coordinate."""
    if point is None:
        return
    if shape_points and (
        abs(shape_points[-1][0] - point[0]) < 1e-10
        and abs(shape_points[-1][1] - point[1]) < 1e-10
    ):
        return
    shape_points.append(point)


def _dedupe_shape_points(shape_points: list[tuple[float, float]]
                         ) -> list[tuple[float, float]]:
    """Return shape points without consecutive duplicate coordinates."""
    cleaned_shape_points: list[tuple[float, float]] = []
    for shape_point in shape_points:
        _append_distinct_shape_point(cleaned_shape_points, shape_point)
    return cleaned_shape_points


def _project_shape_points_only(shape_points: list[tuple[float, float]]
                               ) -> list[tuple[float, float]]:
    """Project a longitude/latitude shape into UTM points for geometry checks."""
    projected_data = _shape_points_to_utm(shape_points)
    if projected_data is None:
        return []
    projected_points, _, _ = projected_data
    return projected_points


def _shape_direct_length_meters(shape_points: list[tuple[float, float]]) -> float | None:
    """Return the straight-line length between a shape's endpoints."""
    projected_points = _project_shape_points_only(shape_points)
    if len(projected_points) < 2:
        return None

    start_x, start_y = projected_points[0]
    end_x, end_y = projected_points[-1]
    return ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5


def _shape_signed_turn_angles(shape_points: list[tuple[float, float]]) -> list[float]:
    """Return signed turn angles between consecutive projected shape segments."""
    projected_points = _project_shape_points_only(shape_points)
    signed_turn_angles: list[float] = []
    for previous_point, current_point, next_point in zip(
            projected_points,
            projected_points[1:],
            projected_points[2:]):
        previous_vector = (
            current_point[0] - previous_point[0],
            current_point[1] - previous_point[1],
        )
        next_vector = (
            next_point[0] - current_point[0],
            next_point[1] - current_point[1],
        )
        previous_length = (previous_vector[0] ** 2 + previous_vector[1] ** 2) ** 0.5
        next_length = (next_vector[0] ** 2 + next_vector[1] ** 2) ** 0.5
        if previous_length <= 0 or next_length <= 0:
            continue

        dot_product = (
            previous_vector[0] * next_vector[0]
            + previous_vector[1] * next_vector[1]
        ) / (previous_length * next_length)
        dot_product = min(max(dot_product, -1.0), 1.0)
        turn_angle = math.degrees(math.acos(dot_product))
        cross_product = (
            previous_vector[0] * next_vector[1]
            - previous_vector[1] * next_vector[0]
        )
        signed_turn_angles.append(turn_angle if cross_product >= 0 else -turn_angle)
    return signed_turn_angles


def _shape_has_unrealistic_curve(shape_points: list[tuple[float, float]],
                                 declared_length_m: float | None) -> bool:
    """Return True when a UTDF curve would create a sharp or Z-shaped link."""
    if len(shape_points) <= 2:
        return False

    signed_turn_angles = _shape_signed_turn_angles(shape_points)
    if not signed_turn_angles:
        return False

    max_turn_angle = max(abs(turn_angle) for turn_angle in signed_turn_angles)
    if max_turn_angle >= MAX_REALISTIC_CURVE_TURN_DEGREES:
        return True

    has_opposite_turns = any(
        previous_turn * next_turn < 0
        for previous_turn, next_turn in zip(signed_turn_angles, signed_turn_angles[1:])
    )
    total_turn_angle = sum(abs(turn_angle) for turn_angle in signed_turn_angles)
    if has_opposite_turns and total_turn_angle >= MAX_REALISTIC_Z_CURVE_TOTAL_DEGREES:
        return True

    shape_length_m = _shape_length_meters(shape_points)
    direct_length_m = _shape_direct_length_meters(shape_points)
    if shape_length_m is None or direct_length_m is None:
        return False

    reference_length_m = declared_length_m or direct_length_m
    max_reasonable_length_m = max(
        reference_length_m * MAX_REALISTIC_SHAPE_LENGTH_RATIO,
        direct_length_m * MAX_REALISTIC_SHAPE_LENGTH_RATIO,
    )
    return shape_length_m > max_reasonable_length_m


def _shape_candidate_score(shape_points: list[tuple[float, float]],
                           declared_length_m: float | None,
                           priority_group: int,
                           priority_order: int) -> tuple[float, float, float, int]:
    """Return a deterministic score for selecting the most realistic UTDF shape."""
    shape_length_m = _shape_length_meters(shape_points) or 0.0
    direct_length_m = _shape_direct_length_meters(shape_points) or shape_length_m
    reference_length_m = declared_length_m or direct_length_m
    length_error_m = abs(shape_length_m - reference_length_m)
    signed_turn_angles = _shape_signed_turn_angles(shape_points)
    max_turn_angle = (
        max(abs(turn_angle) for turn_angle in signed_turn_angles)
        if signed_turn_angles
        else 0.0
    )
    return priority_group, length_error_m, max_turn_angle, priority_order


def _select_realistic_shape_points(
        start_point: tuple[float, float],
        end_point: tuple[float, float],
        current_curve_point: tuple[float, float] | None,
        reverse_curve_point: tuple[float, float] | None,
        declared_length_m: float | None) -> list[tuple[float, float]]:
    """Choose the UTDF shape that avoids unrealistic 90-degree and Z links."""
    candidate_shapes = []
    if reverse_curve_point is not None and current_curve_point is not None:
        candidate_shapes.append((
            0,
            0,
            [start_point, reverse_curve_point, current_curve_point, end_point],
        ))
        candidate_shapes.append((
            0,
            1,
            [start_point, current_curve_point, reverse_curve_point, end_point],
        ))
    if current_curve_point is not None:
        candidate_shapes.append((1, 0, [start_point, current_curve_point, end_point]))
    if reverse_curve_point is not None:
        candidate_shapes.append((1, 1, [start_point, reverse_curve_point, end_point]))
    candidate_shapes.append((2, 0, [start_point, end_point]))

    valid_candidates = []
    for priority_group, priority_order, shape_points in candidate_shapes:
        cleaned_shape_points = _dedupe_shape_points(shape_points)
        if len(cleaned_shape_points) < 2:
            continue
        if _shape_has_unrealistic_curve(cleaned_shape_points, declared_length_m):
            continue

        valid_candidates.append((
            _shape_candidate_score(
                cleaned_shape_points,
                declared_length_m,
                priority_group,
                priority_order,
            ),
            cleaned_shape_points,
        ))

    if valid_candidates:
        return min(valid_candidates, key=lambda candidate: candidate[0])[1]
    return [start_point, end_point]


def _convert_utdf_xy_to_lonlat(value_x: Any, value_y: Any, reference_node: dict,
                               net_unit: str | None) -> tuple[float, float] | None:
    """Convert a UTDF local X/Y point to longitude/latitude using a node anchor."""
    point_x = _extract_number(value_x)
    point_y = _extract_number(value_y)
    if point_x is None or point_y is None:
        return None
    if any(_is_blank(reference_node.get(key)) for key in ("X", "Y", "x_coord", "y_coord")):
        return None

    x_offset = point_x - float(reference_node["X"])
    y_offset = point_y - float(reference_node["Y"])
    return calculate_new_coordinates_from_offsets(
        float(reference_node["x_coord"]),
        float(reference_node["y_coord"]),
        x_offset,
        y_offset,
        net_unit or "feet",
    )


def _get_profile_shape_points(profile: dict, network_nodes: dict | None,
                              net_unit: str | None) -> list[tuple[float, float]]:
    """Return the UTDF-defined centerline points for one directed approach."""
    if not network_nodes:
        return []

    up_node = _get_network_node(network_nodes, profile["from_node"])
    intersection_node = _get_network_node(network_nodes, profile["to_node"])
    if up_node is None or intersection_node is None:
        return []

    start_point = (float(up_node["x_coord"]), float(up_node["y_coord"]))
    end_point = (
        float(intersection_node["x_coord"]),
        float(intersection_node["y_coord"]),
    )
    reverse_curve_point = _convert_utdf_xy_to_lonlat(
        profile.get("reverse_curve_pt_x"),
        profile.get("reverse_curve_pt_y"),
        up_node,
        net_unit,
    )
    curve_point = _convert_utdf_xy_to_lonlat(
        profile.get("curve_pt_x"),
        profile.get("curve_pt_y"),
        intersection_node,
        net_unit,
    )
    # UTDF may store a two-point curve across the current and reverse links.
    # Keep that detail when it creates a realistic road centerline, but reject
    # sharp or Z-shaped candidates that would not represent a real street.
    return _select_realistic_shape_points(
        start_point,
        end_point,
        curve_point,
        reverse_curve_point,
        profile.get("length_m"),
    )


def _shape_points_to_utm(shape_points: list[tuple[float, float]]
                         ) -> tuple[list[tuple[float, float]], int, str] | None:
    """Project longitude/latitude shape points into UTM for distance operations."""
    if not shape_points:
        return None

    projected_points: list[tuple[float, float]] = []
    zone_number = 0
    hemisphere = "north"
    for lon, lat in shape_points:
        point_x, point_y, zone_number, hemisphere = cvt_lonlat_to_utm(lon, lat)
        projected_points.append((point_x, point_y))
    return projected_points, zone_number, hemisphere


def _shape_length_meters(shape_points: list[tuple[float, float]] | None) -> float | None:
    """Return the projected length of a longitude/latitude shape."""
    if not shape_points or len(shape_points) < 2:
        return None

    projected_data = _shape_points_to_utm(shape_points)
    if projected_data is None:
        return None

    projected_points, _, _ = projected_data
    return sum(
        ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
        for (start_x, start_y), (end_x, end_y)
        in zip(projected_points, projected_points[1:])
    )


def _interpolate_point_from_downstream(shape_points: list[tuple[float, float]],
                                       distance_from_downstream_m: float
                                       ) -> tuple[float, float] | None:
    """Return a point located upstream from the intersection along a UTDF shape."""
    projected_data = _shape_points_to_utm(shape_points)
    if projected_data is None:
        return None

    projected_points, zone_number, hemisphere = projected_data
    remaining_distance = max(distance_from_downstream_m, 0.0)
    for downstream_index in range(len(projected_points) - 1, 0, -1):
        down_x, down_y = projected_points[downstream_index]
        up_x, up_y = projected_points[downstream_index - 1]
        segment_dx = up_x - down_x
        segment_dy = up_y - down_y
        segment_length = (segment_dx**2 + segment_dy**2) ** 0.5
        if segment_length <= 0:
            continue
        if remaining_distance <= segment_length:
            ratio = remaining_distance / segment_length
            point_x = down_x + segment_dx * ratio
            point_y = down_y + segment_dy * ratio
            return cvt_utm_to_lonlat(point_x, point_y, zone_number, hemisphere)
        remaining_distance -= segment_length

    first_x, first_y = projected_points[0]
    return cvt_utm_to_lonlat(first_x, first_y, zone_number, hemisphere)


def _split_shape_at_point(shape_points: list[tuple[float, float]],
                          split_point: tuple[float, float] | None
                          ) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Split a profile centerline into upstream and stop-line shape pieces."""
    if not shape_points or split_point is None:
        return shape_points, []

    projected_data = _shape_points_to_utm(shape_points)
    split_projected_data = _shape_points_to_utm([split_point])
    if projected_data is None or split_projected_data is None:
        return shape_points, []

    projected_points, _, _ = projected_data
    split_projected = split_projected_data[0][0]
    best_segment_index = 0
    best_distance = float("inf")
    for index in range(len(projected_points) - 1):
        start_x, start_y = projected_points[index]
        end_x, end_y = projected_points[index + 1]
        segment_dx = end_x - start_x
        segment_dy = end_y - start_y
        segment_length_sq = segment_dx**2 + segment_dy**2
        if segment_length_sq <= 0:
            continue
        ratio = (
            ((split_projected[0] - start_x) * segment_dx
             + (split_projected[1] - start_y) * segment_dy)
            / segment_length_sq
        )
        ratio = min(max(ratio, 0.0), 1.0)
        closest_x = start_x + segment_dx * ratio
        closest_y = start_y + segment_dy * ratio
        distance = ((closest_x - split_projected[0]) ** 2
                    + (closest_y - split_projected[1]) ** 2) ** 0.5
        if distance < best_distance:
            best_distance = distance
            best_segment_index = index

    upstream_shape = [*shape_points[:best_segment_index + 1], split_point]
    stop_shape = [split_point, *shape_points[best_segment_index + 1:]]
    return upstream_shape, stop_shape


def _calculate_turn_bay_node_coord(profile: dict, network_nodes: dict,
                                   net_unit: str | None = None) -> tuple[float, float] | None:
    """Calculate the connector node coordinate at the upstream start of a turn-bay section."""
    shape_points = _get_profile_shape_points(profile, network_nodes, net_unit)
    if not shape_points:
        return None

    projected_data = _shape_points_to_utm(shape_points)
    if projected_data is None:
        return None

    shape_length = _shape_length_meters(shape_points) or 0.0
    if shape_length <= 0:
        return shape_points[-1]

    # UTDF storage/taper lengths can exceed the available coordinate geometry
    # on short links. Keep both split edges usable instead of creating a
    # near-zero upstream segment that overlaps visually after netconvert.
    minimum_main_segment_length = min(MIN_TURN_BAY_SPLIT_EDGE_LENGTH_M, shape_length / 2)
    maximum_bay_length = max(shape_length - minimum_main_segment_length, shape_length / 2)
    bay_length = min(profile["turn_bay_length_m"], maximum_bay_length)
    return _interpolate_point_from_downstream(shape_points, bay_length)


def _source_lane_indices_for_movement(profile: dict, movement: dict) -> list[int]:
    """Return stop-line lane indices that can serve a UTDF movement."""
    if movement["stop_lane_indices"]:
        return movement["stop_lane_indices"]

    through_lanes = profile["through_stop_lane_indices"]
    if movement["turn_type"] == "R":
        return [through_lanes[0]]
    if movement["turn_type"] in {"L", "U"}:
        return [through_lanes[-1]]
    return through_lanes


def _balanced_lane_position(lane_position: int, source_lane_count: int,
                            target_lane_count: int) -> int:
    """Map a source lane position to a balanced target lane position.

    When more source lanes merge into fewer receiving lanes, simple clamping
    overloads the last receiving lane. Proportional bucketing keeps the merge
    balanced while preserving right-to-left lane order.
    """
    if target_lane_count <= 1:
        return 0
    if source_lane_count <= 1:
        return 0
    if source_lane_count <= target_lane_count:
        return min(lane_position, target_lane_count - 1)
    return min(
        int(lane_position * target_lane_count / source_lane_count),
        target_lane_count - 1,
    )


def _target_lane_index_for_movement(profile: dict, turn_type: str, lane_position: int,
                                    source_lane_count: int = 1) -> int:
    """Return a balanced receiving lane on the target edge's main lane group."""
    through_lanes = profile["through_main_lane_indices"]
    if turn_type == "L" or turn_type == "U":
        balanced_position = _balanced_lane_position(
            lane_position,
            source_lane_count,
            len(through_lanes),
        )
        target_position = max(len(through_lanes) - balanced_position - 1, 0)
    else:
        target_position = _balanced_lane_position(
            lane_position,
            source_lane_count,
            len(through_lanes),
        )

    target_lane_index = through_lanes[target_position]
    return min(max(target_lane_index, 0), profile["main_lane_count"] - 1)


def _set_float_attr(element: ET.Element, attr_name: str, value: float | None) -> None:
    """Set a float XML attribute when a valid value is available."""
    formatted_value = _format_xml_number(value)
    if formatted_value is not None:
        element.set(attr_name, formatted_value)


def generate_sumo_nod_xml(utdf_dict: dict, filename: str = "network.nod.xml",
                          net_unit: str | None = None) -> bool:
    """Generate the .nod.xml file.

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        filename (str): The name of the output node XML file (.nod.xml).
        net_unit (str | None): The distance/speed unit used by the UTDF network.

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
    existing_node_ids = set()
    for node_id, node in network_nodes.items():
        node_elem = ET.SubElement(root, "node")
        node_elem.set("id", str(node_id))
        existing_node_ids.add(str(node_id))

        # Use real-world coordinates for SUMO and then use --proj.utm to convert to UTM
        node_elem.set("x", str(node["x_coord"]))
        node_elem.set("y", str(node["y_coord"]))

        node_type_description = node.get("TYPE_DESC")
        if node_type_description == "Signalized":
            node_elem.set("type", "traffic_light")  # Default type

    try:
        edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)
    except ValueError:
        edge_profiles = {}
    for profile in edge_profiles.values():
        if not profile["has_turn_bay"] or profile["bay_node_id"] in existing_node_ids:
            continue

        bay_node_coord = _calculate_turn_bay_node_coord(profile, network_nodes, net_unit)
        if bay_node_coord is None:
            continue

        bay_node_elem = ET.SubElement(root, "node")
        bay_node_elem.set("id", profile["bay_node_id"])
        bay_node_elem.set("x", str(bay_node_coord[0]))
        bay_node_elem.set("y", str(bay_node_coord[1]))
        bay_node_elem.set("type", "unregulated")
        existing_node_ids.add(profile["bay_node_id"])

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


def generate_sumo_connection_xml(utdf_dict: dict, filename: str = "network.con.xml",
                                 net_unit: str | None = None) -> bool:
    """Generate the .con.xml file.
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
        net_unit (str | None): The distance/speed unit used by the UTDF network.

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

    if utdf_dict.get("Lanes") is None:
        raise ValueError("Could not get Lane data from utdf_dict.")

    root_con = ET.Element("connections")

    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)

    # Lane-add/drop connections let vehicles leave the real through-lane section
    # and enter the short stop-line segment that contains turn pockets.
    for profile in edge_profiles.values():
        if not profile["has_turn_bay"]:
            continue

        for lane_slot in profile["stop_lane_slots"]:
            connection = ET.SubElement(root_con, "connection")
            connection.set("from", profile["main_edge_id"])
            connection.set("to", profile["stop_edge_id"])
            connection.set("fromLane", str(lane_slot["main_lane_index"]))
            connection.set("toLane", str(lane_slot["index"]))
            connection.set("dir", "s")
            connection.set("pass", "true")
            connection.set("uncontrolled", "true")

    # Intersection connections start from the stop-line edge, but they always
    # target the downstream edge's real/straight lane group, not its turn bay.
    for profile in edge_profiles.values():
        for movement in profile["movements"]:
            if not movement["dest_node"]:
                continue

            target_edge_id = f"{movement['intersection_node']}_{movement['dest_node']}"
            target_profile = edge_profiles.get(target_edge_id)
            if target_profile is None:
                continue

            source_lane_indices = _source_lane_indices_for_movement(profile, movement)
            sumo_direction = TURN_TYPE_TO_SUMO_DIR[movement["turn_type"]]
            source_lane_count = len(source_lane_indices)
            for lane_position, source_lane_index in enumerate(source_lane_indices):
                target_lane_index = _target_lane_index_for_movement(
                    target_profile,
                    movement["turn_type"],
                    lane_position,
                    source_lane_count,
                )

                connection = ET.SubElement(root_con, "connection")
                connection.set("from", profile["stop_edge_id"])
                connection.set("to", target_profile["main_edge_id"])
                connection.set("fromLane", str(source_lane_index))
                connection.set("toLane", str(target_lane_index))
                connection.set("dir", sumo_direction)
                _set_float_attr(connection, "speed", movement.get("turning_speed_mps"))

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

    network_nodes = utdf_dict.get("network_nodes")
    network_links = cvt_link_df_to_dict(links_df)
    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)

    def add_edge(edge_id: str, from_node: str, to_node: str, lane_count: int,
                 speed_mps: float | None,
                 shape_points: list[tuple[float, float]] | None = None) -> ET.Element:
        """Add one SUMO edge element with the common attributes."""
        edge_element = ET.SubElement(root, "edge")
        edge_element.set("id", edge_id)
        edge_element.set("from", from_node)
        edge_element.set("to", to_node)
        edge_element.set("numLanes", str(max(lane_count, 1)))
        _set_float_attr(edge_element, "speed", speed_mps)
        shape_text = _format_shape_points(shape_points)
        if shape_text is not None:
            edge_element.set("shape", shape_text)
        return edge_element

    def add_main_lane_elements(edge_element: ET.Element, profile: dict,
                               lane_length_m: float | None) -> None:
        """Add explicit lanes for an upstream segment that does not contain turn pockets."""
        for lane_index in range(profile["main_lane_count"]):
            lane_element = ET.SubElement(edge_element, "lane")
            lane_element.set("index", str(lane_index))
            _set_float_attr(lane_element, "length", lane_length_m)
            _set_float_attr(lane_element, "speed", profile["speed_mps"])

    def add_stop_lane_elements(edge_element: ET.Element, profile: dict,
                               lane_length_m: float | None) -> None:
        """Add explicit stop-line lanes so SUMO keeps the intended lane indices."""
        for lane_slot in profile["stop_lane_slots"]:
            lane_element = ET.SubElement(edge_element, "lane")
            lane_element.set("index", str(lane_slot["index"]))
            movement = lane_slot["movement"]
            lane_speed_mps = profile["speed_mps"]
            if movement is not None and movement["speed_mps"] is not None:
                lane_speed_mps = movement["speed_mps"]
            _set_float_attr(lane_element, "length", lane_length_m)
            _set_float_attr(lane_element, "speed", lane_speed_mps)

    def add_profile_edges(profile: dict) -> None:
        """Write the main edge and optional turn-bay edge for one approach profile."""
        shape_points = _get_profile_shape_points(profile, network_nodes, net_unit)
        if profile["has_turn_bay"]:
            bay_node_coord = _calculate_turn_bay_node_coord(
                profile,
                network_nodes,
                net_unit,
            )
            main_shape_points, stop_shape_points = _split_shape_at_point(
                shape_points,
                bay_node_coord,
            )
            main_lane_length_m = _shape_length_meters(main_shape_points)
            stop_lane_length_m = _shape_length_meters(stop_shape_points)
            if main_lane_length_m is None and stop_lane_length_m is None:
                if profile["length_m"] is None:
                    main_lane_length_m = None
                    stop_lane_length_m = profile["turn_bay_length_m"]
                else:
                    stop_lane_length_m = min(profile["turn_bay_length_m"], profile["length_m"])
                    main_lane_length_m = max(profile["length_m"] - stop_lane_length_m, 0.1)

            main_edge_element = add_edge(
                profile["main_edge_id"],
                profile["from_node"],
                profile["bay_node_id"],
                profile["main_lane_count"],
                profile["speed_mps"],
                main_shape_points,
            )
            add_main_lane_elements(main_edge_element, profile, main_lane_length_m)
            stop_edge_element = add_edge(
                profile["stop_edge_id"],
                profile["bay_node_id"],
                profile["to_node"],
                profile["stop_lane_count"],
                profile["speed_mps"],
                stop_shape_points,
            )
            add_stop_lane_elements(
                stop_edge_element,
                profile,
                stop_lane_length_m,
            )
        else:
            edge_element = add_edge(
                profile["main_edge_id"],
                profile["from_node"],
                profile["to_node"],
                profile["stop_lane_count"],
                profile["speed_mps"],
                shape_points,
            )
            add_stop_lane_elements(
                edge_element,
                profile,
                _shape_length_meters(shape_points) or profile["length_m"],
            )

    root = ET.Element("edges")
    written_profile_edge_ids: set[str] = set()
    for int_id, direction_links in network_links.items():
        for direction in direction_links:
            link = direction_links[direction]
            up_node = _normalize_node_id(link["Up ID"])
            intersection_node = _normalize_node_id(int_id)
            edge_id = f"{up_node}_{intersection_node}"
            profile = edge_profiles.get(edge_id)
            if profile is None or profile["edge_id"] in written_profile_edge_ids:
                continue

            add_profile_edges(profile)
            written_profile_edge_ids.add(profile["edge_id"])

    for edge_id, profile in sorted(edge_profiles.items()):
        if edge_id in written_profile_edge_ids:
            continue
        add_profile_edges(profile)
        written_profile_edge_ids.add(edge_id)

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
    active_lane_approach_ids = _collect_active_lane_approach_ids(utdf_dict)

    # Create a lookup dictionary for edges
    edge_lookup_dict = {}
    for int_id, direction_links in network_links.items():
        intersection_node = _normalize_node_id(int_id)
        for direction in direction_links:
            num_lanes = direction_links[direction].get("Lanes")  # Default lanes
            length = direction_links[direction].get("Distance")
            speed = direction_links[direction].get("Speed")

            up_node = _normalize_node_id(direction_links[direction]["Up ID"])
            if not up_node:
                continue

            edge_id = f"{up_node}_{intersection_node}"
            link_lane_count = _extract_int(num_lanes, default=0)
            if link_lane_count <= 0 and edge_id not in active_lane_approach_ids:
                continue

            edge_lookup_dict[edge_id] = {
                "num_lanes": num_lanes,
                "length": length,
                "speed": speed,
                "curve_pt_x": direction_links[direction].get("Curve Pt X"),
                "curve_pt_y": direction_links[direction].get("Curve Pt Y"),
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
    net_unit = kwargs.get("net_unit")
    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)

    flow_id_lst = []
    for int_id, direction_lanes in network_lanes.items():
        for direction in direction_lanes:

            # check whether the node have valid Up Node and Dest Node with volume greater than 0
            intersection_node = _normalize_node_id(int_id)
            up_node = _normalize_node_id(direction_lanes[direction].get("Up Node"))
            dest_node = _normalize_node_id(direction_lanes[direction].get("Dest Node"))
            volume = _get_movement_flow_volume(direction_lanes[direction])

            flow_id = f"{up_node}_{dest_node}"

            if up_node and dest_node and volume and volume > 0:
                source_profile = edge_profiles.get(f"{up_node}_{intersection_node}")
                target_profile = edge_profiles.get(f"{intersection_node}_{dest_node}")
                if source_profile is None or target_profile is None:
                    continue
                flow_number = _format_route_flow_number(volume)
                if int(flow_number) <= 0:
                    continue

                # avoid duplicate flow id in the flow file
                if flow_id not in flow_id_lst:
                    flow_id_lst.append(flow_id)
                    flow_elem = ET.SubElement(root, "flow")
                    flow_elem.set("id", f"{up_node}_{dest_node}")
                    flow_elem.set("from", source_profile["main_edge_id"])
                    flow_elem.set("to", target_profile["main_edge_id"])
                    flow_elem.set("number", flow_number)
                    flow_elem.set("type", "car")
                    flow_elem.set("departLane", "best")
                    if begin_time is not None:
                        flow_elem.set("begin", f"{int(begin_time)}")
                    if end_time is not None:
                        flow_elem.set("end", f"{int(end_time)}")

    xml_str = xml_prettify(root)
    with open(fname, "w") as f:
        f.write(xml_str)
    return True


def _build_turn_movement_records(utdf_dict: dict, net_unit: str | None) -> list[dict[str, Any]]:
    """Return valid UTDF turning movements as SUMO main-edge transitions."""
    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)
    movement_records = []

    for source_profile in edge_profiles.values():
        for movement in source_profile["movements"]:
            movement_volume = _extract_number(movement.get("volume"))
            if movement_volume is None or movement_volume <= 0:
                continue
            if not movement["dest_node"]:
                continue

            target_edge_id = f"{movement['intersection_node']}_{movement['dest_node']}"
            target_profile = edge_profiles.get(target_edge_id)
            if target_profile is None:
                continue

            movement_records.append({
                "source_edge_id": source_profile["main_edge_id"],
                "target_edge_id": target_profile["main_edge_id"],
                "volume": float(movement_volume),
                "movement_name": movement["movement_name"],
            })

    movement_records.sort(
        key=lambda record: (
            record["source_edge_id"],
            record["target_edge_id"],
            record["movement_name"],
        )
    )
    return movement_records


def _group_turn_movements_by_source(movement_records: list[dict[str, Any]]
                                    ) -> tuple[dict[str, list[dict[str, Any]]],
                                               dict[str, float],
                                               dict[str, float]]:
    """Group turning counts by source edge and merge repeated target edges."""
    target_volume_by_source: dict[str, dict[str, float]] = {}
    inbound_volume_by_edge: dict[str, float] = {}
    outbound_volume_by_edge: dict[str, float] = {}

    for movement_record in movement_records:
        source_edge_id = movement_record["source_edge_id"]
        target_edge_id = movement_record["target_edge_id"]
        volume = movement_record["volume"]

        target_volume_by_source.setdefault(source_edge_id, {})
        target_volume_by_source[source_edge_id][target_edge_id] = (
            target_volume_by_source[source_edge_id].get(target_edge_id, 0.0) + volume
        )
        outbound_volume_by_edge[source_edge_id] = outbound_volume_by_edge.get(source_edge_id, 0.0) + volume
        inbound_volume_by_edge[target_edge_id] = inbound_volume_by_edge.get(target_edge_id, 0.0) + volume

    outgoing_records_by_source = {}
    for source_edge_id, target_volumes in target_volume_by_source.items():
        outgoing_records_by_source[source_edge_id] = [
            {
                "source_edge_id": source_edge_id,
                "target_edge_id": target_edge_id,
                "volume": volume,
            }
            for target_edge_id, volume in sorted(target_volumes.items())
        ]

    return outgoing_records_by_source, inbound_volume_by_edge, outbound_volume_by_edge


def _clean_residual_turn_volumes(residual_turn_volumes: dict[str, dict[str, float]],
                                 volume_epsilon: float) -> None:
    """Remove residual turning movements that have already been consumed."""
    for source_edge_id in list(residual_turn_volumes):
        for target_edge_id in list(residual_turn_volumes[source_edge_id]):
            if residual_turn_volumes[source_edge_id][target_edge_id] <= volume_epsilon:
                del residual_turn_volumes[source_edge_id][target_edge_id]

        if not residual_turn_volumes[source_edge_id]:
            del residual_turn_volumes[source_edge_id]


def _build_residual_turn_volume_graph(outgoing_records_by_source: dict[str, list[dict[str, Any]]]
                                      ) -> dict[str, dict[str, float]]:
    """Build a mutable graph of remaining UTDF turning movement volumes."""
    residual_turn_volumes = {}
    for source_edge_id, outgoing_records in outgoing_records_by_source.items():
        residual_turn_volumes[source_edge_id] = {
            outgoing_record["target_edge_id"]: outgoing_record["volume"]
            for outgoing_record in outgoing_records
        }
    return residual_turn_volumes


def _build_boundary_route_endpoints(inbound_volume_by_edge: dict[str, float],
                                    outbound_volume_by_edge: dict[str, float],
                                    volume_epsilon: float,
                                    boundary_source_edge_ids: set[str] | None = None,
                                    boundary_sink_edge_ids: set[str] | None = None,
                                    ) -> tuple[dict[str, float], dict[str, float]]:
    """Return external source and sink edge volumes inferred from UTDF counts."""
    source_volume_by_edge = {
        edge_id: outbound_volume
        for edge_id, outbound_volume in sorted(outbound_volume_by_edge.items())
        if outbound_volume > volume_epsilon
        and inbound_volume_by_edge.get(edge_id, 0.0) <= volume_epsilon
        and (
            boundary_source_edge_ids is None
            or edge_id in boundary_source_edge_ids
        )
    }
    sink_volume_by_edge = {
        edge_id: inbound_volume
        for edge_id, inbound_volume in sorted(inbound_volume_by_edge.items())
        if inbound_volume > volume_epsilon
        and outbound_volume_by_edge.get(edge_id, 0.0) <= volume_epsilon
        and (
            boundary_sink_edge_ids is None
            or edge_id in boundary_sink_edge_ids
        )
    }
    return source_volume_by_edge, sink_volume_by_edge


def _find_longest_residual_path_to_sink(start_edge_id: str,
                                        residual_turn_volumes: dict[str, dict[str, float]],
                                        sink_volume_by_edge: dict[str, float],
                                        max_route_edges: int,
                                        volume_epsilon: float) -> list[str]:
    """Find a counted source-to-sink path that covers many UTDF movements."""
    best_path: list[str] = []
    pending_paths = [[start_edge_id]]

    while pending_paths:
        current_path = pending_paths.pop()
        current_edge_id = current_path[-1]
        if (
            len(current_path) > 1
            and sink_volume_by_edge.get(current_edge_id, 0.0) > volume_epsilon
        ):
            if not best_path or len(current_path) > len(best_path):
                best_path = current_path
            elif (
                len(current_path) == len(best_path)
                and tuple(current_path) < tuple(best_path)
            ):
                best_path = current_path
            continue

        if len(current_path) >= max_route_edges:
            continue

        for target_edge_id in sorted(residual_turn_volumes.get(current_edge_id, {})):
            if residual_turn_volumes[current_edge_id][target_edge_id] <= volume_epsilon:
                continue
            if target_edge_id in current_path:
                continue

            pending_paths.append([*current_path, target_edge_id])

    return best_path


def _path_residual_capacity(edge_path: list[str],
                            residual_turn_volumes: dict[str, dict[str, float]]) -> float:
    """Return the largest route volume that can travel along a residual path."""
    return min(
        residual_turn_volumes[source_edge_id][target_edge_id]
        for source_edge_id, target_edge_id in zip(edge_path, edge_path[1:])
    )


def _find_best_residual_boundary_path(source_edge_ids: list[str],
                                      residual_turn_volumes: dict[str, dict[str, float]],
                                      sink_volume_by_edge: dict[str, float],
                                      max_route_edges: int,
                                      volume_epsilon: float) -> list[str]:
    """Find the longest available boundary-to-boundary route path."""
    best_path: list[str] = []
    best_capacity = 0.0
    for source_edge_id in source_edge_ids:
        candidate_path = _find_longest_residual_path_to_sink(
            source_edge_id,
            residual_turn_volumes,
            sink_volume_by_edge,
            max_route_edges,
            volume_epsilon,
        )
        if not candidate_path:
            continue

        candidate_capacity = _path_residual_capacity(
            candidate_path,
            residual_turn_volumes,
        )
        if len(candidate_path) > len(best_path):
            best_path = candidate_path
            best_capacity = candidate_capacity
        elif len(candidate_path) == len(best_path):
            if candidate_capacity > best_capacity + volume_epsilon:
                best_path = candidate_path
                best_capacity = candidate_capacity
            elif abs(candidate_capacity - best_capacity) <= volume_epsilon:
                if not best_path or tuple(candidate_path) < tuple(best_path):
                    best_path = candidate_path
                    best_capacity = candidate_capacity

    return best_path


def _build_physical_boundary_edge_ids(edge_profiles: dict,
                                      network_nodes: dict | None
                                      ) -> tuple[set[str], set[str]]:
    """Return source and sink edges that touch the modeled network boundary."""
    from_nodes = {profile["from_node"] for profile in edge_profiles.values()}
    to_nodes = {profile["to_node"] for profile in edge_profiles.values()}
    external_node_ids: set[str] = set()
    if network_nodes is not None:
        for node_id, node_info in network_nodes.items():
            node_type = str(node_info.get("TYPE_DESC", "")).strip().lower()
            if node_type == "external node":
                external_node_ids.add(_normalize_node_id(node_id))

    source_edge_ids = set()
    sink_edge_ids = set()
    for profile in edge_profiles.values():
        edge_id = profile["main_edge_id"]
        if profile["from_node"] in external_node_ids or profile["from_node"] not in to_nodes:
            source_edge_ids.add(edge_id)
        if profile["to_node"] in external_node_ids or profile["to_node"] not in from_nodes:
            sink_edge_ids.add(edge_id)
    return source_edge_ids, sink_edge_ids


def _get_node_type(network_nodes: dict | None, node_id: str) -> str:
    """Return a normalized UTDF node type description."""
    if network_nodes is None:
        return ""

    node_info = _get_network_node(network_nodes, node_id)
    if node_info is None:
        return ""
    return str(node_info.get("TYPE_DESC", "")).strip().lower()


def _node_is_signalized(network_nodes: dict | None, node_id: str) -> bool:
    """Return True when the UTDF node is a signalized intersection."""
    return _get_node_type(network_nodes, node_id) == "signalized"


def _build_topology_transition_graph(edge_profiles: dict,
                                     network_nodes: dict | None = None
                                     ) -> dict[str, set[str]]:
    """Return all physically representable edge-to-edge transitions.

    Positive UTDF turning counts are only available at some intersections. For
    network-level routes, vehicles still need to pass through uncounted bends,
    unsignalized nodes, and simple connector movements instead of entering or
    leaving the modeled network there. Signalized zero-count movements are not
    used as connector steps because those counts are explicit UTDF observations.
    """
    profiles_by_main_edge = {
        profile["main_edge_id"]: profile
        for profile in edge_profiles.values()
    }
    outgoing_edges_by_from_node: dict[str, list[str]] = {}
    for profile in edge_profiles.values():
        outgoing_edges_by_from_node.setdefault(profile["from_node"], [])
        outgoing_edges_by_from_node[profile["from_node"]].append(profile["main_edge_id"])

    transition_graph: dict[str, set[str]] = {
        profile["main_edge_id"]: set()
        for profile in edge_profiles.values()
    }
    for profile in edge_profiles.values():
        source_edge_id = profile["main_edge_id"]
        is_signalized_stop_line = _node_is_signalized(
            network_nodes,
            profile["to_node"],
        )
        for movement in profile["movements"]:
            if not movement["dest_node"]:
                continue
            movement_volume = _extract_number(movement.get("volume")) or 0.0
            if is_signalized_stop_line and movement_volume <= 0:
                continue

            target_edge_id = f"{movement['intersection_node']}_{movement['dest_node']}"
            target_profile = edge_profiles.get(target_edge_id)
            if target_profile is not None:
                transition_graph[source_edge_id].add(target_profile["main_edge_id"])

        if transition_graph[source_edge_id] or profile["movements"]:
            continue
        if is_signalized_stop_line:
            continue

        # Links without lane-group movement rows are usually bends or simple
        # pass-through nodes. Continue to downstream edges and avoid the direct
        # reverse edge unless it is the only possible continuation.
        candidate_next_edges = [
            edge_id
            for edge_id in outgoing_edges_by_from_node.get(profile["to_node"], [])
            if edge_id in profiles_by_main_edge
        ]
        non_reverse_edges = [
            edge_id
            for edge_id in candidate_next_edges
            if profiles_by_main_edge[edge_id]["to_node"] != profile["from_node"]
        ]
        transition_graph[source_edge_id].update(non_reverse_edges or candidate_next_edges)

    return transition_graph


def _reverse_transition_graph(transition_graph: dict[str, set[str]]) -> dict[str, set[str]]:
    """Return a reversed copy of a transition graph."""
    reversed_graph: dict[str, set[str]] = {edge_id: set() for edge_id in transition_graph}
    for source_edge_id, target_edge_ids in transition_graph.items():
        for target_edge_id in target_edge_ids:
            reversed_graph.setdefault(target_edge_id, set()).add(source_edge_id)
    return reversed_graph


def _transition_has_capacity(source_edge_id: str,
                             target_edge_id: str,
                             residual_turn_volumes: dict[str, dict[str, float]],
                             counted_transition_keys: set[tuple[str, str]],
                             volume_epsilon: float) -> bool:
    """Return True when a transition can currently be used by a route."""
    if (source_edge_id, target_edge_id) not in counted_transition_keys:
        return True
    return (
        residual_turn_volumes.get(source_edge_id, {}).get(target_edge_id, 0.0)
        > volume_epsilon
    )


def _find_shortest_topology_path(start_edge_id: str,
                                 target_edge_ids: set[str],
                                 transition_graph: dict[str, set[str]],
                                 residual_turn_volumes: dict[str, dict[str, float]],
                                 counted_transition_keys: set[tuple[str, str]],
                                 max_route_edges: int,
                                 volume_epsilon: float,
                                 blocked_edge_ids: set[str] | None = None,
                                 graph_is_reversed: bool = False,
                                 ) -> list[str]:
    """Find a shortest usable path through the current topology graph."""
    if start_edge_id in target_edge_ids:
        return [start_edge_id]

    blocked_edge_ids = blocked_edge_ids or set()
    visited = {start_edge_id}
    pending_paths: deque[list[str]] = deque([[start_edge_id]])
    while pending_paths:
        path = pending_paths.popleft()
        if len(path) >= max_route_edges:
            continue

        current_edge_id = path[-1]
        for next_edge_id in sorted(transition_graph.get(current_edge_id, set())):
            if next_edge_id in visited:
                continue
            if next_edge_id in blocked_edge_ids and next_edge_id not in target_edge_ids:
                continue
            capacity_source_edge_id = current_edge_id
            capacity_target_edge_id = next_edge_id
            if graph_is_reversed:
                capacity_source_edge_id = next_edge_id
                capacity_target_edge_id = current_edge_id

            if not _transition_has_capacity(
                    capacity_source_edge_id,
                    capacity_target_edge_id,
                    residual_turn_volumes,
                    counted_transition_keys,
                    volume_epsilon):
                continue

            next_path = [*path, next_edge_id]
            if next_edge_id in target_edge_ids:
                return next_path
            visited.add(next_edge_id)
            pending_paths.append(next_path)

    return []


def _positive_residual_edges_on_path(edge_path: list[str],
                                     residual_turn_volumes: dict[str, dict[str, float]],
                                     volume_epsilon: float) -> list[tuple[str, str]]:
    """Return counted movements on a route path that still have residual demand."""
    positive_edges = []
    for source_edge_id, target_edge_id in zip(edge_path, edge_path[1:]):
        if (
            residual_turn_volumes.get(source_edge_id, {}).get(target_edge_id, 0.0)
            > volume_epsilon
        ):
            positive_edges.append((source_edge_id, target_edge_id))
    return positive_edges


def _path_residual_capacity_from_edges(
        positive_residual_edges: list[tuple[str, str]],
        residual_turn_volumes: dict[str, dict[str, float]]) -> float:
    """Return the largest route volume supported by counted movements on a path."""
    return min(
        residual_turn_volumes[source_edge_id][target_edge_id]
        for source_edge_id, target_edge_id in positive_residual_edges
    )


def _build_boundary_to_boundary_path_for_movement(
        source_edge_id: str,
        target_edge_id: str,
        boundary_source_edge_ids: set[str],
        boundary_sink_edge_ids: set[str],
        transition_graph: dict[str, set[str]],
        reverse_transition_graph: dict[str, set[str]],
        residual_turn_volumes: dict[str, dict[str, float]],
        counted_transition_keys: set[tuple[str, str]],
        max_route_edges: int,
        volume_epsilon: float) -> list[str]:
    """Extend one residual movement to physical network entry and exit edges."""
    reverse_prefix_path = _find_shortest_topology_path(
        source_edge_id,
        boundary_source_edge_ids,
        reverse_transition_graph,
        residual_turn_volumes,
        counted_transition_keys,
        max_route_edges,
        volume_epsilon,
        graph_is_reversed=True,
    )
    if not reverse_prefix_path:
        return []

    prefix_path = list(reversed(reverse_prefix_path))
    if target_edge_id in prefix_path:
        return []

    route_path = [*prefix_path, target_edge_id]
    remaining_edge_limit = max_route_edges - len(prefix_path)
    if remaining_edge_limit <= 0:
        return []

    suffix_path = _find_shortest_topology_path(
        target_edge_id,
        boundary_sink_edge_ids,
        transition_graph,
        residual_turn_volumes,
        counted_transition_keys,
        remaining_edge_limit + 1,
        volume_epsilon,
        blocked_edge_ids=set(route_path[:-1]),
    )
    if not suffix_path:
        return []

    return [*route_path, *suffix_path[1:]]


def _find_best_physical_boundary_path(
        residual_turn_volumes: dict[str, dict[str, float]],
        boundary_source_edge_ids: set[str],
        boundary_sink_edge_ids: set[str],
        transition_graph: dict[str, set[str]],
        reverse_transition_graph: dict[str, set[str]],
        counted_transition_keys: set[tuple[str, str]],
        max_route_edges: int,
        volume_epsilon: float) -> list[str]:
    """Find one high-value residual path from a real entry edge to a real exit edge."""
    best_path: list[str] = []
    best_positive_count = 0
    best_capacity = 0.0

    for source_edge_id in sorted(residual_turn_volumes):
        for target_edge_id in sorted(residual_turn_volumes[source_edge_id]):
            if residual_turn_volumes[source_edge_id][target_edge_id] <= volume_epsilon:
                continue

            candidate_path = _build_boundary_to_boundary_path_for_movement(
                source_edge_id,
                target_edge_id,
                boundary_source_edge_ids,
                boundary_sink_edge_ids,
                transition_graph,
                reverse_transition_graph,
                residual_turn_volumes,
                counted_transition_keys,
                max_route_edges,
                volume_epsilon,
            )
            if not candidate_path:
                continue

            positive_edges = _positive_residual_edges_on_path(
                candidate_path,
                residual_turn_volumes,
                volume_epsilon,
            )
            if not positive_edges:
                continue

            candidate_capacity = _path_residual_capacity_from_edges(
                positive_edges,
                residual_turn_volumes,
            )
            candidate_positive_count = len(positive_edges)
            if candidate_positive_count > best_positive_count:
                best_path = candidate_path
                best_positive_count = candidate_positive_count
                best_capacity = candidate_capacity
            elif candidate_positive_count == best_positive_count:
                if candidate_capacity > best_capacity + volume_epsilon:
                    best_path = candidate_path
                    best_capacity = candidate_capacity
                elif abs(candidate_capacity - best_capacity) <= volume_epsilon:
                    if not best_path or tuple(candidate_path) < tuple(best_path):
                        best_path = candidate_path
                        best_capacity = candidate_capacity

    return best_path


def _decompose_to_physical_boundary_routes(
        residual_turn_volumes: dict[str, dict[str, float]],
        boundary_source_edge_ids: set[str],
        boundary_sink_edge_ids: set[str],
        topology_transition_graph: dict[str, set[str]],
        max_route_edges: int,
        min_route_volume: float,
        volume_epsilon: float) -> list[dict[str, Any]]:
    """Decompose counted movements without creating internal route endpoints."""
    counted_transition_keys = {
        (source_edge_id, target_edge_id)
        for source_edge_id, target_volumes in residual_turn_volumes.items()
        for target_edge_id in target_volumes
    }
    reverse_graph = _reverse_transition_graph(topology_transition_graph)
    network_routes = []

    while residual_turn_volumes:
        edge_path = _find_best_physical_boundary_path(
            residual_turn_volumes,
            boundary_source_edge_ids,
            boundary_sink_edge_ids,
            topology_transition_graph,
            reverse_graph,
            counted_transition_keys,
            max_route_edges,
            volume_epsilon,
        )
        if not edge_path:
            break

        positive_edges = _positive_residual_edges_on_path(
            edge_path,
            residual_turn_volumes,
            volume_epsilon,
        )
        if not positive_edges:
            break

        route_volume = _path_residual_capacity_from_edges(
            positive_edges,
            residual_turn_volumes,
        )
        if route_volume <= volume_epsilon:
            break

        for source_edge_id, target_edge_id in positive_edges:
            residual_turn_volumes[source_edge_id][target_edge_id] -= route_volume
        _clean_residual_turn_volumes(residual_turn_volumes, volume_epsilon)

        if route_volume >= min_route_volume:
            network_routes.append({
                "main_edge_path": edge_path,
                "volume": route_volume,
            })

    return network_routes


def _decompose_turn_movements_to_routes(movement_records: list[dict[str, Any]],
                                        max_route_edges: int,
                                        min_route_volume: float,
                                        boundary_source_edge_ids: set[str] | None = None,
                                        boundary_sink_edge_ids: set[str] | None = None,
                                        topology_transition_graph: dict[str, set[str]] | None = None,
                                        ) -> list[dict[str, Any]]:
    """Convert intersection turning counts into longer network-level route flows.

    Each UTDF turning count is treated as a movement capacity. The generated
    routes use boundary-to-boundary paths that respect those capacities, so a
    simulated movement can never exceed its original UTDF count. Longer counted
    paths are preferred because they align more downstream intersections with
    the UTDF counts. When adjacent intersection counts are inconsistent, the
    generator leaves the unmatched residual demand out of the network-level
    routes instead of creating or removing vehicles on ordinary internal links.
    """
    volume_epsilon = 1e-6
    (
        outgoing_records_by_source,
        inbound_volume_by_edge,
        outbound_volume_by_edge,
    ) = _group_turn_movements_by_source(movement_records)
    (
        source_volume_by_edge,
        sink_volume_by_edge,
    ) = _build_boundary_route_endpoints(
        inbound_volume_by_edge,
        outbound_volume_by_edge,
        volume_epsilon,
        boundary_source_edge_ids,
        boundary_sink_edge_ids,
    )
    residual_turn_volumes = _build_residual_turn_volume_graph(outgoing_records_by_source)
    if (
        topology_transition_graph is not None
        and boundary_source_edge_ids
        and boundary_sink_edge_ids
    ):
        return _decompose_to_physical_boundary_routes(
            residual_turn_volumes,
            boundary_source_edge_ids,
            boundary_sink_edge_ids,
            topology_transition_graph,
            max_route_edges,
            min_route_volume,
            volume_epsilon,
        )

    network_routes = []

    while residual_turn_volumes:
        source_edge_ids = [
            edge_id for edge_id in sorted(source_volume_by_edge)
            if source_volume_by_edge[edge_id] > volume_epsilon
            and edge_id in residual_turn_volumes
        ]
        if not source_edge_ids:
            break

        edge_path = _find_best_residual_boundary_path(
            source_edge_ids,
            residual_turn_volumes,
            sink_volume_by_edge,
            max_route_edges,
            volume_epsilon,
        )
        if not edge_path:
            break

        route_volume = min(
            source_volume_by_edge[edge_path[0]],
            sink_volume_by_edge[edge_path[-1]],
            _path_residual_capacity(edge_path, residual_turn_volumes),
        )
        if route_volume <= volume_epsilon:
            break

        source_volume_by_edge[edge_path[0]] -= route_volume
        sink_volume_by_edge[edge_path[-1]] -= route_volume
        for source_edge_id, target_edge_id in zip(edge_path, edge_path[1:]):
            residual_turn_volumes[source_edge_id][target_edge_id] -= route_volume
        _clean_residual_turn_volumes(residual_turn_volumes, volume_epsilon)

        if route_volume >= min_route_volume:
            network_routes.append({
                "main_edge_path": edge_path,
                "volume": route_volume,
            })

    return network_routes


def _expand_route_edges_with_turn_bays(main_edge_path: list[str],
                                       edge_profiles_by_main_edge: dict[str, dict]) -> list[str]:
    """Insert short stop-line turn-bay edges into a route path when needed."""
    if not main_edge_path:
        return []

    route_edges = [main_edge_path[0]]
    for source_edge_id, target_edge_id in zip(main_edge_path, main_edge_path[1:]):
        source_profile = edge_profiles_by_main_edge.get(source_edge_id)
        if source_profile is not None and source_profile["has_turn_bay"]:
            route_edges.append(source_profile["stop_edge_id"])
        route_edges.append(target_edge_id)

    return route_edges


def _format_route_flow_number(volume: float) -> str:
    """Format a decomposed route volume for SUMO's flow number attribute."""
    return str(max(int(round(volume)), 0))


def generate_sumo_network_route_xml(utdf_dict: dict, fname: str = "network.rou.xml",
                                    **kwargs) -> bool:
    """Generate a network-level SUMO route file from UTDF turning counts.

    The existing ``generate_sumo_flow_xml`` function writes one local flow for
    each counted intersection movement. This writer instead decomposes the same
    UTDF turning counts into route flows that can travel through multiple
    intersections before leaving the modeled network.

    Args:
        utdf_dict (dict): A dictionary containing UTDF data.
        fname (str): The name of the output route XML file (.rou.xml).
        **kwargs: Additional route-generation settings.
            begin (int): The start time for each generated flow.
            end (int): The end time for each generated flow.
            net_unit (str): The distance/speed unit used by the UTDF network.
            max_route_edges (int): Maximum number of main edges in one route.
            min_route_volume (float): Smallest route volume to keep.

    Raises:
        ValueError: UTDF Lanes data are required.

    Returns:
        bool: True if the XML file is generated successfully, False otherwise.
    """
    if utdf_dict.get("Lanes") is None:
        raise ValueError("UTDF Lanes data are required. ")

    begin_time = kwargs.get("begin")
    end_time = kwargs.get("end")
    net_unit = kwargs.get("net_unit")
    max_route_edges = int(kwargs.get("max_route_edges", 50))
    min_route_volume = float(kwargs.get("min_route_volume", 0.5))

    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)
    edge_profiles_by_main_edge = {
        profile["main_edge_id"]: profile
        for profile in edge_profiles.values()
    }
    boundary_source_edge_ids, boundary_sink_edge_ids = _build_physical_boundary_edge_ids(
        edge_profiles,
        utdf_dict.get("network_nodes"),
    )
    topology_transition_graph = _build_topology_transition_graph(
        edge_profiles,
        utdf_dict.get("network_nodes"),
    )
    movement_records = _build_turn_movement_records(utdf_dict, net_unit)
    network_routes = _decompose_turn_movements_to_routes(
        movement_records,
        max_route_edges=max_route_edges,
        min_route_volume=min_route_volume,
        boundary_source_edge_ids=boundary_source_edge_ids,
        boundary_sink_edge_ids=boundary_sink_edge_ids,
        topology_transition_graph=topology_transition_graph,
    )

    route_volume_by_edges: dict[tuple[str, ...], float] = {}
    for network_route in network_routes:
        route_edges = _expand_route_edges_with_turn_bays(
            network_route["main_edge_path"],
            edge_profiles_by_main_edge,
        )
        if len(route_edges) < 2:
            continue

        route_key = tuple(route_edges)
        route_volume_by_edges[route_key] = (
            route_volume_by_edges.get(route_key, 0.0) + network_route["volume"]
        )

    root = ET.Element("routes")
    ET.SubElement(root, "vType", id="car", type="passenger")

    route_index = 0
    for route_edges, route_volume in sorted(route_volume_by_edges.items()):
        flow_number = _format_route_flow_number(route_volume)
        if int(flow_number) <= 0:
            continue

        route_id = f"network_route_{route_index}"
        route_element = ET.SubElement(root, "route")
        route_element.set("id", route_id)
        route_element.set("edges", " ".join(route_edges))

        flow_element = ET.SubElement(root, "flow")
        flow_element.set("id", f"network_flow_{route_index}")
        flow_element.set("route", route_id)
        flow_element.set("number", flow_number)
        flow_element.set("type", "car")
        flow_element.set("departLane", "best")
        # Network-level flows enter from physical boundary links. Vehicles are
        # already traveling before they reach the modeled network, so placing
        # them on a free boundary position at speed prevents artificial cold-
        # start queues from overpowering the UTDF turning counts.
        flow_element.set("departSpeed", "max")
        flow_element.set("departPos", "random_free")
        if begin_time is not None:
            flow_element.set("begin", f"{int(begin_time)}")
        if end_time is not None:
            flow_element.set("end", f"{int(end_time)}")

        route_index += 1

    xml_str = xml_prettify(root)
    with open(fname, "w") as f:
        f.write(xml_str)
    return True


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

    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)

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

    for profile in edge_profiles.values():
        for lane_slot in profile["stop_lane_slots"]:
            movement = lane_slot["movement"]
            if movement is None or _extract_int(movement.get("num_detects"), default=0) <= 0:
                continue

            lane_id = f"{profile['stop_edge_id']}_{lane_slot['index']}"
            detector = ET.SubElement(add_elem, detector_tag)
            detector.set("id", f"{lane_id}_detector")
            detector.set("lane", lane_id)
            detector.set("pos", "-8")  # must be assigned, backward from the lane end
            detector.set("friendlyPos", "true")
            detector.set("file", f"{sim_output_fname}")  # output file name

    xml_str = xml_prettify(add_elem)
    with open(add_fname, "w") as f:
        f.write(xml_str)
    return True
