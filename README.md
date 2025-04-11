# utdf2gmns

## Introduction

An AMS(Analysis, Modeling and Simulation) tool to convert utdf file to different formats, including GMNS, SUMO etc

Official Document: https://utdf2gmns.readthedocs.io/en/latest/

Official GitHub: https://github.com/xyluo25/utdf2gmns

## Required Input Data

* [X] UTDF.csv

## [Installation](https://utdf2gmns.readthedocs.io/en/latest/)

`pip install utdf2gmns`

## Quick Python Example

Notes:

* This quick start guide assumes you have a valid UTDF file and the required dependencies installed.
* The following example uses a sample UTDF file from the Bullhead City, AZ dataset. You can replace it with your own UTDF file as needed.
* The example below uses automatic geocoding by default. You can choose to geocode automatically ::ref:: automatic_geociding or manually ::ref:: manual_geocoding as per your requirement.

### Prepare your UTDF File

Please note that file name does not need to be UTDF.csv, it can be any name.

```python
import utdf2gmns as ug

region_name = " Bullhead City, AZ"  # Name of the region the UTDF file represents
path_utdf = r"datasets\data_bullhead_seg4\UTDF.csv"  # Path to the UTDF file
```

### Initialize the UTDF2GMNS

```python
# Initialize the UTDF2GMNS object with the UTDF file and region name
net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name, verbose=False)
```

### Signalized Intersection Calculation and Visualization (Optional)

This is the optional step to generate each signalized intersections and visualize them using Sigma-X engine. For large networks, this step may take a long time. (The code will print out total time taken for this step)

```python
# Generate signalized intersections and visualize them using Sigma-X engine
net.utdf_to_gmns_signal_ints()
```

### Geocoding Intersections (Use Automatic Geocoding)

```python
# Geocode intersections using automatic geocoding method

# dist_threshold: The distance threshold for geocoding (default is 0.01 km), unit is km
net.geocode_utdf_intersections(dist_threshold=0.01)
```

### Geocoding Intersections (Use Manual Geocoding)

```python
# Geocode intersections using manual geocoding method
# This method could provide more accurate geocoding results,
# Bit it requires user to provide a single intersection coordinate.

# INTED is the intersection ID in UTDF file
# x_coord and x_coord are the coordinates of the intersection in decimal degrees (Latitude and Longitude)

single_coord={"INTID": "1", "x_coord": -114.568, "x_coord": 35.155}
net.geocode_utdf_intersections(single_intersection_coord=single_coord)
```

### Create GMNS links

```python
# Create GMNS links (polygon-link or line-link)
# is_link_polygon: If True, create polygon links; if False, create line links (default is False)
net.create_gmns_links(is_link_polygon=False)
```

### Save GMNS Network

This step will convert the UTDF network to GMNS format and save it to CSV and json files. Specifically, it will save the following files:

> * **nodes.csv** : Contains information about the nodes in the network.
> * **links.csv** : Contains information about the links in the network.
> * **signal.json** : Contains information about the signals of each signalized intersection in the network.
> * **utdf_network.csv** : Contains information from the UTDF file regarding the network configuration and settings.
> * **utdf_nodes.csv** : Contains information from the UTDF file regarding the nodes in the network.
> * **utdf_links.csv** : Contains information from the UTDF file regarding the links in the network.
> * **utdf_lanes.csv** : Contains information from the UTDF file regarding the lanes in the network.
> * **utdf_phases.csv** : Contains information from the UTDF file regarding the phases in the network.
> * **utdf_timeplans.csv** : Contains information from the UTDF file regarding the time plans in the network.

```python
# Convert UTDF network to GMNS format (CSV and JSON files)
net.utdf_to_gmns(incl_utdf=True)
```

### Convert UTDF Network to SUMO

Since we have already converted the UTDF network to GMNS format, we can now convert it to SUMO format. This step will save the following files:

> * **nod.xml** : Contains information about the nodes in the SUMO network.
> * **edg.xml** : Contains information about the edges in the SUMO network.
> * **con.xml** : Contains information about the connections in the SUMO network.
> * **flow.xml** : Contains information about the flow in the SUMO network.
> * **add.xml** : contains loop detectors information.
> * **net.xml** : Contains information about the network in the SUMO network.
> * **rou.xml** : Contains information about the routes in the SUMO network.
> * **.sumocfg** : Contains configuration information for the SUMO network.

```python
# Convert UTDF network to SUMO format (SUMO files)

# sumo_name is the name of the SUMO network (default is "utdf_to_sumo")
net.utdf_to_sumo(sumo_name="", show_warning_message=True)
```

### Visualize the Network

We provide two methods to visualize the network: Keplergl and Matplotlib.

* Keplergl: A powerful tool for visualizing large-scale geospatial data.
* Matplotlib: A widely used library for creating static, animated, and interactive visualizations in Python.

```python
net_map = ug.plot_net_mpl(net, save_fig=True, fig_name="Bullhead_City.png")
net_map = ug.plot_net_keplergl(net, save_fig=True, fig_name="Bullhead_City.html")
```

Another way to visualize the network is to open generate .sumocfg file (Open use sumo-gui).

### Quick Example (Full Code)

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

    # Step 4: convert UTDF network to GMNS format (csv)
    net.utdf_to_gmns(incl_utdf=True)

    # Step 5 (optional): convert UTDF netowrk to SUMO
    net.utdf_to_sumo(sumo_name="", show_warning_message=False)

    # Step 6 (optional): visualize the network
    # create matplotlib png
    # ug.plot_net_mpl(net)

    # create keplergl interactive map
    # net_map = ug.plot_net_keplergl(net, save_fig=True, fig_name="Bullhead_City.html")
```

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

For more information about the ways you can contribute to utdf2gmns, visit [our GitHub](https://github.com/xyluo25/utdf2gmns). If you' re unsure where to start or how your skills fit in, reach out! You can ask by opening a new issue or leaving a comment on a relevant issue that is already open on GitHub.

## **How to Cite**

If you use utdf2gmns in your work or research, please use the following entry:

```plaintext
Xiangyong, Luo and Xuesong Simon，Zhou. “xyluo25/utdf2gmns: V1.0.0”. Zenodo, December 17, 2022. https://doi.org/10.5281/zenodo.14825686.
```
