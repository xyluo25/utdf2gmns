'''
##############################################################
# Created Date: Friday, February 7th 2025
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET


def _strip_turn_bay_suffix(edge_id: str | None) -> str:
    """Return the original edge id when the connection starts from a turn-bay edge."""
    if not edge_id:
        return ""
    if edge_id.endswith("_bay"):
        return edge_id[:-4]
    return edge_id


def _reverse_edge_id(edge_id: str | None) -> str:
    """Return the reverse edge id for normal UTDF/SUMO edge ids such as 1_2."""
    base_edge_id = _strip_turn_bay_suffix(edge_id)
    edge_nodes = base_edge_id.split("_")
    if len(edge_nodes) != 2:
        return ""
    return f"{edge_nodes[1]}_{edge_nodes[0]}"


def _is_u_turn_connection(connection: ET.Element) -> bool:
    """Return True when a SUMO connection turns back to the reverse edge."""
    from_edge = connection.get("from")
    to_edge = connection.get("to")
    if not from_edge or not to_edge:
        return False
    if from_edge == to_edge:
        return True
    return _reverse_edge_id(from_edge) == _strip_turn_bay_suffix(to_edge)


def _connection_pair(connection: ET.Element) -> tuple[str, str]:
    """Return the edge pair used to compare net.xml and con.xml connections."""
    return connection.get("from", ""), connection.get("to", "")


def _internal_edge_id_from_via_lane(via_lane_id: str | None) -> str:
    """Return the internal edge id from a SUMO via lane id."""
    if not via_lane_id or not via_lane_id.startswith(":"):
        return ""
    if "_" not in via_lane_id:
        return via_lane_id
    return via_lane_id.rsplit("_", 1)[0]


def _get_default_connection_file(path_net: str) -> Path:
    """Return the plain connection file path generated beside a SUMO net file."""
    net_file_path = Path(path_net)
    net_file_name = net_file_path.name
    if not net_file_name.endswith(".net.xml"):
        return net_file_path.with_suffix(".con.xml")
    return net_file_path.with_name(net_file_name[:-len(".net.xml")] + ".con.xml")


def _get_netconvert_executable() -> str | None:
    """Return a usable netconvert executable from SUMO or the package bundle."""
    netconvert_executable = shutil.which("netconvert")
    if netconvert_executable:
        return netconvert_executable

    bundled_netconvert = Path(__file__).parents[2] / "engine" / "netconvert.exe"
    if bundled_netconvert.exists():
        return str(bundled_netconvert)

    return None


def _rebuild_sumo_net_file(path_net: str) -> bool:
    """Rewrite a compiled SUMO net file so internal connection data stays valid."""
    netconvert_executable = _get_netconvert_executable()
    if netconvert_executable is None:
        print("  :netconvert was not found, so the SUMO net file could not be rebuilt.")
        return False

    net_file_path = Path(path_net)
    rebuilt_net_file_path = net_file_path.with_name(
        f"{net_file_path.name}.rebuilt.tmp.xml"
    )
    result = subprocess.run([netconvert_executable,
                             f"--sumo-net-file={path_net}",
                             f"--output-file={rebuilt_net_file_path}",
                             "--no-warnings=true"],
                            capture_output=True,
                            text=True)
    if result.returncode != 0:
        if rebuilt_net_file_path.exists():
            rebuilt_net_file_path.unlink()
        print("  :netconvert failed while rebuilding the SUMO net file.")
        print(f" :{result.stderr}")
        return False

    rebuilt_net_file_path.replace(net_file_path)
    return True


def _read_explicit_connection_pairs(path_con: str | None) -> set[tuple[str, str]]:
    """Read edge-to-edge connections that were explicitly written to .con.xml."""
    if not path_con:
        return set()

    connection_file_path = Path(path_con)
    if not connection_file_path.exists():
        return set()

    connection_tree = ET.parse(connection_file_path)
    return {
        _connection_pair(connection)
        for connection in connection_tree.getroot().findall("connection")
    }


def _build_edge_node_lookup(root: ET.Element) -> tuple[dict[str, tuple[str, str]],
                                                       dict[str, set[str]]]:
    """Build edge endpoint and node outgoing-edge lookup tables from a SUMO net."""
    edge_nodes: dict[str, tuple[str, str]] = {}
    outgoing_edges_by_node: dict[str, set[str]] = {}

    for edge in root.findall("edge"):
        edge_id = edge.get("id")
        from_node = edge.get("from")
        to_node = edge.get("to")
        if not edge_id or not from_node or not to_node:
            continue
        if edge_id.startswith(":") or edge.get("function") == "internal":
            continue

        edge_nodes[edge_id] = (from_node, to_node)
        outgoing_edges_by_node.setdefault(from_node, set()).add(edge_id)

    return edge_nodes, outgoing_edges_by_node


def _is_dead_end_u_turn(connection: ET.Element,
                        edge_nodes: dict[str, tuple[str, str]],
                        outgoing_edges_by_node: dict[str, set[str]]) -> bool:
    """Return True when a U-turn is the only outgoing movement at the end node."""
    from_edge = connection.get("from")
    to_edge = connection.get("to")
    if not from_edge or not to_edge or from_edge not in edge_nodes:
        return False

    _, from_edge_to_node = edge_nodes[from_edge]
    outgoing_edge_ids = outgoing_edges_by_node.get(from_edge_to_node, set())
    to_edge_base_id = _strip_turn_bay_suffix(to_edge)
    has_u_turn_target = any(
        _strip_turn_bay_suffix(edge_id) == to_edge_base_id
        for edge_id in outgoing_edge_ids
    )
    if not has_u_turn_target:
        return False

    other_outgoing_edge_ids = {
        edge_id for edge_id in outgoing_edge_ids
        if _strip_turn_bay_suffix(edge_id) != to_edge_base_id
    }
    return len(other_outgoing_edge_ids) == 0


def _find_dead_end_u_turn_connections_to_remove(connections: list[ET.Element],
                                                explicit_connection_pairs: set[tuple[str, str]],
                                                edge_nodes: dict[str, tuple[str, str]],
                                                outgoing_edges_by_node: dict[str, set[str]]
                                                ) -> list[ET.Element]:
    """Find synthetic dead-end U-turn connections and their internal via chain."""
    connections_to_remove = []
    removed_connection_ids = set()
    pending_internal_edge_ids = set()
    processed_internal_edge_ids = set()

    for connection in connections:
        if not _is_u_turn_connection(connection):
            continue
        if _connection_pair(connection) in explicit_connection_pairs:
            continue
        if not _is_dead_end_u_turn(connection, edge_nodes, outgoing_edges_by_node):
            continue

        connections_to_remove.append(connection)
        removed_connection_ids.add(id(connection))
        internal_edge_id = _internal_edge_id_from_via_lane(connection.get("via"))
        if internal_edge_id:
            pending_internal_edge_ids.add(internal_edge_id)

    while pending_internal_edge_ids:
        internal_edge_id = sorted(pending_internal_edge_ids)[0]
        pending_internal_edge_ids.remove(internal_edge_id)
        if internal_edge_id in processed_internal_edge_ids:
            continue
        processed_internal_edge_ids.add(internal_edge_id)

        for connection in connections:
            if id(connection) in removed_connection_ids:
                continue
            if connection.get("from") != internal_edge_id:
                continue

            connections_to_remove.append(connection)
            removed_connection_ids.add(id(connection))
            next_internal_edge_id = _internal_edge_id_from_via_lane(connection.get("via"))
            if next_internal_edge_id:
                pending_internal_edge_ids.add(next_internal_edge_id)

    return connections_to_remove


def remove_sumo_U_turn(path_net: str, path_con: str | None = None,
                       rebuild_net: bool = True) -> bool:
    """Remove only non-explicit dead-end U-turns in the SUMO network.

    SUMO can add U-turn connections automatically at dead ends during
    ``netconvert``. Those synthetic U-turns should be removed. U-turns that are
    explicitly present in the generated ``.con.xml`` file come from UTDF lane
    movements and must be preserved.

    Args:
        path_net (str): Path to the SUMO ``.net.xml`` file.
        path_con (str | None): Optional path to the generated plain
            ``.con.xml`` file. If omitted, the function looks for a file with
            the same prefix beside ``path_net``.
        rebuild_net (bool): Whether to rewrite the compiled net with
            ``netconvert`` after deleting connections. This keeps SUMO's
            internal via-connection tables consistent.

    Returns:
        bool: True when the SUMO network file was updated successfully.
    """

    # check if path is a string and ends with .net.xml
    if not isinstance(path_net, str):
        raise ValueError("path_net must be a string")
    if not path_net.endswith(".net.xml"):
        raise ValueError("path_net must end with .net.xml")

    path_con = path_con or str(_get_default_connection_file(path_net))
    explicit_connection_pairs = _read_explicit_connection_pairs(path_con)

    # open the xml file and find all connections
    with open(path_net, 'r') as f:
        tree = ET.parse(f)

    root = tree.getroot()
    connections = root.findall("connection")
    edge_nodes, outgoing_edges_by_node = _build_edge_node_lookup(root)

    connections_to_remove = _find_dead_end_u_turn_connections_to_remove(
        connections,
        explicit_connection_pairs,
        edge_nodes,
        outgoing_edges_by_node,
    )
    for connection in connections_to_remove:
        root.remove(connection)

    # write the modified xml to the file
    tree.write(path_net, encoding='utf-8', xml_declaration=True)

    if rebuild_net:
        if not _rebuild_sumo_net_file(path_net):
            return False

    print(f"  :{len(connections_to_remove)} dead-end U-turn connections removed from the SUMO network")
    return True
