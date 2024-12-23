# -*- coding:utf-8 -*-
##############################################################
# Created Date: Friday, January 27th 2023
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################

import os
import pickle
from pathlib import Path
import subprocess

import pandas as pd

# import utility functions from pyufunc
from pyufunc import (func_running_time,
                     path2linux,
                     check_files_in_dir,
                     generate_unique_filename)

# For deployment
from utdf2gmns.func_lib.geocoding_intersection import generate_intersection_coordinates
from utdf2gmns.func_lib.read_utdf import (generate_intersection_from_Links,
                                          read_UTDF)
from utdf2gmns.func_lib.geocoding_Nodes import update_node_from_one_intersection
from utdf2gmns.func_lib.signal_intersections import parse_signal_control
from utdf2gmns.func_lib.geocoding_Links import (generate_links,
                                                generate_links_polygon,
                                                reformat_link_dataframe_to_dict)

# SUMO related functions
from utdf2gmns.func_lib.gmns2sumo import generate_nod_xml, generate_edg_xml


pd.options.mode.chained_assignment = None  # default='warn'


class UTDF2GMNS:
    """UTDF2GMNS performs the data conversion from UTDF to different formats.
    The class includes functions such as:
        - read_UTDF_file (default): read UTDF file and generate dataframes for Networks,
            Nodes, Links, Lanes, Timeplans, and Phases
        - geocode_intersections: geocode intersections
        - create_signal_control: signalize intersections
        - create_network: create network from UTDF data by combining Nodes, Links, Lanes, and Phases
        - utdf_to_gmns: convert UTDF data to GMNS data and save to the output directory
        - utdf_to_sumo: convert UTDF data to SUMO data and save to the output directory
    """
    def __init__(self, utdf_filename: str, region_name: str = "", *, verbose: bool = False):
        self._utdf_filename = utdf_filename
        self._utdf_region_name = region_name
        self._verbose = verbose  # whether to print the verbose message

        # check if city_name is provided
        if not region_name:
            print("  :region_name not provided, "
                  "it is recommended to specify the region name that the UTDF.csv file represents.")

        # load UTDF data from the file in the initialization
        self.__load_utdf()

    def __load_utdf(self) -> None:
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

        # initialize the instance variables
        self._is_geocoding_intersections = False
        return None

    def geocode_intersections(self, single_coord: dict = {}, dist_threshold: float = 0.01) -> None:
        """Geocode intersections
        Firstly, geocode one intersection from given single intersection coordinate.
        Then, according to the Nodes information, calculate all intersections based on relative distance.

        Args:
            single_coord (dict): a single intersection coordinates, defaults to {}.
                If not provided, geocoding one intersection from address.
                sample data: {"INTID": "1", "x_coord": -114.568, "y_coord": 35.155}
            dist_threshold (float): distance threshold for geocoding intersections, defaults to 0.01. Unit: km

        Note:
            - single_coord should follow the format: {"INTID": "1", "x_coord": -114.568, "y_coord": 35.155}
            - if single_coord is not provided, geocode intersections from address (region_name must be assigned).

        Raises:
            ValueError: Single coordinate should have INTID, x_coord, and y_coord keys!
            ValueError: INTID should be an integer!
            ValueError: x_coord should be a float!
            ValueError: y_coord should be a float!
            ValueError: single_coord: {int_id} is not in the Nodes!
            Exception: No valid intersection is geo-coded!

        Returns:
            None
        """

        # check if single coordinate is provided and validate it's value
        if single_coord:
            if not {"INTID", "x_coord", "y_coord"}.issubset(set(single_coord.keys())):
                raise ValueError("Single coordinate should have INTID, x_coord, and y_coord keys!")
            if not isinstance(single_coord.get("INTID"), str):
                raise ValueError("INTID should be a string!")
            if not isinstance(single_coord.get("x_coord"), float):
                raise ValueError("x_coord should be a float!")
            if not isinstance(single_coord.get("y_coord"), float):
                raise ValueError("y_coord should be a float!")

            # check if id is in the Nodes
            int_id = int(single_coord.get("INTID"))
            if int_id not in self._utdf_dict.get("Nodes")["INTID"].tolist():
                raise ValueError(f"single_coord: {int_id} is not in the Nodes!")

            single_intersection = single_coord

        else:
            if self._utdf_region_name:
                # generate intersections with name for coordinations
                df_utdf_intersection = generate_intersection_from_Links(
                    self._utdf_dict.get("Links"),
                    self._utdf_region_name)

                # geocoding one intersection from address, with threshold 0.01 km
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
        node_df = update_node_from_one_intersection(single_intersection,
                                                    self._utdf_dict.get("Nodes"),
                                                    self.network_unit)

        # self._utdf_dict["Nodes"] = node_df
        self.network_nodes = node_df
        self._is_geocoding_intersections = True
        return None

    def create_signal_control(self) -> None:
        """Signalize intersections
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
        return None

    def create_network(self, *, default_width: float = 12, is_link_polygon: bool = False) -> None:
        """Create network from UTDF data by combining Nodes, Links, Lanes, and Phases

        Args:
            default_width (float): default width of the link, defaults to 12.
            is_link_polygon (bool): whether to create link polygon (bbox), defaults to False.

        Returns:
            None

        """
        width = self.network_settings.get("DefWidth", default_width)
        unit = self.network_unit

        # whether to use link polygon
        if is_link_polygon:
            links_dict = generate_links_polygon(self._utdf_dict.get("Links"), self.network_nodes, width, unit)

        else:
            links_dict = generate_links(self._utdf_dict.get("Links"), self.network_nodes, width, unit)

        self.network_links = links_dict
        return None

    def utdf_to_gmns(self, *, output_dir: str = "", incl_utdf: bool = True, is_link_polygon: bool = False) -> None:
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
            None
        """

        # check if the output directory exists
        utdf_dir = Path(self._utdf_filename).parent.absolute()
        gmns_output_dir = output_dir or os.path.join(utdf_dir, "utdf_to_gmns")
        if not os.path.exists(gmns_output_dir):
            os.makedirs(gmns_output_dir)

        # save the GMNS data to the output directory
        if not hasattr(self, "network_nodes"):
            self.create_network(is_link_polygon=is_link_polygon)

        if not hasattr(self, "network_links"):
            self.create_network(is_link_polygon=is_link_polygon)

        pd.DataFrame(self.network_nodes.values()).to_csv(
            os.path.join(gmns_output_dir, "node.csv"), index=False)
        pd.DataFrame(self.network_links.values()).to_csv(
            os.path.join(gmns_output_dir, "link.csv"), index=False)

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
        print(f"  :Successfully saved GMNS(csv) data to {gmns_output_dir}.")
        return None

    def utdf_to_sumo(self, *, output_dir: str = "", sumo_name: str = "", show_warning_message: bool = False) -> None:
        """Convert UTDF data to SUMO data and save to the output directory

        Args:
            out_dir (str): the output directory for the generated sumo files.
                Defaults to "". If not provided, the output directory is the same as the UTDF file.
            sumo_name (str): name the generated sumo files. Defaults to "".
                If not provided, the name is "utdf_to_sumo".
            show_warning_message (bool): whether to show warning message during the net processing.
                Defaults to False.

        Returns:
            None
        """

        # check if the output directory exists
        utdf_dir = Path(self._utdf_filename).parent.absolute()
        sumo_output_dir = output_dir or os.path.join(utdf_dir, "utdf_to_sumo")
        if not os.path.exists(sumo_output_dir):
            os.makedirs(sumo_output_dir)

        # save the SUMO data to the output directory
        if not hasattr(self, "network_nodes"):
            self.create_network()

        if not hasattr(self, "network_links"):
            self.create_network()

        xml_name = sumo_name or "utdf_to_sumo"

        # create SUMO .nod.xml file
        output_node_file = os.path.join(sumo_output_dir, f"{xml_name}.nod.xml")
        generate_nod_xml(self.network_nodes, output_node_file)

        # create SUMO .edg.xml file
        int_links = reformat_link_dataframe_to_dict(self._utdf_dict.get("Links"))
        output_edge_file = os.path.join(sumo_output_dir, f"{xml_name}.edg.xml")
        generate_edg_xml(int_links, output_edge_file)

        # convert the .nod.xml and .edg.xml files to .net.xml file
        # sumo-netconvert -n network.nod.xml -e network.edg.xml -o network.net.xml
        result = subprocess.run(["netconvert",
                                 f"--node-files={output_node_file}",
                                 f"--edge-files={output_edge_file}",
                                 f"--output-file={xml_name}.net.xml"],
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
            result = subprocess.run([nc_filename,
                                     f"--node-files={output_node_file}",
                                     f"--edge-files={output_edge_file}",
                                     f"--output-file={xml_name}.net.xml"],
                                    cwd=sumo_output_dir,
                                    capture_output=True,
                                    text=True)

        if result.returncode != 0:
            print("  :SUMO netconvert from nod.xml, edg.xml to net.xml failed!")
            print(f" :{result.stderr}")
            return None

        print(f"  :Successfully generated SUMO network to {sumo_output_dir}.")
        if show_warning_message:
            print("Warning message in generating SUMO network:")
            print(f"{result.stderr}")
        return None
