'''
##############################################################
# Created Date: Thursday, March 12th 2026
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

from __future__ import annotations

import math
import re
from typing import Any

import pandas as pd

from utdf2gmns.func_lib.gmns.geocoding_Links import cvt_utm_to_lonlat
from utdf2gmns.func_lib.sumo.gmns2sumo import (
    TURN_TYPE_TO_SUMO_DIR,
    _build_sumo_edge_profile_dict,
    _calculate_turn_bay_node_coord,
    _format_xml_number,
    _get_profile_shape_points,
    _normalize_node_id,
    _shape_length_meters,
    _shape_points_to_utm,
    _source_lane_indices_for_movement,
    _split_shape_at_point,
    _target_lane_index_for_movement,
    generate_net_link_lookup_dict,
)


TURN_TYPE_TO_GMNS_TYPE = {
    "R": "right",
    "T": "thru",
    "L": "left",
    "U": "uturn",
}
DEFAULT_LANE_WIDTH_FEET = 12.0
DEFAULT_LANE_WIDTH_METERS = 3.6


def _format_number(value: float | int | None) -> float | str:
    """Return a compact number for CSV output while preserving blanks."""
    formatted_value = _format_xml_number(value)
    if formatted_value is None:
        return ""
    return float(formatted_value)


def _format_csv_list(values: list[int]) -> str:
    """Return lane indices as a readable comma-separated CSV cell."""
    return ",".join(str(value) for value in values)


def _get_lane_width_meters(utdf_dict: dict, net_unit: str | None) -> float:
    """Return the lane width used to offset GMNS lane centerlines."""
    lane_width_value = None
    network_df = utdf_dict.get("Network")
    if network_df is not None and "RECORDNAME" in network_df and "DATA" in network_df:
        matching_rows = network_df[
            network_df["RECORDNAME"].astype(str) == "DefWidth"
        ]
        if not matching_rows.empty:
            lane_width_text = str(matching_rows.iloc[0]["DATA"]).strip()
            if lane_width_text.lower() not in {"", "nan", "none", "null"}:
                try:
                    lane_width_value = float(lane_width_text)
                except ValueError:
                    number_matches = re.findall(r"-?\d+(?:\.\d+)?", lane_width_text)
                    if number_matches:
                        lane_width_value = float(number_matches[0])

    if lane_width_value is None:
        lane_width_value = (
            DEFAULT_LANE_WIDTH_FEET
            if net_unit and "feet" in net_unit
            else DEFAULT_LANE_WIDTH_METERS
        )

    if net_unit and "feet" in net_unit:
        return lane_width_value * 0.3048
    return lane_width_value


def _build_polygon_geometry(shape_points: list[tuple[float, float]] | None,
                            lane_count: int,
                            lane_width_meters: float,
                            lane_index: int | None = None) -> str:
    """Return a GMNS link or lane polygon as WKT geometry.

    When ``lane_index`` is not provided, the polygon covers the full directional
    link width. When ``lane_index`` is provided, the polygon covers only that
    lane. Adjacent lane polygons reuse the same offset boundary, so they touch
    at shared edges without overlapping.
    """
    if not shape_points:
        return ""

    lane_count = max(lane_count, 1)
    center_lane_index = (lane_count - 1) / 2
    if lane_index is None:
        right_offset_meters = (center_lane_index + 0.5) * lane_width_meters
        left_offset_meters = -right_offset_meters
    else:
        lane_center_offset_meters = (center_lane_index - lane_index) * lane_width_meters
        right_offset_meters = lane_center_offset_meters + lane_width_meters / 2
        left_offset_meters = lane_center_offset_meters - lane_width_meters / 2

    projected_data = _shape_points_to_utm(shape_points)
    if projected_data is None:
        return ""

    projected_points, zone_number, hemisphere = projected_data
    if len(projected_points) < 2:
        return ""

    # Turn-bay splits can create a very short interior segment next to an
    # existing UTDF curve point. Dropping only those tiny interior kinks keeps
    # the link endpoints fixed and prevents lane-width offsets from folding.
    polygon_width_meters = abs(right_offset_meters - left_offset_meters)
    minimum_segment_length_meters = min(1.0, max(0.1, polygon_width_meters / 4))
    if len(projected_points) > 2:
        cleaned_projected_points: list[tuple[float, float]] = [projected_points[0]]
        for projected_point in projected_points[1:-1]:
            previous_projected_point = cleaned_projected_points[-1]
            segment_length_meters = math.hypot(
                projected_point[0] - previous_projected_point[0],
                projected_point[1] - previous_projected_point[1],
            )
            if segment_length_meters < minimum_segment_length_meters:
                continue
            cleaned_projected_points.append(projected_point)

        if len(cleaned_projected_points) > 1:
            previous_projected_point = cleaned_projected_points[-1]
            final_projected_point = projected_points[-1]
            final_segment_length_meters = math.hypot(
                final_projected_point[0] - previous_projected_point[0],
                final_projected_point[1] - previous_projected_point[1],
            )
            if final_segment_length_meters < minimum_segment_length_meters:
                cleaned_projected_points.pop()

        cleaned_projected_points.append(projected_points[-1])
        projected_points = cleaned_projected_points

    boundaries: list[list[tuple[float, float]]] = []
    for offset_meters in [right_offset_meters, left_offset_meters]:
        offset_projected_points: list[tuple[float, float]] = []
        last_normal: tuple[float, float] | None = None
        for point_index, projected_point in enumerate(projected_points):
            candidate_normals: list[tuple[float, float]] = []
            if point_index > 0:
                start_point = projected_points[point_index - 1]
                end_point = projected_point
                segment_dx = end_point[0] - start_point[0]
                segment_dy = end_point[1] - start_point[1]
                segment_length = math.hypot(segment_dx, segment_dy)
                if segment_length > 0:
                    candidate_normals.append((
                        segment_dy / segment_length,
                        -segment_dx / segment_length,
                    ))
            if point_index < len(projected_points) - 1:
                start_point = projected_point
                end_point = projected_points[point_index + 1]
                segment_dx = end_point[0] - start_point[0]
                segment_dy = end_point[1] - start_point[1]
                segment_length = math.hypot(segment_dx, segment_dy)
                if segment_length > 0:
                    candidate_normals.append((
                        segment_dy / segment_length,
                        -segment_dx / segment_length,
                    ))

            if not candidate_normals:
                normal = last_normal
            elif len(candidate_normals) == 1:
                normal = candidate_normals[0]
            else:
                normal_x = candidate_normals[0][0] + candidate_normals[1][0]
                normal_y = candidate_normals[0][1] + candidate_normals[1][1]
                normal_length = math.hypot(normal_x, normal_y)
                normal = (
                    candidate_normals[1]
                    if normal_length <= 0
                    else (normal_x / normal_length, normal_y / normal_length)
                )

            if normal is None:
                offset_projected_points.append(projected_point)
                continue

            last_normal = normal
            offset_projected_points.append((
                projected_point[0] + normal[0] * offset_meters,
                projected_point[1] + normal[1] * offset_meters,
            ))

        boundaries.append([
            cvt_utm_to_lonlat(point_x, point_y, zone_number, hemisphere)
            for point_x, point_y in offset_projected_points
        ])

    right_boundary_points, left_boundary_points = boundaries
    polygon_points = [*right_boundary_points, *reversed(left_boundary_points)]
    if len(polygon_points) < 3:
        return ""
    first_point = polygon_points[0]
    last_point = polygon_points[-1]
    if (
        abs(first_point[0] - last_point[0]) > 1e-12
        or abs(first_point[1] - last_point[1]) > 1e-12
    ):
        polygon_points.append(first_point)

    point_text = [
        f"{_format_xml_number(point[0])} {_format_xml_number(point[1])}"
        for point in polygon_points
    ]
    return f"POLYGON (({', '.join(point_text)}))"


def _get_network_nodes(utdf_dict: dict) -> dict:
    """Return geocoded network nodes or raise a clear export error."""
    network_nodes = utdf_dict.get("network_nodes")
    if network_nodes is None:
        raise ValueError("No network_nodes found, please run geocode_utdf_intersections() first.")
    return network_nodes


def _get_profile_segment_records(profile: dict, network_nodes: dict,
                                 net_unit: str | None,
                                 lane_width_meters: float) -> list[dict[str, Any]]:
    """Return the GMNS link segment rows represented by one SUMO edge profile."""
    shape_points = _get_profile_shape_points(profile, network_nodes, net_unit)

    if not profile["has_turn_bay"]:
        return [{
            "link_id": profile["main_edge_id"],
            "from_node_id": profile["from_node"],
            "to_node_id": profile["to_node"],
            "lanes": profile["stop_lane_count"],
            "length_m": _shape_length_meters(shape_points) or profile["length_m"],
            "free_speed_mps": profile["speed_mps"],
            "geometry": _build_polygon_geometry(
                shape_points,
                profile["stop_lane_count"],
                lane_width_meters,
            ),
            "_shape_points": shape_points,
            "main_link_id": profile["main_edge_id"],
            "is_turn_bay_link": False,
        }]

    bay_node_coord = _calculate_turn_bay_node_coord(profile, network_nodes, net_unit)
    if bay_node_coord is None:
        return [{
            "link_id": profile["main_edge_id"],
            "from_node_id": profile["from_node"],
            "to_node_id": profile["to_node"],
            "lanes": profile["stop_lane_count"],
            "length_m": _shape_length_meters(shape_points) or profile["length_m"],
            "free_speed_mps": profile["speed_mps"],
            "geometry": _build_polygon_geometry(
                shape_points,
                profile["stop_lane_count"],
                lane_width_meters,
            ),
            "_shape_points": shape_points,
            "main_link_id": profile["main_edge_id"],
            "is_turn_bay_link": False,
        }]

    main_shape_points, stop_shape_points = _split_shape_at_point(
        shape_points,
        bay_node_coord,
    )
    main_length_m = _shape_length_meters(main_shape_points)
    stop_length_m = _shape_length_meters(stop_shape_points)
    if main_length_m is None and stop_length_m is None:
        if profile["length_m"] is None:
            main_length_m = None
            stop_length_m = profile["turn_bay_length_m"]
        else:
            stop_length_m = min(profile["turn_bay_length_m"], profile["length_m"])
            main_length_m = max(profile["length_m"] - stop_length_m, 0.1)

    return [
        {
            "link_id": profile["main_edge_id"],
            "from_node_id": profile["from_node"],
            "to_node_id": profile["bay_node_id"],
            "lanes": profile["main_lane_count"],
            "length_m": main_length_m,
            "free_speed_mps": profile["speed_mps"],
            "geometry": _build_polygon_geometry(
                main_shape_points,
                profile["main_lane_count"],
                lane_width_meters,
            ),
            "_shape_points": main_shape_points,
            "main_link_id": profile["main_edge_id"],
            "is_turn_bay_link": False,
        },
        {
            "link_id": profile["stop_edge_id"],
            "from_node_id": profile["bay_node_id"],
            "to_node_id": profile["to_node"],
            "lanes": profile["stop_lane_count"],
            "length_m": stop_length_m,
            "free_speed_mps": profile["speed_mps"],
            "geometry": _build_polygon_geometry(
                stop_shape_points,
                profile["stop_lane_count"],
                lane_width_meters,
            ),
            "_shape_points": stop_shape_points,
            "main_link_id": profile["main_edge_id"],
            "is_turn_bay_link": True,
        },
    ]


def _get_profile_segments_by_link_id(utdf_dict: dict,
                                     net_unit: str | None) -> dict[str, dict[str, Any]]:
    """Build link segment records keyed by generated GMNS link id."""
    network_nodes = _get_network_nodes(utdf_dict)
    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)
    lane_width_meters = _get_lane_width_meters(utdf_dict, net_unit)
    segments_by_link_id = {}
    for edge_id in sorted(edge_profiles):
        profile = edge_profiles[edge_id]
        for segment in _get_profile_segment_records(
                profile,
                network_nodes,
                net_unit,
                lane_width_meters):
            segments_by_link_id[segment["link_id"]] = segment
    return segments_by_link_id


def _build_lane_record(profile: dict, lane_index: int, link_id: str,
                       lane_length_m: float | None, lane_speed_mps: float | None,
                       lane_count: int, shape_points: list[tuple[float, float]] | None,
                       lane_width_meters: float,
                       lane_slot: dict | None = None) -> dict[str, Any]:
    """Create one GMNS lane row from a profile lane slot."""
    movement = lane_slot.get("movement") if lane_slot else None
    turn_type = lane_slot.get("turn_type", "T") if lane_slot else "T"
    lane_type = TURN_TYPE_TO_GMNS_TYPE.get(turn_type, "thru")
    movement_name = movement.get("movement_name", "") if movement else ""
    dest_node = movement.get("dest_node", "") if movement else ""
    movement_id = ""
    if movement is not None and dest_node:
        movement_id = (
            f"{movement['up_node']}_{movement['intersection_node']}_"
            f"{dest_node}_{movement_name}"
        )

    if movement is not None and movement.get("speed_mps") is not None:
        lane_speed_mps = movement["speed_mps"]

    return {
        "lane_id": f"{link_id}_{lane_index}",
        "link_id": link_id,
        "lane_num": lane_index,
        "length_m": _format_number(lane_length_m),
        "speed_mps": _format_number(lane_speed_mps),
        "geometry": _build_polygon_geometry(
            shape_points,
            lane_count,
            lane_width_meters,
            lane_index=lane_index,
        ),
        "type": lane_type,
        "movement_name": movement_name,
        "mvmt_id": movement_id,
        "up_node": movement.get("up_node", "") if movement else profile["from_node"],
        "dest_node": dest_node,
        "volume": movement.get("volume", "") if movement else "",
        "numDetects": movement.get("num_detects", "") if movement else "",
        "is_turn_bay_lane": bool(lane_slot and lane_slot.get("is_turn_bay")),
        "is_added_turn_bay_lane": bool(lane_slot and lane_slot.get("is_added_turn_bay_lane")),
    }


def generate_gmns_node(utdf_dict: dict, filename: str = "node.csv",
                       net_unit: str | None = None) -> bool:
    """Generate ``node.csv`` with original intersections and turn-bay nodes."""
    network_nodes = _get_network_nodes(utdf_dict)
    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)

    node_rows = []
    existing_node_ids = set()
    for node_id, node in network_nodes.items():
        node_row = dict(node)
        normalized_node_id = _normalize_node_id(node_row.get("INTID", node_id))
        if not normalized_node_id or normalized_node_id in existing_node_ids:
            continue
        node_row["node_id"] = normalized_node_id
        node_row["INTID"] = normalized_node_id
        node_row["node_type"] = node_row.get("TYPE_DESC", "")
        node_row["is_turn_bay_node"] = False
        node_rows.append(node_row)
        existing_node_ids.add(normalized_node_id)

    for edge_id in sorted(edge_profiles):
        profile = edge_profiles[edge_id]
        if not profile["has_turn_bay"] or profile["bay_node_id"] in existing_node_ids:
            continue

        bay_node_coord = _calculate_turn_bay_node_coord(profile, network_nodes, net_unit)
        if bay_node_coord is None:
            continue

        node_rows.append({
            "node_id": profile["bay_node_id"],
            "INTID": profile["bay_node_id"],
            "x_coord": bay_node_coord[0],
            "y_coord": bay_node_coord[1],
            "node_type": "Turn Bay",
            "TYPE_DESC": "Turn Bay",
            "is_turn_bay_node": True,
            "main_link_id": profile["main_edge_id"],
        })
        existing_node_ids.add(profile["bay_node_id"])

    df_node = pd.DataFrame(node_rows)
    front_cols = ["node_id", "x_coord", "y_coord", "node_type"]
    other_cols = [column for column in df_node.columns if column not in front_cols]
    df_node = df_node[front_cols + other_cols]
    df_node["node_id"] = df_node["node_id"].astype("string")
    if "INTID" in df_node.columns:
        df_node["INTID"] = df_node["INTID"].astype("string")
    df_node.to_csv(filename, index=False)
    return True


def generate_gmns_link(utdf_dict: dict, filename: str = "link.csv",
                       net_unit: str | None = None) -> bool:
    """Generate ``link.csv`` using the same turn-bay split as SUMO export."""
    segments_by_link_id = _get_profile_segments_by_link_id(utdf_dict, net_unit)
    df_link = pd.DataFrame(segments_by_link_id.values())
    if df_link.empty:
        df_link.to_csv(filename, index=False)
        return True

    df_link["length_m"] = df_link["length_m"].map(_format_number)
    df_link["free_speed_mps"] = df_link["free_speed_mps"].map(_format_number)
    df_link = df_link.drop(columns=["_shape_points"], errors="ignore")
    for id_column in ["link_id", "from_node_id", "to_node_id", "main_link_id"]:
        if id_column in df_link.columns:
            df_link[id_column] = df_link[id_column].astype("string")
    front_cols = [
        "link_id",
        "from_node_id",
        "to_node_id",
        "lanes",
        "length_m",
        "free_speed_mps",
        "geometry",
    ]
    other_cols = [column for column in df_link.columns if column not in front_cols]
    df_link = df_link[front_cols + other_cols]
    df_link.to_csv(filename, index=False)
    return True


def generate_lane_lookup_dict(utdf_dict: dict, net_unit: str | None = None) -> dict:
    """Return GMNS lane rows built from the shared SUMO edge profile model."""
    network_nodes = _get_network_nodes(utdf_dict)
    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)
    lane_width_meters = _get_lane_width_meters(utdf_dict, net_unit)
    lane_lookup_dict = {}

    for edge_id in sorted(edge_profiles):
        profile = edge_profiles[edge_id]
        segments = {
            segment["link_id"]: segment
            for segment in _get_profile_segment_records(
                profile,
                network_nodes,
                net_unit,
                lane_width_meters,
            )
        }

        has_written_turn_bay = (
            profile["has_turn_bay"]
            and profile["main_edge_id"] in segments
            and profile["stop_edge_id"] in segments
        )
        if has_written_turn_bay:
            main_segment = segments[profile["main_edge_id"]]
            for lane_index in range(profile["main_lane_count"]):
                lane_record = _build_lane_record(
                    profile,
                    lane_index,
                    profile["main_edge_id"],
                    main_segment["length_m"],
                    profile["speed_mps"],
                    profile["main_lane_count"],
                    main_segment.get("_shape_points"),
                    lane_width_meters,
                )
                lane_lookup_dict[lane_record["lane_id"]] = lane_record

            stop_segment = segments[profile["stop_edge_id"]]
            for lane_slot in profile["stop_lane_slots"]:
                lane_record = _build_lane_record(
                    profile,
                    lane_slot["index"],
                    profile["stop_edge_id"],
                    stop_segment["length_m"],
                    profile["speed_mps"],
                    profile["stop_lane_count"],
                    stop_segment.get("_shape_points"),
                    lane_width_meters,
                    lane_slot,
                )
                lane_lookup_dict[lane_record["lane_id"]] = lane_record
            continue

        segment = segments[profile["main_edge_id"]]
        for lane_slot in profile["stop_lane_slots"]:
            lane_record = _build_lane_record(
                profile,
                lane_slot["index"],
                profile["main_edge_id"],
                segment["length_m"],
                profile["speed_mps"],
                profile["stop_lane_count"],
                segment.get("_shape_points"),
                lane_width_meters,
                lane_slot,
            )
            lane_lookup_dict[lane_record["lane_id"]] = lane_record

    return lane_lookup_dict


def generate_link_lookup_dict(utdf_dict: dict) -> dict:
    """Return the filtered UTDF directed link lookup used by network export."""
    return generate_net_link_lookup_dict(utdf_dict)


def generate_gmns_lane(utdf_dict: dict, filename: str = "lane.csv",
                       net_unit: str | None = None) -> bool:
    """Generate ``lane.csv`` using real through lanes plus short turn-bay lanes."""
    lanes_dict = generate_lane_lookup_dict(utdf_dict, net_unit=net_unit)
    df_lane = pd.DataFrame(lanes_dict.values())
    if df_lane.empty:
        df_lane.to_csv(filename, index=False)
        return True

    for id_column in ["lane_id", "link_id", "mvmt_id", "up_node", "dest_node"]:
        if id_column in df_lane.columns:
            df_lane[id_column] = df_lane[id_column].astype("string")
    front_cols = [
        "lane_id",
        "link_id",
        "lane_num",
        "length_m",
        "speed_mps",
        "geometry",
        "type",
        "movement_name",
        "mvmt_id",
    ]
    other_cols = [column for column in df_lane.columns if column not in front_cols]
    df_lane = df_lane[front_cols + other_cols]
    df_lane.to_csv(filename, index=False)
    return True


def _build_turn_bay_connector_movement(profile: dict) -> dict[str, Any]:
    """Create the free connector movement from an upstream link into a bay link."""
    inbound_lane_indices = [
        lane_slot["main_lane_index"]
        for lane_slot in profile["stop_lane_slots"]
    ]
    outbound_lane_indices = [
        lane_slot["index"]
        for lane_slot in profile["stop_lane_slots"]
    ]

    return {
        "mvmt_id": f"{profile['main_edge_id']}_to_{profile['stop_edge_id']}",
        "node_id": profile["bay_node_id"],
        "ib_link_id": profile["main_edge_id"],
        "ob_link_id": profile["stop_edge_id"],
        "type": "thru",
        "movement_name": "TURN_BAY_CONNECTOR",
        "num_lanes": len(outbound_lane_indices),
        "volume": 0,
        "ib_lane_indices": _format_csv_list(inbound_lane_indices),
        "ob_lane_indices": _format_csv_list(outbound_lane_indices),
        "sumo_dir": "s",
        "is_turn_bay_connector": True,
        "control": "free",
    }


def _build_intersection_movement(profile: dict, target_profile: dict,
                                 movement: dict,
                                 inbound_link_id: str) -> dict[str, Any] | None:
    """Create one GMNS movement row from an intersection turning movement."""
    source_lane_indices = _source_lane_indices_for_movement(profile, movement)
    if not source_lane_indices:
        return None

    target_lane_indices = [
        _target_lane_index_for_movement(
            target_profile,
            movement["turn_type"],
            lane_position,
            len(source_lane_indices),
        )
        for lane_position, _ in enumerate(source_lane_indices)
    ]
    movement_name = movement["movement_name"]
    movement_id = (
        f"{movement['up_node']}_{movement['intersection_node']}_"
        f"{movement['dest_node']}_{movement_name}"
    )

    return {
        "mvmt_id": movement_id,
        "node_id": movement["intersection_node"],
        "ib_link_id": inbound_link_id,
        "ob_link_id": target_profile["main_edge_id"],
        "type": TURN_TYPE_TO_GMNS_TYPE.get(movement["turn_type"], "invalid"),
        "movement_name": movement_name,
        "num_lanes": len(source_lane_indices),
        "volume": movement.get("volume") or 0,
        "ib_lane_indices": _format_csv_list(source_lane_indices),
        "ob_lane_indices": _format_csv_list(target_lane_indices),
        "sumo_dir": TURN_TYPE_TO_SUMO_DIR.get(movement["turn_type"], ""),
        "turning_speed_mps": _format_number(movement.get("turning_speed_mps")),
        "is_turn_bay_connector": False,
        "control": "",
    }


def generate_gmns_movement(utdf_dict: dict, filename: str = "movement.csv",
                           net_unit: str | None = None) -> bool:
    """Generate ``movement.csv`` from the same lane connections used by SUMO."""
    if utdf_dict.get("Lanes") is None:
        raise ValueError("Could not get Lane data from utdf_dict.")

    edge_profiles = _build_sumo_edge_profile_dict(utdf_dict, net_unit)
    segments_by_link_id = _get_profile_segments_by_link_id(utdf_dict, net_unit)
    movement_rows = []

    for edge_id in sorted(edge_profiles):
        profile = edge_profiles[edge_id]
        has_written_turn_bay = (
            profile["has_turn_bay"]
            and profile["stop_edge_id"] in segments_by_link_id
        )
        inbound_link_id = profile["stop_edge_id"] if has_written_turn_bay else profile["main_edge_id"]

        if has_written_turn_bay:
            movement_rows.append(_build_turn_bay_connector_movement(profile))

        for movement in profile["movements"]:
            if not movement["dest_node"]:
                continue

            target_edge_id = f"{movement['intersection_node']}_{movement['dest_node']}"
            target_profile = edge_profiles.get(target_edge_id)
            if target_profile is None:
                continue

            movement_row = _build_intersection_movement(
                profile,
                target_profile,
                movement,
                inbound_link_id,
            )
            if movement_row is not None:
                movement_rows.append(movement_row)

    df_movement = pd.DataFrame(movement_rows)
    if df_movement.empty:
        df_movement.to_csv(filename, index=False)
        return True

    for id_column in ["mvmt_id", "node_id", "ib_link_id", "ob_link_id"]:
        if id_column in df_movement.columns:
            df_movement[id_column] = df_movement[id_column].astype("string")
    front_cols = [
        "mvmt_id",
        "node_id",
        "ib_link_id",
        "ob_link_id",
        "type",
        "movement_name",
        "num_lanes",
        "volume",
        "ib_lane_indices",
        "ob_lane_indices",
    ]
    other_cols = [column for column in df_movement.columns if column not in front_cols]
    df_movement = df_movement[front_cols + other_cols]
    df_movement.to_csv(filename, index=False)
    return True
