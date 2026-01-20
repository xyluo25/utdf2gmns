[![PyPI version](https://badge.fury.io/py/utdf2gmns.svg)](https://badge.fury.io/py/utdf2gmns)[![Downloads](https://static.pepy.tech/badge/utdf2gmns)](https://pepy.tech/project/utdf2gmns)[![](https://img.shields.io/pypi/wheel/gensim.svg)](https://pypi.org/project/utdf2gmns/)[![](https://img.shields.io/pypi/pyversions/utdf2gmns.svg)](https://www.python.org/)[![](https://img.shields.io/github/release-date/xyluo25/utdf2gmns.svg)](https://img.shields.io/github/release-date/xyluo25/utdf2gmns.svg)[![](https://readthedocs.org/projects/utdf2gmns/badge/?version=latest)](https://utdf2gmns.readthedocs.io/en/latest/?badge=latest)[![](https://img.shields.io/github/contributors/xyluo25/utdf2gmns)](https://github.com/xyluo25/utdf2gmns/graphs/contributors)[![](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/license/mit)

- [utdf2gmns](#utdf2gmns)
  - [Introduction](#introduction)
  - [Required Input Data](#required-input-data)
  - [Installation](#installation)
  - [Quick Python Example](#quick-python-example)
    - [Prepare your UTDF File](#prepare-your-utdf-file)
    - [Initialize the UTDF2GMNS](#initialize-the-utdf2gmns)
    - [Signalized Intersection Calculation and Visualization (Optional)](#signalized-intersection-calculation-and-visualization-optional)
    - [Geocoding Intersections (Use Automatic Geocoding)](#geocoding-intersections-use-automatic-geocoding)
    - [Geocoding Intersections (Use Manual Geocoding)](#geocoding-intersections-use-manual-geocoding)
    - [Create GMNS links](#create-gmns-links)
    - [Save GMNS Network](#save-gmns-network)
    - [Convert UTDF Network to SUMO](#convert-utdf-network-to-sumo)
    - [Visualize the Network](#visualize-the-network)
    - [Quick Example (Full Code)](#quick-example-full-code)
  - [Call for Contributions](#call-for-contributions)
  - [How to Cite](#how-to-cite)

# utdf2gmns

## Introduction

An AMS(Analysis, Modeling and Simulation) tool to convert utdf file to different formats, including GMNS, SUMO etc.

utdf2gmns explored an automatic process of network coordinating, traffic signal integration, traffic flow conversion from Synchro to SUMO, identifying both the feasibility and challenges involved. The approach began with a comparative analysis of traffic network features, data formats, and signal timing schemas between the two platforms. Key challenges in converting Synchro UTDF data into microsimulation-ready networks focusing on signal integration, spatial conversion, and turning flow accuracy. Signal conversion remains a critical bottleneck, requiring precise alignment of phasing, timing, and coordination data to ensure reliable simulation outcomes. Network conversion also presents difficulties, particularly in translating Synchro’s relative coordinate system into georeferenced formats compatible with GIS tools. Additionally, accurately transforming turning movement data is essential for modeling realistic intersection behavior but often involves tedious manual preprocessing.

While previous efforts have made progress in isolated aspects of the conversion process, none offer a fully automated and scalable end-to-end solution. To fill this gap, we introduce [utdf2gmns](https://pypi.org/project/utdf2gmns/), an open-source Python tool designed to automate the transformation of Synchro UTDF files into GMNS-compliant networks for SUMO simulation. The tool supports automatic geocoding, integration with the Sigma-X engine for intersection analysis, robust SUMO network generation, and extendibility to other microsimulation platforms. Future work will focus on expanding support for adaptive signal systems, incorporating real-time data inputs, and enhancing interoperability with additional simulation frameworks to promote reproducibility and collaborative research in traffic modeling.

Official Document: https://utdf2gmns.readthedocs.io/en/latest/

Official GitHub: https://github.com/xyluo25/utdf2gmns

Previous Development: https://github.com/asu-trans-ai-lab/utdf2gmns ([Initial commit: Dec 17, 2022, total 144 commits](https://github.com/asu-trans-ai-lab/utdf2gmns/commits/main/?after=29c374e7d0d5315605a2d8e6a4fa7b40fb54921f+139))

## Required Input Data

* [X] UTDF.csv  (file name does not need to be UTDF.csv, it can be any name.)

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
# But it requires user to provide a single intersection coordinate.

# INTID is the intersection ID in UTDF file
# x_coord and y_coord are the coordinates of the intersection in decimal degrees (Latitude and Longitude)

single_coord={"INTID": "1", "x_coord": -114.568, "y_coord": 35.155}
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

## How to Cite

If you use utdf2gmns in your work or research, please use the following entry:

```plaintext
Xiangyong, Luo and Xuesong Simon，Zhou. “xyluo25/utdf2gmns: V1.0.0”. Zenodo, December 17, 2022. https://doi.org/10.5281/zenodo.14825686.
```
