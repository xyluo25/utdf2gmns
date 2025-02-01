opposite_ped = {
    'NB_PED': 'SBT',
    'EB_PED': 'WBT',
    'SB_PED': 'NBT',
    'WB_PED': 'EBT',
    'NE_PED': 'SWT',
    'SE_PED': 'NWT',
    'SW_PED': 'NET',
    'NW_PED': 'SET'
}

def findBestMatchDirection(direction, allDirection):
    bound = direction[0:2]
    turn = direction[2:]
    if direction in opposite_ped and opposite_ped[direction] in allDirection:
        return opposite_ped[direction]
    if bound+'T' in allDirection:
        return bound+'T'
    if 'PED' not in turn and bound+'L' in allDirection:
        return bound+'L'
    if 'PED' not in turn and bound+'R' in allDirection:
        return bound+'R'
    if 'PED' in turn and 'PED' in allDirection:
        return turn
    return 'N/A'

    
    

def find_candidates(slope_info, all_traffic_bounds):    
    direction_candidates = {
       'delta_x_negative': ['SB', 'SW', 'WB', 'NW', 'NB'],
       'delta_x_positive': ['NB', 'NE', 'EB', 'SE', 'SB'],
       'delta_x_0': ['EB', 'WB'],
       'delta_y_negative': ['EB', 'SE', 'SB', 'SW', 'WB'],
       'delta_y_positive': ['WB', 'NW', 'NB', 'NE', 'EB'],
       'delta_y_0': ['NB', 'SB'],
       'abs_slope_larger_than_1': ['SE', 'SB', 'SW', 'NE', 'NB', 'NW'],
       'abs_slope_smaller_than_1': ['SW', 'WB', 'NE', 'NW', 'EB', 'SE']
    }

    
    delta_x = slope_info[0]
    delta_y = slope_info[1]
    slope = slope_info[2]
    
    traffic_bounds = set(all_traffic_bounds)
    if delta_x < 0:
        traffic_bounds.intersection_update(direction_candidates['delta_x_negative'])
    elif delta_x > 0:
        traffic_bounds.intersection_update(direction_candidates['delta_x_positive'])
    else:
        traffic_bounds.intersection_update(direction_candidates['delta_x_0'])
    print (traffic_bounds)
    if delta_y < 0:
        traffic_bounds.intersection_update(direction_candidates['delta_y_negative'])
    elif delta_y > 0:
        traffic_bounds.intersection_update(direction_candidates['delta_y_positive'])
    else:
        traffic_bounds.intersection_update(direction_candidates['delta_y_0'])
    print (traffic_bounds)    
    if abs(slope) < 1:
        traffic_bounds.intersection_update(direction_candidates['abs_slope_smaller_than_1'])
    elif abs(slope) > 1:
        traffic_bounds.intersection_update(direction_candidates['abs_slope_larger_than_1'])
    print (traffic_bounds)
    return traffic_bounds

def direction_mapping(sumo_data, sumo_id, unique_inbound_edges, all_traffic_bounds, errors):
    
    print ("direction", all_traffic_bounds, unique_inbound_edges)
    all_traffic_bounds = set(all_traffic_bounds)
    assigned_bounds = set()
    
    inbound_direction_mapping = {}
    candidate_mapping = {}
    for edge_id in unique_inbound_edges:
        if ':' in edge_id:
            continue
        slope_info = sumo_data.sumo_nbsw[edge_id]
        candidates = find_candidates(slope_info, all_traffic_bounds)
        print (edge_id, slope_info, candidates, all_traffic_bounds)
        if len(candidates) == 0:
            print(f"{sumo_id}: match traffic bound failed for {edge_id}")
            print(all_traffic_bounds)
            print (sumo_data.sumo_signal_info[sumo_id])
            errors.append(f"match traffic bound failed for {edge_id}")
            #exit(0)
            return False, {}
        if len(candidates) == 1:
            selected = candidates.pop()
            if (selected in assigned_bounds):
                errors.append(f"{sumo_id}: Duplicate edges matches to the same movement {edge_id}")
                return False, {}
            
            assigned_bounds.add(selected)
            inbound_direction_mapping[edge_id] = selected
        else:
            candidate_mapping[edge_id] = candidates
    
    print (f'fitted {sumo_id}', inbound_direction_mapping)
    print (f'candidates {sumo_id}', candidate_mapping)
    updated = True
    while updated and len(candidate_mapping) > 0:
        updated = False
        keys = set(candidate_mapping.keys())
        for edge_id in keys:
            candidate_mapping[edge_id] = (candidate_mapping[edge_id] - assigned_bounds)
            if len(candidate_mapping[edge_id]) == 1:
                selected = candidate_mapping[edge_id].pop()
                assigned_bounds.add(selected)
                inbound_direction_mapping[edge_id] = selected
                candidate_mapping.pop(edge_id)
                updated = True
                print ('updated', candidate_mapping, inbound_direction_mapping)

    print (candidate_mapping, inbound_direction_mapping)
    if len(candidate_mapping) > 0:
        # there are multiple movements contains the same set of candidates, need to compare abs slope
        ordered_by_abs_slope = ['SB', 'NB', 'SW', 'NE', 'SE', 'NW', 'EB', 'WB']
        for bound in ordered_by_abs_slope:
            if bound in (all_traffic_bounds-assigned_bounds):
                max_abs_slope = 0
                candidate_pick = None
                for edge_id in candidate_mapping:
                    if bound in (candidate_mapping[edge_id] - assigned_bounds):
                        slope = sumo_data.sumo_nbsw[edge_id][2]
                        print ("compare", edge_id, sumo_data.sumo_nbsw[edge_id], candidate_mapping[edge_id])
                        if abs(slope) > max_abs_slope:
                            max_abs_slope = abs(slope)
                            candidate_pick = edge_id
                if (candidate_pick == None):
                    return False, {}
                inbound_direction_mapping[candidate_pick] = bound
                candidate_mapping.pop(candidate_pick)
                assigned_bounds.add(candidate_pick)
        print (inbound_direction_mapping)

    return len(candidate_mapping) == 0, inbound_direction_mapping
    
def get_start_dir_deprecated(slope_info, all_synchro_dirs):

    delta_x = slope_info[0]
    delta_y = slope_info[1]
    slope = slope_info[2]
    if abs(slope) > 1:
        if delta_y < 0:
            if 'SB' in all_synchro_dirs:
                return('SB')
            elif 'SW' in all_synchro_dirs:
                return('SW')
            elif 'SE' in all_synchro_dirs:
                return('SE')                
            else:
                #return possible direction
                return('p_SB')
        else:
            if 'NW' in all_synchro_dirs:
                return('NW')
            elif 'NB' in all_synchro_dirs:
                return('NB')
            elif 'NE' in all_synchro_dirs:
                return('NE')
            else:
                return('p_NB')
    else:
        if delta_x < 0:
            if 'SW' in all_synchro_dirs:
                return('SW')
            elif 'WB' in all_synchro_dirs:
                return('WB')
            elif 'NE' in all_synchro_dirs:
                return('NE')
            else:
                return('p_WB')
        else:
            if 'NW' in all_synchro_dirs:
                return('NW')
            elif 'EB' in all_synchro_dirs:
                return('EB')
            elif 'SE' in all_synchro_dirs:
                return('SE')
            else:
                return('p_EB')
           
def getCombinationForBarrier(barrier, rings, ringIndex, currentComb, result):
    #print(barrier, ringIndex, len(barrier), currentComb, len(barrier)-ringIndex>=0)
    if len(rings)-ringIndex<=0:
        result.append(list(currentComb))
        
        return
    key = rings[ringIndex]
    for i in barrier[key]:
        currentComb.append(str(i))
        #print('c', barrier, i, currentComb)
        getCombinationForBarrier(barrier, rings, ringIndex+1, currentComb, result)
        currentComb.pop(len(currentComb)-1)

def generateGreen(sumo_signal, protected, permitted, all_directions, duration, pedOnlyPhase):
    value = ['r']* len(sumo_signal)
    result = []
    allValid = True
    pedStart = 0
    i = 0
    
    
    for j in sumo_signal:
        sumo_lane = sumo_signal[j]
        if 'synchro_dir' not in sumo_lane:
            sumo_lane['signal_dir'] = 'N/A'
            print(sumo_lane)
            allValid = False
        elif 'signal_dir' in sumo_lane and sumo_lane['signal_dir'] == 'STOP':
            sumo_lane['signal_dir'] = 'STOP'
        elif sumo_lane['synchro_dir'] in all_directions:
            sumo_lane['signal_dir'] = sumo_lane['synchro_dir']
        elif 'PED' in sumo_lane['synchro_dir']:
            if len(sumo_lane['ped_allowed']) == 0:
                print ('Error For Ped:', sumo_lane);
                #allValid = False
            #sumo_lane['signal_dir'] = 'PED'
        else:
            sumo_lane['signal_dir'] = findBestMatchDirection(sumo_lane['synchro_dir'], all_directions)
            if sumo_lane['signal_dir'] == 'N/A':
                print ('Error For signal_dir:', sumo_lane);
                allValid = False
        if pedStart == 0 and 'synchro_dir' in sumo_lane and 'PED' in sumo_lane['synchro_dir']:
            pedStart = i
        i += 1
        #print (j, sumo_signal)
    
    if allValid == False:
        print (sumo_signal)
        print ('Not Valid', sumo_lane, all_directions)
        print ('\r\n')
        return False;
    ii = 0
    for j in sumo_signal:    
        sumo_lane = sumo_signal[j]
        try:
            comment = '''if 'PED' in sumo_lane['synchro_dir']:
                if 'PED' in sumo_lane['ped_allowed']:
                    print (sumo_lane, 'conflicts', protected.intersection(sumo_lane['ped_conflicts']))
                    if len(protected.intersection(sumo_lane['ped_conflicts'])) == 0:
                        value[int(j)] = 'G'
                elif sumo_lane['ped_allowed'].intersection(protected) == protected:
                    value[int(j)] = 'G'
                    '''
            if 'STOP' in sumo_lane['synchro_dir']:
                value[int(j)] = 's'
            elif 'PED' in sumo_lane['synchro_dir']:
                if pedOnlyPhase:
                    if 'PED' in protected:
                        hasConflict = False
                        for c in sumo_lane['ped_conflicts'][0]:
                            if value[int(c)] == 'G' or value[int(c)] == 'g':
                                hasConflict = True
                        if not hasConflict:
                            for c in sumo_lane['ped_conflicts'][1]:
                                if value[int(c)] == 'G':
                                    hasConflict = True                             
                        if not hasConflict:
                            value[int(j)] = 'G'                    
                elif sumo_lane['ped_allowed'].intersection(protected) == protected:
                    hasConflict = False
                    for c in sumo_lane['ped_conflicts'][0]:
                        if value[int(c)] == 'G' or value[int(c)] == 'g':
                            hasConflict = True
                    if not hasConflict:
                        for c in sumo_lane['ped_conflicts'][1]:
                            if value[int(c)] == 'G':
                                hasConflict = True                             
                    if not hasConflict:
                        value[int(j)] = 'G' 
            elif sumo_lane['signal_dir'] in protected:
                if(sumo_lane['synchro_dir'] == sumo_lane['signal_dir'] or sumo_lane['dir'] == 's'):
                    value[int(j)] = 'G'
                else:
                    value[int(j)] = 'g'
            # Permitted phases
            elif sumo_lane['signal_dir'] in permitted:
                value[int(j)] = 'g'
            ii += 1
            #print (sumo_lane['synchro_dir'], value[int(j)])
        except IndexError:
            #print(synchro2sumo[i])
            pass
    
    duration['state'] = value
    duration['pedStart'] = pedStart
    return duration

def getPhaseTiming(synchro_signal, sumo_signal, all_directions, phaseInfo, pedExclusive = False):
    currentPhases = phaseInfo['phases']
    result = []
    # Generate Green Phase
    maxDur = 2147483647
    minDur = 2147483647
    protected_directions = set()
    permitted_directions = set()
    
    for phase in currentPhases:
        timings = synchro_signal[phase]
        minDur = min(minDur, timings['MinGreen'])
        maxDur = min(maxDur, timings['MaxGreen'])
        yellow = timings['Yellow']
        allRed = timings['AllRed']
        if 'protected' in synchro_signal[phase]:
            protected_directions = protected_directions.union(synchro_signal[phase]['protected'])
        if 'permitted' in synchro_signal[phase]:
            permitted_directions = permitted_directions.union(synchro_signal[phase]['permitted'])
    permitted_directions = permitted_directions.difference(protected_directions)
    print ("\t", phaseInfo, protected_directions, permitted_directions)
    return generateGreen(sumo_signal, 
                  protected_directions, 
                  permitted_directions, 
                  all_directions,
                  {'minDur': minDur, 'maxDur': maxDur, 'yellow': yellow, 'allRed': allRed, 'name': f"({','.join(phaseInfo['phases'])})"}, pedExclusive)

def buildTransitionPhase(synchro_signal, greens, phases):
    #print(synchro_signal, phases)
    transitionPhases = []
    nextMap = {}
    offset = len(phases)
    for i in range(len(phases)):
        current_green = greens[i]['state']
        phase = phases[i]
        if 'pedStart' in phase and phase['pedStart'] > 0:
            end = phase['pedStart']
        else:
            end = len(current_green)
        newNext = []
        for nextPhaseIndex in phase['next']:
            next_green = greens[nextPhaseIndex]['state']
            yellow = list(current_green)
            all_read = ['r'] * len(current_green)
            for si in range(len(current_green)):
                if current_green[si] == 's':
                    all_read[si] = 's'
                    yellow[si] = 's'

            hasCommonGreen = False;
            hasDiff = False;
            needYellow = False
            for j in range(len(next_green)):
                #print (current_green)
                if current_green[j] != next_green[j]:
                    hasDiff = True
                if current_green[j] == 'g' or current_green[j] == 'G':
                    if next_green[j] == 'r':
                        needYellow = True
                        yellow[j] = 'y'
                    if next_green[j] == 'g' or next_green[j] == 'G':
                        hasCommonGreen = True
            if not hasDiff:
                print ('Phase is the same', i, nextPhaseIndex)
                newNext.append(nextPhaseIndex)
                continue
            if not needYellow:
                newNext.append(nextPhaseIndex)
                continue
            newNext.append(offset)
            yellowPhase = {'name': f"{greens[i].get('name', '')}-{greens[nextPhaseIndex].get('name', '')}-Y", 'duration':  greens[i]['yellow'], 'state': "".join(yellow)}
            if hasCommonGreen == False:
                yellowPhase['next'] = offset + 1
                transitionPhases.append(yellowPhase)
                redPhase = {'name': f"{greens[i].get('name', '')}-{greens[nextPhaseIndex].get('name', '')}-R", 'duration':  greens[i]['allRed'], 'state': "".join(all_read), 'next': nextPhaseIndex}
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
        n+=1
    for t in transitionPhases:
        finalPhases.append(t)
        n+=1
    return finalPhases

def buildlinkDuration(synchro_signal, sumo_signal):
    linkDuration = {}
    for phase in synchro_signal:
        if phase == 'brp_info':
            continue
        index = 0
        for i in sumo_signal:
            sumo_lane = sumo_signal[i]
            
            if 'protected' in synchro_signal[phase] and ('synchro_dir' in sumo_lane) and sumo_lane['synchro_dir'] in synchro_signal[phase]['protected']:
                #print (synchro_signal[phase]['protected'], sumo_lane['synchro_dir'])
                if index in linkDuration:
                    linkDuration[index]['linkMaxDur'] = max(linkDuration[index]['linkMaxDur'], synchro_signal[phase]['MaxGreen'])
                    linkDuration[index]['linkMinDur'] = min(linkDuration[index]['linkMinDur'], synchro_signal[phase]['MinGreen'])
                else:
                    linkDuration[index] = {}
                    linkDuration[index]['linkMaxDur'] = synchro_signal[phase]['MaxGreen']
                    linkDuration[index]['linkMinDur'] = synchro_signal[phase]['MinGreen']
                    linkDuration[index]['dir'] =  sumo_lane['synchro_dir']
                    break
            index+=1
    return linkDuration

def extract_dir_info(synchro_signal):
    synchrodir = []
    exclude_dir = ['PED','HOLD']
    print ('99999', synchro_signal)
    for phase in synchro_signal:
        if 'protected' in synchro_signal[phase]:
            direct = synchro_signal[phase]['protected']
            for i in direct:
                if i not in synchrodir and i not in exclude_dir:
                    synchrodir.append(i)
        if 'permitted' in synchro_signal[phase]:
            direct = synchro_signal[phase]['permitted']
            for i in direct:
                if i not in synchrodir and i not in exclude_dir:
                    synchrodir.append(i)
    
    return(synchrodir)      
    
def createSignalTimingPlan(synchro_signal, sumo_signal):
    print ('create timing:', synchro_signal)
    all_directions = extract_dir_info(synchro_signal)
    phaseIndex = 0
    phaseQueue = []
    
    for barrierIndex in synchro_signal['brp_info']:
        barrierRings = synchro_signal['brp_info'][barrierIndex]
        offset = len(phaseQueue)
        position = 0
        combPos = []
        phaseName = []
        queue = []
        
        print ('phaseIndex', phaseIndex, barrierRings)
        for ringIndex in barrierRings:
            ring = barrierRings[ringIndex]
            phaseName.append(ring[position])
            combPos.append(position)        
        queue.append(combPos)
        
        print (queue, 'phases', phaseQueue)
        readIndex = 0
        position += 1
        phaseIndex += 1
        while readIndex < position:
            current = queue[readIndex]
            #currentPhaseName = phaseQueue[readIndex]
            nextPhase = []
            #print ('c', current)
            #print ('br', barrierRings.keys())
            brKeys = list(barrierRings)
            for i in range(len(current)):
                j = brKeys[i]
                #print(i,j, current[i], barrierRings[j], current[i]+1 < len(barrierRings[j]))
                if current[i]+1 < len(barrierRings[j]):
                    nextPos = list(current)
                    nextPos[i] += 1
                    try:
                        findNext = queue.index(nextPos)
                        nextPhase.append(findNext + offset)
                    except ValueError:
                        queue.append(nextPos)
                        #nextPhaseName = list(currentPhaseName)
                        #nextPhaseName[i] = barrierRings[j][current[i]+1]
                        #phaseQueue.append(nextPhaseName)
                        nextPhase.append(phaseIndex)
                        position += 1
                        phaseIndex += 1
                        
            readIndex +=1
            if len(nextPhase) == 0:
                # print (barrierIndex, len(synchro_signal['brp_info']))
                if barrierIndex == max(synchro_signal['brp_info'].keys()):
                    nextPhase.append(0)
                    #getPhaseTiming(synchro_signal, sumo_signal, all_directions, currentPhaseName, phaseQueue[0], allRed = False)
                else:
                    nextPhase.append(phaseIndex)
                    #print (phaseIndex, phaseQueue)
                    #getPhaseTiming(synchro_signal, sumo_signal, all_directions, currentPhaseName, phaseQueue[phaseIndex], allRed = False)
            
            currentName = []
            for c in range(len(current)):
                j = brKeys[c]
                name = barrierRings[j][current[c]]
                #print ('cc', current, c, j, name)
                currentName.append(name)
            phaseQueue.append({'phases': currentName, 'next': nextPhase})
            #print ('phase and next', currentName, nextPhase)
    #print (synchro_signal['brp_info'])
    
    # Check if PED exclusive phase exists
    pedExclusive = False
    for phase in phaseQueue:
        try:
            if len(phase['phases']) == 1 and synchro_signal[phase['phases'][0]]['protected'][0] == 'PED':
                pedExclusive = True
        except KeyError:
            pass
    
    greenPhases = []
    for phase in phaseQueue:
        ret = getPhaseTiming(synchro_signal, sumo_signal, all_directions, phase, pedExclusive)
        if not ret:
            return False
        else:
            greenPhases.append(ret)
            
    #print('green', greenPhases)
    return buildTransitionPhase(synchro_signal, greenPhases, phaseQueue)
    #return True


#print(id, ret)

def combine_bound_dir(bound, direction, allDirs):
    if direction.capitalize() == 'S':
        direction = 'T'
    elif direction == 'l' and 'L' in allDirs:
        direction = 'L2'
    elif direction == 'r' and 'R' in allDirs:
        direction = 'R2'
    else:
        direction = direction.capitalize()
    return(bound+direction)

sumo_dir_suffix_order = ['R2', 'R', 'T', 'L', 'L2']

def process_pedestrian_crossing(sumo_id, sumo_data, ped_edge, all_directions, errors = []):
    crossedDirection = {
        'from': {
            'WB': 'NB',
            'SB': 'WB',
            'EB': 'SB',
            'NB': 'EB',
            'NW': 'NE',
            'SW': 'NW',
            'SE': 'SW',
            'NE': 'SE',
            'NW': 'NE'
        },
        'to': {
            'EBT': 'NB',
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
            'SWR': 'SW'            
        }
    }     

    junction_id = sumo_id
    crossing_dict = sumo_data.crossing_dict
    sumo_signal_info = sumo_data.sumo_signal_info
    if not ped_edge['toEdge'] in crossing_dict:
        return
    crossed_edges = crossing_dict[ped_edge['toEdge']]
    
    #print(value['toEdge'], crossing_dict[value['toEdge']][-1])
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
    found = False
    conflicts = set()
    conflict_from = set()
    conflict_to = set()
    for crossed_edge in crossed_edges:
        for j in sumo_signal_info[junction_id]:
            if sumo_signal_info[junction_id][j]['fromEdge'] == crossed_edge and 'synchro_dir' in sumo_signal_info[junction_id][j]:
                conflicts.add(sumo_signal_info[junction_id][j]['synchro_dir'])
                conflict_from.add(j)
            if sumo_signal_info[junction_id][j]['toEdge'] == crossed_edge and 'synchro_dir' in sumo_signal_info[junction_id][j]:
                conflicts.add(sumo_signal_info[junction_id][j]['synchro_dir'])
                conflict_to.add(j)
            print ('\t', crossed_edge,  sumo_signal_info[junction_id][j])
    ped_edge['ped_allowed'] = all_directions-conflicts
    ped_edge['ped_conflicts'] = (conflict_from, conflict_to)
    ped_edge['synchro_dir'] = 'PED'
    print ('\n\t', conflicts, '\n')
