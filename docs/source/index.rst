
Welcome to utdf2gmns documentation!
===================================

.. image:: https://badge.fury.io/py/utdf2gmns.svg
   :target: https://badge.fury.io/py/utdf2gmns

.. image:: https://static.pepy.tech/badge/utdf2gmns
   :target: https://pepy.tech/project/utdf2gmns

.. image:: https://img.shields.io/pypi/wheel/gensim.svg
   :target: https://pypi.org/project/utdf2gmns/

.. image:: https://img.shields.io/pypi/pyversions/utdf2gmns.svg
   :target: https://www.python.org/

.. image:: https://img.shields.io/github/release-date/xyluo25/utdf2gmns.svg
   :target: https://img.shields.io/github/release-date/xyluo25/utdf2gmns.svg

.. image:: https://readthedocs.org/projects/utdf2gmns/badge/?version=latest
   :target: https://utdf2gmns.readthedocs.io/en/latest/?badge=latest

.. image:: https://img.shields.io/github/contributors/xyluo25/utdf2gmns
   :target: https://github.com/xyluo25/utdf2gmns/graphs/contributors

.. .. image:: https://zenodo.org/badge/DOI/
..    :target:

.. image:: https://img.shields.io/badge/License-MIT-blue.svg
   :target: https://opensource.org/license/mit

An AMS (Analysis, Modeling and Simulation) tool to convert utdf file to different formats, including GMNS, SUMO etc.

utdf2gmns explored an automatic process of network coordinating, traffic signal integration, traffic flow conversion from Synchro to SUMO, identifying both the feasibility and challenges involved. The approach began with a comparative analysis of traffic network features, data formats, and signal timing schemas between the two platforms. Key challenges in converting Synchro UTDF data into microsimulation-ready networks focusing on signal integration, spatial conversion, and turning flow accuracy. Signal conversion remains a critical bottleneck, requiring precise alignment of phasing, timing, and coordination data to ensure reliable simulation outcomes. Network conversion also presents difficulties, particularly in translating Synchro’s relative coordinate system into georeferenced formats compatible with GIS tools. Additionally, accurately transforming turning movement data is essential for modeling realistic intersection behavior but often involves tedious manual preprocessing.

While previous efforts have made progress in isolated aspects of the conversion process, none offer a fully automated and scalable end-to-end solution. To fill this gap, we introduce `utdf2gmns`_, an open-source Python tool designed to automate the transformation of Synchro UTDF files into GMNS-compliant networks for SUMO simulation. The tool supports automatic geocoding, integration with the Sigma-X engine for intersection analysis, robust SUMO network generation, and extendibility to other microsimulation platforms. Future work will focus on expanding support for adaptive signal systems, incorporating real-time data inputs, and enhancing interoperability with additional simulation frameworks to promote reproducibility and collaborative research in traffic modeling.

Official Document: https://utdf2gmns.readthedocs.io/en/latest/

Official GitHub: https://github.com/xyluo25/utdf2gmns

Previous Development: `ASU Trans-AI-LAB`_ (`Initial commit Dec 17, 2022, total 144 commits`_)


.. toctree::
   :maxdepth: 3
   :caption: utdf2gmns Navigation

   pages/_installation.rst
   pages/quick_start.rst
   pages/_read_utdf.rst
   pages/_geocoding_intersection.rst
   pages/_signal_conversion.rst
   pages/_utdf2gmns.rst
   pages/_gmns2sumo.rst
   pages/_sigma_x.rst
   pages/api_reference.rst
   pages/support.rst

Indices and Tables
==================

* :ref:`genindex`
.. * :ref:`modindex`
.. * :ref:`search`

.. _`utdf2gmns`: https://pypi.org/project/utdf2gmns/
.. _`ASU Trans-AI-LAB`: https://github.com/asu-trans-ai-lab/utdf2gmns
.. _`Initial commit Dec 17, 2022, total 144 commits`: https://github.com/asu-trans-ai-lab/utdf2gmns/commits/main/?after=29c374e7d0d5315605a2d8e6a4fa7b40fb54921f+139