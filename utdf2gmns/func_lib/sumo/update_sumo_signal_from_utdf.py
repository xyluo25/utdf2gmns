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

    # get signal intersection ids from UTDF
    signalized_int_ids = list(set(utdf_dict.get("Timeplans")["INTID"].tolist()))

    # read sumo network
    sumo_net = ReadSUMO(sumo_net_xml)

    # parse signal intersection information
    utdf_signal = {}

    for int_id in signalized_int_ids:

        # in this case sumo id equal to UTDF signal intersection id
        int_id = str(int_id)

        utdf_signal[int_id] = parse_signal_control(df_phase=utdf_dict.get("Phases"),
                                                   df_lane=utdf_dict.get("Lanes"),
                                                   int_id=int_id)
        UTDF_DIRS = set(extract_dir_info(utdf_signal[int_id]))
        traffic_directions = set(map(lambda s: s[0:2], UTDF_DIRS))

        if verbose:
            print(f"\nIntersection id: {int_id} \nDirections: {UTDF_DIRS}\n")

        unique_inbound_edges = []
        for connection_index in sumo_net.sumo_signal_info[int_id].keys():
            sumo_movement = sumo_net.sumo_signal_info[int_id][connection_index]
            if ":" not in sumo_movement["fromEdge"] and sumo_movement["fromEdge"] not in unique_inbound_edges:
                unique_inbound_edges.append(sumo_movement["fromEdge"])

        if len(unique_inbound_edges) != len(traffic_directions):
            if verbose:
                print(f"  :UTDF node {int_id} does not have the same "
                      f"number of inbounds with SUMO {int_id}")

        flag, inbound_direction_mapping = direction_mapping(sumo_net,
                                                            int_id,
                                                            unique_inbound_edges,
                                                            traffic_directions,
                                                            verbose=verbose)

        if not flag:
            if verbose:
                print(f"  :UTDF node {int_id} map inbounds with SUMO {int_id} failed")

        for connection_index in sumo_net.sumo_signal_info[int_id].keys():
            sumo_movement = sumo_net.sumo_signal_info[int_id][connection_index]

            if ":" not in sumo_movement["fromEdge"]:
                if sumo_movement["fromEdge"] not in inbound_direction_mapping:
                    if verbose:
                        print(f"  :UTDF node {int_id} match inbound failed")
                    break
                if sumo_movement["dir"] == "s":
                    synchro_dir = "T"
                else:
                    synchro_dir = sumo_movement["dir"].upper()
                sumo_movement["dir"] = inbound_direction_mapping[sumo_movement["fromEdge"]] + synchro_dir

            else:
                process_pedestrian_crossing(int_id, sumo_net, sumo_movement, UTDF_DIRS)

    control_type = {"0": "static", "1": "actuated", "2": "actuated", "3": "actuated"}

    valid_ids = {}
    valid = 0

    for int_id in signalized_int_ids:
        if verbose:
            print(f"  :processing signal @ id: {int_id}")

        ret = create_SignalTimingPlan(
            utdf_signal[int_id],
            sumo_net.sumo_signal_info[int_id],
            verbose=verbose)
        linkDur = build_linkDuration(
            utdf_signal[int_id],
            sumo_net.sumo_signal_info[int_id])

        if ret:
            for i in sumo_net.sumo_signal_info[int_id]:
                if verbose:
                    print(f"  :{i} {sumo_net.sumo_signal_info[int_id][i]}")
            timeplans = utdf_dict.get("Timeplans")
            types = str(control_type[list(timeplans['DATA'][(timeplans['INTID'] == str(int_id)) & (
                timeplans['RECORDNAME'] == 'Control Type')])[0]])
            offsets = str(list(timeplans['DATA'][(timeplans['INTID'] == str(int_id)) & (
                timeplans['RECORDNAME'] == 'Offset')])[0])

            sumo_net.replace_tl_logic_xml(int_id, ret, linkDur, types, int(float(offsets)))
            valid_ids[int_id] = int_id
            valid += 1
    print(f"  :Total signal intersections: {len(signalized_int_ids)}"
          f", valid intersections: {valid}\n")

    # update sumo.net.xml
    sumo_net.write_xml()

    return True
