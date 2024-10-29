## utdf2gmns

## Introduction

A AMS(Analysis, Modeling and Simulation) tool to convert utdf file to different formats, including GMNS, SUMO etc

## Required Input Data

* [X] UTDF.csv

## **Package dependencies**:

* [X] geocoder==1.38.1
* [X] pandas==2.2.3
* [X] xlml >=5.3.0
* [X] pyufunc == 0.3.7
* [X] shapely == 2.0.6
* [X] matplotlib >=3.9.2
* [X] pyproj == 3.7.0

## Installation

`pip install utdf2gmns`

## Simple Example

```python
import utdf2gmns as ug
import pandas as pd

if __name__ == "__main__":

    city = " Bullhead City, AZ"
    path = r"datasets\data_bullhead_seg4"

    # get user added intersection data
    path_user_added_intersection = fr"{path}\utdf_intersection_sample.csv"

    # option= 1, generate movement_utdf.csv directly
    # option= 2, generate movement_utdf.csv step by step (more flexible)
    option = 2

    if option == 1:
        # NOTE: Option 1, generate movement_utdf.csv directly

        res = ug.generate_movement_utdf(path, city, isSave2csv=False,
                                        path_utdf_intersection=path_user_added_intersection)

    if option == 2:
        # NOTE: Option 2, generate movement_utdf.csv step by step (more flexible)
        path_utdf = fr"{path}\UTDF.csv"
        path_node = fr"{path}\node.csv"
        path_movement = fr"{path}\movement.csv"

        # Step 1: read UTDF.csv
        utdf_dict_data = ug.read_UTDF_file(path_utdf)

        # Step 1.1: get intersection data from UTDF.csv
        df_intersection = ug.generate_intersection_from_Links(utdf_dict_data["Links"], city_name=city)

        utdf_dict_data["utdf_intersection"] = df_intersection

        # Step 1.2: geocoding intersection data

        # # Step 1.2.1: if user added intersection data, read it
        # df_intersection_geo = pd.read_csv(path_user_added_intersection)

        # Step 1.2.2: else generate intersection data from UTDF.csv
        df_intersection_geo = ug.generate_intersection_coordinates(df_intersection)

        # Step 2: read node.csv and movement.csv
        df_node = pd.read_csv(path_node)
        df_movement = pd.read_csv(path_movement)

        # Step 3: match intersection_geo and node
        df_intersection_node = ug.match_intersection_node(df_intersection_geo, df_node, max_distance_threshold=0.1)

        # Step 4: match movement and intersection_node
        df_movement_intersection = ug.match_movement_and_intersection_node(df_movement, df_intersection_node)

        # Step 5: match movement and utdf_lane
        df_movement_utdf_lane = ug.match_movement_utdf_lane(df_movement_intersection, utdf_dict_data)

        # Step 6: match movement and utdf_phase_timeplans
        df_movement_utdf_phase = ug.match_movement_utdf_phase_timeplans(df_movement_utdf_lane, utdf_dict_data)

        # Step 7: sve movement_utdf.csv
        # df_movement_utdf_phase.to_csv(fr"{path}\movement_utdf.csv", index=False)

```

## TODO LIST

* [X] Print out how many intersections being geocoded.
* [X] Print out check log.
* [X] Number of lanes of the movements from synchro file.
* [X] Print geocoding details (in percentage)
* [ ] Add cycle length and green time for each movement.
* [ ] Add detailed information for user to load coordinated intersection data.
* [ ] geocoding Lanes
* [ ] Cvt gmns to SUMO

## Call for Contributions

The utdf2gmns project welcomes your expertise and enthusiasm!

Small improvements or fixes are always appreciated. If you are considering larger contributions to the source code, please contact us through email:

    Dr. Xiangyong Luo:  luoxiangyong01@gmail.com

    Dr. Xuesong Simon Zhou:  xzhou74@asu.edu

Writing code isn't the only way to contribute to utdf2gmns. You can also:

* Review pull requests
* Help us stay on top of new and old issues
* Develop tutorials, presentations, and other educational materials
* Develop graphic design for our brand assets and promotional materials
* Translate website content
* Help with outreach and onboard new contributors
* Write grant proposals and help with other fundraising efforts

For more information about the ways you can contribute to utdf2gmns, visit [our GitHub](https://github.com/asu-trans-ai-lab/utdf2gmns). If you' re unsure where to start or how your skills fit in, reach out! You can ask by opening a new issue or leaving a comment on a relevant issue that is already open on GitHub.

## **How to Cite**

If you use utdf2gmns in your work or research, please use the following entry:

Luo, X. and Zhou, X. (2022, December 17). UTDF2GMNS. Retrieved from https://github.com/xyluo25/utdf2gmns
