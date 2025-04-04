'''
##############################################################
# Created Date: Friday, October 18th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''
import os
from typing import TYPE_CHECKING
from pathlib import Path
import pyufunc as pf
import pandas as pd
# import keplergl
# import geopandas as gpd
# import matplotlib.pyplot as plt

if TYPE_CHECKING:
    import geopandas as gpd
    import keplergl
    import matplotlib.pyplot as plt  # for type hinting only


@pf.requires("matplotlib", verbose=False)
def plot_net_mpl(net: object, *, save_fig: bool = False,
                 fig_name: str = "utdf_network.png",
                 fig_size: tuple = (12, 12), dpi: int = 600) -> "plt.figure":
    """Plot network

    Args:
        net (object): the utdf2gmns.UTDF2GMNS object
        save_fig (bool): whether to save the figure. Defaults to False.
        fig_name (str): the name of the figure. Defaults to "utdf_network.png".
        fig_size (tuple): the size of the figure. Defaults to (12, 12).
        dpi (int): the dpi of the figure. Defaults to 600.

    Returns:
        plt.figure: the figure object

    """
    pf.import_package("matplotlib", verbose=False)  # ensure matplotlib is imported
    import matplotlib.pyplot as plt  # ensure matplotlib is imported

    # crate a fix ans axis
    is_plot = False
    fig, ax = plt.subplots(figsize=fig_size)

    # plot intersections
    if hasattr(net, 'network_nodes'):
        for node in net.network_nodes:
            x = net.network_nodes[node]['x_coord']
            y = net.network_nodes[node]['y_coord']
            ax.plot(x, y, 'ro')
        is_plot = True

    # plot links
    if hasattr(net, 'network_links'):
        for link in net.network_links:
            try:
                x, y = net.network_links[link]['geometry']["exterior"].xy
            except Exception:
                x, y = net.network_links[link]['geometry'].coords.xy
            ax.fill(x, y, color='gray')
        is_plot = True

    if is_plot:

        # Set equal scaling
        # ax.set_aspect('equal')

        # Add labels and title
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_title('UTDF Network')

        if save_fig:
            plt.savefig(fig_name, dpi=dpi)

        plt.show()

    return fig


@pf.requires("keplergl", "geopandas", verbose=False)
def plot_net_keplergl(net: object, *, save_fig: bool = False,
                      fig_name: str = "utdf_network.html") -> "keplergl.KeplerGl":
    """Plot network in keplergl

    Args:
        net (object): the utdf2gmns.UTDF2GMNS object
        save_fig (bool): whether to save the figure. Defaults to False.
        fig_name (str): the name of the figure. Defaults to "utdf_network.html".

    Returns:
        keplergl.KeplerGl: the keplergl map
    """
    pf.import_package("keplergl", verbose=False)
    pf.import_package("geopandas", verbose=False)  # ensure geopandas is imported
    # ensure keplergl is imported
    import keplergl  # ensure keplergl is imported
    import geopandas as gpd  # ensure geopandas is imported

    # check the extension of the fig_name
    if not fig_name.endswith('.html'):
        fig_name = fig_name + '.html'

    # get node and link data
    df_nodes = pd.DataFrame(net.network_nodes.values())
    df_links = pd.DataFrame(net.network_links.values())
    gdf_links = gpd.GeoDataFrame(df_links, geometry='geometry')

    # create a keplergl map
    map_1 = keplergl.KeplerGl(height=800)
    map_1.add_data(data=df_nodes, name='network_nodes')
    map_1.add_data(data=gdf_links, name='network_links')

    # save the map
    if save_fig:
        path_output = Path(net._utdf_filename).parent
        path_output_fig = pf.path2linux(os.path.join(path_output, fig_name))

        map_1.save_to_html(file_name=path_output_fig)
        # print(f"  :Successfully save the network to {path_output_fig}")

    # map_1.show()
    return map_1
