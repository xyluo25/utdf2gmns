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
  - name: Oak Ridge National Laboratory, United States
    index: 1
date: 11 April 2025
bibliography: paper.bib
---
# Summary

UTDF2GMNS[^1] implements an automated workflow for network coordination, traffic signal integration, and traffic flow conversion from Synchro to SUMO. The process begins with a comparative analysis of network topologies, data representations, and signal timing schemas in both environments. Converting Synchro UTDF data to a network ready for microsimulation poses several challenges, including accurate signal integration, spatial transformation, and preservation of turning flow fidelity. Signal conversion represents a primary bottleneck, as it demands precise mapping of phasing plans, timing parameters, and coordination strategies to ensure valid simulation results. Network conversion is further complicated by translating Synchro’s relative coordinate system into georeferenced formats compatible with geographic information system tools. Furthermore, accurate transformation of turning movement data is essential for realistic intersection modeling.

Existing methods address only isolated conversion tasks and lack a fully automated, scalable end-to-end workflow. To fill this gap, we introduce [utdf2gmns](https://pypi.org/project/utdf2gmns/), an open-source Python library that automates the transformation of Synchro UTDF files into GMNS-compliant SUMO networks. utdf2gmns provides automatic geocoding, Sigma-X engine integration for intersection analysis, robust SUMO network generation, and extensibility to other microsimulation platforms. Future work will extend support for adaptive signal control, integrate real-time data inputs, and enhance interoperability with additional simulation frameworks to promote reproducibility and collaborative traffic-modeling research.

# Statement of need

Traffic microsimulation is essential for evaluating and improving urban transportation systems by providing high-resolution analysis of flow, congestion, and infrastructure performance. Such simulations depend on precise modeling of signal control, network geometry, and turning movements. Although Synchro’s Universal Traffic Data Format (UTDF) delivers comprehensive intersection data, converting UTDF into simulation-ready networks remains manual, labor-intensive, and error-prone, limiting seamless interoperability with microsimulation platforms.

Several critical challenges remain when converting Synchro UTDF data into microsimulation-compatible networks, such as those required by Simulation of Urban Mobility (SUMO) [@lopez2018microscopic]. First, accurate signal conversion demands detailed extraction and mapping of phasing, timing, and coordination parameters into standardized control formats; errors here can substantially degrade simulation fidelity. Second, network conversion requires transforming Synchro’s relative coordinate system into georeferenced longitude–latitude coordinates for seamless GIS integration, a labor-intensive and error-prone process that limits scalability. Third, realistic intersection dynamics hinge on precise turning movement conversion, which typically involves extensive manual preprocessing; inaccuracies at this stage can propagate through the simulation, undermining the validity of subsequent analyses.

Prior efforts have addressed individual aspects of Synchro‐to‐SUMO conversion but have not yielded a unified, automated workflow. @zhang2024integration convert Synchro signal data into a SUMO network but require separate preprocessing of UTDF files and SUMO inputs. @ban2022multiscale integrate Synchro signals within a vehicle‐traffic‐demand platform, yet their Synchro and SUMO networks are independently prepared. @coogan2021coordinated focus on geometry and phasing conversion but rely on relative coordinates and scale only to a few intersections. @udomsilp2017traffic and @singh2017impact optimize signal timings in Synchro and then import cycle lengths or green times into SUMO to evaluate performance. Despite these advances, no existing method delivers a fully automated, end-to-end solution.

To address these gaps, we present utdf2gmns ([Luo and Zhou 2022](https://github.com/xyluo25/utdf2gmns)), an open-source Python tool that automates the conversion of Synchro UTDF files into GMNS-compliant networks [@smith2020general] and generates simulation-ready inputs for SUMO. By leveraging the GMNS, a robust framework for standardized network representation [@berg2022gmns; @lu2023virtual; @luo2024strategic; @luo2024innovation], utdf2gmns enhances data consistency, reproducibility, and collaboration through four core capabilities: it automates geocoding of Synchro’s relative coordinates into accurate longitude–latitude pairs; integrates with the Sigma-X engine ([Milan 2022](https://github.com/milan1981/Sigma-X)) to extract and optimize key intersection metrics (phasing diagrams, turning volumes, movement capacities, volume-to-capacity ratios, and control delays); generates GMNS-compliant SUMO networks that fully preserve signal coordination, traffic flows, and turning movements; and provides a modular architecture for extension to additional microsimulation platforms, thereby promoting broader standardization and community-driven development.

# Acknowledgements

Prof.Xuesong Simon Zhou from Arizona State University, for his valueable feedback and suggestions during the development of the project. His insights on traffic simulation and data formats were instrumental in shaping the direction of this library. Prof. Milan Zlatkovic from University of Wyoming, for the power of sigma-x engine to visualize signalized intersections and his expertise in traffic modeling and simulation has been invaluable. Yiran Zhang from University of Washington, for her valuable feedback and debuging of signal conversation during the early development of the project.

Additional support was provided by the U.S. Department of Energy (DOE), Office of Energy Efficiency and Renewable Energy (EERE), Vehicle Technologies Office. Any opinions, findings, and conclusions or recommendations expressed in this material are those of the author(s) and do not necessarily reflect the views of the USDOT, DOE, and the U.S. Government assumes no liability for the contents or use thereof.

# References

[^1]: This manuscript has been authored in part by UT-Battelle, LLC, under contract DE-AC05-00OR22725 with the US Department of Energy (DOE). The publisher acknowledges the US government license to provide public access under the [DOE Public Access Plan](https://www.energy.gov/doe-public-access-plan)
