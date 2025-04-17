# -*- coding:utf-8 -*-
##############################################################
# Created Date: Friday, January 27th 2023
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################

import os
import json
from pathlib import Path
import subprocess
import pandas as pd

# import utility functions from pyufunc
import pyufunc as pf

from utdf2gmns.util_lib.pkg_utils import time_unit_converter, time_str_to_seconds

# For deployment
from utdf2gmns.func_lib.utdf.geocoding_intersection import generate_intersection_coordinates
from utdf2gmns.func_lib.utdf.read_utdf import (generate_intersection_from_Links, read_UTDF)
from utdf2gmns.func_lib.utdf.cvt_utdf_lane_df_to_dict import cvt_lane_df_to_dict

from utdf2gmns.func_lib.gmns.geocoding_Nodes import update_node_from_one_intersection
from utdf2gmns.func_lib.gmns.geocoding_Links import (generate_links,
                                                     generate_links_polygon,
                                                     cvt_link_df_to_dict)
from utdf2gmns.func_lib.gmns.sigma_x_process_signal_intersection import cvt_utdf_to_signal_intersection

# SUMO related functions
from utdf2gmns.func_lib.sumo.signal_intersections import parse_signal_control
from utdf2gmns.func_lib.sumo._update_sumo_signal_from_utdf import update_sumo_signal_from_utdf
from utdf2gmns.func_lib.sumo._remove_u_turn import remove_sumo_U_turn
from utdf2gmns.func_lib.sumo.gmns2sumo import (generate_sumo_nod_xml,
                                               update_sumo_nod_xml_for_turn_bay,
                                               generate_sumo_edg_xml,
                                               generate_sumo_flow_xml,
                                               generate_sumo_connection_xml,
                                               generate_sumo_loop_detector_add_xml)
from utdf2gmns.func_lib.sumo._adjust_turn_bay import update_turn_bay_length


pd.options.mode.chained_assignment = None  # default='warn'


class UTDF2GMNS:
    """UTDF2GMNS performs the data conversion from UTDF to different formats.
    The class includes functions such as:
        - geocode_utdf_intersections: geocode intersections

        - create_signal_control: signalize intersections

        - create_gmns_links: create network from UTDF data by combining Nodes, Links, Lanes, and Phases

        - utdf_to_gmns: convert UTDF data to GMNS data and save to the output directory

        - utdf_to_sumo: convert UTDF data to SUMO data and save to the output directory

        - and more...
    """
    def __init__(self, utdf_filename: str, region_name: str = "", *, verbose: bool = False):
        """Initialize UTDF2GMNS class with UTDF file and region name

        Args:
            utdf_filename (str): the path to the UTDF file.
            region_name (str): the metropolitan region/place the utdf file represent. Defaults to "".
            verbose (bool): whether to printout processing message. Defaults to False.
        """
        print("Initializing UTDF2GMNS...")
        self._utdf_filename = pf.path2linux(os.path.abspath(utdf_filename))
        self._utdf_region_name = region_name
        self._verbose = verbose

        # check if city_name is provided
        if not region_name:
            print("  :region_name not provided, "
                  "it is recommended to specify the region name that the UTDF.csv file represents.")

        # load UTDF data from the file in the initialization
        self.__load_utdf()

    def __load_utdf(self) -> bool:
        """Load UTDF file and generate dataframes for Networks, Nodes, Links, Lanes, Timeplans, and Phases
        """

        # TDD: check if the file exists
        if not os.path.exists(self._utdf_filename):
            raise FileNotFoundError(f"UTDF file {self._utdf_filename} not found!")

        # read UTDF file and create dataframes
        utdf_dict_data = read_UTDF(self._utdf_filename)

        # Extract network settings from utdf_dict_data
        self.network_settings = {
            utdf_dict_data.get("Network")
            .loc[i, "RECORDNAME"]: utdf_dict_data.get("Network")
            .loc[i, "DATA"]
            for i in range(len(utdf_dict_data.get("Network")))}

        self.network_unit = "feet, mph" if str(self.network_settings.get("Metric")) == "0" else "meters, km/h"

        # assign to instance variable
        self._utdf_dict = utdf_dict_data
        self.network_int_ids = [str(int_id) for int_id in set(self._utdf_dict.get("Nodes")["INTID"].tolist())]
        self.network_int_ids_signalized = [str(int_id) for int_id in set(
            self._utdf_dict.get("Timeplans")["INTID"].tolist())]

        # initialize the instance variables
        self._is_geocoding_intersections = False

        print(f"  :Total number of intersections in the UTDF file: {len(self.network_int_ids)}")
        return True

    def geocode_utdf_intersections(self,
                                   *,
                                   single_intersection_coord: dict = None,
                                   dist_threshold: float = 0.01,
                                   return_dict_value: bool = False) -> dict:
        """Geocode intersections
        Firstly, geocode one intersection from given single intersection coordinate.
        Then, according to the Nodes information, calculate all intersections based on relative coordinates.

        Args:
            single_intersection_coord (dict): a single intersection coordinates, defaults to None.
                If not provided, geocoding one intersection from address.
                Sample data: {"INTID": "1", "x_coord": -114.568, "y_coord": 35.155}
            dist_threshold (float): distance threshold for geocoding intersections, defaults to 0.01. Unit: km
                only used when single_intersection_coord is not provided.

        Note:
            - single_intersection_coord should follow the format:
                {"INTID": "1", "x_coord": -114.568, "y_coord": 35.155}
            - if single_intersection_coord is not provided,
                geocode intersections from address (region_name must be provided from input).
            - dist_threshold is the distance threshold for geocoding intersections. Defaults to 0.01. Unit: km
                and only used when single_intersection_coord is not provided.

        Raises:
            ValueError: Single coordinate should have INTID, x_coord, and y_coord keys!
            ValueError: INTID should be an integer!
            ValueError: x_coord should be a float!
            ValueError: y_coord should be a float!
            ValueError: single_intersection_coord: {int_id} is not in the Nodes!
            Exception: No valid intersection is geo-coded!

        Returns:
            bool: whether the geocoding intersections is successful.
        """
        print("\nGeocoding UTDF intersections...")
        # check if single coordinate is provided and validate it's value
        if single_intersection_coord:
            if not {"INTID", "x_coord", "y_coord"}.issubset(set(single_intersection_coord.keys())):
                raise ValueError("Single coordinate should have INTID, x_coord, and y_coord keys!")

            if not isinstance(single_intersection_coord.get("INTID"), str):
                raise ValueError("INTID should be a string!")

            if not isinstance(single_intersection_coord.get("x_coord"), float):
                raise ValueError("x_coord should be a float!")

            if not isinstance(single_intersection_coord.get("y_coord"), float):
                raise ValueError("y_coord should be a float!")

            # check if id is in the Nodes
            int_id = int(single_intersection_coord.get("INTID"))
            if str(int_id) not in self.network_int_ids:
                raise ValueError(f"single intersection: {int_id} not in the UTDF Nodes!")

            single_intersection = single_intersection_coord

        elif self._utdf_region_name:
            # generate intersections with name for coordinations
            df_utdf_intersection = generate_intersection_from_Links(
                self._utdf_dict.get("Links"),
                self._utdf_region_name)

            # geocoding one intersection from address, with threshold (default 0.01) km
            single_intersection = generate_intersection_coordinates(
                df_utdf_intersection,
                dist_threshold=dist_threshold,
                geocode_one=True)

            # check if the single_intersection is empty
            if single_intersection["INTID"] is None:
                raise Exception(
                    "\n  No valid intersection is geo-coded!"
                    "  Please change dist_threshold or provide single_coord manually.")
        else:
            raise Exception(
                "\nCould not geocode intersections, two ways to solve this issue: \n"
                "  1. provide city_name when initializing UTDF2GMNS class; \n"
                "  2. provide single_coord manually while running geocoding_intersections()."
            )

        # update Nodes from single_intersection
        node_dict = update_node_from_one_intersection(single_intersection,
                                                      self._utdf_dict.get("Nodes"),
                                                      self.network_unit)

        self.network_nodes = node_dict
        self._utdf_dict["network_nodes"] = node_dict
        self._is_geocoding_intersections = True

        return node_dict if return_dict_value else {}

    def create_signal_control(self) -> bool:
        """Signalize intersections
        1. get signal intersection id from phase
        2. parse signal control from UTDF data and create signal control for each intersection
        3. assign signal control to network_signal_control, a dictionary as internal variable
        """

        # get signal intersection id from phase
        df_phase = self._utdf_dict.get("Phases")
        df_lane = self._utdf_dict.get("Lanes")
        signal_int_id = df_phase["INTID"].unique()

        signal_intersections = {
            int_id: parse_signal_control(df_phase, df_lane, int_id)
            for int_id in signal_int_id
        }
        self.network_signal_control = signal_intersections
        return True

    def create_gmns_links(self, *, default_width: float = 12, is_link_polygon: bool = False) -> bool:
        """Create network from UTDF data by combining Nodes, Links, Lanes, and Phases

        Args:
            default_width (float): default width of the link, defaults to 12.
            is_link_polygon (bool): whether to create link polygon (bbox), defaults to False.

        Returns:
            bool: whether the network is created successfully.
        """

        width = self.network_settings.get("DefWidth", default_width)
        unit = self.network_unit

        # whether to create link polygon
        if is_link_polygon:
            links_dict = generate_links_polygon(self._utdf_dict.get("Links"), self.network_nodes, width, unit)
        else:
            links_dict = generate_links(self._utdf_dict.get("Links"), self.network_nodes, width, unit)

        self.network_links = links_dict
        print(f"  :Total number of edges generated: {len(links_dict)}")

        return True

    @pf.func_running_time
    def utdf_to_gmns_signal_ints(self, *, output_dir: str = "") -> bool:
        """ Empower Sigma-X engine to generate each signal intersection with visualization  """

        print("\nRunning Sigma-X engine... \n")
        # print out approximate time for processing
        total_seconds = 3.5 * len(self.network_int_ids_signalized)
        print("  :Processing each signal intersection, please wait...")
        print(f"  :Total time for {len(self.network_int_ids_signalized)} intersections"
              f" might be: {time_unit_converter(total_seconds, 's', 'm', False):.2f} minutes...")
        cvt_utdf_to_signal_intersection(
            self._utdf_filename, verbose=self._verbose)
        return True

    def utdf_to_gmns(self, *, output_dir: str = "", incl_utdf: bool = True, is_link_polygon: bool = False) -> bool:
        """Convert UTDF data to GMNS data and save to the output directory

        Args:
            out_dir (str): output directory to save the GMNS data, defaults to the same directory as the UTDF file.
            incl_utdf (bool): whether to save the UTDF data to the output directory, defaults to True.
            is_link_polygon (bool): whether to create link polygon, defaults to False.

        Note:
            - the UTDF data includes Nodes, Networks, Timeplans, Links, Lanes, and Phases.
            - the GMNS data includes node.csv and link.csv.

        Raises:
            FileNotFoundError: Output directory not found!

        Returns:
            bool: whether the conversion is successful.
        """
        print("\nConverting UTDF to GMNS...")
        # check if the output directory exists
        utdf_dir = Path(self._utdf_filename).parent.absolute()
        gmns_output_dir = output_dir or os.path.join(utdf_dir, "utdf_to_gmns")
        gmns_output_dir = pf.path2linux(gmns_output_dir)  # convert to universal path format

        # create the output directory if it does not exist
        if not os.path.exists(gmns_output_dir):
            os.makedirs(gmns_output_dir)

        # Create node and link data if not exist
        if not hasattr(self, "network_nodes"):
            raise Exception("Please geocode intersections first: net.geocode_utdf_intersections()")

        if not hasattr(self, "network_links"):
            self.create_gmns_links(is_link_polygon=is_link_polygon)

        if not hasattr(self, "network_signal_control"):
            self.create_signal_control()

        # Save the GMNS data to the output directory
        pd.DataFrame(self.network_nodes.values()).to_csv(
            os.path.join(gmns_output_dir, "node.csv"), index=False)
        pd.DataFrame(self.network_links.values()).to_csv(
            os.path.join(gmns_output_dir, "link.csv"), index=False)

        with open(os.path.join(gmns_output_dir, "signal.json"), "w") as f:
            json.dump(self.network_signal_control, f)

        # save the UTDF data to the output directory
        if incl_utdf:
            self._utdf_dict.get("Nodes").to_csv(
                os.path.join(gmns_output_dir, "utdf_nodes.csv"),
                index=False)
            self._utdf_dict.get("Network").to_csv(
                os.path.join(gmns_output_dir, "utdf_network.csv"),
                index=False)
            self._utdf_dict.get("Timeplans").to_csv(
                os.path.join(gmns_output_dir, "utdf_timeplans.csv"),
                index=False)
            self._utdf_dict.get("Links").to_csv(
                os.path.join(gmns_output_dir, "utdf_links.csv"),
                index=False)
            self._utdf_dict.get("Lanes").to_csv(
                os.path.join(gmns_output_dir, "utdf_lanes.csv"),
                index=False)
            self._utdf_dict.get("Phases").to_csv(
                os.path.join(gmns_output_dir, "utdf_phases.csv"),
                index=False)
        print(f"  :Successfully saved GMNS(csv) data to \n    {gmns_output_dir}.")
        return True

    def utdf_to_sumo(self, *, output_dir: str = "", sim_name: str = "",
                     show_warning_message: bool = False,
                     disable_U_turn: bool = True,
                     sim_start_time: int = 0,
                     sim_duration: int = 3600  # 1 hour
                     ) -> bool:
        """Convert UTDF to SUMO and save networks to the output directory

        Args:
            out_dir (str): the output directory for the generated sumo files.
                Defaults to "". If not provided, the output directory is the same as the UTDF file.

            sim_name (str): name the generated sumo files. Defaults to "".
                If not provided, the name is "utdf_to_sumo".

            show_warning_message (bool): whether to show warning message during the net processing.
                Defaults to False.

            disable_U_turn (bool): whether to remove U-turns in the SUMO network.
                Defaults to True.

            sim_start_time (int): the start time of the simulation in seconds.
                The program will extract start time from UTDF file, if not provided, will use the default value of 0.

            sim_duration (int): the duration of the simulation in seconds.
                Defaults to 3600 seconds (1 hour).

        Returns:
            bool: whether the conversion is successful.
        """
        print("\nConverting UTDF to SUMO using GMNS standard...")
        # check if the output directory exists
        utdf_dir = Path(self._utdf_filename).parent.absolute()
        sumo_output_dir = output_dir or os.path.join(utdf_dir, "utdf_to_sumo")
        sumo_output_dir = pf.path2linux(sumo_output_dir)

        # create the output directory if it does not exist
        os.makedirs(sumo_output_dir, exist_ok=True)

        # Crate network nodes and links if not exist
        if not hasattr(self, "network_nodes"):
            raise Exception("Please geocode intersections first: net.geocode_utdf_intersections()")

        # if not hasattr(self, "network_links"):
        #     self.create_gmns_links(is_link_polygon=is_link_polygon)
        #     print()

        xml_name = sim_name or "utdf_to_sumo"

        # create SUMO .nod.xml file
        output_node_file = os.path.join(sumo_output_dir, f"{xml_name}.nod.xml")
        output_node_file = pf.path2linux(output_node_file)
        generate_sumo_nod_xml(self._utdf_dict, output_node_file)
        print(f"  :generated SUMO node xml file: {xml_name}.nod.xml")

        # add additional nodes for turn bay implementation
        # update_sumo_nod_xml_for_turn_bay(self._utdf_dict, self.network_unit, output_node_file)
        # print(f"  :updated SUMO node xml file for turn bay: {xml_name}.nod.xml")

        # create SUMO .edg.xml file
        output_edge_file = os.path.join(sumo_output_dir, f"{xml_name}.edg.xml")
        output_edge_file = pf.path2linux(output_edge_file)
        generate_sumo_edg_xml(self._utdf_dict, self.network_unit, output_edge_file)
        print(f"  :generated SUMO edge xml file: {xml_name}.edg.xml")

        # Create SUMO .con.xml file
        output_con_file = os.path.join(sumo_output_dir, f"{xml_name}.con.xml")
        output_con_file = pf.path2linux(output_con_file)
        generate_sumo_connection_xml(self._utdf_dict, output_con_file)
        print(f"  :generated SUMO connection xml file: {xml_name}.con.xml")

        # Create SUMO loop detector in .add.xml file
        output_add_file = os.path.join(sumo_output_dir, f"{xml_name}.add.xml")
        output_add_file = pf.path2linux(output_add_file)
        generate_sumo_loop_detector_add_xml(self._utdf_dict, self.network_unit,
                                            detector_type="E1",
                                            add_fname=output_add_file,
                                            sim_output_fname="")
        print(f"  :generated SUMO loop detector xml file: {xml_name}.add.xml")

        # convert .nod.xml and .edg.xml files to .net.xml file
        output_net_file = os.path.join(sumo_output_dir, f"{xml_name}.net.xml")
        output_net_file = pf.path2linux(output_net_file)
        try:
            # sumo-netconvert -n network.nod.xml -e network.edg.xml -o network.net.xml
            result = subprocess.run(["netconvert",
                                     f"--node-files={output_node_file}",
                                     f"--edge-files={output_edge_file}",
                                     f"--connection-files={output_con_file}",
                                     f"--output-file={output_net_file}",
                                     "--no-warnings=true",
                                     "--proj.utm"],
                                    cwd=sumo_output_dir,
                                    capture_output=True,
                                    text=True)
            if result.returncode != 0:
                # the return code is 0, which means the command executed failed
                # One of the reason is that the running environment is not set up correctly
                # Such as SUMO_HOME is not set up correctly or
                # SUMO is not installed

                # We will run netconvert (nc) from the package build-in file
                # get the path of the netconvert(nc) file under the engine directory
                nc_filename = Path(__file__).parent / "engine" / "netconvert.exe"
                nc_filename = pf.path2linux(nc_filename)
                result = subprocess.run([nc_filename,
                                         f"--node-files={output_node_file}",
                                         f"--edge-files={output_edge_file}",
                                         f"--connection-files={output_con_file}",
                                         f"--output-file={output_net_file}",
                                         "--no-warnings=true",
                                         "--proj.utm"],
                                        cwd=sumo_output_dir,
                                        capture_output=True,
                                        text=True)

            if result.returncode != 0:
                print("  :SUMO netconvert from nod.xml, edg.xml to net.xml failed!")
                print(f" :{result.stderr}")
                return False

            print(f"  :Successfully generated SUMO network to \n    {sumo_output_dir}.")
            if show_warning_message:
                pass
                # print("Warning message in generating SUMO network:")
                # print(f"{result.stderr}")
        except Exception as e:
            print(f"  :Error in generating SUMO network: {e}")
            return False

        # update turn bay length in the SUMO network
        # update_turn_bay_length(output_net_file, self._utdf_dict, self.network_unit)
        # print(f"  :Successfully updated turn bay length to \n    {sumo_output_dir}.")

        # update SUMO signal in .net.xml file
        update_sumo_signal_from_utdf(output_net_file, self._utdf_dict, verbose=self._verbose)
        print(f"  :Successfully updated SUMO signal xml to \n    {sumo_output_dir}.")

        # create SUMO .flow.xml file
        output_flow_file = os.path.join(sumo_output_dir, f"{xml_name}.flow.xml")
        output_flow_file = pf.path2linux(output_flow_file)
        if begin := self.network_settings.get("ScenarioTime"):
            begin_time = time_str_to_seconds(begin, verbose=False)
        else:
            begin_time = sim_start_time
        end_time = begin_time + sim_duration
        generate_sumo_flow_xml(self._utdf_dict, output_flow_file,
                               begin=begin_time,
                               end=end_time)

        # create .rou.xml file
        output_rou_file = os.path.join(sumo_output_dir, f"{xml_name}.rou.xml")
        output_rou_file = pf.path2linux(output_rou_file)

        try:
            print("\n  :Generating SUMO .rou.xml file from UTDF lanes...")
            jtrrouter_fname = Path(__file__).parent / "engine" / "jtrrouter.exe"
            jtrrouter_fname = pf.path2linux(jtrrouter_fname)
            result = subprocess.run([jtrrouter_fname,
                                     f"--route-files={output_flow_file}",
                                     f"--net-file={output_net_file}",
                                     "--accept-all-destinations=false",
                                     f"--output-file={output_rou_file}",
                                     "--remove-loops=true",
                                     "--no-internal-links=false",
                                     "--no-warnings=true"],
                                    cwd=sumo_output_dir,
                                    capture_output=True,
                                    text=True)
            if result.returncode != 0:
                print(f" :{result.stderr}")

                # get the path of the randomTrips.py file under the func_lib directory
                print("  :Generating SUMO .rou.xml file with random trips...")
                path_random_trips = Path(__file__).parent / "func_lib" / "sumo" / "randomTrips.py"
                path_random_trips = pf.path2linux(path_random_trips)

                # run randomTrips.py to generate .rou.xml file
                result = subprocess.run(["python",
                                        path_random_trips,
                                        "-n", output_net_file,
                                         "-r", output_rou_file],
                                        cwd=sumo_output_dir,
                                        capture_output=True,
                                        text=True)
            if result.returncode != 0:
                print("  :SUMO create .flow.xml failed!")
                print(f" :{result.stderr}")
                return False

            print(f"  :Successfully generated default flow file to \n    {sumo_output_dir}.")
        except Exception as e:
            print(f"  :Error in generating SUMO route file: {e}")
            return False

        # remove U-turns in the SUMO network
        if disable_U_turn:
            print()
            remove_sumo_U_turn(output_net_file)
            print()

        # create .sumocfg file for the generated network
        # will generate default .rou.xml file for the network
        sumo_cfg_file = os.path.join(sumo_output_dir, f"{xml_name}.sumocfg")
        sumo_cfg_file = pf.path2linux(sumo_cfg_file)

        cfg_str = (
            f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'\n'
            f'<configuration>\n'
            f'    <input>\n'
            f'        <net-file value="{xml_name}.net.xml"/>\n'
            f'        <route-files value="{xml_name}.rou.xml"/>\n'
            f'        <additional-files value="{xml_name}.add.xml"/>\n'
            f'    </input>\n'
            f'    <output>\n'
            f'        <edgedata-output value="EdgeData.xml"/>\n'
            f'    </output>\n'
            f'    <time>\n'
            f'        <begin value="{begin_time}"/>\n'
            f'        <end value="{end_time}"/>\n'
            f'        <step-length value="1"/>\n'
            f'    </time>\n'
            f'</configuration>\n'
        )

        # Parse the XML string
        # pretty_xml_str = minidom.parseString(cfg_str).toprettyxml(indent="    ")
        with open(sumo_cfg_file, "w") as f:
            f.write(cfg_str)

        print(f"  :Successfully generated SUMO configuration file to \n    {sumo_output_dir}.")

        return True
