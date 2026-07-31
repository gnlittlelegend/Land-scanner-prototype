import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.validators.polygon_validator import validate_geojson, validate_coordinates

def test_valid_polygon():
    polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [-122.4194, 37.7749],
                [-122.4194, 37.7849],
                [-122.4094, 37.7849],
                [-122.4094, 37.7749],
                [-122.4194, 37.7749]
            ]
        ]
    }
    
    is_valid, msg = validate_geojson(polygon)
    assert is_valid, f"GeoJSON validation failed: {msg}"
    
    is_valid, msg = validate_coordinates(polygon)
    assert is_valid, f"Coordinate validation failed: {msg}"
    
    print("[PASS] Valid polygon test")

def test_invalid_polygon_type():
    polygon = {"type": "Point", "coordinates": [0, 0]}
    is_valid, msg = validate_geojson(polygon)
    assert not is_valid, "Should have failed for Point type"
    print("[PASS] Invalid polygon type test")

def test_unclosed_polygon():
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-122.4194, 37.7749],
            [-122.4194, 37.7849],
            [-122.4094, 37.7849],
            [-122.4094, 37.7749]
        ]]
    }
    is_valid, msg = validate_geojson(polygon)
    assert not is_valid, "Should have failed for unclosed polygon"
    print("[PASS] Unclosed polygon test")

if __name__ == "__main__":
    test_valid_polygon()
    test_invalid_polygon_type()
    test_unclosed_polygon()
    print("All tests passed!")