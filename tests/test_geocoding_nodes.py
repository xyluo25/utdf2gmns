import sys

import pytest

from utdf2gmns.func_lib.gmns.geocoding_Nodes import (
    calculate_new_coordinates_from_offsets,
)


def test_calculate_new_coordinates_reports_missing_geopy(monkeypatch):
    """Raise an actionable error when the geopy dependency is unavailable."""
    monkeypatch.setitem(sys.modules, "geopy", None)

    with pytest.raises(ImportError, match=r"geopy>=2\.4\.1 is required"):
        calculate_new_coordinates_from_offsets(
            base_lon=-114.59807666698381,
            base_lat=35.02605198650903,
            x_offset=0.0,
            y_offset=0.0,
            unit="feet, mph",
        )
