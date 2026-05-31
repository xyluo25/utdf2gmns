'''
##############################################################
# Created Date: Monday, December 30th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Ms. Yiran Zhang
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

from utdf2gmns.func_lib.sumo.read_sumo import ReadSUMO
from utdf2gmns.func_lib.sumo.signal_intersections import parse_signal_control
from utdf2gmns.func_lib.sumo.signal_mapping import (direction_mapping,
                                                    build_linkDuration,
                                                    extract_dir_info,
                                                    create_SignalTimingPlan,
                                                    process_pedestrian_crossing)
from utdf2gmns.func_lib.utdf.read_utdf import read_UTDF
from utdf2gmns.func_lib.utdf.cvt_utdf_lane_df_to_dict import cvt_lane_df_to_dict


BLANK_TEXT_VALUES = {"", "nan", "none", "null"}


def _is_blank(value: object) -> bool:
    """Return True when a UTDF cell does not contain useful data."""
    if value is None:
        return True
    return str(value).strip().lower() in BLANK_TEXT_VALUES


def _normalize_utdf_node_id(value: object) -> str:
    """Return a stable UTDF node id string for edge-id matching."""
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


def _node_sort_key(node_id: str) -> tuple[int, int | str]:
    """Sort node ids numerically when possible and lexically otherwise."""
    normalized_node_id = _normalize_utdf_node_id(node_id)
    try:
        return 0, int(normalized_node_id)
    except ValueError:
        return 1, normalized_node_id


def _extract_float(value: object, default: float = 0.0) -> float:
    """Extract a numeric UTDF cell value for simple signal decisions."""
    if _is_blank(value):
        return default
    try:
        return float(str(value).strip())
    except ValueError:
        return default


def _strip_turn_bay_suffix(edge_id: str) -> str:
    """Return the main edge id for a SUMO turn-bay edge id."""
    if edge_id.endswith("_bay"):
        return edge_id[:-4]
    return edge_id


def _get_up_node_from_edge_id(edge_id: str, intersection_id: str) -> str:
    """Extract the upstream UTDF node id from a generated SUMO inbound edge id."""
    main_edge_id = _strip_turn_bay_suffix(edge_id)
    normalized_intersection_id = _normalize_utdf_node_id(intersection_id)
    suffix = f"_{normalized_intersection_id}"
    if not main_edge_id.endswith(suffix):
        return ""
    return main_edge_id[:-len(suffix)]


def _get_dest_node_from_edge_id(edge_id: str, intersection_id: str) -> str:
    """Extract the downstream UTDF node id from a generated SUMO outbound edge id."""
    main_edge_id = _strip_turn_bay_suffix(edge_id)
    normalized_intersection_id = _normalize_utdf_node_id(intersection_id)
    prefix = f"{normalized_intersection_id}_"
    if not main_edge_id.startswith(prefix):
        return ""
    return main_edge_id[len(prefix):]


def _is_utdf_movement_name(value: str) -> bool:
    """Return True when text looks like a UTDF vehicle movement name."""
    if len(value) < 3:
        return False
    return value[:2].isalpha() and value[2] in {"R", "T", "L", "U"}


def _sumo_dir_to_utdf_turn(sumo_dir: str | None) -> str:
    """Convert SUMO connection direction text into a UTDF movement suffix."""
    if sumo_dir == "s":
        return "T"
    if sumo_dir == "t":
        return "U"
    if sumo_dir in {"l", "L"}:
        return "L"
    if sumo_dir in {"r", "R"}:
        return "R"
    return str(sumo_dir or "").upper()


def _build_signal_controller_mapping(
        timeplans_df,
        sumo_signal_ids: set[str] | None = None) -> dict[str, str]:
    """Map each signalized node to the UTDF controller that owns its timings.

    UTDF Timeplans support ``Node 0`` through ``Node 7`` records so one
    controller can operate multiple intersections. In that case Synchro writes
    the timing and phase records only for the controller INTID, while the local
    intersection still has its own lane movement records.
    """
    if timeplans_df is None or "INTID" not in timeplans_df or "RECORDNAME" not in timeplans_df:
        return {}

    allowed_signal_ids = None
    if sumo_signal_ids is not None:
        allowed_signal_ids = {
            _normalize_utdf_node_id(signal_id)
            for signal_id in sumo_signal_ids
        }

    controller_mapping: dict[str, str] = {}
    normalized_intids = timeplans_df["INTID"].map(_normalize_utdf_node_id)
    for controller_id in sorted(set(normalized_intids), key=_node_sort_key):
        if not controller_id:
            continue

        if allowed_signal_ids is None or controller_id in allowed_signal_ids:
            controller_mapping[controller_id] = controller_id

        controller_rows = timeplans_df[normalized_intids == controller_id]
        node_rows = controller_rows[
            controller_rows["RECORDNAME"].astype(str).str.strip().str.lower().str.startswith("node")
        ]
        for node_id in node_rows.get("DATA", []):
            normalized_node_id = _normalize_utdf_node_id(node_id)
            if not normalized_node_id or normalized_node_id == "0":
                continue
            if allowed_signal_ids is not None and normalized_node_id not in allowed_signal_ids:
                continue
            controller_mapping.setdefault(normalized_node_id, controller_id)

    return controller_mapping


def _build_inbound_direction_mapping_from_lanes(
        network_lanes: dict,
        intersection_id: str,
        inbound_edges: list[str]) -> tuple[dict[str, str], set[str]]:
    """Map generated SUMO inbound edges to UTDF bounds using Up Node values.

    The old fallback uses geometry slopes, which can fail for short turn-bay
    edges or for approaches with zero-lane movements. Generated SUMO edge ids
    preserve the UTDF upstream and intersection node ids, so this exact lookup
    is the preferred mapping when the network was produced by this package.
    """
    movement_lanes = network_lanes.get(str(intersection_id))
    if movement_lanes is None and str(intersection_id).isdigit():
        movement_lanes = network_lanes.get(int(intersection_id))
    if movement_lanes is None:
        return {}, set()

    lane_directions: set[str] = set()
    bounds_by_up_node: dict[str, set[str]] = {}
    for movement_name, movement_info in movement_lanes.items():
        if not _is_utdf_movement_name(movement_name):
            continue

        up_node = _normalize_utdf_node_id(movement_info.get("Up Node"))
        dest_node = _normalize_utdf_node_id(movement_info.get("Dest Node"))
        if not up_node or not dest_node:
            continue

        lane_directions.add(movement_name)
        bounds_by_up_node.setdefault(up_node, set()).add(movement_name[:2])

    inbound_direction_mapping = {}
    for inbound_edge in inbound_edges:
        up_node = _get_up_node_from_edge_id(inbound_edge, str(intersection_id))
        candidate_bounds = bounds_by_up_node.get(up_node, set())
        if len(candidate_bounds) == 1:
            inbound_direction_mapping[inbound_edge] = next(iter(candidate_bounds))

    return inbound_direction_mapping, lane_directions


def _build_movement_lookup_from_lanes(
        network_lanes: dict,
        intersection_id: str) -> dict[tuple[str, str], list[str]]:
    """Return UTDF movement names keyed by ``(up_node, dest_node)``."""
    movement_lanes = network_lanes.get(str(intersection_id))
    if movement_lanes is None and str(intersection_id).isdigit():
        movement_lanes = network_lanes.get(int(intersection_id))
    if movement_lanes is None:
        return {}

    movement_names_by_node_pair: dict[tuple[str, str], list[str]] = {}
    for movement_name, movement_info in movement_lanes.items():
        if not _is_utdf_movement_name(movement_name):
            continue

        up_node = _normalize_utdf_node_id(movement_info.get("Up Node"))
        dest_node = _normalize_utdf_node_id(movement_info.get("Dest Node"))
        if not up_node or not dest_node:
            continue

        movement_names_by_node_pair.setdefault((up_node, dest_node), [])
        movement_names_by_node_pair[(up_node, dest_node)].append(movement_name)

    return movement_names_by_node_pair


def _select_movement_name_for_sumo_connection(
        movement_names_by_node_pair: dict[tuple[str, str], list[str]],
        intersection_id: str,
        sumo_movement: dict,
        fallback_bound: str) -> str:
    """Map one SUMO connection to the best UTDF movement name.

    SUMO's connection ``dir`` can be ambiguous after geometry simplification,
    especially around short turn-bay edges and skewed intersections. The UTDF
    destination node is a stronger signal because it identifies the actual
    counted movement in the source file.
    """
    up_node = _get_up_node_from_edge_id(sumo_movement["fromEdge"], intersection_id)
    dest_node = _get_dest_node_from_edge_id(sumo_movement["toEdge"], intersection_id)
    movement_names = movement_names_by_node_pair.get((up_node, dest_node), [])
    fallback_turn = _sumo_dir_to_utdf_turn(sumo_movement.get("dir"))
    fallback_movement_name = f"{fallback_bound}{fallback_turn}"

    if not movement_names:
        return fallback_movement_name
    if len(movement_names) == 1:
        return movement_names[0]
    if fallback_movement_name in movement_names:
        return fallback_movement_name

    matching_turn_names = [
        movement_name for movement_name in movement_names
        if fallback_turn in movement_name[2:]
    ]
    if matching_turn_names:
        return sorted(matching_turn_names)[0]
    return sorted(movement_names)[0]


def _get_movement_info(
        network_lanes: dict,
        intersection_id: str,
        movement_name: str) -> dict:
    """Return one UTDF movement record from the converted lane dictionary."""
    movement_lanes = network_lanes.get(str(intersection_id))
    if movement_lanes is None and str(intersection_id).isdigit():
        movement_lanes = network_lanes.get(int(intersection_id))
    if movement_lanes is None:
        return {}
    return movement_lanes.get(movement_name, {})


def _movement_is_uncontrolled(movement_info: dict) -> bool:
    """Return True when UTDF marks a movement phase as uncontrolled with -1."""
    for phase_index in range(1, 5):
        phase_value = str(movement_info.get(f"Phase{phase_index}", "")).strip()
        permitted_value = str(movement_info.get(f"PermPhase{phase_index}", "")).strip()
        if phase_value == "-1" or permitted_value == "-1":
            return True
    return False


def _right_turn_has_channelized_control(movement_name: str, movement_info: dict) -> bool:
    """Return True when a right turn is channelized outside the main signal head."""
    if "R" not in movement_name[2:]:
        return False

    # UTDF values: 0=no, 1=yield, 2=free, 3=stop, 4=signal.
    right_channeled = int(_extract_float(movement_info.get("Right Channeled")))
    return right_channeled in {1, 2, 3}


def _right_turn_allows_rtor(movement_name: str, movement_info: dict) -> bool:
    """Return True when UTDF allows right-turn-on-red for this lane group."""
    if "R" not in movement_name[2:]:
        return False
    return _extract_float(movement_info.get("Allow RTOR")) > 0


def _movement_is_inactive(movement_info: dict) -> bool:
    """Return True for placeholder movements with no lanes and no demand."""
    lane_count = _extract_float(movement_info.get("Lanes"))
    volume = _extract_float(movement_info.get("Volume"))
    lane_group_flow = _extract_float(movement_info.get("Lane Group Flow"))
    normalized_lane_group_flow = _extract_float(movement_info.get("Lane_Group_Flow"))
    return (
        lane_count <= 0
        and volume <= 0
        and lane_group_flow <= 0
        and normalized_lane_group_flow <= 0
    )


def _build_inbound_direction_mapping_from_utdf(
        utdf_dict: dict,
        intersection_id: str,
        inbound_edges: list[str]) -> tuple[dict[str, str], set[str]]:
    """Build exact inbound mapping directly from a UTDF dictionary."""
    lane_df = utdf_dict.get("Lanes")
    if lane_df is None:
        return {}, set()
    return _build_inbound_direction_mapping_from_lanes(
        cvt_lane_df_to_dict(lane_df),
        intersection_id,
        inbound_edges,
    )


def update_sumo_signal_from_utdf(sumo_net_xml: str, utdf_dict_or_fname: dict | str, verbose: bool = False) -> bool:
    """update sumo signal (.net.xml) from UTDF signal information

    Args:
        sumo_net_xml (str): the path of sumo network xml file
        utdf_dict_or_fname (dict | str): the UTDF dictionary or the path of UTDF csv file
        verbose (bool): whether to print the process. Defaults to False.

    Example:
        >>> import utdf2gmns as ug
        >>> sumo_net_xml = "your sumo network xml file"
        >>> utdf_dict_or_fname = "your utdf file, in csv format"
        >>> ug.update_sumo_signal_from_utdf(sumo_net_xml, utdf_dict_or_fname, verbose=True)

    Returns:
        bool: whether the generation is successful
    """

    # Check if utdf_dict_or_fname is a dictionary or a file name
    if isinstance(utdf_dict_or_fname, dict):
        utdf_dict = utdf_dict_or_fname
    elif isinstance(utdf_dict_or_fname, str):
        utdf_dict = read_UTDF(utdf_dict_or_fname)
    else:
        raise TypeError("utdf_dict_or_fname must be a dictionary or a file name")

    # check if sumo_net_xml ends with .net.xml
    if not sumo_net_xml.endswith(".net.xml"):
        raise ValueError("sumo_net_xml must end with .net.xml")

    # read sumo network
    sumo_net = ReadSUMO(sumo_net_xml)

    timeplans = utdf_dict.get("Timeplans")
    signal_controller_by_node = _build_signal_controller_mapping(
        timeplans,
        set(sumo_net.sumo_signal_info.keys()),
    )
    signalized_int_ids = [
        node_id for node_id in sorted(signal_controller_by_node, key=_node_sort_key)
        if node_id in sumo_net.sumo_signal_info
    ]

    # parse signal intersection information
    utdf_signal = {}
    network_lanes = cvt_lane_df_to_dict(utdf_dict.get("Lanes"))

    for int_id in signalized_int_ids:

        # in this case sumo id equal to UTDF signal intersection id
        int_id = str(int_id)
        controller_id = signal_controller_by_node[int_id]

        utdf_signal[int_id] = parse_signal_control(df_phase=utdf_dict.get("Phases"),
                                                   df_lane=utdf_dict.get("Lanes"),
                                                   int_id=controller_id,
                                                   lane_int_id=int_id)
        phase_directions = set(extract_dir_info(utdf_signal[int_id]))

        if verbose:
            print(f"\nIntersection id: {int_id} "
                  f"(UTDF controller {controller_id}) \nDirections: {phase_directions}\n")

        unique_inbound_edges = []
        for connection_index in sumo_net.sumo_signal_info[int_id].keys():
            sumo_movement = sumo_net.sumo_signal_info[int_id][connection_index]
            if ":" not in sumo_movement["fromEdge"] and sumo_movement["fromEdge"] not in unique_inbound_edges:
                unique_inbound_edges.append(sumo_movement["fromEdge"])

        exact_mapping, lane_directions = _build_inbound_direction_mapping_from_lanes(
            network_lanes,
            int_id,
            unique_inbound_edges,
        )
        movement_names_by_node_pair = _build_movement_lookup_from_lanes(
            network_lanes,
            int_id,
        )
        UTDF_DIRS = phase_directions | lane_directions
        traffic_directions = {direction[:2] for direction in UTDF_DIRS}

        if len(unique_inbound_edges) != len(traffic_directions):
            if verbose:
                print(f"  :UTDF node {int_id} does not have the same "
                      f"number of inbounds with SUMO {int_id}")

        inbound_direction_mapping = dict(exact_mapping)
        unmapped_inbound_edges = [
            inbound_edge for inbound_edge in unique_inbound_edges
            if inbound_edge not in inbound_direction_mapping
        ]
        remaining_directions = traffic_directions - set(inbound_direction_mapping.values())
        flag = len(unmapped_inbound_edges) == 0

        if unmapped_inbound_edges and remaining_directions:
            flag, fallback_mapping = direction_mapping(sumo_net,
                                                       int_id,
                                                       unmapped_inbound_edges,
                                                       remaining_directions,
                                                       verbose=verbose)
            inbound_direction_mapping.update(fallback_mapping)

        if not flag:
            if verbose:
                print(f"  :UTDF node {int_id} map inbounds with SUMO {int_id} failed")

        for connection_index in sumo_net.sumo_signal_info[int_id].keys():
            sumo_movement = sumo_net.sumo_signal_info[int_id][connection_index]

            if ":" not in sumo_movement["fromEdge"]:
                if sumo_movement["fromEdge"] not in inbound_direction_mapping:
                    if verbose:
                        print(f"  :UTDF node {int_id} match inbound failed")
                    sumo_movement["synchro_dir"] = "STOP"
                    sumo_movement["signal_dir"] = "STOP"
                    continue

                sumo_movement["sumo_dir"] = sumo_movement["dir"]
                movement_name = _select_movement_name_for_sumo_connection(
                    movement_names_by_node_pair,
                    int_id,
                    sumo_movement,
                    inbound_direction_mapping[sumo_movement["fromEdge"]],
                )
                movement_info = _get_movement_info(
                    network_lanes,
                    int_id,
                    movement_name,
                )
                if _movement_is_inactive(movement_info):
                    sumo_movement["synchro_dir"] = "STOP"
                    sumo_movement["signal_dir"] = "STOP"
                    continue

                sumo_movement["synchro_dir"] = movement_name
                if _movement_is_uncontrolled(movement_info):
                    sumo_movement["uncontrolled"] = True
                elif _right_turn_has_channelized_control(movement_name, movement_info):
                    sumo_movement["uncontrolled"] = True
                elif _right_turn_allows_rtor(movement_name, movement_info):
                    sumo_movement["rtor_allowed"] = True

            else:
                process_pedestrian_crossing(int_id, sumo_net, sumo_movement, UTDF_DIRS)

    # UTDF coordinated/actuated control types include timing splits, but this
    # exporter does not build SUMO traffic-light detector calls for actuated
    # phase extension. Writing SUMO ``actuated`` programs would therefore run
    # most phases at MinGreen and severely under-serve high-volume movements.
    # Use fixed programs from the UTDF split timings unless detector-actuated
    # TLS logic is implemented explicitly.
    control_type = {"0": "static", "1": "static", "2": "static", "3": "static"}

    valid_ids = {}
    valid = 0

    def get_timeplan_value(controller_id: str, record_name: str,
                           default: str) -> str:
        """Read one Timeplans value for a controller, with a safe default."""
        if timeplans is None:
            return default

        matching_values = timeplans["DATA"][
            (timeplans["INTID"].map(_normalize_utdf_node_id) == controller_id)
            & (timeplans["RECORDNAME"] == record_name)
        ].tolist()
        if not matching_values:
            return default

        value = matching_values[0]
        if _is_blank(value):
            return default
        return str(value)

    def get_signal_type(controller_id: str) -> str:
        """Convert a UTDF Control Type value into a SUMO tlLogic type."""
        raw_control_type = get_timeplan_value(controller_id, "Control Type", "0")
        try:
            control_type_id = str(int(float(raw_control_type)))
        except ValueError:
            control_type_id = "0"
        return control_type.get(control_type_id, "static")

    for int_id in signalized_int_ids:
        if verbose:
            print(f"  :processing signal @ id: {int_id}")

        controller_id = signal_controller_by_node[int_id]
        cycle_length_text = get_timeplan_value(controller_id, "Cycle Length", "0")
        try:
            cycle_length = float(cycle_length_text)
        except ValueError:
            cycle_length = 0.0

        ret = create_SignalTimingPlan(
            utdf_signal[int_id],
            sumo_net.sumo_signal_info[int_id],
            verbose=verbose,
            cycle_length=cycle_length)
        linkDur = build_linkDuration(
            utdf_signal[int_id],
            sumo_net.sumo_signal_info[int_id])

        if ret:
            for i in sumo_net.sumo_signal_info[int_id]:
                if verbose:
                    print(f"  :{i} {sumo_net.sumo_signal_info[int_id][i]}")

            types = get_signal_type(controller_id)
            offsets = get_timeplan_value(controller_id, "Offset", "0")
            try:
                offset_seconds = float(offsets)
            except ValueError:
                offset_seconds = 0.0

            sumo_net.replace_tl_logic_xml(int_id, ret, linkDur, types, offset_seconds)
            valid_ids[int_id] = int_id
            valid += 1
    print(f"  :Total signal intersections: {len(signalized_int_ids)}"
          f", valid intersections: {valid}\n")

    # update sumo.net.xml
    sumo_net.write_xml()

    return True
