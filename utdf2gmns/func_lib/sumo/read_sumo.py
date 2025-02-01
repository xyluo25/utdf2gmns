'''
##############################################################
# Created Date: Sunday, December 22nd 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Ms. Yiran Zhang
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

import xml.etree.ElementTree as ET
import numpy as np
import io


class ReadSUMO:
    def __init__(self, net_filename: str):
        self._net_filename = net_filename
        self._tree = ET.parse(net_filename)
        self._root = self._tree.getroot()

        # parse the xml file
        self.__parse_sumo_xml()
        self.__parse_edges()

    def __parse_sumo_xml(self, sumo_ids_filter=None):

        # initialize signal info and inbound edges
        sumo_signal_info = {}
        inbound_edges = {}

        for connection in self._root.findall("connection"):
            # get the tlLogic_ids
            tlLogic_ids = connection.get("tl")

            if tlLogic_ids is None:
                continue

            if sumo_ids_filter is None or tlLogic_ids in sumo_ids_filter:
                if tlLogic_ids not in sumo_signal_info:
                    sumo_signal_info[tlLogic_ids] = {}
                connection_index = connection.get('linkIndex')
                if connection_index is None:
                    continue

                inbound_edge_id = connection.get('from')
                if (inbound_edge_id not in inbound_edges) and ':' not in inbound_edge_id:
                    inbound_edges[inbound_edge_id] = tlLogic_ids

                sumo_signal_info[tlLogic_ids][connection_index] = {}
                sumo_signal_info[tlLogic_ids][connection_index]['dir'] = connection.get('dir')
                sumo_signal_info[tlLogic_ids][connection_index]['fromEdge'] = connection.get('from')
                sumo_signal_info[tlLogic_ids][connection_index]['fromLane'] = connection.get('fromLane')
                sumo_signal_info[tlLogic_ids][connection_index]['toEdge'] = connection.get('to')
                sumo_signal_info[tlLogic_ids][connection_index]['toLane'] = connection.get('toLane')
        self.sumo_signal_info = sumo_signal_info
        self.inbound_edges = inbound_edges

    def __parse_edges(self):
        self.sumo_nbsw = {}
        self.crossing_dict = {}
        for edge in self._root.findall('edge'):
            edge_ids = edge.get('id')
            if edge_ids in self.inbound_edges.keys():
                for lane in edge.findall('lane'):
                    # selected the last two points
                    shape_info = lane.get('shape').split(' ')[-2:]
                    shape_slope = self.get_slope(shape_info)
                    self.sumo_nbsw[edge_ids] = shape_slope
                    break
            if edge.get('function') == 'crossing':
                self.crossing_dict[edge_ids] = edge.get('crossingEdges').split(' ')

    def get_slope(self, shape_info):
        x1, y1 = shape_info[0].split(',')
        x2, y2 = shape_info[1].split(',')
        if x1 == x2:
            slope = np.inf
        else:
            slope = (float(y2) - float(y1)) / (float(x2) - float(x1))
        return ([float(x2) - float(x1), float(y2) - float(y1), slope])

    def replace_tl_logic_xml(self, signal_id, ret, linkDur, types, offsets, program_id: int = 0):
        f = io.StringIO()
        f.writelines(
            f'\t<tlLogic id="{signal_id}" type="{types}" programID="{program_id}" offset="{offsets}">\n')

        if types == 'actuated':
            f.write('\t\t<param key="detector-gap" value="2.0"/>\n')
            f.write('\t\t<param key="file" value="NULL"/>\n')
            f.write('\t\t<param key="freq" value="300"/>\n')
            f.write('\t\t<param key="max-gap" value="3.0"/>\n')
            f.write('\t\t<param key="passing-time" value="2.0"/>\n')
            f.write('\t\t<param key="show-detectors" value="false"/>\n')
            f.write('\t\t<param key="vTypes" value=""/>\n')

        if ret:
            for r in ret:
                name = r.get("name", "")
                if isinstance(r['next'], int):
                    next_str = str(r['next'])
                else:
                    next_str = " ".join([str(s) for s in r['next']])
                if 'minDur' in r:
                    if types == 'actuated':
                        duration = r['minDur']
                    else:
                        duration = r['maxDur']

                    f.write(f'\t\t<phase name="{name}" duration="{duration:.1f}" maxDur="{r["maxDur"]:.1f}"'
                            f' minDur="{r["minDur"]:.1f}" next="{next_str}" state="{r["state"]}"/>\n')
                else:
                    f.write(f'\t\t<phase name="{name}" duration="{float(r["duration"]):.1f}"'
                            f' next="{next_str}" state="{r["state"]}"/>\n')

            for link in linkDur:
                f.write(
                    f'\t\t<param key="linkMinDur:{link}" value="{float(linkDur[link]["linkMaxDur"]):.1f}"/>\n')
                f.write(
                    f'\t\t<param key="linkMinDur:{link}" value="{float(linkDur[link]["linkMinDur"]):.1f}"/>\n')
        f.write('\t</tlLogic>\n')

        new_tlLogic_element = ET.fromstring(f.getvalue())
        
        for tlLogic in self._root.findall('tlLogic'):
            if tlLogic.get('id') == new_tlLogic_element.get('id'):
                tlLogic.clear()
                tlLogic.attrib.update(new_tlLogic_element.attrib)
                for phase in new_tlLogic_element:
                    tlLogic.append(phase)
        
        f.close()
        
    def write_xml(self):
        self._tree.write(self._net_filename, encoding='utf-8', xml_declaration=True)
