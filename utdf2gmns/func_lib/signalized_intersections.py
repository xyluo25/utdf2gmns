'''
##############################################################
# Created Date: Thursday, October 17th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''


import pandas as pd
from collections import OrderedDict


def parse_phase_signal(df_phase: pd.DataFrame, int_id: int) -> dict:
    """Extract signal data from the UTDF Phase data by intersection ID

    Args:
        df_Phase (pd.DataFrame): UTDF Phase data
        int_id (int): Intersection ID

    Returns:
        dict: {"D1"" {}, "D2": {}, "D3": {}}

    """
    # get dataframe of the intersection
    df_phase_id = df_phase[df_phase['INTID'] == str(int_id)]
    col_names = list(df_phase["RECORDNAME"].unique())

    if 'RECORDNAME' in df_phase_id:
        del df_phase_id['RECORDNAME']
    if 'INTID' in df_phase_id:
        del df_phase_id['INTID']

    phase_info = list(df_phase_id)
    result = {}
    for phs in phase_info:
        signal_data = list(df_phase[phs][(df_phase['RECORDNAME'].isin(col_names)) & (df_phase['INTID'] == str(int_id))])
        res = dict(zip(col_names, signal_data))

        # save the signal data
        if res["MinGreen"]:
            result[phs] = res

    # prepare brp info
    phs = result.keys()

    brp_phs_mapping = {result[i]['BRP']: i for i in phs}
    brp_phs_mapping = dict(OrderedDict(sorted(brp_phs_mapping.items())))

    brp = {}
    for brp_info, value in brp_phs_mapping.items():
        brp_info = str(brp_info)
        if not brp_info:
            continue

        info_0 = brp_info[0]
        info_1 = brp_info[1]

        if info_0 not in brp:
            brp[info_0] = {info_1: []}
        elif info_1 not in brp[info_0]:
            brp[info_0][info_1] = []

        brp[info_0][info_1].append(value)
    result['brp_info'] = brp

    return result


def parse_lane(df_lane: pd.DataFrame, int_id: int) -> dict:
    """Extract lane data from the UTDF Lane data by intersection ID

    Args:
        df_lane (pd.DataFrame): UTDF Lane data
        int_id (int): Intersection ID

    Returns:
        dict: {'D5': {'protected': ['NBL']}, 'D2': {'protected': ['NBT'], 'permitted': ['NBR']}, 'D1': {'protected': ['SBL']}, 'D6': {'protected': ['SBT'], 'permitted': ['SBR']}, 'D3': {'protected': ['EBL']}, 'D8': {'protected': ['EBT'], 'permitted': ['EBR']}, 'D7': {'protected': ['WBL']}, 'D4': {'protected': ['WBT'], 'permitted': ['WBR']}}

    """

    # prepare single lane dataframe for the intersection
    df_lane = df_lane[~df_lane['INTID'].isnull()]
    df_lane_id = df_lane[df_lane['INTID'] == str(int_id)]
    df_lane_id.index = df_lane_id['RECORDNAME']

    traffic_movement_data = {}
    inbound_nodes = {}
    need_lookup = []
    for traffic_movement in df_lane_id.columns:

        if traffic_movement in ['RECORDNAME', 'INTID', 'PED', 'HOLD']:
            continue

        if "Up Node" not in df_lane_id[traffic_movement]:
            continue

        val = df_lane_id[traffic_movement][['Up Node']]
        if not val.iloc[0]:
            continue

        up_node = int(df_lane_id[traffic_movement]['Up Node'])
        dest_node = int(df_lane_id[traffic_movement]['Dest Node'])

        traffic_movement_data[traffic_movement] = {
            "UpNode": up_node,
            "DestNode": dest_node,
            "Lanes": df_lane_id[traffic_movement]['Lanes'],
            "Protected": [],
            "Permitted": []
        }

        # Synchro may support up to 4 phases
        for i in range(1, 5):

            key = f'Phase{i}'
            if key in df_lane_id.index:
                val = df_lane_id[traffic_movement][[key]].iloc[0]
                if val and int(df_lane_id[traffic_movement][key]) > 0:
                    traffic_movement_data[traffic_movement]["Protected"].append(
                        f"D{int(df_lane_id[traffic_movement][key])}")

            key = f'PermPhase{i}'
            if key in df_lane_id.index:
                val = df_lane_id[traffic_movement][[key]].iloc[0]
                if val and int(df_lane_id[traffic_movement][key]) > 0:
                    traffic_movement_data[traffic_movement]["Permitted"].append(
                        f"D{int(df_lane_id[traffic_movement][key])}")

        len_protected = len(traffic_movement_data[traffic_movement]['Protected'])
        len_permitted = len(traffic_movement_data[traffic_movement]['Permitted'])
        if len_permitted + len_protected == 0:
            need_lookup.append([up_node, dest_node, traffic_movement])
        elif up_node in inbound_nodes:
            inbound_nodes[up_node].append(traffic_movement)

        else:
            inbound_nodes[up_node] = [traffic_movement]

    # Check if one way street
    total_lanes_per_bound = {}
    for movement, value in traffic_movement_data.items():
        bound = movement[:2]
        if bound not in total_lanes_per_bound:
            total_lanes_per_bound[bound] = int(
                traffic_movement_data[movement]["Lanes"])
        else:
            total_lanes_per_bound[bound] += int(value["Lanes"])

    phases = {}
    for pair in need_lookup:
        up_node = pair[0]
        dest_node = pair[1]
        movement = pair[2]
        if total_lanes_per_bound[movement[:2]] == 0:
            continue
        if (up_node in inbound_nodes):
            possible_list = inbound_nodes[up_node]
        elif (dest_node in inbound_nodes):
            possible_list = inbound_nodes[dest_node]
        else:
            print(f"did not found possible list for movement {movement} at node {int_id}")
            continue
        if len(possible_list) == 0:
            print(f"did not found possible list for movement {movement} at node {int_id}")
            continue

        type_ = 'Protected' if movement[-1] == 'T' else 'Permitted'
        if len(possible_list) == 1:
            traffic_movement_data[movement][type_] = traffic_movement_data[possible_list[0]]['Protected']
        else:
            through_movement = movement[:2] + 'T'
            if through_movement in possible_list:
                traffic_movement_data[movement][type_] = traffic_movement_data[through_movement]['Protected']
            else:
                traffic_movement_data[movement][type_] = traffic_movement_data[possible_list[0]]['Protected']
    phases = {}
    for bound, movement_data in traffic_movement_data.items():
        for phase in movement_data['Protected']:
            if phase not in phases:
                phases[phase] = {"protected": []}
            elif "protected" not in phases[phase]:
                phases[phase]["protected"] = []
            phases[phase]['protected'].append(bound)

        for phase in movement_data['Permitted']:
            if phase not in phases:
                phases[phase] = {"permitted": []}
            elif "permitted" not in phases[phase]:
                phases[phase]["permitted"] = []
            phases[phase]["permitted"].append(bound)
    return phases


def parse_signalized_intersection(df_phase: pd.DataFrame, df_lane: pd.DataFrame, int_id: int) -> dict:
    """Extract signalized intersection data from the UTDF Phase and Lane data by intersection ID

    Args:
        df_Phase (pd.DataFrame): UTDF Phase data
        df_Lane (pd.DataFrame): UTDF Lane data
        int_id (int): Intersection ID

    Returns:
        dict: {'D1': {'protected': ['SBL']},
        'D2': {'protected': ['NBT'], 'permitted': ['NBR']},
        'D3': {'protected': ['EBL']},
        'D4': {'protected': ['WBT'], 'permitted': ['WBR']},
        'D5': {'protected': ['NBL']},
        'D6': {'protected': ['SBT'], 'permitted': ['SBR']},
        'D7': {'protected': ['WBL']},
        'D8': {'protected': ['EBT'], 'permitted': ['EBR']}}
    """

    signal_int = parse_phase_signal(df_phase, int_id)
    phase_info = parse_lane(df_lane, int_id)

    phase_key = list(phase_info.keys())

    for phs in phase_key:
        for pro_per in list(phase_info[phs].keys()):
            signal_int[phs][pro_per] = phase_info[phs][pro_per]

    return signal_int
