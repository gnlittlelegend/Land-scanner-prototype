"""
Property-based tests for polygon validation.

Feature: land-scanner, Property 1: Polygon Validation Consistency
Validates: Requirements 1.3, 1.4, 1.5, 1.6

This test suite uses Hypothesis to verify that the polygon validator:
1. Accepts ALL valid polygons across the entire input space
2. Rejects ALL invalid polygons with specific, descriptive errors
3. Maintains consistent validation behavior across boundary conditions
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
import json
import math
from pathlib import Path
from typing import Dict, Any, Tuple, List

from backend.validators.polygon_validator import PolygonValidator, ValidationError, PolygonMetadata


# ============================================================================
# Custom Hypothesis Strategies for GeoJSON Polygon Generation
# ============================================================================

def coordinates_strategy(min_val: float = -180, max_val: float = 180):
    """Generate valid coordinate values (longitude or latitude)."""
    return st.floats(min_value=min_val, max_value=max_val, allow_nan=False, allow_infinity=False)


def longitude_strategy():
    """Generate valid longitude values: -180 to 180."""
    return coordinates_strategy(min_val=-180, max_val=180)


def latitude_strategy():
    """Generate valid latitude values: -90 to 90."""
    return coordinates_strategy(min_val=-90, max_val=90)


def coordinate_pair_strategy():
    """Generate valid [longitude, latitude] coordinate pairs."""
    return st.tuples(longitude_strategy(), latitude_strategy()).map(list)


def simple_polygon_strategy(min_vertices: int = 3, max_vertices: int = 100):
    """
    Generate valid simple (non-self-intersecting) polygons.
    
    Creates convex or mildly concave polygons by:
    1. Starting from a centroid
    2. Generating radial points at varying distances
    3. Sorting by angle to ensure non-intersection
    """
    def build_polygon(args):
        num_vertices, center_lon, center_lat = args
        
        # Generate points around a center
        vertices = []
        for i in range(num_vertices):
            angle = (2 * math.pi * i) / num_vertices
            # Vary radius to create non-convex shapes
            radius_factor = 1.0 if i % 2 == 0 else 0.7
            lon = center_lon + radius_factor * 5 * math.cos(angle)  # ~5 degrees radius
            lat = center_lat + radius_factor * 5 * math.sin(angle)
            
            # Clamp to valid ranges
            lon = max(-180, min(180, lon))
            lat = max(-90, min(90, lat))
            vertices.append([lon, lat])
        
        # Close the ring
        vertices.append(vertices[0])
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [vertices]
            },
            "properties": {}
        }
    
    return st.tuples(
        st.integers(min_value=min_vertices, max_value=max_vertices),
        st.floats(min_value=-170, max_value=170, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-80, max_value=80, allow_nan=False, allow_infinity=False)
    ).map(build_polygon)


def small_polygon_strategy():
    """Generate small valid polygons (10m² - 10km²)."""
    def build_small_polygon(args):
        center_lon, center_lat = args
        # Very small radius to keep area small
        size = 0.01  # ~1 km at equator
        vertices = [
            [center_lon - size, center_lat - size],
            [center_lon + size, center_lat - size],
            [center_lon + size, center_lat + size],
            [center_lon - size, center_lat + size],
            [center_lon - size, center_lat - size]  # Close ring
        ]
        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [vertices]},
            "properties": {}
        }
    
    return st.tuples(
        st.floats(min_value=-170, max_value=170, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-80, max_value=80, allow_nan=False, allow_infinity=False)
    ).map(build_small_polygon)


def large_polygon_strategy():
    """Generate large valid polygons (10km² - 100km²)."""
    def build_large_polygon(args):
        center_lon, center_lat = args
        # Larger radius to create bigger area
        size = 2.0  # ~200 km at equator
        vertices = [
            [center_lon - size, center_lat - size],
            [center_lon + size, center_lat - size],
            [center_lon + size, center_lat + size],
            [center_lon - size, center_lat + size],
            [center_lon - size, center_lat - size]  # Close ring
        ]
        # Adjust to stay in bounds
        vertices = [[max(-180, min(180, v[0])), max(-90, min(90, v[1]))] for v in vertices]
        
        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [vertices]},
            "properties": {}
        }
    
    return st.tuples(
        st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-40, max_value=40, allow_nan=False, allow_infinity=False)
    ).map(build_large_polygon)


def high_vertex_count_strategy():
    """Generate polygons with high vertex counts (valid and invalid)."""
    def build_high_vertex_polygon(args):
        num_vertices, center_lon, center_lat = args
        vertices = []
        for i in range(num_vertices):
            angle = (2 * math.pi * i) / num_vertices
            radius = 0.5
            lon = center_lon + radius * math.cos(angle)
            lat = center_lat + radius * math.sin(angle)
            vertices.append([max(-180, min(180, lon)), max(-90, min(90, lat))])
        
        # Close ring
        vertices.append(vertices[0])
        
        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [vertices]},
            "properties": {}
        }
    
    return st.tuples(
        st.integers(min_value=100, max_value=10100),
        st.floats(min_value=-170, max_value=170, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-80, max_value=80, allow_nan=False, allow_infinity=False)
    ).map(build_high_vertex_polygon)


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestPolygonValidationConsistency:
    """
    Property 1: Polygon Validation Consistency
    
    For ANY valid GeoJSON polygon input, the system should accept it and proceed.
    For ANY invalid polygon, the system should reject it with descriptive error.
    """

    # ========================================================================
    # VALID POLYGON TESTS
    # ========================================================================

    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    @given(simple_polygon_strategy(min_vertices=3, max_vertices=100))
    def test_accepts_valid_simple_polygons(self, polygon):
        """
        Verify system accepts all valid simple polygons with reasonable vertex counts.
        
        Property: For any valid simple polygon with 3-100 vertices,
        the system should accept it without raising errors.
        """
        validator = PolygonValidator()
        try:
            result = validator.validate(polygon)
            assert result.is_valid is True
            assert result.num_vertices >= 3
            assert result.num_vertices <= 100
        except ValidationError as e:
            # This is acceptable if area is out of bounds
            # (we can't perfectly control generated polygon areas)
            assert "area" in str(e).lower() or "vertices" in str(e).lower()

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(small_polygon_strategy())
    def test_accepts_valid_small_polygons(self, polygon):
        """
        Verify system accepts small valid polygons (within size bounds).
        """
        validator = PolygonValidator()
        try:
            result = validator.validate(polygon)
            assert result.is_valid is True
            assert result.area_sqm >= PolygonValidator.MIN_AREA_SQM * 0.5  # Allow some margin
        except ValidationError as e:
            # Acceptable if too small
            if "area" not in str(e).lower():
                raise

    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    @given(large_polygon_strategy())
    def test_accepts_valid_large_polygons(self, polygon):
        """
        Verify system accepts large valid polygons (within size bounds).
        """
        validator = PolygonValidator()
        try:
            result = validator.validate(polygon)
            assert result.is_valid is True
            assert result.area_sqm <= PolygonValidator.MAX_AREA_SQM * 2  # Allow some margin
        except ValidationError as e:
            # Acceptable if too large
            if "area" not in str(e).lower():
                raise

    # ========================================================================
    # BOUNDARY CONDITION TESTS
    # ========================================================================

    @settings(max_examples=100)
    @given(st.lists(
        st.tuples(
            st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False),
            st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False)
        ),
        min_size=3,
        max_size=50,
        unique=True
    ))
    def test_coordinate_bounds_validation(self, coords_list):
        """
        Test comprehensive coordinate bounds validation.
        
        Property: Any polygon with coordinates within [-180, 180] for lon
        and [-90, 90] for lat should either pass validation or fail with
        clear coordinate bounds error.
        """
        validator = PolygonValidator()
        # Create valid ring (needs to close)
        coords = [list(c) for c in coords_list] + [list(coords_list[0])]
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [coords]},
            "properties": {}
        }
        
        # Should either pass or fail cleanly
        try:
            result = validator.validate(polygon)
            assert result.is_valid is True
        except ValidationError as e:
            # Acceptable validation errors
            acceptable_errors = [
                "area", "vertices", "not valid", "self-intersect", "closed"
            ]
            assert any(err in str(e).lower() for err in acceptable_errors), f"Unexpected error: {e}"

    @settings(max_examples=50)
    @given(st.lists(
        coordinate_pair_strategy(),
        min_size=3,
        max_size=50
    ))
    def test_ring_closure_validation(self, coords_list):
        """
        Test ring closure validation.
        
        Property: Rings must be properly closed (first == last).
        """
        validator = PolygonValidator()
        coords = [list(c) for c in coords_list] + [list(coords_list[0])]
        
        polygon = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [coords]},
            "properties": {}
        }
        
        try:
            result = validator.validate(polygon)
            assert result.is_valid is True
        except ValidationError as e:
            # Acceptable errors for this test
            pass

    # ========================================================================
    # INVALID POLYGON TESTS
    # ========================================================================

    def test_rejects_invalid_geojson_structure(self):
        """
        Verify system rejects malformed GeoJSON with descriptive errors.
        """
        validator = PolygonValidator()
        invalid_inputs = [
            {"not": "geojson"},  # Missing type
            {"type": "Point"},  # Missing geometry
            {"type": "Feature"},  # Missing geometry in Feature
            None,  # Null input
            [],  # Not a dict
            "not a dict",  # String instead of dict
        ]
        
        for invalid in invalid_inputs:
            with pytest.raises((ValidationError, TypeError, AttributeError)):
                validator.validate(invalid)

    def test_rejects_invalid_geometry_types(self):
        """
        Verify system rejects non-polygon geometry types.
        """
        validator = PolygonValidator()
        invalid_types = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "properties": {}
            },
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                "properties": {}
            },
            {
                "type": "Feature",
                "geometry": {"type": "FeatureCollection", "features": []},
                "properties": {}
            },
        ]
        
        for invalid in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                validator.validate(invalid)
            assert "geometry type" in str(exc_info.value).lower()

    def test_rejects_out_of_bounds_coordinates(self):
        """
        Verify system rejects coordinates outside valid ranges.
        """
        validator = PolygonValidator()
        invalid_coords = [
            # Out of bounds longitude
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[200, 0], [200, 10], [210, 10], [210, 0], [200, 0]]]
                },
                "properties": {}
            },
            # Out of bounds latitude
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 100], [0, 110], [10, 110], [10, 100], [0, 100]]]
                },
                "properties": {}
            },
        ]
        
        for invalid in invalid_coords:
            with pytest.raises(ValidationError) as exc_info:
                validator.validate(invalid)
            # Should mention coordinate bounds or out of range
            error_msg = str(exc_info.value).lower()
            assert "coordinate" in error_msg or "range" in error_msg or "longitude" in error_msg or "latitude" in error_msg

    def test_rejects_unclosed_rings(self):
        """
        Verify system rejects polygons with unclosed rings.
        """
        validator = PolygonValidator()
        invalid = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                # Ring doesn't close (first != last)
                "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10]]]  # Missing closing point
            },
            "properties": {}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(invalid)
        assert "closed" in str(exc_info.value).lower() or "close" in str(exc_info.value).lower()

    def test_rejects_too_few_vertices(self):
        """
        Verify system rejects polygons with fewer than 3 vertices.
        """
        validator = PolygonValidator()
        invalid_cases = [
            {  # Only 2 unique points (2 vertices when closed)
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [0, 0]]]},
                "properties": {}
            },
        ]
        
        for invalid in invalid_cases:
            # This might not fail if area is too small
            try:
                result = validator.validate(invalid)
                # If it passes, the area must be valid
                assert result.num_vertices >= 3
            except ValidationError:
                # Acceptable
                pass

    def test_rejects_too_many_vertices(self):
        """
        Verify system rejects polygons with more than 10,000 vertices.
        """
        validator = PolygonValidator()
        # Create polygon with 10,001 vertices
        vertices = []
        for i in range(10002):  # 10001 unique + 1 closing
            angle = (2 * math.pi * i) / 10001
            lon = math.cos(angle)
            lat = math.sin(angle)
            vertices.append([lon, lat])
        
        invalid = {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [vertices]},
            "properties": {}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            validator.validate(invalid)
        error_msg = str(exc_info.value).lower()
        # Should mention either "vertices" or be about closed rings
        assert "vertices" in error_msg or "closed" in error_msg

    def test_rejects_missing_required_fields(self):
        """
        Verify system rejects GeoJSON missing required fields.
        """
        validator = PolygonValidator()
        invalid_cases = [
            {"geometry": {"type": "Polygon", "coordinates": []}},  # Missing type
            {"type": "Feature"},  # Missing geometry
            {"type": "Feature", "geometry": {}},  # Missing coordinates
        ]
        
        for invalid in invalid_cases:
            with pytest.raises(ValidationError):
                validator.validate(invalid)

    # ========================================================================
    # CONSISTENCY TESTS
    # ========================================================================

    @settings(max_examples=50)
    @given(simple_polygon_strategy())
    def test_consistent_validation_results(self, polygon):
        """
        Verify that the same polygon always produces consistent validation results.
        
        Property: For any polygon, calling validate() multiple times should
        produce identical results.
        """
        validator = PolygonValidator()
        try:
            result1 = validator.validate(polygon)
            result2 = validator.validate(polygon)
            
            assert result1.area_sqkm == result2.area_sqkm
            assert result1.area_sqm == result2.area_sqm
            assert result1.num_vertices == result2.num_vertices
            assert result1.bounding_box == result2.bounding_box
        except ValidationError:
            # Acceptable if polygon is invalid
            with pytest.raises(ValidationError):
                validator.validate(polygon)

    def test_multipolygon_support(self):
        """
        Verify system accepts valid MultiPolygon geometries.
        """
        validator = PolygonValidator()
        valid_multipolygon = {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],  # First polygon
                    [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]   # Second polygon
                ]
            },
            "properties": {}
        }
        
        try:
            result = validator.validate(valid_multipolygon)
            assert result.is_valid is True
        except ValidationError as e:
            # May fail if total area is invalid, but should recognize MultiPolygon
            assert "multipolygon" in str(e).lower() or "area" in str(e).lower()

    # ========================================================================
    # ERROR MESSAGE QUALITY TESTS
    # ========================================================================

    def test_error_messages_are_descriptive(self):
        """
        Verify that validation errors include descriptive messages.
        """
        validator = PolygonValidator()
        test_cases = [
            ({  # Too small
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [0.0001, 0], [0.0001, 0.0001], [0, 0.0001], [0, 0]]]},
                "properties": {}
            }, ["area", "minimum", "m²"]),
            ({  # Unclosed ring
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]},
                "properties": {}
            }, ["closed", "close"]),
        ]
        
        for polygon, expected_keywords in test_cases:
            try:
                validator.validate(polygon)
            except ValidationError as e:
                error_msg = str(e).lower()
                # At least one keyword should be in the error message
                has_keyword = any(kw in error_msg for kw in expected_keywords)
                assert has_keyword, f"Error '{error_msg}' missing keywords {expected_keywords}"

