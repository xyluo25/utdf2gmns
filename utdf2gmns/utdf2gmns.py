# -*- coding:utf-8 -*-
##############################################################
# Created Date: Friday, January 27th 2023
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################

import os
import pickle

import pandas as pd

# import utility functions from pyufunc
from pyufunc import (func_running_time,
                     path2linux,
                     check_files_in_dir,
                     generate_unique_filename)

# For deployment
from utdf2gmns.func_lib.geocoding_intersection import generate_intersection_coordinates
from utdf2gmns.func_lib.match_node_intersection_movement_utdf import (
    match_intersection_node, match_movement_and_intersection_node,
    match_movement_utdf_lane, match_movement_utdf_phase_timeplans)
from utdf2gmns.func_lib.read_utdf import (generate_intersection_from_Links,
                                          read_UTDF_file)
from utdf2gmns.func_lib.geocoding_Nodes import update_node_from_one_intersection
from utdf2gmns.func_lib.signalized_intersections import parse_signalized_intersection
from utdf2gmns.func_lib.geocoding_Links import generate_links

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
    def __init__(self, utdf_filename: str, city_name: str):
        self._utdf_filename = utdf_filename
        self._city_name = city_name

        self._is_geocoding_intersections = False

    def load_utdf(self) -> None:
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

        # save to instance variable
        self.utdf_dict = utdf_dict_data
        return None

    def geocoding_intersections(self, dist_threshold: float = 0.01, single_coord: dict = {}) -> None:
        """Geocoding intersections
        Firstly, geocoding one intersection from address
        Then, according to the Nodes information, calculate all intersections based on relative distance.

        Args:
            dist_threshold (float): distance threshold for geocoding intersections, defaults to 0.01.
            single_coord (dict): a single intersection coordinate data, defaults to {}.
                If not provided, geocoding one intersection from address.
                sample data: {"INTID": 1, "x_coord": -114.568, "y_coord": 35.155}

        Raises:
            ValueError: Single coordinate should have INTID, x_coord, and y_coord keys!
            ValueError: INTID should be an integer!
            ValueError: x_coord should be a float!
            ValueError: y_coord should be a float!
            Exception: No valid intersection is geo-coded!

        Returns:
            None
        """

        # check if single coordinate is provided and validate it's value
        if single_coord:
            if not {"INTID", "x_coord", "y_coord"}.issubset(set(single_coord.keys())):
                raise ValueError("Single coordinate should have INTID, x_coord, and y_coord keys!")
            if not isinstance(single_coord.get("INTID"), int):
                raise ValueError("INTID should be an integer!")
            if not isinstance(single_coord.get("x_coord"), float):
                raise ValueError("x_coord should be a float!")
            if not isinstance(single_coord.get("y_coord"), float):
                raise ValueError("y_coord should be a float!")

            # check if id is in the Nodes
            if single_coord.get("INTID") not in self.utdf_dict.get("Nodes")["INTID"].tolist():
                raise ValueError("INTID is not in the Nodes!")

            single_intersection = single_coord

        else:
            # generate intersections with name for coordinations
            df_utdf_intersection = generate_intersection_from_Links(self.utdf_dict.get("Links"),
                                                                    self._city_name)

            # geocoding one intersection from address, with threshold 0.01 km
            single_intersection = generate_intersection_coordinates(
                df_utdf_intersection,
                dist_threshold=dist_threshold,
                geocode_one=True)

            # check if the single_intersection is empty
            if single_intersection["INTID"] is None:
                raise Exception("No valid intersection is geo-coded!"
                                " Please change dist_threshold or provide single_coord manually.")

        # update Nodes from single_intersection
        node_df = update_node_from_one_intersection(single_intersection, self.utdf_dict.get("Nodes"), self.network_unit)

        self.utdf_dict["Nodes"] = node_df
        self._is_geocoding_intersections = True
        return None

    def signalize_intersections(self) -> None:
        """Signalize intersections
        """

        # get signal intersection id from phase
        df_phase = self.utdf_dict.get("Phases")
        df_lane = self.utdf_dict.get("Lanes")
        signal_int_id = df_phase["INTID"].unique()

        signal_intersections = {
            int_id: parse_signalized_intersection(df_phase, df_lane, int_id)
            for int_id in signal_int_id
        }
        self.network_signal_intersections = signal_intersections
        return None

    def create_network(self, default_width: float = 0.0) -> None:
        """Create network from UTDF data by combining Nodes, Links, Lanes, and Phases
        """
        width = default_width or self.network_settings.get("DefWidth", 12)
        unit = self.network_unit

        links_dict = generate_links(self.utdf_dict.get("Links"), self.utdf_dict.get("Nodes"), width, unit)
        self.network_links = links_dict

        return None

    def save_results_to_csv(self, out_dir: str, *, intersections: bool = True, links: bool = True, UTDF: bool = False):
        """Save results to csv files

        Args:
            out_dir (str): output directory to save the results
            intersections (bool): whether to save coordinated intersections to csv.
                Defaults to True.
            links (bool): whether to save link geometry to csv. Defaults to True.
            UTDF (bool): Whether to save categorized UTDF data to csv. Defaults to True.
                Categories include Nodes, Networks, Timeplans, Links, Lanes, and Phases.
        """

        # check if the output directory exists
        if not os.path.exists(out_dir):
            raise FileNotFoundError(f"Output directory {out_dir} not found!")

        if UTDF:
            if hasattr(self, "utdf_dict"):
                for category in self.utdf_dict.keys():
                    self.utdf_dict[category].to_csv(os.path.join(out_dir, f"UTDF_{category}.csv"), index=False)

        if intersections:
            if self._is_geocoding_intersections:
                self.utdf_dict.get("Nodes").to_csv(os.path.join(out_dir, "intersections.csv"), index=False)
            else:
                print("  :No intersection geometry generated!, please geocode intersections first!")

        if links:
            if hasattr(self, "network_links"):
                df_lst = []
                for int_id, value in self.network_links.items():
                    df_value = pd.DataFrame([value])
                    df_value["LinkID"] = int_id
                    df_lst.append(df_value)
                pd.concat(df_lst).to_csv(os.path.join(out_dir, "links.csv"), index=False)
            else:
                print("  :No link geometry generated!, please create network first!")
