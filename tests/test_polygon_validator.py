"""
Property-based and unit tests for PolygonValidator.

Feature: land-scanner, Property 1: Polygon Validation Consistency
Validates: Requirements 1.3, 1.4, 1.5, 1.6
"""

import pytest
from hypothesis import given, strategies as st, assume
from backend.validators.polygon_validator import PolygonValidator, PolygonValidationError
from backend.models import Polygon


# Hypothesis strategies for generating valid polygons

@st.composite
def valid_geojson_polygons(draw):
    """Generate valid GeoJSON polygons."""
    # Generate a simple rectangle polygon
    lon_min = draw(st.floats(min_value=-170, max_value=170))
    lat_min = draw(st.floats(min_value=-80, max_value=80))
    width = draw(st.floats(min_value=1, max_value=30))
    height = draw(st.floats(min_value=1, max_value=30))
    
    lon_max = min(lon_min + width, 180)
    lat_max = min(lat_min + height, 90)
    
    coordinates = [
        [
            [lon_min, lat_min],
            [lon_max, lat_min],
            [lon_max, lat_max],
            [lon_min, lat_max],
            [lon_min, lat_min]  # Close the ring
        ]
    ]
    
    return {
        "type": "Polygon",
        "coordinates": coordinates
    }


@st.composite
def invalid_geojson_polygons(draw):
    """Generate invalid GeoJSON polygons."""
    choice = draw(st.integers(min_value=0, max_value=4))
    
    if choice == 0:
        # Missing type field
        return {"coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    elif choice == 1:
        # Missing coordinates field
        return {"type": "Polygon"}
    elif choice == 2:
        # Invalid geometry type
        return {
            "type": "Point",
            "coordinates": [0, 0]
        }
    elif choice == 3:
        # Too few coordinates
        return {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0]]]
        }
    else:
        # Coordinate out of range
        return {
            "type": "Polygon",
            "coordinates": [[[0, 0], [200, 0], [200, 100], [0, 100], [0, 0]]]
        }


# Unit Tests

class TestPolygonValidatorUnit:
    """Unit tests for PolygonValidator."""
    
    def test_valid_simple_polygon(self):
        """Test validation of a simple valid polygon."""
        polygon_data = {
            "type": "Polygon",
            "coordinates": [
                [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
            ]
        }
        
        result = PolygonValidator.validate(polygon_data)
        
        assert isinstance(result, Polygon)
        assert result.is_valid is True
        assert result.crs == "EPSG:4326"
        assert result.area_sqkm > 0
    
    def test_valid_polygon_with_hole(self):
        """Test validation of a polygon with a hole."""
        polygon_data = {
            "type": "Polygon",
            "coordinates": [
                [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],  # Exterior ring
                [[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]]       # Interior ring (hole)
            ]
        }
        
        result = PolygonValidator.validate(polygon_data)
        
        assert isinstance(result, Polygon)
        assert result.is_valid is True
    
    def test_invalid_missing_type_field(self):
        """Test rejection of GeoJSON missing type field."""
        polygon_data = {
            "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
        }
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        assert "type" in str(exc_info.value).lower()
    
    def test_invalid_missing_coordinates_field(self):
        """Test rejection of GeoJSON missing coordinates field."""
        polygon_data = {
            "type": "Polygon"
        }
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        assert "coordinates" in str(exc_info.value).lower()
    
    def test_invalid_geometry_type(self):
        """Test rejection of invalid geometry type."""
        polygon_data = {
            "type": "LineString",
            "coordinates": [[0, 0], [1, 1], [2, 2]]
        }
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        assert "LineString" in str(exc_info.value) or "geometry type" in str(exc_info.value).lower()
    
    def test_invalid_too_few_coordinates(self):
        """Test rejection of polygon with too few points."""
        polygon_data = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 1]]]  # Only 2 points
        }
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        assert "at least 4" in str(exc_info.value).lower() or "coordinates" in str(exc_info.value).lower()
    
    def test_invalid_longitude_out_of_range_high(self):
        """Test rejection of coordinates with longitude > 180."""
        polygon_data = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [200, 0], [200, 10], [0, 10], [0, 0]]]
        }
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        assert "longitude" in str(exc_info.value).lower() or "out of range" in str(exc_info.value).lower()
    
    def test_invalid_longitude_out_of_range_low(self):
        """Test rejection of coordinates with longitude < -180."""
        polygon_data = {
            "type": "Polygon",
            "coordinates": [[[-200, 0], [0, 0], [0, 10], [-200, 10], [-200, 0]]]
        }
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        assert "longitude" in str(exc_info.value).lower() or "out of range" in str(exc_info.value).lower()
    
    def test_invalid_latitude_out_of_range_high(self):
        """Test rejection of coordinates with latitude > 90."""
        polygon_data = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [10, 0], [10, 100], [0, 100], [0, 0]]]
        }
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        assert "latitude" in str(exc_info.value).lower() or "out of range" in str(exc_info.value).lower()
    
    def test_invalid_latitude_out_of_range_low(self):
        """Test rejection of coordinates with latitude < -90."""
        polygon_data = {
            "type": "Polygon",
            "coordinates": [[[0, -100], [10, -100], [10, 0], [0, 0], [0, -100]]]
        }
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        assert "latitude" in str(exc_info.value).lower() or "out of range" in str(exc_info.value).lower()
    
    def test_valid_multipolygon(self):
        """Test validation of a valid MultiPolygon."""
        polygon_data = {
            "type": "MultiPolygon",
            "coordinates": [
                [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]],
                [[[10, 10], [15, 10], [15, 15], [10, 15], [10, 10]]]
            ]
        }
        
        result = PolygonValidator.validate(polygon_data)
        
        assert isinstance(result, Polygon)
        assert result.is_valid is True
    
    def test_polygon_metadata_calculation(self):
        """Test that polygon metadata is correctly calculated."""
        polygon_data = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
        
        result = PolygonValidator.validate(polygon_data)
        
        # Check bounding box
        assert result.bounding_box == (0, 0, 1, 1)
        
        # Check centroid is approximately at center
        assert 0.4 < result.centroid[0] < 0.6
        assert 0.4 < result.centroid[1] < 0.6
        
        # Check area is positive
        assert result.area_sqkm > 0
    
    def test_error_message_descriptive_missing_type(self):
        """Test that error message is descriptive for missing type."""
        polygon_data = {"coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        error_msg = str(exc_info.value)
        assert len(error_msg) > 10  # Should be descriptive
        assert "type" in error_msg.lower()
    
    def test_error_message_descriptive_invalid_coordinates(self):
        """Test that error message is descriptive for invalid coordinates."""
        polygon_data = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0]]]
        }
        
        with pytest.raises(PolygonValidationError) as exc_info:
            PolygonValidator.validate(polygon_data)
        
        error_msg = str(exc_info.value)
        assert len(error_msg) > 10  # Should be descriptive


# Property-Based Tests

class TestPolygonValidatorProperties:
    """Property-based tests for PolygonValidator.
    
    Feature: land-scanner, Property 1: Polygon Validation Consistency
    Validates: Requirements 1.3, 1.4, 1.5, 1.6
    """
    
    @given(valid_geojson_polygons())
    def test_valid_polygons_always_accepted(self, polygon_data):
        """
        Property 1: For any valid GeoJSON polygon, system should accept it.
        """
        result = PolygonValidator.validate(polygon_data)
        
        assert isinstance(result, Polygon)
        assert result.is_valid is True
        assert result.crs == "EPSG:4326"
        assert result.area_sqkm > 0
    
    @given(invalid_geojson_polygons())
    def test_invalid_polygons_always_rejected(self, polygon_data):
        """
        Property 1: For any invalid GeoJSON polygon, system should reject it.
        """
        with pytest.raises(PolygonValidationError):
            PolygonValidator.validate(polygon_data)
    
    @given(valid_geojson_polygons())
    def test_polygon_bounding_box_contains_all_coordinates(self, polygon_data):
        """
        Property: Bounding box should contain all polygon coordinates.
        """
        result = PolygonValidator.validate(polygon_data)
        
        minx, miny, maxx, maxy = result.bounding_box
        
        # All coordinates should be within bounds
        for ring in polygon_data["coordinates"]:
            for lon, lat in ring:
                assert minx <= lon <= maxx, f"Longitude {lon} outside bounds"
                assert miny <= lat <= maxy, f"Latitude {lat} outside bounds"
    
    @given(valid_geojson_polygons())
    def test_polygon_bounding_box_is_valid(self, polygon_data):
        """
        Property: Bounding box dimensions should be consistent and non-negative.
        For rectangles generated, max coordinates should be >= min coordinates.
        """
        result = PolygonValidator.validate(polygon_data)
        
        minx, miny, maxx, maxy = result.bounding_box
        
        # Bounding box should have valid dimensions
        assert minx <= maxx, f"Invalid x-range: {minx} > {maxx}"
        assert miny <= maxy, f"Invalid y-range: {miny} > {maxy}"
    
    @given(st.floats(min_value=-170, max_value=170),
           st.floats(min_value=-80, max_value=80),
           st.floats(min_value=0.1, max_value=10),
           st.floats(min_value=0.1, max_value=10))
    def test_valid_coordinates_always_pass_validation(self, lon_min, lat_min, width, height):
        """
        Property 1: For any valid coordinates in range, validation should pass.
        Generates simple rectangles that are guaranteed to be valid.
        """
        # Ensure coordinates don't exceed bounds and form valid rectangle
        lon_max = min(lon_min + width, 180)
        lat_max = min(lat_min + height, 90)
        
        # Skip if rectangle is degenerate (zero area)
        assume(lon_max > lon_min and lat_max > lat_min)
        
        polygon_data = {
            "type": "Polygon",
            "coordinates": [
                [[lon_min, lat_min], [lon_max, lat_min], [lon_max, lat_max], [lon_min, lat_max], [lon_min, lat_min]]
            ]
        }
        
        result = PolygonValidator.validate(polygon_data)
        assert result.is_valid is True
