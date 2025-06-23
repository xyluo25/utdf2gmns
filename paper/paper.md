---
title: "utdf2gmns: A Python Package for Automating Synchro UTDF to SUMO Simulation"
tags:
  - Python
  - UTDF
  - SUMO
  - Traffic Micro-simulation
  - Automation
authors:
  - name: Xiangyong Luo
    orcid: 0009-0003-1290-9983
    affiliation: "1" # (Multiple affiliations must be quoted)
  - name: Yiran Zhang
    orcid: 0000-0002-7392-8841
    affiliation: "2"
  - name: Xuesong (Simon) Zhou
    orcid: 0000-0002-9963-5369
    affiliation: "3"

affiliations:
  - name: Oak Ridge National Laboratory, United States
    index: 1
  - name: University of Washington, Seattle, WA, United States
    index: 2
  - name: Arizona State University, Tempe, AZ, United States
    index: 3

date: 11 April 2025
bibliography: paper.bib
---
# Summary

UTDF2GMNS[^1] implements an automated workflow for network coordination, traffic signal integration, and traffic flow conversion from Synchro to SUMO. The process begins with a comparative analysis of network topologies, data representations, and signal timing schemas in both environments. Converting Synchro UTDF data to a network ready for microsimulation poses several challenges, including accurate signal integration, spatial transformation, and preservation of turning flow fidelity. Signal conversion represents a primary bottleneck, as it demands precise mapping of phasing plans, timing parameters, and coordination strategies to ensure valid simulation results. Network conversion is further complicated by translating Synchro’s relative coordinate system into georeferenced formats compatible with geographic information system tools. Furthermore, accurate transformation of turning movement data is essential for realistic intersection modeling.

Existing methods address only isolated conversion tasks and lack a fully automated, scalable end-to-end workflow. To fill this gap, we introduce [utdf2gmns](https://pypi.org/project/utdf2gmns/), an open-source Python library that automates the transformation of Synchro UTDF files into GMNS-compliant SUMO networks. utdf2gmns provides automatic geocoding, Sigma-X engine integration for intersection analysis, robust SUMO network generation, and extensibility to other microsimulation platforms. Future work will extend support for adaptive signal control, integrate real-time data inputs, and enhance interoperability with additional simulation frameworks to promote reproducibility and collaborative traffic-modeling research.

# Statement of need

Traffic microsimulation is essential for evaluating and improving urban transportation systems by providing high-resolution analysis of flow, congestion, and infrastructure performance. Such simulations depend on precise modeling of signal control, network geometry, and turning movements. Although Synchro’s Universal Traffic Data Format (UTDF) delivers comprehensive intersection data, converting UTDF into simulation-ready networks remains manual, labor-intensive, and error-prone, limiting seamless interoperability with microsimulation platforms.

Several critical challenges remain when converting Synchro UTDF data into microsimulation-compatible networks, such as those required by Simulation of Urban Mobility (SUMO) [@lopez2018microscopic]. First, accurate signal conversion demands detailed extraction and mapping of phasing, timing, and coordination parameters into standardized control formats; errors here can substantially degrade simulation fidelity. Second, network conversion requires transforming Synchro’s relative coordinate system into georeferenced longitude–latitude coordinates for seamless GIS integration, a labor-intensive and error-prone process that limits scalability. Third, realistic intersection dynamics hinge on precise turning movement conversion, which typically involves extensive manual preprocessing; inaccuracies at this stage can propagate through the simulation, undermining the validity of subsequent analyses.

To address these gaps[@zhang2024integration;@ban2022multiscale;@coogan2021coordinated;@udomsilp2017traffic;@singh2017impact], we present utdf2gmns ([Luo and Zhou 2022](https://github.com/xyluo25/utdf2gmns)), an open-source Python tool that automates the conversion of Synchro UTDF files into GMNS-compliant networks [@smith2020general] and generates simulation-ready inputs for SUMO. By leveraging the GMNS, a robust framework for standardized network representation [@berg2022gmns; @lu2023virtual; @luo2024strategic; @luo2024innovation], utdf2gmns enhances data consistency, reproducibility, and collaboration through four core capabilities: it automates geocoding of Synchro’s relative coordinates into accurate longitude–latitude pairs; integrates with the Sigma-X engine ([Milan 2022](https://github.com/milan1981/Sigma-X)) to extract and optimize key intersection metrics (phasing diagrams, turning volumes, movement capacities, volume-to-capacity ratios, and control delays); generates GMNS-compliant SUMO networks that fully preserve signal coordination, traffic flows, and turning movements; and provides a modular architecture for extension to additional microsimulation platforms, thereby promoting broader standardization and community-driven development.

Hands-On Tutorial

```python

import utdf2gmns as ug


if __name__ == "__main__":

    region_name = "Region-name"  # e.g. " Tempe, AZ"
    path_utdf = "Path-to-UTDF.csv"  # e.g "datasets/data_bullhead_seg4/UTDF.csv

    # Step 1: Initialize the UTDF2GMNS
    net = ug.UTDF2GMNS(utdf_filename=path_utdf, region_name=region_name, verbose=False)

    # Step 2: Geocode intersection
    net.geocode_utdf_intersections(single_intersection_coord={}, dist_threshold=0.01)

    # Step 3: convert UTDF network to GMNS format (csv)
    net.utdf_to_gmns(incl_utdf=True)

    # Step 4: convert UTDF network to SUMO
    net.utdf_to_sumo(sim_name="", show_warning_message=True, disable_U_turn=True, sim_duration=7200)

    # Step 5 (optional): visualize the network
    net_map = ug.plot_net_mpl(net, save_fig=True, fig_name=f"{region_name}.png")
    net_map = ug.plot_net_keplergl(net, save_fig=True, fig_name=f"{region_name}.html")

    # Step 6: Sigma-X visualize signalized intersection
    # net.utdf_to_gmns_signal_ints()

```

# Acknowledgements

Prof.Xuesong Simon Zhou from Arizona State University, for his valuable feedback and suggestions during the development of the project. Prof. Milan Zlatkovic from University of Wyoming, for the power of sigma-x engine to visualize signalized intersections. Yiran Zhang from University of Washington, for her valuable feedback and debugging of signal conversation during the early development of the project.

Additional support was provided by the U.S. Department of Energy (DOE), Office of Energy Efficiency and Renewable Energy (EERE), Vehicle Technologies Office. Any opinions, findings, and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the USDOT, DOE, and the U.S. Government assumes no liability for the contents or use thereof.

# References

[^1]: This manuscript has been authored in part by UT-Battelle, LLC, under contract DE-AC05-00OR22725 with the US Department of Energy (DOE). The publisher acknowledges the US government license to provide public access under the [DOE Public Access Plan](https://www.energy.gov/doe-public-access-plan)
