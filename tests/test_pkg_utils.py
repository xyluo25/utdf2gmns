# -*- coding:utf-8 -*-
##############################################################
# Created Date: Sunday, February 18th 2024
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################
import pytest
from utdf2gmns.pkg_utils import calculate_point2point_distance_in_km


def test_calculate_point2point_distance_in_km():
    point1 = (0, 0)
    point2 = (0, 1)
    expected_distance = 111.19492664455873  # Approximate distance in km
    calculated_distance = calculate_point2point_distance_in_km(point1, point2)
    assert pytest.approx(calculated_distance, 0.1) == expected_distance


def test_calculate_point2point_distance_in_km_non_tuple():
    point1 = [0, 0]
    point2 = [0, 1]
    with pytest.raises(AssertionError, match="should be a tuple"):
        calculate_point2point_distance_in_km(point1, point2)