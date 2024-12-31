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
    from utdf2gmns.util_lib.pkg_utils import calculate_point2point_distance_in_km
except Exception:
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[1]))
    from utdf2gmns.util_lib.pkg_utils import calculate_point2point_distance_in_km


def test_calculate_point2point_distance_in_km():
    point1 = (0, 0)
    point2 = (0, 1)
    expected_distance = 111.19492664455873  # Approximate distance in km
    calculated_distance = calculate_point2point_distance_in_km(point1, point2)
    assert calculated_distance == pytest.approx(expected_distance, 0.1)
