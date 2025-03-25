## utdf2gmns

## Introduction

An AMS(Analysis, Modeling and Simulation) tool to convert utdf file to different formats, including GMNS, SUMO etc

## Required Input Data

* [X] UTDF.csv

## Installation

`pip install utdf2gmns`

## Simple Example

```python
import utdf2gmns as ug

if __name__ == "__main__":

    region_name = " Bullhead City, AZ"
    path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"

    # Step 1: Initialize the UTDF2GMNS
    net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name)

    # Step 2: Geocode intersection
	# if user manually provide single intersection coordinate, such as:
	# single_coord={"INTID": "1", "x_coord": -114.568, "y_coord": 35.155}
	# Intersections will geocoded base on this point (Recommended Method)
    net.geocode_utdf_intersections(single_intersection_coord={}, dist_threshold=0.01)

    # Step 3: create network links: user can genrate polygon-link or line-link
    net.create_gmns_links(is_link_polygon=False)

    # Step 4: create signal intesection control
    net.create_signal_control()

    # Step 5: convert UTDF network to GMNS format (csv)
    net.utdf_to_gmns(incl_utdf=True)

    # Step 6 (optional): convert UTDF netowrk to SUMO
    net.utdf_to_sumo(sumo_name="", show_warning_message=False)

    # Step 7 (optional): visualize the network
    # create matplotlib png
    # ug.plot_net_mpl(net)

    # create keplergl interactive map
    # net_map = ug.plot_net_keplergl(net, save_fig=True, fig_name="Bullhead_City.html")

```

## TODO LIST

* [ ] create more xml files for sumo
* [ ] convert volume/flow to .rou.xml
* [ ] Generate sumo Net use sumolib
* [ ] Add cycle length and green time for each movement.
* [X] Print out how many intersections being geocoded.
* [X] Print out check log.
* [X] Number of lanes of the movements from synchro file.
* [X] Print geocoding details (in percentage)
* [X] Add detailed information for user to load coordinated intersection data.
* [X] geocoding Lanes
* [X] Cvt gmns to SUMO
* [X] update plot function to visuzalize gmns node and links
* [X] create .rou.xml for sumo (auto generated)

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

```plaintext
Luo, X. and Zhou, X. (2022, December 17). UTDF2GMNS. Retrieved from https://github.com/xyluo25/utdf2gmns
```
