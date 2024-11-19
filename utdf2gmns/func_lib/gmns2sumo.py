'''
##############################################################
# Created Date: Sunday, October 20th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''

# SUMO network specification: https://sumo.dlr.de/docs/Networks/SUMO_Road_Networks.html#network_format
# SUMO-GUI Specification: https://sumo.dlr.de/docs/sumo-gui.html#interaction_with_the_view
# SUMO netedit specification: https://sumo.dlr.de/docs/Netedit/index.html#processing_menu_options

import sumolib
import xmltodict

res = xmltodict.parse('')

from sumolib.net.node import Node
from sumolib.net.edge import Edge
from sumolib import net

path_net = r"C:\Users\xyluo25\ASU Dropbox\Xiangyong Luo\xluo25_asu\Learning\SUMO_xl\00hello\helloWorld.net.xml"

ne = net.readNet(path_net)
