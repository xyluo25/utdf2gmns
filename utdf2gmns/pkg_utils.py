# -*- coding:utf-8 -*-
##############################################################
# Created Date: Wednesday, November 16th 2022
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################

from math import sin, cos, sqrt, atan2, radians


def calculate_point2point_distance_in_km(point1: tuple, point2: tuple) -> float:
    """ point1 and point2: a tuple of (longitude, latitude) """

    # approximate radius of earth in km
    R = 6373.0

    lat1 = radians(point1[1])
    lon1 = radians(point1[0])
    lat2 = radians(point2[1])
    lon2 = radians(point2[0])

    lon_diff = lon2 - lon1
    lat_diff = lat2 - lat1

    a = sin(lat_diff / 2)**2 + cos(lat1) * cos(lat2) * sin(lon_diff / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c

    # return math.pow((point1[0] - point2[0]) ** 2 + (point1[1] - point2[1]) ** 2, 0.5)

    # the distance is in km
    return distance
