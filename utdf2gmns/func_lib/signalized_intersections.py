'''
##############################################################
# Created Date: Thursday, October 17th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''


import pandas as pd
from collections import OrderedDict


def parse_phase(df_phase: pd.DataFrame, int_id: int) -> dict:
    """Extract signal Phase data by intersection ID

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


def parse_lane(df_lane: pd.DataFrame, int_id: int, verbose: bool = False) -> dict:
    """Extract single lane data by intersection ID

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

        # skip the columns that are not traffic movements
        if traffic_movement in ['RECORDNAME', 'INTID', 'PED', 'HOLD']:
            continue

        # skip the traffic movements that do not have an up node
        if not df_lane_id[traffic_movement].loc['Up Node']:
            continue

        # collect the traffic movement data for the intersection
        traffic_movement_data[traffic_movement] = df_lane_id[traffic_movement].to_dict()
        traffic_movement_data[traffic_movement]["Protected"] = []
        traffic_movement_data[traffic_movement]["Permitted"] = []

        # Synchro may support up to 4 phases
        for i in range(1, 5):

            key = f'Phase{i}'
            if key in df_lane_id.index:
                phase_val = df_lane_id[traffic_movement].loc[key]
                if phase_val and phase_val != '-1':
                    traffic_movement_data[traffic_movement]["Protected"].append(
                        f"D{phase_val}")

            key = f'PermPhase{i}'
            if key in df_lane_id.index:
                perm_phase_val = df_lane_id[traffic_movement].loc[key]
                if perm_phase_val and perm_phase_val != '-1':
                    traffic_movement_data[traffic_movement]["Permitted"].append(
                        f"D{perm_phase_val}")

        len_protected = len(traffic_movement_data[traffic_movement]['Protected'])
        len_permitted = len(traffic_movement_data[traffic_movement]['Permitted'])

        up_node = traffic_movement_data[traffic_movement]['Up Node']
        dest_node = traffic_movement_data[traffic_movement]['Dest Node']
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

    # Look up the traffic movement data for the traffic movements that do not have an up node
    for pair in need_lookup:
        up_node, dest_node, movement = pair

        # skip if the movement is not in the traffic movement data
        if total_lanes_per_bound[movement[:2]] == 0:
            continue

        if (up_node in inbound_nodes):
            possible_list = inbound_nodes[up_node]
        elif (dest_node in inbound_nodes):
            possible_list = inbound_nodes[dest_node]
        else:
            if verbose:
                print(f"  :Info: did not found possible list for movement {movement} at node {int_id}")
            continue
        if len(possible_list) == 0:
            if verbose:
                print(f"  :Info: did not found possible list for movement {movement} at node {int_id}")
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

    traffic_movement_data['phases'] = phases

    return traffic_movement_data


def parse_timeplans(df_timeplans: pd.DataFrame, int_id: int) -> dict:
    """Extract signal Time plan data by intersection ID

    Args:
        df_timeplans (pd.DataFrame): UTDF Time plan data
        int_id (int): Intersection ID

    Returns:
        dict: the time plan data for the intersection
    """

    # prepare single dataframe for the intersection
    df_timeplans = df_timeplans[~df_timeplans['INTID'].isnull()]
    df_timeplans_id = df_timeplans[df_timeplans['INTID'] == str(int_id)]

    # prepare single timeplans for the intersection
    int_timeplans = {}
    for i in range(len(df_timeplans_id)):
        int_timeplans[df_timeplans_id.loc[i, "RECORDNAME"]] = df_timeplans_id.loc[i, "DATA"]
    return int_timeplans


def parse_signal_control(df_phase: pd.DataFrame, df_lane: pd.DataFrame, int_id: int) -> dict:
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

    int_phase = parse_phase(df_phase, int_id)
    int_lane = parse_lane(df_lane, int_id)
    int_lane_phase = int_lane['phases']

    phase_key = list(int_lane_phase.keys())
    for phs in phase_key:
        for pro_per in list(int_lane_phase[phs].keys()):
            try:
                int_phase[phs][pro_per] = int_lane_phase[phs][pro_per]
            except KeyError as e:
                print("  :Error: Intersection ID: ", int_id)
                print(e)

    return int_phase
