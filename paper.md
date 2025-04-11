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

affiliations:
  - name: Xiangyong Luo, Oak Ridge National Laboratory, United States
    index: 1
date: 11 April 2025
bibliography: paper.bib
---

# Summary

An AMS (Analysis, Modeling and Simulation) tool to convert utdf file to different formats, including GMNS, SUMO etc.

utdf2gmns explored an automatic process of network coordinating, traffic signal integration, traffic flow conversion from Synchro to SUMO, identifying both the feasibility and challenges involved. The approach began with a comparative analysis of traffic network features, data formats, and signal timing schemas between the two platforms. Key challenges in converting Synchro UTDF data into microsimulation-ready networks focusing on signal integration, spatial conversion, and turning flow accuracy. Signal conversion remains a critical bottleneck, requiring precise alignment of phasing, timing, and coordination data to ensure reliable simulation outcomes. Network conversion also presents difficulties, particularly in translating Synchro’s relative coordinate system into georeferenced formats compatible with GIS tools. Additionally, accurately transforming turning movement data is essential for modeling realistic intersection behavior but often involves tedious manual preprocessing.

While previous efforts have made progress in isolated aspects of the conversion process, none offer a fully automated and scalable end-to-end solution. To fill this gap, we introduce [utdf2gmns](https://pypi.org/project/utdf2gmns/), an open-source Python tool designed to automate the transformation of Synchro UTDF files into GMNS-compliant networks for SUMO simulation. The tool supports automatic geocoding, integration with the Sigma-X engine for intersection analysis, robust SUMO network generation, and extendibility to other microsimulation platforms. Future work will focus on expanding support for adaptive signal systems, incorporating real-time data inputs, and enhancing interoperability with additional simulation frameworks to promote reproducibility and collaborative research in traffic modeling.

# Statement of need

Traffic microsimulation is essential for evaluating and enhancing urban transportation systems, providing insights into traffic flow management, congestion mitigation, and infrastructure improvements. Accurate simulations require precise representation of traffic signals, network geometries, and turning movements. However, conventional approaches to preparing simulation-ready networks, particularly from popular tools such as Synchro, remain largely manual and error-prone. Synchro's Universal Traffic Data Format (UTDF) provides comprehensive intersection data but lacks efficient interoperability with microsimulation software, leading to labor-intensive data preparation, potential inaccuracies, and inconsistencies.

Several critical challenges persist in effectively converting Synchro UTDF data into microsimulation-compatible networks, such as those used by Simulation of Urban Mobility (SUMO) `[@lopez2018microscopic]`. One primary challenge is signal conversion. Translating intersection control parameters accurately into standardized formats involves detailed extraction, interpretation, and alignment of signal phasing, timing, and coordination data. Inaccuracies in this step can significantly affect the reliability of simulation outputs, underscoring the necessity for precise and automated methods. Another substantial challenge involves network conversion. Synchro typically utilizes relative coordinate systems, which must be converted into real-world geographic coordinates (longitude and latitude) for effective integration with Geographic Information Systems (GIS). This conversion process is often tedious, error-prone, and requires considerable manual effort, complicating large-scale or complex network simulations. Additionally, accurate turning flow conversion is essential for realistic simulation of intersection dynamics. Converting turning movement data, which is crucial for capturing the complexity of urban traffic interactions, frequently involves extensive manual preprocessing. Imprecise conversion in this stage can propagate through simulations, compromising the accuracy and usefulness of the resulting analyses.

Existing research and implementations have not yet provided comprehensive solutions to all the identified challenges simultaneously. `@zhang2024integration` introduced a method to convert Synchro signal data to a SUMO network; however, this conversion requires preliminary preparation of both the Synchro UTDF file and the SUMO network separately. `@ban2022multiscale` converted Synchro signal data into SUMO to facilitate calibration within a vehicle-traffic-demand (VTD) simulation platform; however, the networks used in Synchro and SUMO were prepared independently and differently. `@coogan2021coordinated` conducted an early effort to convert Synchro's geometric and phasing data into SUMO, primarily emphasizing geometry conversion. Nevertheless, their network conversion employed relative coordinates and was limited to selected intersections, lacking automation and scalability for broader application. `@udomsilp2017traffic` leveraged Synchro for optimizing network signal timings, specifically cycle lengths, and subsequently employed these optimal cycle lengths as inputs into SUMO simulations to evaluate travel-time improvements. Similarly, `@singh2017impact` utilized Synchro for traffic signal optimization, incorporating optimal green times into SUMO simulations to assess start-up lost times. Despite these contributions, a fully integrated and automated solution remains lacking in current literature.

To address these gaps, we introduce utdf2gmns ([Luo and Zhou 2022](https://github.com/xyluo25/utdf2gmns)), an open-source Python tool (\autoref{Figure 1: Design Framework}) that automates the conversion of Synchro UTDF files into GMNS-compliant (General Modeling Network Specification) networks `[@smith2020general]`, which can then be readily transformed into simulation-ready networks for the widely used simulator SUMO. By combining the advantages of the GMNS, a robust framework that standardizes network representation `[@berg2022gmns; @lu2023virtual; @luo2024strategic; @luo2024innovation]`, enhances data consistency, reproducibility, and collaboration, utdf2gmns specifically contributes through the following functionalities: (1) Automatic geocoding of Synchro networks (\autoref{Figure 2: Geocoding Intersection}), automates the transformation of relative coordinates into precise longitude and latitude, significantly reducing manual effort and ensuring accurate spatial representation. (2) Enhanced Sigma-X (SIGnal Modeling Application for eXcel) engine integration, leverage the Sigma-X engine ([Milan 2022](https://github.com/milan1981/Sigma-X)) to automatically extract, calculate, visualize, optimize essential signalized intersection metrics. This includes detailed phasing diagrams, turning volume statistics, movement capacities, volume-to-capacity (V/C) ratios, and intersection control delays, providing comprehensive analysis and facilitating informed decision-making. (3) Robust SUMO network generation, utdf2gmns carefully generates GMNS-compliant SUMO simulation networks by fully considering critical parameters such as signal coordination, traffic flows, and turning movements, thus accurately reflecting real-world operational scenarios. (4) Extendibility to other microsimulation platforms, built as an open-source modular tool, utdf2gmns enables easy adaptation and extension to additional simulation software platforms beyond SUMO. This promotes broader standardization, reproducibility, and community-driven enhancement in traffic simulation research.

# Figures

![Figure 1: Design Framework.\label{Figure 1: Design Framework}](docs/source/_static/framework.png){ width=60%; }
Figure 1: Design Framework

![Figure 2: Geocoding Intersection.\label{Figure 2: Geocoding Intersection}](docs/source/_static/geocoding_intersection.png){ width=60% }
Figure 2: Geocoding Intersection

# Acknowledgements

Prof.Xuesong Simon Zhou for Arizona State University, for his valueable feedback and suggestions during the development of the project. His insights on traffic simulation and data formats were instrumental in shaping the direction of this library.

Prof. Milan Zlatkovic from University of Wyoming, for the power of sigma-x engine to visualize signalized intersections and his expertise in traffic modeling and simulation has been invaluable.

Yiran Zhang from University of Washington, for her valuable feedback and debuging of signal conversation during the early development of the project.

Oak Ridge National Lab (ORNL) for providing the datasets used in the early development and testing of this library. Their commitment to open data and research collaboration has greatly facilitated this work.

# References
