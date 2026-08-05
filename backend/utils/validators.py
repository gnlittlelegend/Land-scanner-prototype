"""Validation utilities for Land Scanner."""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def validate_coordinates(lon: float, lat: float) -> bool:
    """
    Validate geographic coordinates.
    
    Args:
        lon: Longitude (-180 to 180)
        lat: Latitude (-90 to 90)
        
    Returns:
        True if valid, False otherwise
    """
    return -180 <= lon <= 180 and -90 <= lat <= 90


def validate_coordinate_range(coordinates: list) -> Tuple[bool, str]:
    """
    Validate all coordinates in a list.
    
    Args:
        coordinates: Nested list of coordinate arrays
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    def check_coords(coords):
        if isinstance(coords, (list, tuple)):
            if len(coords) == 0:
                return True  # Empty is valid at higher levels
            if isinstance(coords[0], (int, float)):
                # This is a coordinate pair
                if len(coords) >= 2:
                    if not validate_coordinates(coords[0], coords[1]):
                        return False
            else:
                # Recurse
                for coord in coords:
                    if not check_coords(coord):
                        return False
        return True

    if check_coords(coordinates):
        return True, ""
    return False, "Coordinates out of valid range (-180 to 180 lon, -90 to 90 lat)"
