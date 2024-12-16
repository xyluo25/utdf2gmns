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
import warnings

import pandas as pd

# import utility functions from pyufunc
from pyufunc import (func_running_time,
                     path2linux,
                     check_files_in_dir,
                     generate_unique_filename)

# For deployment
from utdf2gmns.func_lib.geocoding_intersection import generate_intersection_coordinates
from utdf2gmns.func_lib.match_node_intersection_movement_utdf import (
    match_intersection_node,
    match_movement_and_intersection_node,
    match_movement_utdf_lane,
    match_movement_utdf_phase_timeplans)
from utdf2gmns.func_lib.read_utdf import (generate_intersection_from_Links,
                                          read_UTDF_file)
from utdf2gmns.func_lib.geocoding_Nodes import update_node_from_one_intersection
from utdf2gmns.func_lib.signalized_intersections import parse_signal_control
from utdf2gmns.func_lib.geocoding_Links import (generate_links,
                                                generate_links_polygon,
                                                reformat_link_dataframe_to_dict)

# SUMO related functions
from utdf2gmns.func_lib.gmns2sumo import generate_nod_xml, generate_edg_xml


pd.options.mode.chained_assignment = None  # default='warn'


@func_running_time
def generate_movement_utdf(input_dir: str = "",
                           city_name: str = "",
                           output_dir: str = "",
                           path_utdf_intersection: str = "",
                           isSave2csv: bool = True) -> list:
    """generate movement_utdf.csv file from merging UTDF file to GMNS movement.csv file

    Parameters
    ----------
    input_dir : str, optional
        the path of input directory, by default "", which means current working directory
    city_name : str, optional
        the name of the city where the UTDF file is located, by default ""
    UTDF_file : str, optional
        the name of UTDF file, by default None
    node_file : str, optional
        the name of node.csv file, by default None
    movement_file : str, optional
        the name of movement.csv file, by default None
    output_dir : str, optional
        the path of output directory, by default "", which means the same as input directory
    isSave2csv : bool, optional
        whether to save the movement_utdf.csv file, by default True

    Returns
    -------
    list
        a list of movement_utdf.csv file

    """

    # if not specified input_dir, use current working directory
    input_dir = input_dir or os.getcwd()

    # check if required files exist in the input directory
    # files_from_directory = get_filenames_by_ext(input_dir, file_ext="csv")

    # if not required, raise an exception
    isRequired = check_files_in_dir(["UTDF.csv"], input_dir)
    isRequired_sub = check_files_in_dir(["node.csv", "movement.csv"], input_dir)

    # required files are not found, raise an exception
    if not isRequired:
        raise Exception("Required file UTDF.csv are not found!")

    # read UTDF file and create dataframes of utdf_intersection and utdf_lane
    path_utdf = path2linux(os.path.join(input_dir, "UTDF.csv"))

    if not city_name:
        raise Exception("City name is not provided, please provide the city name!")

    print("\nStep 1: read UTDF file...")
    utdf_dict_data = read_UTDF_file(path_utdf)
    utdf_dict_data["utdf_intersection"] = generate_intersection_from_Links(utdf_dict_data.get("Links"), city_name)

    # geocoding the utdf_intersection and store it into utdf_dict_data
    # If not automatically geocode, save the utdf_geo.csv file in the input directory
    # And user manually add coord_x and coord_y to in utdf_geo.csv file
    # And re-run the function to generate the final movement_utdf.csv file

    print("Step 1.1: geocoding UTDF intersections from address...")
    # check utdf_geo.csv file existence
    if path_utdf_intersection:
        # read user manually added utdf_geo.csv file from the input directory
        # and store it into utdf_dict_data
        print(
            "     : read user manually added utdf_geo.csv file from the input directory...")
        utdf_dict_data["utdf_geo"] = pd.read_csv(path_utdf_intersection)

        # check if user manually added coord_x and coord_y to in utdf_geo.csv file
        if not {"coord_x", "coord_y"}.issubset(set(utdf_dict_data.get("utdf_geo").columns)):
            raise Exception(
                "coord_x or coord_y not found in the utdf_geo.csv file!, please add coord_x and coord_y manually \
                 and re-run the code afterwards."
            )

#     if os.path.exists(path2linux(os.path.join(input_dir, "utdf_geo.csv"))):
#         # read utdf_geo.csv file from the input directory
#         utdf_dict_data["utdf_geo"] = pd.read_csv(path2linux(
#             os.path.join(input_dir, "utdf_geo.csv")))
#
#         # check if user manually added coord_x and coord_y to in utdf_geo.csv file
#         if not {"coord_x", "coord_y"}.issubset(set(utdf_dict_data.get("utdf_geo").columns)):
#             raise Exception(
#                 "coord_x or coord_y not found in the utdf_geo.csv file!, please add coord_x and coord_y manually \
#                  and re-run the code afterwards."
#             )

    # check utdf_geo in utdf_dict_data or not
    # if not generate utdf_geo automatically
    if "utdf_geo" not in utdf_dict_data.keys():
        try:
            # geocoding utdf_intersection automatically
            utdf_dict_data["utdf_geo"] = generate_intersection_coordinates(
                utdf_dict_data.get("utdf_intersection"))
        except Exception as e:
            # #  Save the utdf_geo.csv file in the input directory
            utdf_dict_data.get("utdf_intersection").to_csv(
                path2linux(os.path.join(input_dir, "utdf_geo.csv")), index=False)

            raise Exception(
                "We can not geocoding intersections automatically, \
                 We save utdf_geo.csv file in your input dir,   \
                please manually add coord_x and coord_y to the utdf_geo.csv file \
                in your input directory and re-run the code afterwards."
            ) from e

    # required_sub files are not found, will return utdf_intersection and utdf_lane
    if not isRequired_sub:
        print("Because node.csv and movement.csv are not found, \
            the function will return data from utdf in a dictionary, \
            keys are: Lanes, Nodes, Networks, Timeplans, Links and utdf_geo.\n")

        # store object into pickle file
        with open(path2linux(os.path.join(input_dir, "utdf2gmns.pickle")), 'wb') as f:
            pickle.dump(utdf_dict_data, f, pickle.HIGHEST_PROTOCOL)
        return utdf_dict_data

    # get the path of each file,
    # since the input directory and files are checked, no need to validate the filename
    print("Step 2: read node.csv and movement.csv (GMNS format)...")
    path_node = path2linux(os.path.join(input_dir, "node.csv"))
    path_movement = path2linux(os.path.join(input_dir, "movement.csv"))

    # read node and movement files
    df_node = pd.read_csv(path_node)
    df_movement = pd.read_csv(path_movement)
    print(f"    : {len(df_node)} nodes loaded.")
    print(f"    : {len(df_movement)} movements loaded.\n")

    # match utdf_intersection_geo with node
    print("Step 3: Performing data merging from GMNS nodes"
          "to UTDF intersections based on distance threshold(default 0.1km)...")
    df_intersection_node = match_intersection_node(utdf_dict_data.get("utdf_geo"),
                                                   df_node)

    # match movement with intersection_node
    print("Step 4: Performing data merging from UTDF intersections(geocoded) to GMNS movements based on OSM id...")
    df_movement_intersection = match_movement_and_intersection_node(df_movement,
                                                                    df_intersection_node)

    # match movement with utdf_lane
    print("Step 5: Performing data merging from UTDF Lanes to GMNS movements based on UTDF id...")
    df_movement_utdf_lane = match_movement_utdf_lane(
        df_movement_intersection, utdf_dict_data)

    # match movement with utdf_phase_timeplans
    print("Step 6: Performing data merging from UTDF phases and timeplans to GMNS movements based on UTDF id...")
    df_movement_utdf_phase = match_movement_utdf_phase_timeplans(
        df_movement_utdf_lane, utdf_dict_data)

    # store utdf_intersection_geo and movement_utdf to utdf_dict_data
    utdf_dict_data["movement_utdf_phase"] = df_movement_utdf_phase
    utdf_dict_data["utdf_geo_GMNS_node"] = df_intersection_node

    # save the output file, the default isSave2csv is True
    # if not specified, output path is input directory,
    # output file name = movement_utdf.csv
    if isSave2csv:
        if not output_dir:
            output_dir = input_dir
        output_file_name_1 = generate_unique_filename(
            os.path.join(output_dir, "movement_utdf.csv"))
        df_movement_utdf_phase.to_csv(output_file_name_1, index=False)

        output_file_name_2 = generate_unique_filename(
            os.path.join(output_dir, "utdf_intersection.csv"))
        utdf_dict_data.get("utdf_geo").to_csv(output_file_name_2, index=False)

        # with open(path2linux(os.path.join(output_dir, "utdf2gmns.pickle")), 'wb') as f:
        #     pickle.dump(utdf_dict_data, f, pickle.HIGHEST_PROTOCOL)

        print(f" : Successfully saved movement_utdf.csv to: {output_file_name_1}.")
        print(f" : Successfully saved utdf_intersection.csv to: {output_file_name_2}.")

    return [df_movement_utdf_phase, utdf_dict_data]


class UTDF2GMNS:
    """UTDF2GMNS performs the data conversion from UTDF to other formats.
    The class includes functions such as:
        - read_UTDF_file (default): read UTDF file and generate dataframes for Networks, Nodes, Links, Lanes, Timeplans, and Phases
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
        utdf_dict_data = read_UTDF_file(self._utdf_filename)

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

    def create_network(self, default_width: float = 12, is_link_polygon: bool = False) -> None:
        """Create network from UTDF data by combining Nodes, Links, Lanes, and Phases

        Args:
            default_width (float): default width of the link, defaults to 12.
            is_link_polygon (bool): whether to create link polygon, defaults to False.

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

    def utdf_to_gmns(self, out_dir: str = "", *, incl_utdf: bool = True, is_link_polygon: bool = False) -> None:
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
        gmns_out_dir = out_dir or os.path.join(utdf_dir, "utdf_to_gmns")
        if not os.path.exists(gmns_out_dir):
            os.makedirs(gmns_out_dir)

        # save the GMNS data to the output directory
        if not hasattr(self, "network_nodes"):
            self.create_network(is_link_polygon=is_link_polygon)

        if not hasattr(self, "network_links"):
            self.create_network(is_link_polygon=is_link_polygon)

        pd.DataFrame(self.network_nodes.values()).to_csv(os.path.join(gmns_out_dir, "node.csv"), index=False)
        pd.DataFrame(self.network_links.values()).to_csv(os.path.join(gmns_out_dir, "link.csv"), index=False)

        # save the UTDF data to the output directory
        if incl_utdf:
            self._utdf_dict.get("Nodes").to_csv(os.path.join(gmns_out_dir,
                                                             "utdf_nodes.csv"),
                                                index=False)
            self._utdf_dict.get("Network").to_csv(os.path.join(gmns_out_dir,
                                                               "utdf_network.csv"),
                                                  index=False)
            self._utdf_dict.get("Timeplans").to_csv(os.path.join(gmns_out_dir,
                                                                 "utdf_timeplans.csv"),
                                                    index=False)
            self._utdf_dict.get("Links").to_csv(os.path.join(gmns_out_dir,
                                                             "utdf_links.csv"),
                                                index=False)
            self._utdf_dict.get("Lanes").to_csv(os.path.join(gmns_out_dir,
                                                             "utdf_lanes.csv"),
                                                index=False)
            self._utdf_dict.get("Phases").to_csv(os.path.join(gmns_out_dir,
                                                              "utdf_phases.csv"),
                                                 index=False)
        print(f"  :Successfully saved GMNS(csv) data to {gmns_out_dir}.")
        return None

    def utdf_to_sumo(self, out_dir: str = "", sumo_name: str = "", *,
                     show_warning_message: bool = False) -> None:
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
        sumo_out_dir = out_dir or os.path.join(utdf_dir, "utdf_to_sumo")
        if not os.path.exists(sumo_out_dir):
            os.makedirs(sumo_out_dir)

        # save the SUMO data to the output directory
        if not hasattr(self, "network_nodes"):
            self.create_network()

        if not hasattr(self, "network_links"):
            self.create_network()

        xml_name = sumo_name or "utdf_to_sumo"

        # create SUMO .nod.xml file
        output_node_file = os.path.join(sumo_out_dir, f"{xml_name}.nod.xml")
        generate_nod_xml(self.network_nodes, output_node_file)

        # create SUMO .edg.xml file
        # extract link data from df_link
        int_links = reformat_link_dataframe_to_dict(self._utdf_dict.get("Links"))
        output_edge_file = os.path.join(sumo_out_dir, f"{xml_name}.edg.xml")
        generate_edg_xml(int_links, output_edge_file)

        # convert the .nod.xml and .edg.xml files to .net.xml file
        # sumo-netconvert -n network.nod.xml -e network.edg.xml -o network.net.xml
        result = subprocess.run(["netconvert",
                                 f"--node-files={output_node_file}",
                                 f"--edge-files={output_edge_file}",
                                 f"--output-file={xml_name}.net.xml"],
                                cwd=sumo_out_dir,
                                capture_output=True,
                                text=True)
        if result.returncode != 0:
            # the return code is 0, which means the command executed failed
            # One of the reason is that the running environment is not set up correctly
            # Such as SUMO_HOME is not set up correctly or
            # SUMO is not installed

            # We will run netconvert from the package build-in file
            # get the path of the netconvert file under the engine directory
            netconvert_file = Path(__file__).parent / "engine" / "netconvert.exe"
            result = subprocess.run([netconvert_file,
                                     f"--node-files={output_node_file}",
                                     f"--edge-files={output_edge_file}",
                                     f"--output-file={xml_name}.net.xml"],
                                    cwd=sumo_out_dir,
                                    capture_output=True,
                                    text=True)

        if result.returncode != 0:
            print("  :SUMO netconvert from nod.xml, edg.xml to net.xml failed!")
            print(f" :{result.stderr}")
            return None

        print(f"  :Successfully generated SUMO network to {sumo_out_dir}.")
        if show_warning_message:
            print("Warning message in generating SUMO network:")
            print(f"{result.stderr}")
        return None
