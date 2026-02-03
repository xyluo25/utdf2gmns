'''
##############################################################
# Created Date: Monday, February 2nd 2026
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''


from pathlib import Path
import os
import sys
import json
from collections import defaultdict
import subprocess

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
import sumolib


def sumo2geojson(net_file: str,
                 output_file: str,
                 lanes: bool = False,
                 junctions: bool = False,
                 internal: bool = False,
                 junction_coords: bool = False,
                 boundary: bool = False,
                 edge_data_timeline: bool = False,
                 edge_data: str = None,
                 pt_lines: str = None) -> None:
    """ Convert SUMO net file to geojson format, in default exports edge geometries only.

    Args:
        net_file (str): The SUMO .net.xml file to convert
        output_file (str): The output geojson file path
        lanes (bool): Export lane geometries instead of edge geometries. Defaults to False.
        junctions (bool): Export junction geometries. Defaults to False.
        internal (bool): Export internal geometries. Defaults to False.
        junction_coords (bool): Append junction coordinates to edge shapes. Defaults to False.
        boundary (bool): Export boundary shapes instead of center-lines. Defaults to False.
        edge_data_timeline (bool): exports all time intervals (by default only the first is exported). Defaults to False.
        edge_data (str): Optional edgeData to include in the output. Defaults to None.
        pt_lines (str): Optional ptline information to include in the output. Defaults to None.

    Returns:
        The conversion result in geojson format.
    """

    # TDD validate input and output file
    if not isinstance(net_file, str):
        raise TypeError(f"The specified net file path must be a string: {net_file}")
    if not isinstance(output_file, str):
        raise TypeError(f"The specified output file path must be a string: {output_file}")
    if not Path(net_file).is_file():
        raise FileNotFoundError(f"The specified net file does not exist: {net_file}")

    # Validate input extension in .net.xml and output in .geojson
    if not net_file.endswith('.net.xml'):
        raise ValueError(f"The specified net file is not a valid SUMO .net.xml file: {net_file}")
    if not output_file.endswith('.geojson'):
        output_file += '.geojson'

    # Use command statement run net2geojson.py
    cmd = f'python "{Path(__file__).parent / "net2geojson.py"}" -n "{net_file}" -o "{output_file}"'
    if lanes:
        cmd += ' -l'
    if junctions:
        cmd += ' --junctions'
    if internal:
        cmd += ' -i'
    if junction_coords:
        cmd += ' -j'
    if boundary:
        cmd += ' -b'
    if edge_data_timeline:
        cmd += ' --edgedata-timeline'
    if edge_data:
        cmd += f' -d "{edge_data}"'
    if pt_lines:
        cmd += f' -p "{pt_lines}"'

    # Execute the command using subprocess
    execute_ = subprocess.run(cmd, shell=True, check=True)

    return execute_


if __name__ == "__main__":
    path = "./utdf_to_sumo.net.xml"

    output = "./utdf_to_sumo_boundary.geojson"
    sumo2geojson(path, output, boundary=True)
