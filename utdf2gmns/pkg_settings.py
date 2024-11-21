# -*- coding:utf-8 -*-
##############################################################
# Created Date: Friday, January 27th 2023
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################

utdf_categories = {
    "Network": "Network Settings",
    "Nodes": "Node Data",
    "Links": "Link Data",
    "Lanes": "Lane Group Data",
    "Timeplans": "Timing Plan Settings",
    "Phases": "Phasing Data"}

utdf_metadata = {
    "Network": """
        Metric: 0=feet, mph, 1=meters, km/h;
    """,
    "Nodes": """
        INTID: Intersection ID;
        Type: 0 for signalized intersection, 1 for external node, 2 for bend, 3 for unsignalized, 4 for roundabout;
        X, Y, Z: Coordinates of the node, Z is elevation;""",
    "Links": """
        INTID: Intersection ID;
        UPID: Upstream node ID;
        Lanes: Number of lanes, for bend or external;
        Distance: travel distance in feet;
        Time: Travel time;
        Speed: Travel speed, mph or km/h;
        Grade: Grade in percent;
        Median: Median width in feet;
        Offset: Offset of link to right of center line, normally zero;
        TWLTL: 1 indicates a TWLTL for link (visual Only);
        Crosswalk Width: Width of crosswalk at end of link. Also affects the radius of the curb and right turns;
        Mandatory and Positioning Distances: For lane change start points;
        Curve Pt X, Pt Y, Pt Z: Used to define a curve point;
            The other curve point is defined in the reverse link. Blank indicates a straight link;
        """,
    "Lanes": """
        INTID: Intersection ID;
        UPID: Upstream node ID;
        Dest Node: Destination node number for this movement;
        Lanes: For each lane group, enter the number of lanes. Shared lanes count as through lanes,
            unless there is no through movement, in which case LR lanes count as left lanes.
        Shared: Enter code for sharing of this lane with adjacent movements.
            This field specified which movements the through lanes are shared with.
            Enter 0, 1, 2, 3 for No-sharing, shared-with-left, shared-with-right, shared-with-both;
            This field is normally 0 for turning lane groups.
            if a left shares with left2 or u-turns, the sharing is coded as 1.
        Width: Enter the average lane width for the group in feet or meters. Decimal meters permitted.
        Storage: Enter the length of a turning bay if applicable.
            Leave this field blank for through lane groups or
            if the turning lane goes all the way back to the previous intersection.
        Taper: The value of the Storage taper length.
        StLanes: Enter the number of lanes in the storage bay.
            This can be more or less than the number of turning lanes, but must be at least 1.
        Grade: Write only, use the new links section.
        Speed: Write only, use the new links section.
        Phase1, Phase2, Phase3, Phase4: Each lane group can have four primary phases associated with them.
            Enter phases that give a green to this movement in these fields. Enter -1 for an uncontrolled movement.
        PermPhase1, ..., PermPhase4: Each lane group can have four permitted phases associated with them.
            With permitted phases, left turns must yield to oncoming traffic, right turns must yield to pedestrians.
        LostTime: Write only, use lost time adjustment.
        Lost Time Adjust: Combination of Startup Lost time minus Extension of Effective Green.
            Total Lost Time = Yellow + All-Red + Lost Time Adjust.
        IdealFlow: Ideal Saturated Flow Rate per lane. 1900 default.
        SatFlow: Saturated flow rate for protected movements. Normally calculated, * indicates overridden value.
        SatFlowPerm: Saturated flow rate for permitted movements. Normally calculated, * indicates overridden value.
        SatFlowFTOR: Saturated flow rate for RTOR(right turn on red) movements.
            Normally calculated, * indicates overridden value.
        Allow RTOR: Enter 1 to allow RTORs on this lane group, 0 to disallow.
        Volume: The volume table is the preferred method for storing volumes.
            This entry is provided to allow convenient transferring of all data.
        Peds: Number of pedestrians conflicting with the right turn movement.
        Bicycles: Number of bicycles conflicting with the right turn movement.
        PHF: Peak Hour Factor. The volume table is the preferred method for storing volumes.15-minute peak hour factor.
            This entry is provided to allow convenient transferring of all data.
        Growth: the percent growth rate applied to volumes. 100 by default.
        HeavyVehicles: The percent of trucks, busses, and RVs for each movement.
        BusStops: The number of bus stops per hours blocking traffic.
        Midblock: Percent of traffic originating from mid-block driveways.
        Distance: Write only, use the new links section.
        Travel Time: Write only, use the new links section.
        Right Channeled: if R and R2 movements exists, listed for R2 movement.
            Values are: 0=no, 1=yield, 2=free,3=stop, 4=signal.
        Right Radius: If right turn channeled, curb radius of right turn.
        Add Lanes: Number of add lanes after right turn channel.
        Alignment: Controls how add lanes align thru an intersection.
            0=align left, 1=align to right, 2=align left no adds, 3=align right no adds.
        Enter Blocked: 0 vehicles wait if no space in node. 1 vehicles do not make check.
        HeadwayFact: Headway factor.
        Turning Speed: The simulation turning speed.
        FirstDetect: Distance from the leading extension detector to stop bar in feet or meters.
            Leave blank if no detectors for lane group. Supplemented by actual detector information.
        LastDetect: Same definition s Ver6, supplemented by actual detector information.
        DetectPhase1, DetectPhase2, DetectPhase3, DetectPhase4: use extend phase.
        ExtendPhase: Detector calls go to this phase.
        SwitchPhase: Will set switch phase.
            Note that the extend phase will not get called when switch phase is green, per NTCIP specs.
        numDetects: Number of detectors rows.
        DetectSize1, DetectSize2, DetectSize3, DetectSize4, DetectSize5:
            Distance from detector to stop bar. Detector 1 is closest to stop bar. Size of detector longitudinally.
        DetectType1, DetectType2, DetectType3, DetectType4, DetectType5: Detector type, sum of these flags.
            only 1 and 2 are currently implemented in Synchro.
            1=call, 2=extend, 4=queue detector(set non-zero value for queue time), 8=count volume, 16=count occupancy,
            32=yellow lock, 64=red lock, 128=passage detector,
            Synchro currently assumes all detectors are presence. 256=added initial.
        DetectExtend1, DetectExtend2, DetectExtend3, DetectExtend4, DetectExtend5: Extend time for detector in seconds.
        DetectDelay1: Delay time, detector 1 only.""",
    "Timeplans": """
        Control Type: 0=pretimed, 1=actd uncoord, 2=semiact uncoord, 3=acted coordinated.
        Cycle Length: Cycle length in seconds.
        Lock Timings: 0=unlocked, 1=locked. Timings will still be read from Time Plan and Phasings section when locked.
        Referenced To: the part of phase to which offsets are referenced.
            0=refGreen, the last of the phases to turn green (TS1 style),
            1=refYellow, the first phase to turn yellow (170 style without rest in walk),
            2=refRed, the first phase to turn red (not used often),
            3=refFirstGreen, the first referenced phase to turn green(TS2 style),
            4=ref170, the beginning of flashing don't walk (170 style with in walk).
        Reference Phase: phase numbers offsets are referenced to. if tow phases are referenced,
            the phase for ring A is multiplied by 100, phase 2 and 6 are written 206.
        Offset: Offset in seconds. Offset is referenced as specified by Referenced to and Referenced Phase.
            On reading, the Start Times in Phasings section read after will override the offsets here.
            To read offsets, include a second TimePlan section with offset records only, after the Phasing section.
        Master: 0=normal, 1=master controller, master controller will keep offset at zero,
            only one master allowed per cycle length.
        Yield: 0=single, 1=flexible, 2=phase. Defined yield points for non-coordinated phases.
        Node0, Node1, Node2, Node3, Node4, Node5, Node6, Node7: Used to assign multiple nodes to one controller.
            If nodes 101 and 102 use the same controller,
            the timing plan and phasing data will only be included for INTID 101.
            The node records for INTID 101 will be: Node 0, 101, 101; Node 1, 101, 102; Node 2, 101, 0;
            A zero value indicates no more nodes.
            There will be no time plan and phasing records for node 102, they are defined by node 101. """,
    "Phases": """
        A phase is a timing unit that controls the operation of one or more movements.
        RECORDNAME: Name of the phase;
        INTID: Intersection ID;
        D1, D2, D3, D4, D5, D6, D7, D8: The phase number for each ring;
        BRP: Entry is for rings and barriers.
        MinGreen: Minimum green time (tenths of seconds);
        MaxGreen: Maximum time for the green phase (tenths of seconds);
        VehExt: This is the time the signal is helo green by each actuation.
            It is also the maximum gap when using a volume density controller (hundredths of seconds);
        TimeBeforeReduce: This is the time before gap reduction starts on volume density controllers (seconds);
        TimeToReduce: this is the amount of time to reduce the gap from VehExt to MinGap.
        MinGap: this is the minimum gap to achieve (hundredths of seconds);
        Yellow: Time each phase displays yellow(tenths of seconds);
            All-Red + Yellow must equal a whole number of seconds;
        AllRed: Time each phase displays all-red clearance before the next phase(tenths of seconds);
            All-Red + Yellow no longer need to equal to a whole number of seconds in Synchro;
        Recall: This field can have the following values:
            0=no recall, 1=minimum recall, 2=pedestrian recall, 3=maximum recall, 4=rest in walk.
            if recall is not zero, the phase will be serviced on every cycle for the minimum green time,
            walk+don't walk time, or maximum green time respectively.
        Walk: Time for Walk indication or 0 for no pedestrian phase (seconds);
        DontWalk: Time for the Flashing Don't Walk interval (seconds).
            Note that Flashing don't walk ends at the start of yellow time.
        PedCalls: This is the number of pedestrian calls hour received by this phase.
            Set this field to blank for no pedestrian phase.
            Set this field to zero or other number to activate a pedestrian phase.
            If PedCalls is not used, a 0 or blank in Don't Walk can be used to turn off the pedestrian phase.
        MinSplit: Minimum split is used by Synchro during split optimization.
        DualEntry: Can be set to Yes or No. Yes to have this phase appear when a phase is showing in another ring
            and no calls or recalls are present within this ring and barrier.
        InhabitMax: Can be set to Yes or No. (1=Yes, 0=No).
            Inhibit maximum termination is used to disable the maximum termination functions
            of all phases in the selected timing ring.
        Start: is the begin time referenced to the system clock.
        End: Is the end time of phase referenced to the system clock.
        Yield170: Is the phase yield or force off time, referenced to the system clock, beginning of yellow.
            It is referenced to the beginning of FDW if recall is set to CoordMax.
        LocalStart, LocalYield, LocalYield170:
            There are the same values as above except they are referenced to the local offset point.
        StartTime: is read and used to set offsets.
        ActGreen: is the actuated green time and is the average of the five percentiles used for HCM analysis.
            To get the Actuated Split, add the Yellow and All-Red time.
    """
}

utdf_link_column_names = {
    1: 'RECORDNAME',
    2: 'INTID',
    3: 'NB',
    4: 'SB',
    5: "EB",
    6: "WB",
    7: "NE",
    8: "NW",
    9: "SE",
    10: "SW"}

utdf_lane_column_names = {1: 'Up_Node',
                          2: 'Dest_Node',
                          3: 'Lanes',
                          4: 'Shared',
                          5: 'Width',
                          6: 'Storage',
                          7: 'Taper',
                          8: 'StLanes',
                          9: 'Grade',
                          10: 'Speed',
                          11: 'Phase1',
                          12: 'PermPhase1',
                          13: 'LostTime',
                          14: 'Lost_Time_Adjust',
                          15: 'IdealFlow',
                          16: 'SatFlow',
                          17: 'SatFlowPerm',
                          18: 'Allow_RTOR',
                          19: 'SatFlowRTOR',
                          20: 'Volume',
                          21: 'Peds',
                          22: 'Bicycles',
                          23: 'PHF',
                          24: 'Growth',
                          25: 'HeavyVehicles',
                          26: 'BusStops',
                          27: 'Midblock',
                          28: 'Distance',
                          29: 'TravelTime',
                          30: 'Right_Channeled',
                          31: 'Right_Radius',
                          32: 'Add_Lanes',
                          33: 'Alignment',
                          34: 'Enter',
                          35: 'Blocked',
                          36: 'HeadwayFact',
                          37: 'Turning_Speed',
                          38: 'FirstDetect',
                          39: 'LastDetect',
                          40: 'DetectPhase1',
                          41: 'DetectPhase2',
                          42: 'DetectPhase3',
                          43: 'DetectPhase4',
                          44: 'SwitchPhase',
                          45: 'numDetects',
                          46: 'DetectPos1',
                          47: 'DetectSize1',
                          48: 'DetectType1',
                          49: 'DetectExtend1',
                          50: 'DetectQueue1',
                          51: 'DetectDelay1',
                          52: 'DetectPos2',
                          53: 'DetectSize2',
                          54: 'DetectType2',
                          55: 'DetectExtend2',
                          56: 'Exit_Lanes',
                          57: 'CBD',
                          58: 'Lane_Group_Flow'}
