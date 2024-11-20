'''
##############################################################
# Created Date: Friday, October 18th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
'''
import matplotlib.pyplot as plt


def plot_net(net: object, *, save_fig: bool = False,
             fig_name: str = "utdf_network.png",
             fig_size: tuple = (12, 12), dpi: int = 600) -> plt.figure:
    """
    Plot network
    """

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
            x, y = net.network_links[link]['geometry'].exterior.xy
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
