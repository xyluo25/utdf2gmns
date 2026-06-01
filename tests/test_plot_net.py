import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

matplotlib = pytest.importorskip("matplotlib")
matplotlib.use("Agg")
plt = pytest.importorskip("matplotlib.pyplot")
shapely_geometry = pytest.importorskip("shapely.geometry")

plot_net_path = Path(__file__).resolve().parents[1] / "utdf2gmns" / "func_lib" / "plot_net.py"
plot_net_spec = importlib.util.spec_from_file_location("plot_net_for_test", plot_net_path)
assert plot_net_spec is not None
assert plot_net_spec.loader is not None
plot_net_module = importlib.util.module_from_spec(plot_net_spec)
plot_net_spec.loader.exec_module(plot_net_module)
plot_net_mpl = plot_net_module.plot_net_mpl


def test_plot_net_mpl_accepts_shapely_polygon_and_linestring(tmp_path, monkeypatch):
    """Plot Shapely polygons from exterior coordinates and lines from coords."""
    monkeypatch.setattr(plt, "show", lambda: None)

    utdf_file = tmp_path / "UTDF.csv"
    utdf_file.write_text("", encoding="utf-8")

    network = SimpleNamespace(
        _utdf_filename=str(utdf_file),
        network_nodes={},
        network_links={
            "polygon_link": {
                "geometry": shapely_geometry.Polygon(
                    [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 0.0)]
                ),
            },
            "line_link": {
                "geometry": shapely_geometry.LineString([(0.0, 0.0), (1.0, 1.0)]),
            },
        },
    )

    figure = plot_net_mpl(network)
    axis = figure.axes[0]

    assert len(axis.patches) == 1
    assert len(axis.lines) == 1

    plt.close(figure)
