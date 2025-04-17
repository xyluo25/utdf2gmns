# -*- coding:utf-8 -*-
##############################################################
# Created Date: Wednesday, November 16th 2022
# Contact Info: luoxiangyong01@gmail.com
# Author/Copyright: Mr. Xiangyong Luo
##############################################################

import math
from math import sin, cos, sqrt, atan2, radians
from datetime import datetime
import pyufunc as pf


def calculate_point2point_distance_in_km(point1: list, point2: list) -> float:
    """ point1 and point2: a tuple of (longitude, latitude) """

    # TDD: Test-Driven Development
    # assert isinstance(point1, list), "point1 should be a list"
    # assert isinstance(point2, list), "point2 should be a list"

    # approximate radius of earth in km
    R = 6373.0

    lon1 = radians(point1[0])
    lat1 = radians(point1[1])
    lon2 = radians(point2[0])
    lat2 = radians(point2[1])

    lon_diff = lon2 - lon1
    lat_diff = lat2 - lat1

    a = sin(lat_diff / 2)**2 + cos(lat1) * cos(lat2) * sin(lon_diff / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def point_coord_on_line_2dim(x1: float, y1: float, x2: float, y2: float, distance: float) -> tuple:
    """Given a starting point (x1, y1) and an ending point (x2, y2) in 2D space,
    return the coordinates of the point at a given distance from the starting point.

    Args:
        x1 (float): x-coordinate of the starting point.
        y1 (float): y-coordinate of the starting point.
        x2 (float): x-coordinate of the ending point.
        y2 (float): y-coordinate of the ending point.
        distance (float): The distance from the starting point.

    Returns:
        tuple: A tuple containing the x and y coordinates of the point at the given distance.
    """
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx**2 + dy**2)
    if length == 0:
        return x1, y1
    ratio = distance / length
    x = x1 + ratio * dx
    y = y1 + ratio * dy
    return (x, y)


def point_coord_on_line_lonlat(lon1: float, lat1: float, lon2: float, lat2: float, distance: float) -> tuple:
    """
    Given a start point (lon1, lat1) and end point (lon2, lat2),
    return the longitude/latitude of the point at `distance` meters
    from the start, following the great circle path.

    Args:
        lon1 (float): Longitude of the starting point in degrees.
        lat1 (float): Latitude of the starting point in degrees.
        lon2 (float): Longitude of the ending point in degrees.
        lat2 (float): Latitude of the ending point in degrees.
        distance (float): Distance from the start point, in meters.

    Returns:
        (lon, lat): Tuple of longitude and latitude in degrees.
    """
    # Convert to radians
    φ1 = math.radians(lat1)
    λ1 = math.radians(lon1)
    φ2 = math.radians(lat2)
    λ2 = math.radians(lon2)

    # Earth radius (mean)
    R = 6_371_000.0

    # Compute the great-circle distance between start and end
    Δφ = φ2 - φ1
    Δλ = λ2 - λ1
    a = math.sin(Δφ / 2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(Δλ / 2)**2
    sig = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    if sig == 0 or distance == 0:
        # coincident points or zero distance
        return lon1, lat1

    # Initial bearing from point 1 to point 2
    θ = math.atan2(
        math.sin(Δλ) * math.cos(φ2),
        math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(Δλ))

    # Angular distance along the great circle
    δ = distance / R

    # Compute the new point
    φ3 = math.asin(math.sin(φ1) * math.cos(δ) + math.cos(φ1) * math.sin(δ) * math.cos(θ))
    λ3 = λ1 + math.atan2(math.sin(θ) * math.sin(δ) * math.cos(φ1),
                         math.cos(δ) - math.sin(φ1) * math.sin(φ3))

    # Normalize lon to −180…+180°
    lon3 = (math.degrees(λ3) + 540) % 360 - 180
    lat3 = math.degrees(φ3)

    return (lon3, lat3)


def time_unit_converter(value: float, from_unit: str, to_unit: str, verbose: bool = True) -> float:
    """ Convert a time value between seconds, minutes, hours, days, years

    Args:
        value (float): The numerical value to convert.
        from_unit (str): The unit of the input value.
        to_unit (str): The desired output unit.

    Example:
        >>> from pyufunc import time_unit_converter
        >>> time_unit_converter(1, "hours", "minutes")
        60.0

    Returns:
        float: The converted value in the target unit.

    Raises:
        ValueError: If an invalid unit is provided.
    """

    # Define aliases to standardize unit names.
    unit_aliases = {
        "s": "seconds", "sec": "seconds", "secs": "seconds", "second": "seconds", "seconds": "seconds",
        "m": "minutes", "min": "minutes", "mins": "minutes", "minute": "minutes", "minutes": "minutes",
        "h": "hours", "hr": "hours", "hrs": "hours", "hour": "hours", "hours": "hours",
        "d": "days", "day": "days", "days": "days",
        "y": "years", "yr": "years", "yrs": "years", "year": "years", "years": "years",
        "season": "season", "seasons": "season",
        "quarter": "quarter", "quarters": "quarter",
        "lunar year": "lunar year", "lunar years": "lunar year"
    }

    # Conversion factors in seconds.
    conversion_factors = {
        "seconds": 1,
        "minutes": 60,                     # 60 seconds
        "hours": 3600,                     # 60 minutes * 60 seconds
        "days": 86400,                     # 24 hours * 3600 seconds
        "years": 31536000,                 # 365 days * 86400 seconds
    }

    # Normalize the provided unit strings.
    from_unit_norm = unit_aliases.get(from_unit.lower().strip())
    to_unit_norm = unit_aliases.get(to_unit.lower().strip())

    if from_unit_norm is None or to_unit_norm is None:
        raise ValueError(
            "Invalid unit provided. Allowed units: seconds, minutes, hours, days, years, season, quarter, lunar year.")

    # Convert the input value to seconds.
    value_in_seconds = value * conversion_factors[from_unit_norm]

    # Convert from seconds to the target unit.
    result = value_in_seconds / conversion_factors[to_unit_norm]

    if verbose:
        print(
            f"  :{value} {from_unit_norm} is approximately {result} {to_unit_norm}")
    return result


def time_str_to_seconds(time_str: str, to_unit: str = "seconds", verbose: bool = True) -> int:
    """Convert a time string to seconds

    Args:
        time_str (str): A time string, e.g., "12:00AM", "9:00am", "3:00pm"
        to_unit (str): The desired output unit. e.g. "seconds", "minutes", "hours", "days"
        verbose (bool): Whether to print the conversion result. Defaults to True.

    Example:
        >>> from pyufunc import time_str_to_seconds
        >>> time_str_to_seconds("12:00AM")
        0

        >>> time_str_to_seconds("9:00am")
        34200.0

        >>> time_str_to_seconds("3:30pm")
        55800.0

        >>> time_str_to_seconds("3:30pm", to_unit="minutes")
        930.0

    Returns:
        int: The time in the target unit.
    """

    time_str = pf.str_strip(time_str).lower()

    fmt = [
        "%I:%M",        # 12-hour, no AM/PM
        "%I:%M:%S",     # 12-hour with seconds
        "%I:%M%p",      # 12-hour with AM/PM
        "%I:%M %p",      # 12-hour with AM/PM
        "%H:%M",        # 24-hour
        "%H:%M:%S"      # 24-hour with seconds
    ]

    dt = None
    for each_fmt in fmt:
        try:
            dt = datetime.strptime(time_str, each_fmt)
            break
        except ValueError:
            continue

    if dt is None:
        raise ValueError(f"  :Invalid time string: {time_str}")

    total_seconds = dt.hour * 3600 + dt.minute * 60 + dt.second

    unit_aliases = {
        "s": "seconds", "sec": "seconds", "secs": "seconds", "second": "seconds", "seconds": "seconds",
        "m": "minutes", "min": "minutes", "mins": "minutes", "minute": "minutes", "minutes": "minutes",
        "h": "hours", "hr": "hours", "hrs": "hours", "hour": "hours", "hours": "hours",
        "d": "days", "day": "days", "days": "days",
        "y": "years", "yr": "years", "yrs": "years", "year": "years", "years": "years",
    }

    # Conversion factors in seconds.
    conversion_factors = {
        "seconds": 1,
        "minutes": 60,                     # 60 seconds
        "hours": 3600,                     # 60 minutes * 60 seconds
        "days": 86400,                     # 24 hours * 3600 seconds
        "years": 31536000,                 # 365 days * 86400 seconds
    }

    # Convert from seconds to the target unit.
    to_unit_norm = unit_aliases.get(to_unit.lower().strip())
    result = total_seconds / conversion_factors[to_unit_norm]

    if verbose:
        print(
            f"  :{time_str} is approximately {result} {to_unit_norm}")
    return result
