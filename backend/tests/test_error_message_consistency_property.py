"""
Property-based test for error message consistency.

Feature: distance-unit-standardization, Property 5: Error messages contain only square metres
Validates: Requirements 2.3, 9.3, 9.5

This test verifies that:
1. All error messages related to polygon area use only m² unit
2. Error messages never contain "km²" or kilometre-based units
3. Error messages are consistent across boundary conditions
"""

import pytest
import math
from hypothesis import given, strategies as st, settings, HealthCheck

from backend.validators.polygon_validator import PolygonValidator, ValidationError


# ============================================================================
# Custom Hypothesis Strategies for Boundary Polygon Generation
# ============================================================================

def create_tiny_polygon(center_lon: float, center_lat: float, delta: float) -> dict:
    """Create a tiny polygon with specified delta from center."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [center_lon, center_lat],
                [center_lon + delta, center_lat],
                [center_lon + delta, center_lat + delta],
                [center_lon, center_lat + delta],
                [center_lon, center_lat]
            ]]
        },
        "properties": {}
    }


def create_large_polygon(center_lon: float, center_lat: float, delta: float) -> dict:
    """Create a large polygon with specified delta from center."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [center_lon, center_lat],
                [center_lon + delta, center_lat],
                [center_lon + delta, center_lat + delta],
                [center_lon, center_lat + delta],
                [center_lon, center_lat]
            ]]
        },
        "properties": {}
    }


def tiny_polygon_strategy():
    """
    Generate polygons that are too small (below 10 m² minimum).
    
    Uses very small delta values to ensure polygon area is below minimum.
    """
    return st.tuples(
        st.floats(min_value=-170, max_value=170, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-80, max_value=80, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.000001, max_value=0.00001, allow_nan=False, allow_infinity=False)
    ).map(lambda args: create_tiny_polygon(args[0], args[1], args[2]))


def large_polygon_strategy():
    """
    Generate polygons that are too large (above 100,000,000 m² maximum).
    
    Uses large delta values to ensure polygon area exceeds maximum.
    """
    return st.tuples(
        st.floats(min_value=-170, max_value=170, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-80, max_value=80, allow_nan=False, allow_infinity=False),
        st.floats(min_value=1.0, max_value=2.0, allow_nan=False, allow_infinity=False)
    ).map(lambda args: create_large_polygon(args[0], args[1], args[2]))


# ============================================================================
# Property Tests for Error Message Consistency
# ============================================================================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(polygon=tiny_polygon_strategy())
def test_error_messages_never_contain_km_units(polygon):
    """
    Property 5: Error messages contain only square metres
    
    For ANY polygon that fails validation (at boundaries or otherwise),
    the error message should NEVER contain "km²" or other km-based units.
    It should ONLY contain "m²" for metres.
    
    Validates: Requirements 2.3, 9.3, 9.5
    
    Feature: distance-unit-standardization, Property 5: Error messages contain only square metres
    """
    validator = PolygonValidator()
    
    try:
        validator.validate(polygon)
        # If validation passes, this test isn't applicable to this polygon
        pytest.skip("Polygon passed validation, cannot test error message")
    except ValidationError as exc_info:
        error_msg = str(exc_info)
        
        # CRITICAL: Error message must NOT contain km-based units
        assert "km²" not in error_msg, \
            f"Error message contains 'km²' (forbidden). Message: {error_msg}"
        assert "km2" not in error_msg.lower(), \
            f"Error message contains 'km2' (forbidden). Message: {error_msg}"
        assert "square kilometer" not in error_msg.lower(), \
            f"Error message contains 'square kilometer' (forbidden). Message: {error_msg}"
        
        # REQUIRED: Error message must contain m² unit
        assert "m²" in error_msg, \
            f"Error message does not contain 'm²' unit. Message: {error_msg}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(polygon=large_polygon_strategy())
def test_large_polygon_error_messages_never_contain_km(polygon):
    """
    Property 5: Error messages contain only square metres (for large polygons)
    
    For ANY large polygon that exceeds maximum area, the error message
    should express the area in m² only, never in km².
    
    Validates: Requirements 2.3, 9.3, 9.5
    
    Feature: distance-unit-standardization, Property 5: Error messages contain only square metres
    """
    validator = PolygonValidator()
    
    try:
        validator.validate(polygon)
        # If validation passes, this test isn't applicable to this polygon
        pytest.skip("Polygon passed validation, cannot test error message")
    except ValidationError as exc_info:
        error_msg = str(exc_info)
        
        # CRITICAL: Error message must NOT contain km-based units
        assert "km²" not in error_msg, \
            f"Error message contains 'km²' (forbidden). Message: {error_msg}"
        assert "km2" not in error_msg.lower(), \
            f"Error message contains 'km2' (forbidden). Message: {error_msg}"
        assert "square kilometer" not in error_msg.lower(), \
            f"Error message contains 'square kilometer' (forbidden). Message: {error_msg}"
        
        # REQUIRED: Error message must contain m² unit
        assert "m²" in error_msg, \
            f"Error message does not contain 'm²' unit. Message: {error_msg}"


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(
    tiny_polygon=tiny_polygon_strategy(),
    large_polygon=large_polygon_strategy()
)
def test_all_boundary_error_messages_use_metres_only(tiny_polygon, large_polygon):
    """
    Property 5: Error messages contain only square metres (comprehensive boundary test)
    
    For ANY combination of polygons at validation boundaries (too small or too large),
    all error messages should use m² consistently and never mention km.
    
    Validates: Requirements 2.3, 9.3, 9.5
    
    Feature: distance-unit-standardization, Property 5: Error messages contain only square metres
    """
    validator = PolygonValidator()
    
    for polygon in [tiny_polygon, large_polygon]:
        try:
            validator.validate(polygon)
        except ValidationError as exc_info:
            error_msg = str(exc_info)
            
            # Check no km-based units appear
            assert "km²" not in error_msg, \
                f"Tiny/Large polygon error has 'km²': {error_msg}"
            assert "km2" not in error_msg.lower(), \
                f"Tiny/Large polygon error has 'km2': {error_msg}"
            
            # Check m² unit appears for area-related errors
            if "area" in error_msg.lower():
                assert "m²" in error_msg, \
                    f"Area error missing 'm²' unit: {error_msg}"


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(polygon=tiny_polygon_strategy())
def test_minimum_area_error_format_consistency(polygon):
    """
    Property 5: Error messages contain only square metres (minimum area focus)
    
    For ANY polygon below minimum area, the error message should:
    1. Indicate it's below minimum
    2. Show "10 m²" as the minimum threshold
    3. Show actual area in m²
    4. NEVER mention km²
    
    Validates: Requirements 2.1, 2.3, 9.1, 9.3, 9.5
    
    Feature: distance-unit-standardization, Property 5: Error messages contain only square metres
    """
    validator = PolygonValidator()
    
    try:
        validator.validate(polygon)
        pytest.skip("Polygon passed validation, cannot test error message")
    except ValidationError as exc_info:
        error_msg = str(exc_info)
        
        # Check for below minimum indicator
        if "below" in error_msg.lower() or "minimum" in error_msg.lower():
            # This is a minimum area error
            assert "10 m²" in error_msg or "10m²" in error_msg, \
                f"Minimum error missing '10 m²' threshold: {error_msg}"
            assert "km²" not in error_msg, \
                f"Minimum error contains 'km²': {error_msg}"
            assert "m²" in error_msg, \
                f"Minimum error missing 'm²' unit: {error_msg}"


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(polygon=large_polygon_strategy())
def test_maximum_area_error_format_consistency(polygon):
    """
    Property 5: Error messages contain only square metres (maximum area focus)
    
    For ANY polygon above maximum area, the error message should:
    1. Indicate it exceeds maximum
    2. Show area value in m² (not km²)
    3. Show maximum threshold in m²
    4. NEVER mention km²
    
    Validates: Requirements 2.2, 2.3, 9.2, 9.3, 9.5
    
    Feature: distance-unit-standardization, Property 5: Error messages contain only square metres
    """
    validator = PolygonValidator()
    
    try:
        validator.validate(polygon)
        pytest.skip("Polygon passed validation, cannot test error message")
    except ValidationError as exc_info:
        error_msg = str(exc_info)
        
        # Check for exceeds maximum indicator
        if "exceeds" in error_msg.lower() or "maximum" in error_msg.lower():
            # This is a maximum area error
            assert "100,000,000 m²" in error_msg or "100000000 m²" in error_msg or "100000000m²" in error_msg or "1e8 m²" in error_msg, \
                f"Maximum error missing '100,000,000 m²' threshold (or similar): {error_msg}"
            assert "km²" not in error_msg, \
                f"Maximum error contains 'km²': {error_msg}"
            assert "m²" in error_msg, \
                f"Maximum error missing 'm²' unit: {error_msg}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
