# -*- coding:utf-8 -*-
##############################################################
# Created Date: Monday, November 28th 2022
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################

# from geopy.geocoders import Nominatim
# import googlemaps
from typing import Any, TYPE_CHECKING

# from pathlib import Path
# import geocoder
import pandas as pd
import pyufunc as pf
# from pyufunc import func_running_time
from utdf2gmns.util_lib.pkg_utils import calculate_point2point_distance_in_km

if TYPE_CHECKING:
    import geocoder  # for type hinting only, ensure geocoder is imported when TYPE_CHECKING


@pf.requires("geocoder", verbose=False)
def geocoder_geocoding_from_address(address: str) -> tuple:
    """geocoding from address using geocoder

    Args:
        address (str): the address to be geocoded

    Returns:
        tuple: the longitude and latitude of the address
    """
    pf.import_package("geocoder", verbose=False)  # ensure geocoder is imported
    import geocoder  # ensure geocoder is imported

    # initialize geocoder arcgis client
    location_instance = geocoder.arcgis(address).geojson

    # get the location
    try:
        location_lng_lat = list(location_instance["features"][0]["geometry"]["coordinates"])
    except Exception:
        location_lng_lat = [0, 0]

    return location_lng_lat


@pf.func_running_time
def generate_intersection_coordinates(df_intersection: pd.DataFrame,
                                      dist_threshold: float = 0.01,
                                      geocode_one: bool = False) -> Any:
    """generate_coordinates_from_intersection: geocoding intersections

    Args:
        df_intersection (pd.DataFrame): the dataframe of intersections
        dist_threshold (float): maximum distance threshold to compare two nodes,
            defaults to 0.01 (10 meters), unit: km
        geocode_one: geocoding one valid intersection, defaults to False.

    Raises:
        Exception: intersection_name and city_name must included in the dataframe
        Exception: geocoding intersections failed

    Returns:
        pd.DataFrame or dict: a dataframe of intersections with coordinates or a dictionary of one intersection
    """

    # dist_threshold is the threshold to determine whether the intersection is able to geocode, using km as unit
    df = df_intersection.copy(deep=True)

    # check required columns exist in the dataframe
    if not {"intersection_name", "city_name"}.issubset(set(df.columns)):
        raise Exception("intersection_name and city_name are not in the dataframe,"
                        " please check the input file.")

    # Create one column named "reversed_int_name"
    for i in range(len(df)):
        if "&" in df.loc[i, "intersection_name"]:
            int_name_lst = df.loc[i, "intersection_name"].split("&")
            df.loc[i, "reversed_int_name"] = int_name_lst[1] + " & " + int_name_lst[0]
        else:
            df.loc[i, "reversed_int_name"] = df.loc[i, "intersection_name"]

    # create two columns named "full_name_int" and "full_name_int_r" as reverse of "full_name_int"
    df["full_name_int"] = df["intersection_name"] + ", " + df["city_name"]
    df["full_name_int_r"] = df["reversed_int_name"] + ", " + df["city_name"]

    # Step 4: geocoding
    print("  :geocoding intersections...")
    int_full_name_list = df["full_name_int"].tolist()
    int_full_name_r_list = df["full_name_int_r"].tolist()

    # the number of intersections to be geocode
    num_intersection = len(int_full_name_list)
    distance = []

    lng_lat_full_name = []
    lng_lat_full_name_reversed = []

    for i in range(num_intersection):
        int_id = df.loc[i, "synchro_INTID"]
        try:
            lng_lat = geocoder_geocoding_from_address(int_full_name_list[i])
            lng_lat_reverse = geocoder_geocoding_from_address(int_full_name_r_list[i])

            dist = calculate_point2point_distance_in_km(lng_lat, lng_lat_reverse)

            if geocode_one and lng_lat != (0, 0) and lng_lat_reverse != (0, 0) and dist <= dist_threshold:
                x_coord = lng_lat[0]
                y_coord = lng_lat[1]
                print(f"   :Geocode ID: {int_id}, coords: {x_coord}, {y_coord}.")
                return {"INTID": int_id, "x_coord": x_coord, "y_coord": y_coord}

            lng_lat_full_name.append(lng_lat)
            lng_lat_full_name_reversed.append(lng_lat_reverse)
            distance.append(dist)

        except Exception as e:
            print(f"  :Could not geocode intersection id: {int_id} with {e}")

    # if not return value in the loop, which means no valid intersection is geo-coded
    if geocode_one:
        return {"INTID": None, "x_coord": None, "y_coord": None}

    # create new column named distance_from_full_name
    for i in range(len(df)):
        df["distance_to_full_name"] = distance

        if distance[i] <= dist_threshold:
            df.loc[i, "x_coord"] = lng_lat_full_name[i][0]
            df.loc[i, "y_coord"] = lng_lat_full_name_reversed[i][1]

        else:
            # use None to indicate the intersection is not able to geocode
            df.loc[i, "x_coord"] = None
            df.loc[i, "y_coord"] = None

    created_column_names = ["reversed_int_name", "full_name_int",
                            "full_name_intersection_reversed", "distance_to_full_name"]
    df_final = df.loc[:, ~df.columns.isin(created_column_names)]

    # print summary information
    print(
        f" {len(df_final) - df_final['x_coord'].isna().sum()} / {len(df_final)} intersections geocoded.")
    print(
        f" {df_final['x_coord'].isna().sum()} / {len(df_final)} intersections are not able to geocode.")

    return df_final

# def googlemaps_geocoding_from_address(address, api_key) -> tuple:
#
#     # initialize googlemaps client
#     gmaps = googlemaps.Client(key=api_key)
#
#     # Geocoding an address
#     location_instance = gmaps.geocode(address)
#
#     # get the location
#     location_lng_lat = (location_instance[0]['geometry']['location']['lat'], location_instance[0]['geometry']['location']['lng'])
#
#     return location_lng_lat
#
#
# def geopy_geocoding_from_address(address: str) -> tuple:
#
#     # initialize geopy client
#     geo_locator = Nominatim(user_agent="myGeopyGeocoder")
#
#     # Geocoding an address
#     try:
#         location = geo_locator.geocode(address, timeout=10)
#         location_lng_lat = (location.longitude, location.latitude)
#     except Exception as e:
#
#         location_lng_lat = (0,0)
#         print(
#             f"Error: {address} is not able to geocode, for {e}, try to use (0 ,0) to as lng and lat \n")
#
#     return location_lng_lat
