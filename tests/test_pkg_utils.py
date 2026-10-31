# -*- coding:utf-8 -*-
##############################################################
# Created Date: Sunday, February 18th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
from __future__ import absolute_import

import pytest
from pathlib import Path

try:
    from utdf2gmns.util_lib.pkg_utils import (
        calculate_point2point_distance_in_km,
        distance_on_line_lonlat,
        point_coord_on_line_lonlat,
        point_on_line,
    )
except Exception:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from utdf2gmns.util_lib.pkg_utils import (
        calculate_point2point_distance_in_km,
        distance_on_line_lonlat,
        point_coord_on_line_lonlat,
        point_on_line,
    )


def test_calculate_point2point_distance_in_km():
    point1 = (0, 0)
    point2 = (0, 1)
    expected_distance = 111.19492664455873  # Approximate distance in km
    calculated_distance = calculate_point2point_distance_in_km(point1, point2)
    assert calculated_distance == pytest.approx(expected_distance, 0.1)


@pytest.mark.parametrize(
    "coordinates, distance, expected",
    [((0, 0, 3, 4), 2.5, (1.5, 2.0)), ((1, 2, 1, 2), 10, (1, 2))],
)
def test_point_on_line_preserves_existing_api(coordinates, distance, expected):
    """Keep the original helper callable after merging the dev utility names."""
    assert point_on_line(*coordinates, distance) == pytest.approx(expected)


def test_geographic_helpers_use_meters_and_longitude_first():
    """A 1 km eastward offset at the equator should preserve latitude."""
    longitude, latitude = point_coord_on_line_lonlat(0, 0, 1, 0, 1000)

    assert longitude == pytest.approx(0.0089932160592)
    assert latitude == pytest.approx(0.0, abs=1e-12)
    assert distance_on_line_lonlat(0, 0, longitude, latitude) == pytest.approx(1000)
