"""
##############################################################
# Created Date: Sunday, December 22nd 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Ms. Yiran Zhang
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
"""

opposite_ped = {
    "NB_PED": "SBT",
    "EB_PED": "WBT",
    "SB_PED": "NBT",
    "WB_PED": "EBT",
    "NE_PED": "SWT",
    "SE_PED": "NWT",
    "SW_PED": "NET",
    "NW_PED": "SET",
}


def findBestMatchDirection(direction: str, allDirection: str) -> str:
    """ Find the best match direction for the given direction"""

    bound = direction[0:2]
    turn = direction[2:]
    if direction in opposite_ped and opposite_ped[direction] in allDirection:
        return opposite_ped[direction]
    if bound + "T" in allDirection:
        return bound + "T"
    if "PED" not in turn and bound + "L" in allDirection:
        return bound + "L"
    if "PED" not in turn and bound + "R" in allDirection:
        return bound + "R"
    if "PED" in turn and "PED" in allDirection:
        return turn
    return "N/A"


def find_candidates(slope_info: str, all_traffic_bounds: set) -> set:
    """Find the candidate traffic bounds for the given slope information"""

    direction_candidates = {
        "delta_x_negative": ["SB", "SW", "WB", "NW", "NB"],
        "delta_x_positive": ["NB", "NE", "EB", "SE", "SB"],
        "delta_x_0": ["EB", "WB"],
        "delta_y_negative": ["EB", "SE", "SB", "SW", "WB"],
        "delta_y_positive": ["WB", "NW", "NB", "NE", "EB"],
        "delta_y_0": ["NB", "SB"],
        "abs_slope_larger_than_1": ["SE", "SB", "SW", "NE", "NB", "NW"],
        "abs_slope_smaller_than_1": ["SW", "WB", "NE", "NW", "EB", "SE"],
    }
    delta_x = slope_info[0]
    delta_y = slope_info[1]
    slope = slope_info[2]

    traffic_bounds = set(all_traffic_bounds)
    if delta_x < 0:
        traffic_bounds.intersection_update(direction_candidates["delta_x_negative"])
    elif delta_x > 0:
        traffic_bounds.intersection_update(direction_candidates["delta_x_positive"])
    else:
        traffic_bounds.intersection_update(direction_candidates["delta_x_0"])
    # print(traffic_bounds)
    if delta_y < 0:
        traffic_bounds.intersection_update(direction_candidates["delta_y_negative"])
    elif delta_y > 0:
        traffic_bounds.intersection_update(direction_candidates["delta_y_positive"])
    else:
        traffic_bounds.intersection_update(direction_candidates["delta_y_0"])
    # print(traffic_bounds)
    if abs(slope) < 1:
        traffic_bounds.intersection_update(
            direction_candidates["abs_slope_smaller_than_1"]
        )
    elif abs(slope) > 1:
        traffic_bounds.intersection_update(
            direction_candidates["abs_slope_larger_than_1"]
        )
    # print(traffic_bounds)
    return traffic_bounds


def direction_mapping(sumo_data,
                      sumo_id,
                      unique_inbound_edges,
                      all_traffic_bounds,
                      errors: list = [], verbose: bool = False) -> tuple:
    """Map the inbound edges to the traffic bounds"""

    if verbose:
        print(f"  :Int id: {sumo_id}\n  :Directions: {all_traffic_bounds}\n"
              f"  :Inbound edges: {unique_inbound_edges}")

    all_traffic_bounds = set(all_traffic_bounds)
    assigned_bounds = set()

    inbound_direction_mapping = {}
    candidate_mapping = {}
    for edge_id in unique_inbound_edges:
        if ":" in edge_id:
            continue
        slope_info = sumo_data.sumo_nbsw[edge_id]
        candidates = find_candidates(slope_info, all_traffic_bounds)

        if verbose:
            print(f"  :Edge id: {edge_id}\n  :Slope info: {slope_info}\n"
                  f"  :Candidates: {candidates}\n  :All traffic bounds: {all_traffic_bounds}")

        if len(candidates) == 0:
            if verbose:
                print(f"  :Intersection id {sumo_id}: match traffic bound failed for {edge_id}")

            errors.append(f"match traffic bound failed for {edge_id}")
            # exit(0)
            return False, {}

        if len(candidates) == 1:
            selected = candidates.pop()
            if selected in assigned_bounds:
                errors.append(f"{sumo_id}: Duplicate edges matches to the same movement {edge_id}")
                return False, {}

            assigned_bounds.add(selected)
            inbound_direction_mapping[edge_id] = selected
        else:
            candidate_mapping[edge_id] = candidates

    updated = True
    while updated and len(candidate_mapping) > 0:
        updated = False
        keys = set(candidate_mapping.keys())
        for edge_id in keys:
            candidate_mapping[edge_id] = candidate_mapping[edge_id] - assigned_bounds
            if len(candidate_mapping[edge_id]) == 1:
                selected = candidate_mapping[edge_id].pop()
                assigned_bounds.add(selected)
                inbound_direction_mapping[edge_id] = selected
                candidate_mapping.pop(edge_id)
                updated = True
                # print("updated", candidate_mapping, inbound_direction_mapping)

    # print(candidate_mapping, inbound_direction_mapping)
    if len(candidate_mapping) > 0:
        # there are multiple movements contains the same set of candidates, need to compare abs slope
        ordered_by_abs_slope = ["SB", "NB", "SW", "NE", "SE", "NW", "EB", "WB"]
        for bound in ordered_by_abs_slope:
            if bound in (all_traffic_bounds - assigned_bounds):
                max_abs_slope = 0
                candidate_pick = None
                for edge_id in candidate_mapping:
                    if bound in (candidate_mapping[edge_id] - assigned_bounds):
                        slope = sumo_data.sumo_nbsw[edge_id][2]
                        # print("compare", edge_id,
                        #       sumo_data.sumo_nbsw[edge_id],
                        #       candidate_mapping[edge_id])

                        if abs(slope) > max_abs_slope:
                            max_abs_slope = abs(slope)
                            candidate_pick = edge_id
                if candidate_pick is None:
                    return False, {}
                inbound_direction_mapping[candidate_pick] = bound
                candidate_mapping.pop(candidate_pick)
                assigned_bounds.add(candidate_pick)
        # print(inbound_direction_mapping)

    return (len(candidate_mapping) == 0, inbound_direction_mapping)


def getCombinationForBarrier(barrier, rings, ringIndex, currentComb, result):
    # print(barrier, ringIndex, len(barrier), currentComb, len(barrier)-ringIndex>=0)
    if len(rings) - ringIndex <= 0:
        result.append(list(currentComb))
        return

    key = rings[ringIndex]
    for i in barrier[key]:
        currentComb.append(str(i))
        # print('c', barrier, i, currentComb)
        getCombinationForBarrier(barrier, rings, ringIndex + 1, currentComb, result)
        currentComb.pop(len(currentComb) - 1)


def generateGreen(sumo_signal, protected, permitted, all_directions, duration, pedOnlyPhase, verbose: bool = False):
    value = ["r"] * len(sumo_signal)
    allValid = True
    pedStart = 0
    i = 0

    for j in sumo_signal:
        sumo_lane = sumo_signal[j]
        sumo_lane['synchro_dir'] = sumo_lane['dir']
        if "synchro_dir" not in sumo_lane:
            sumo_lane["signal_dir"] = "N/A"
            allValid = False
        elif "signal_dir" in sumo_lane and sumo_lane["signal_dir"] == "STOP":
            sumo_lane["signal_dir"] = "STOP"
        elif sumo_lane["synchro_dir"] in all_directions:
            sumo_lane["signal_dir"] = sumo_lane["synchro_dir"]
        elif "PED" in sumo_lane["synchro_dir"]:
            if len(sumo_lane["ped_allowed"]) == 0:
                if verbose:
                    print("Error For Ped:", sumo_lane)
        else:
            sumo_lane["signal_dir"] = findBestMatchDirection(
                sumo_lane["synchro_dir"], all_directions
            )
            if sumo_lane["signal_dir"] == "N/A":
                if verbose:
                    print("Error For signal_dir:", sumo_lane)
                allValid = False
        if (
            pedStart == 0
            and "synchro_dir" in sumo_lane
            and "PED" in sumo_lane["synchro_dir"]
        ):
            pedStart = i
        i += 1

    if allValid is False:
        return False
    ii = 0
    for j in sumo_signal:
        sumo_lane = sumo_signal[j]
        try:
            """if 'PED' in sumo_lane['synchro_dir']:
            if 'PED' in sumo_lane['ped_allowed']:
                print (sumo_lane, 'conflicts', protected.intersection(sumo_lane['ped_conflicts']))
                if len(protected.intersection(sumo_lane['ped_conflicts'])) == 0:
                    value[int(j)] = 'G'
            elif sumo_lane['ped_allowed'].intersection(protected) == protected:
                value[int(j)] = 'G'
            """
            if "STOP" in sumo_lane["synchro_dir"]:
                value[int(j)] = "s"
            elif "PED" in sumo_lane["synchro_dir"]:
                if pedOnlyPhase:
                    if "PED" in protected:
                        hasConflict = False
                        for c in sumo_lane["ped_conflicts"][0]:
                            if value[int(c)] == "G" or value[int(c)] == "g":
                                hasConflict = True
                        if not hasConflict:
                            for c in sumo_lane["ped_conflicts"][1]:
                                if value[int(c)] == "G":
                                    hasConflict = True
                        if not hasConflict:
                            value[int(j)] = "G"
                elif sumo_lane["ped_allowed"].intersection(protected) == protected:
                    hasConflict = False
                    for c in sumo_lane["ped_conflicts"][0]:
                        if value[int(c)] == "G" or value[int(c)] == "g":
                            hasConflict = True
                    if not hasConflict:
                        for c in sumo_lane["ped_conflicts"][1]:
                            if value[int(c)] == "G":
                                hasConflict = True
                    if not hasConflict:
                        value[int(j)] = "G"
            elif sumo_lane["signal_dir"] in protected:
                if (sumo_lane["synchro_dir"] == sumo_lane["signal_dir"] or sumo_lane["dir"] == "s"):
                    value[int(j)] = "G"
                else:
                    value[int(j)] = "g"
            # Permitted phases
            elif sumo_lane["signal_dir"] in permitted:
                value[int(j)] = "g"
            ii += 1
        except IndexError:
            pass

    duration["state"] = value
    duration["pedStart"] = pedStart
    return duration


def get_PhaseTiming(utdf_signal, sumo_signal, all_directions, phaseInfo, pedExclusive=False, verbose: bool = False):
    currentPhases = phaseInfo["phases"]
    # result = []
    # Generate Green Phase
    maxDur = 2147483647
    minDur = 2147483647
    protected_directions = set()
    permitted_directions = set()

    for phase in currentPhases:
        timings = utdf_signal[phase]
        minDur = min(minDur, float(timings["MinGreen"]))
        maxDur = min(maxDur, float(timings["MaxGreen"]))
        yellow = timings["Yellow"]
        allRed = timings["AllRed"]
        if "protected" in utdf_signal[phase]:
            protected_directions = protected_directions.union(
                utdf_signal[phase]["protected"]
            )
        if "permitted" in utdf_signal[phase]:
            permitted_directions = permitted_directions.union(
                utdf_signal[phase]["permitted"]
            )
    permitted_directions = permitted_directions.difference(protected_directions)

    return generateGreen(
        sumo_signal,
        protected_directions,
        permitted_directions,
        all_directions,
        {
            "minDur": minDur,
            "maxDur": maxDur,
            "yellow": yellow,
            "allRed": allRed,
            "name": f"({','.join(phaseInfo['phases'])})",
        },
        pedExclusive,
        verbose=verbose,
    )


def build_TransitionPhase(synchro_signal, greens, phases):
    # print(synchro_signal, phases)
    transitionPhases = []
    # nextMap = {}
    offset = len(phases)
    for i in range(len(phases)):
        current_green = greens[i]['state']
        phase = phases[i]
        # if 'pedStart' in phase and phase['pedStart'] > 0:
        #     end = phase['pedStart']
        # else:
        #     end = len(current_green)
        newNext = []
        for nextPhaseIndex in phase['next']:
            next_green = greens[nextPhaseIndex]['state']
            yellow = list(current_green)
            all_read = ['r'] * len(current_green)
            for si in range(len(current_green)):
                if current_green[si] == 's':
                    all_read[si] = 's'
                    yellow[si] = 's'

            hasCommonGreen = False
            hasDiff = False
            needYellow = False
            for j in range(len(next_green)):
                # print (current_green)
                if current_green[j] != next_green[j]:
                    hasDiff = True
                if current_green[j] == 'g' or current_green[j] == 'G':
                    if next_green[j] == 'r':
                        needYellow = True
                        yellow[j] = 'y'
                    if next_green[j] == 'g' or next_green[j] == 'G':
                        hasCommonGreen = True
            if not hasDiff:
                # print('Phase is the same', i, nextPhaseIndex)
                newNext.append(nextPhaseIndex)
                continue
            if not needYellow:
                newNext.append(nextPhaseIndex)
                continue
            newNext.append(offset)
            yellowPhase = {'name': f"{greens[i].get('name', '')}-{greens[nextPhaseIndex].get('name', '')}-Y",
                           'duration': greens[i]['yellow'], 'state': "".join(yellow)}
            if hasCommonGreen is False:
                yellowPhase['next'] = offset + 1
                transitionPhases.append(yellowPhase)
                redPhase = {'name': f"{greens[i].get('name', '')}-{greens[nextPhaseIndex].get('name', '')}-R",
                            'duration': greens[i]['allRed'], 'state': "".join(all_read), 'next': nextPhaseIndex}
                transitionPhases.append(redPhase)
                offset += 2
            else:
                yellowPhase['next'] = nextPhaseIndex
                transitionPhases.append(yellowPhase)
                offset += 1
        greens[i]['next'] = newNext
        greens[i]['state'] = "".join(greens[i]['state'])

    n = 0
    finalPhases = []
    for g in greens:
        finalPhases.append(g)
        n += 1
    for t in transitionPhases:
        finalPhases.append(t)
        n += 1
    return finalPhases


def build_linkDuration(utdf_signal, sumo_signal):
    linkDuration = {}
    for phase in utdf_signal:
        if phase == 'brp_info':
            continue

        index = 0
        for i in sumo_signal:
            sumo_lane = sumo_signal[i]
            # print('sumo_lane', sumo_lane)

            mask_protected = "protected" in utdf_signal[phase]
            mask_lane = "synchro_dir" in sumo_lane
            # print("protected", utdf_signal[phase])
            make_signal = sumo_lane.get("synchro_dir", None) in utdf_signal[phase].get("protected", [])

            if all([mask_protected, mask_lane, make_signal]):
                if index in linkDuration:
                    linkDuration[index]['linkMaxDur'] = max(
                        float(linkDuration[index]['linkMaxDur']),
                        float(utdf_signal[phase]['MaxGreen']))

                    linkDuration[index]['linkMinDur'] = min(
                        float(linkDuration[index]['linkMinDur']),
                        float(utdf_signal[phase]['MinGreen']))
                else:
                    linkDuration[index] = {}
                    linkDuration[index]['linkMaxDur'] = utdf_signal[phase]['MaxGreen']
                    linkDuration[index]['linkMinDur'] = utdf_signal[phase]['MinGreen']
                    linkDuration[index]['dir'] = sumo_lane['synchro_dir']
                    break
            index += 1
    return linkDuration


def extract_dir_info(utdf_signal):
    synchro_dir = []
    exclude_dir = ['PED', 'HOLD']
    # print('99999', synchro_signal)
    for phase in utdf_signal:
        if 'protected' in utdf_signal[phase]:
            direct = utdf_signal[phase]['protected']
            for i in direct:
                if i not in synchro_dir and i not in exclude_dir:
                    synchro_dir.append(i)
        if 'permitted' in utdf_signal[phase]:
            direct = utdf_signal[phase]['permitted']
            for i in direct:
                if i not in synchro_dir and i not in exclude_dir:
                    synchro_dir.append(i)

    return synchro_dir


def create_SignalTimingPlan(utdf_signal, sumo_signal, verbose=False):
    # print('create timing:', utdf_signal)
    all_directions = extract_dir_info(utdf_signal)
    phaseIndex = 0
    phaseQueue = []

    for barrierIndex in utdf_signal['brp_info']:
        barrierRings = utdf_signal['brp_info'][barrierIndex]
        offset = len(phaseQueue)
        position = 0
        combPos = []
        phaseName = []
        queue = []

        # print('phaseIndex', phaseIndex, barrierRings)
        for ringIndex in barrierRings:
            ring = barrierRings[ringIndex]
            phaseName.append(ring[position])
            combPos.append(position)
        queue.append(combPos)

        # print(queue, 'phases', phaseQueue)
        readIndex = 0
        position += 1
        phaseIndex += 1
        while readIndex < position:
            current = queue[readIndex]
            # currentPhaseName = phaseQueue[readIndex]
            nextPhase = []
            # print ('c', current)
            # print ('br', barrierRings.keys())
            brKeys = list(barrierRings)
            for i in range(len(current)):
                j = brKeys[i]
                # print(i,j, current[i], barrierRings[j], current[i]+1 < len(barrierRings[j]))
                if current[i] + 1 < len(barrierRings[j]):
                    nextPos = list(current)
                    nextPos[i] += 1
                    try:
                        findNext = queue.index(nextPos)
                        nextPhase.append(findNext + offset)
                    except ValueError:
                        queue.append(nextPos)
                        # nextPhaseName = list(currentPhaseName)
                        # nextPhaseName[i] = barrierRings[j][current[i]+1]
                        # phaseQueue.append(nextPhaseName)
                        nextPhase.append(phaseIndex)
                        position += 1
                        phaseIndex += 1

            readIndex += 1
            if len(nextPhase) == 0:
                # print (barrierIndex, len(utdf_signal['brp_info']))
                if barrierIndex == max(utdf_signal['brp_info'].keys()):
                    nextPhase.append(0)
                    # getPhaseTiming(utdf_signal, sumo_signal, all_directions,
                    # currentPhaseName, phaseQueue[0], allRed = False)
                else:
                    nextPhase.append(phaseIndex)
                    # getPhaseTiming(utdf_signal, sumo_signal, all_directions,
                    # currentPhaseName, phaseQueue[phaseIndex], allRed = False)

            currentName = []
            for c in range(len(current)):
                j = brKeys[c]
                name = barrierRings[j][current[c]]
                # print ('cc', current, c, j, name)
                currentName.append(name)
            phaseQueue.append({'phases': currentName, 'next': nextPhase})
            # print ('phase and next', currentName, nextPhase)
    # print (utdf_signal['brp_info'])

    # Check if PED exclusive phase exists
    pedExclusive = False
    for phase in phaseQueue:
        try:
            if len(phase['phases']) == 1 and utdf_signal[phase['phases'][0]]['protected'][0] == 'PED':
                pedExclusive = True
        except KeyError:
            pass

    greenPhases = []
    for phase in phaseQueue:
        ret = get_PhaseTiming(utdf_signal, sumo_signal,
                              all_directions, phase, pedExclusive, verbose=verbose)
        if not ret:
            if verbose:
                print('Error in phase', phase)
            return False
        else:
            greenPhases.append(ret)

    if verbose:
        print('  :green', greenPhases)
        print('  :phaseQueue', phaseQueue)
    return build_TransitionPhase(utdf_signal, greenPhases, phaseQueue)


def combine_bound_dir(bound, direction, allDirs):
    if direction.capitalize() == 'S':
        direction = 'T'
    elif direction == 'l' and 'L' in allDirs:
        direction = 'L2'
    elif direction == 'r' and 'R' in allDirs:
        direction = 'R2'
    else:
        direction = direction.capitalize()
    return (bound + direction)


sumo_dir_suffix_order = ['R2', 'R', 'T', 'L', 'L2']


def assign_dir2sumo(sumo_id, ordered_direction, sumo_signal_info, sumo2synchro):
    ordered_dir_dict = ordered_direction[sumo_id]
    sumo_dict = sumo_signal_info[sumo_id]
    error = []
    # check the number of directions in sumo
    edges_lst = []
    # get all sumo direction by fromEdge, to check if we have both 'l' and 'L'
    sumo_dir_by_edge = {}
    for index_num in sumo_dict:
        edge = sumo_dict[index_num]['fromEdge']
        # I revise this
        # if 'w' not in edge '''and 'signal_dir' not in sumo_dict[index_num]''':
        if 'w' not in edge and 'signal_dir' not in sumo_dict[index_num]:
            if edge not in edges_lst:
                edges_lst.append(edge)
                sumo_dir_by_edge[edge] = set()
            sumo_dir_by_edge[edge].add(sumo_dict[index_num]['dir'])

    # check if the # of bounds from synchro equals to SUMO
    # eg, if synchro: wb, nb, eb, the # of edge in sumo ideally = 3
    if len(edges_lst) != len(ordered_dir_dict.keys()):
        checked_id = {}
        checked_id['sumo_dir_num'] = len(edges_lst)
        checked_id['synchro_dir_num'] = len(ordered_dir_dict.keys())
        # print(edges_lst)
        # print(ordered_dir_dict)
        return (checked_id)
    else:
        dir_lst = list(ordered_dir_dict.keys())
        direction_in_sumo = []
        for index_num in sumo_dict:
            edges = sumo_dict[index_num]['fromEdge']
            # same here
            # if 'w' not in edges '''and 'signal_dir' not in sumo_dict[index_num]''':
            if 'w' not in edges and 'signal_dir' not in sumo_dict[index_num]:
                dir_index = edges_lst.index(sumo_dict[index_num]['fromEdge'])
                # print(dir_lst[dir_index])
                # print(sumo_dict[index_num]['fromEdge'], sumo_dict[index_num]['toEdge'], sumo_dict[index_num]['dir'])
                # print (sumo_dir_by_edge)
                all_sumo_dir_per_edge = sumo_dir_by_edge[sumo_dict[index_num]['fromEdge']]
                direct = combine_bound_dir(
                    dir_lst[dir_index], sumo_dict[index_num]['dir'], all_sumo_dir_per_edge)

                # check the direction
                # here if the direction matches, even l, R, T not in the direction
                # at all, we think the direction matahces
                if direct not in ordered_dir_dict[dir_lst[dir_index]]:
                    # start fuzzy mapping
                    if direct[0:3] in ordered_dir_dict[dir_lst[dir_index]]:
                        fuzzy_dir = direct[0:3]
                    elif direct + '2' in ordered_dir_dict[dir_lst[dir_index]]:
                        fuzzy_dir = direct + '2'
                    elif all([sumo_dict[index_num]['dir'] == 'L',
                              's' not in all_sumo_dir_per_edge,
                              direct[0:2] + 'T' in ordered_dir_dict[dir_lst[dir_index]]]):
                        fuzzy_dir = direct[0:2] + 'T'
                        error.append('\tPartial map to straight(%s->%s)' %
                                     (direct, fuzzy_dir))
                    elif all([sumo_dict[index_num]['dir'] == 'R',
                              's' not in all_sumo_dir_per_edge,
                              direct[0:2] + 'T' in ordered_dir_dict[dir_lst[dir_index]]]):
                        fuzzy_dir = direct[0:2] + 'T'
                        error.append('\tPartial map to straight(%s->%s)' %
                                     (direct, fuzzy_dir))
                    elif direct[2:3] == 'R':
                        fuzzy_dir = direct
                    else:
                        fuzzy_dir = direct
                        error.append('\tsumo direction %s (%s) not found in synchro, %s' % (
                            direct, sumo_dict[index_num]['dir'], str(all_sumo_dir_per_edge)))
                else:
                    fuzzy_dir = direct
                direction_in_sumo.append(fuzzy_dir)

            else:
                direction_in_sumo.append('PED')
        if (len(error) > 0):
            pass
            # print('Warning (%s:%s)' % (sumo_id, sumo2synchro[sumo_id]))
            # print('\n'.join(error))
            # print(ordered_dir_dict)
            # print('')
        return (direction_in_sumo)


def process_pedestrian_crossing(sumo_id, sumo_data, ped_edge, all_directions, errors=[]):
    crossedDirection = {
        'from': {'WB': 'NB',
                 'SB': 'WB',
                 'EB': 'SB',
                 'NB': 'EB',
                 'NW': 'NE',
                 'SW': 'NW',
                 'SE': 'SW',
                 'NE': 'SE'},
        'to': {'EBT': 'NB',
               'SBL': 'NB',
               'NBR': 'NB',
               'WBT': 'SB',
               'NBL': 'SB',
               'SBR': 'SB',
               'NBT': 'WB',
               'EBL': 'WB',
               'WBR': 'WB',
               'SBT': 'EB',
               'WBL': 'EB',
               'EBR': 'EB',
               'SWT': 'SE',
               'NWL': 'SE',
               'SER': 'SE',
               'NET': 'NW',
               'SEL': 'NW',
               'NWR': 'NW',
               'SET': 'NE',
               'SWL': 'NE',
               'NER': 'NE',
               'NWT': 'SW',
               'NEL': 'SW',
               'SWR': 'SW'}
    }

    junction_id = sumo_id
    crossing_dict = sumo_data.crossing_dict
    sumo_signal_info = sumo_data.sumo_signal_info
    if ped_edge['toEdge'] not in crossing_dict:
        return
    crossed_edges = crossing_dict[ped_edge['toEdge']]

    # print(value['toEdge'], crossing_dict[value['toEdge']][-1])
    '''
    found = False
    for j in sumo_signal_info[junction_id]:
        if sumo_signal_info[junction_id][j]['fromEdge'] == crossed_edges:
            searchDir = sumo_signal_info[junction_id][j]['synchro_dir'][:2]
            #print(searchDir)
            ped_dir = crossedDirection['from'][searchDir]
            #print('ped_dir', ped_dir)
            found = True
            break
    if found == False:
        for j in sumo_signal_info[junction_id]:
            if sumo_signal_info[junction_id][j]['toEdge'] == crossed_edges:
                searchDir = sumo_signal_info[junction_id][j]['synchro_dir']
                #print(searchDir)
                ped_dir = crossedDirection['to'][searchDir]
                #print('ped_dir', ped_dir)
                found = True
                break
    if found == False:
        errors.append('Cannot find crossing edges for node %s crossing'% junction_id, ped_edge)
    if found:
        ped_edge['synchro_dir']=ped_dir+'_PED'
   '''
    # found = False
    conflicts = set()
    conflict_from = set()
    conflict_to = set()
    for crossed_edge in crossed_edges:
        for j in sumo_signal_info[junction_id]:
            if all([sumo_signal_info[junction_id][j]['fromEdge'] == crossed_edge,
                    'synchro_dir' in sumo_signal_info[junction_id][j]]):
                conflicts.add(sumo_signal_info[junction_id][j]['synchro_dir'])
                conflict_from.add(j)
            if all([sumo_signal_info[junction_id][j]['toEdge'] == crossed_edge,
                    'synchro_dir' in sumo_signal_info[junction_id][j]]):
                conflicts.add(sumo_signal_info[junction_id][j]['synchro_dir'])
                conflict_to.add(j)
            # print('\t', crossed_edge, sumo_signal_info[junction_id][j])
    ped_edge['ped_allowed'] = all_directions - conflicts
    ped_edge['ped_conflicts'] = (conflict_from, conflict_to)
    ped_edge['synchro_dir'] = 'PED'
    # print('\n\t', conflicts, '\n')
