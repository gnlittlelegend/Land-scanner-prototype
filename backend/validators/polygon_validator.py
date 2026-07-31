import json
from typing import Tuple

def validate_geojson(polygon_data: dict) -> Tuple[bool, str]:
    if not isinstance(polygon_data, dict):
        return False, "Invalid GeoJSON: not an object"
    
    if "type" not in polygon_data:
        return False, "Invalid GeoJSON: missing type field"
    
    if polygon_data["type"] != "Polygon":
        return False, f"Invalid GeoJSON: expected Polygon, got {polygon_data['type']}"
    
    if "coordinates" not in polygon_data:
        return False, "Invalid GeoJSON: missing coordinates"
    
    coords = polygon_data["coordinates"]
    if not isinstance(coords, list) or len(coords) == 0:
        return False, "Invalid GeoJSON: invalid coordinates structure"
    
    if len(coords[0]) < 4:
        return False, "Invalid GeoJSON: polygon must have at least 4 points"
    
    if coords[0][0] != coords[0][-1]:
        return False, "Invalid GeoJSON: polygon must be closed"
    
    return True, "Valid"

def validate_coordinates(polygon_data: dict) -> Tuple[bool, str]:
    coords = polygon_data.get("coordinates", [])
    if not coords or not coords[0]:
        return False, "Empty coordinates"
    
    for ring in coords:
        for point in ring:
            if len(point) != 2:
                return False, f"Invalid coordinate: {point}"
            lon, lat = point
            if not (-180 <= lon <= 180):
                return False, f"Invalid longitude: {lon}"
            if not (-90 <= lat <= 90):
                return False, f"Invalid latitude: {lat}"
    
    return True, "Valid coordinates"