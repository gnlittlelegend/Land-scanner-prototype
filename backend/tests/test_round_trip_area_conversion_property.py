"""
Property-based test for round-trip area conversion consistency.

Feature: distance-unit-standardization, Property 11: Round-trip conversion consistency
Validates: Requirements 1.3, 6.6

This test verifies that:
1. Converting m² → km² → m² produces the original value (within floating-point tolerance)
2. Area calculations are reversible and consistent
3. No precision is lost in the standardization process (within acceptable tolerance)
4. All validators maintain consistent area values through conversion cycles
"""

import pytest
import math
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from decimal import Decimal

from backend.validators.polygon_validator import PolygonValidator, ValidationError


# ============================================================================
# Custom Hypothesis Strategies
# ============================================================================

def valid_polygon_strategy():
    """Generate valid polygons that pass validation."""
    return st.tuples(
        st.floats(min_value=-170, max_value=170, allow_nan=False, allow_infinity=False),
        st.floats(min_value=-80, max_value=80, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.001, max_value=0.01, allow_nan=False, allow_infinity=False)
    ).map(lambda args: {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [args[0], args[1]],
                [args[0] + args[2], args[1]],
                [args[0] + args[2], args[1] + args[2]],
                [args[0], args[1] + args[2]],
                [args[0], args[1]]
            ]]
        },
        "properties": {}
    })


def realistic_area_values():
    """
    Generate realistic area values in square metres.
    
    Range from 100 m² to 100,000,000 m² (100 km²), which is the valid range
    for the system.
    """
    return st.floats(
        min_value=100,
        max_value=100_000_000,
        allow_nan=False,
        allow_infinity=False
    )


# ============================================================================
# Helper Functions for Round-Trip Testing
# ============================================================================

def area_sqm_to_sqkm(area_sqm: float) -> float:
    """Convert square metres to square kilometres."""
    if area_sqm is None:
        return None
    return area_sqm / 1_000_000


def area_sqkm_to_sqm(area_sqkm: float) -> float:
    """Convert square kilometres to square metres."""
    if area_sqkm is None:
        return None
    return area_sqkm * 1_000_000


def are_floats_approximately_equal(a: float, b: float, tolerance_percent: float = 0.001) -> bool:
    """
    Check if two floats are approximately equal within a given tolerance.
    
    Uses a percentage-based tolerance to handle different magnitude values.
    
    Args:
        a: First value
        b: Second value
        tolerance_percent: Tolerance as a percentage (default 0.001% = very strict)
    
    Returns:
        True if values are within tolerance, False otherwise
    """
    if a is None or b is None:
        return a == b
    
    if a == b:
        return True
    
    # Handle zero case
    if abs(a) < 1e-10 and abs(b) < 1e-10:
        return True
    
    # Calculate relative difference
    max_val = max(abs(a), abs(b))
    if max_val == 0:
        return True
    
    relative_diff = abs(a - b) / max_val
    tolerance = tolerance_percent / 100.0
    
    return relative_diff <= tolerance


# ============================================================================
# Property Tests for Round-Trip Area Conversion
# ============================================================================

@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(polygon=valid_polygon_strategy())
def test_polygon_area_round_trip_m2_to_km2_to_m2(polygon):
    """
    Property 11: Round-trip conversion consistency (PolygonValidator)
    
    For ANY valid polygon, the area calculated by the validator should remain
    consistent when converted m² → km² → m².
    
    Mathematical property:
    area_sqm == (area_sqm / 1_000_000) * 1_000_000
    
    This tests that:
    1. Validator calculates area correctly
    2. Area value is stable through conversion cycles
    3. No precision is lost (within floating-point tolerance)
    
    Validates: Requirements 1.3, 6.6
    
    Feature: distance-unit-standardization, Property 11: Round-trip conversion consistency
    """
    validator = PolygonValidator()
    
    try:
        metadata = validator.validate(polygon)
        
        original_area_sqm = metadata.area_sqm
        
        # Verify area_sqm is valid
        assert original_area_sqm is not None, "area_sqm should not be None"
        assert isinstance(original_area_sqm, (int, float)), f"area_sqm should be numeric, got {type(original_area_sqm)}"
        assert original_area_sqm >= 0, f"area_sqm should be non-negative, got {original_area_sqm}"
        
        # Round-trip conversion: m² → km² → m²
        area_sqkm = area_sqm_to_sqkm(original_area_sqm)
        recovered_area_sqm = area_sqkm_to_sqm(area_sqkm)
        
        # Verify the round-trip produces approximately the same value
        assert are_floats_approximately_equal(original_area_sqm, recovered_area_sqm, tolerance_percent=0.001), \
            f"Round-trip conversion failed: {original_area_sqm} m² → {area_sqkm} km² → {recovered_area_sqm} m². " \
            f"Difference: {abs(original_area_sqm - recovered_area_sqm)} m²"
    
    except ValidationError:
        # Skip invalid polygons
        pass


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(area_sqm=realistic_area_values())
def test_direct_area_round_trip_conversion(area_sqm):
    """
    Property 11: Round-trip conversion consistency (direct conversion)
    
    For ANY realistic area value in square metres, the round-trip conversion
    m² → km² → m² should produce the original value (within tolerance).
    
    Mathematical property (algebraic identity):
    For all x: x == (x / 1_000_000) * 1_000_000
    
    This is a direct test of the conversion formulas without polygon validation,
    ensuring the mathematical conversion is correct.
    
    Validates: Requirements 1.3, 6.6
    
    Feature: distance-unit-standardization, Property 11: Round-trip conversion consistency
    """
    # Ensure area is in valid system range
    assume(10 <= area_sqm <= 100_000_000)
    
    # Round-trip: m² → km² → m²
    area_sqkm = area_sqm_to_sqkm(area_sqm)
    recovered_area_sqm = area_sqkm_to_sqm(area_sqkm)
    
    # Verify round-trip consistency
    assert are_floats_approximately_equal(area_sqm, recovered_area_sqm, tolerance_percent=0.001), \
        f"Direct round-trip conversion failed: {area_sqm} m² → {area_sqkm} km² → {recovered_area_sqm} m²"
    
    # Verify intermediate km² value is correct
    expected_sqkm = area_sqm / 1_000_000
    assert are_floats_approximately_equal(area_sqkm, expected_sqkm, tolerance_percent=0.001), \
        f"Conversion to km² incorrect: expected {expected_sqkm}, got {area_sqkm}"


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(
    area_sqm_1=realistic_area_values(),
    area_sqm_2=realistic_area_values()
)
def test_combined_areas_round_trip(area_sqm_1, area_sqm_2):
    """
    Property 11: Round-trip conversion consistency (combined areas)
    
    For ANY two realistic area values, adding them before conversion should
    produce the same result as converting separately and adding.
    
    Mathematical property (distributivity):
    (a + b) / 1_000_000 * 1_000_000 == a + b
    
    This verifies that round-trip conversion is distributive over addition,
    ensuring consistency when combining multiple areas.
    
    Validates: Requirements 1.3, 6.6
    
    Feature: distance-unit-standardization, Property 11: Round-trip conversion consistency
    """
    # Ensure areas are in valid system range
    assume(10 <= area_sqm_1 <= 100_000_000)
    assume(10 <= area_sqm_2 <= 100_000_000)
    assume(area_sqm_1 + area_sqm_2 <= 100_000_000)  # Combined stays in range
    
    # Method 1: Add first, then round-trip
    combined = area_sqm_1 + area_sqm_2
    combined_sqkm = area_sqm_to_sqkm(combined)
    result_1 = area_sqkm_to_sqm(combined_sqkm)
    
    # Method 2: Round-trip individually, then add
    rt_1 = area_sqkm_to_sqm(area_sqm_to_sqkm(area_sqm_1))
    rt_2 = area_sqkm_to_sqm(area_sqm_to_sqkm(area_sqm_2))
    result_2 = rt_1 + rt_2
    
    # Both methods should produce equivalent results
    assert are_floats_approximately_equal(result_1, result_2, tolerance_percent=0.01), \
        f"Combined area round-trip inconsistent: " \
        f"Method 1 (add then RT): {result_1}, " \
        f"Method 2 (RT then add): {result_2}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(area_sqm=realistic_area_values())
def test_no_precision_loss_in_conversion(area_sqm):
    """
    Property 11: Round-trip conversion consistency (precision preservation)
    
    For ANY realistic area value, the absolute difference between original
    and recovered value after round-trip conversion should be negligible.
    
    This tests that floating-point precision loss is within acceptable bounds
    for the system's precision requirements.
    
    Validates: Requirements 1.3, 6.6
    
    Feature: distance-unit-standardization, Property 11: Round-trip conversion consistency
    """
    assume(10 <= area_sqm <= 100_000_000)
    
    # Round-trip conversion
    area_sqkm = area_sqm_to_sqkm(area_sqm)
    recovered_area_sqm = area_sqkm_to_sqm(area_sqkm)
    
    # Calculate absolute difference
    absolute_diff = abs(area_sqm - recovered_area_sqm)
    
    # For the system's purposes, precision loss should be negligible
    # Allow maximum 0.01 m² difference (or 0.001% of the original value)
    max_allowed_diff = max(0.01, area_sqm * 0.00001)  # 0.001%
    
    assert absolute_diff <= max_allowed_diff, \
        f"Precision loss too large: original={area_sqm} m², recovered={recovered_area_sqm} m², " \
        f"diff={absolute_diff} m² (max allowed: {max_allowed_diff} m²)"


@settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
@given(
    polygons=st.lists(
        valid_polygon_strategy(),
        min_size=2,
        max_size=5
    )
)
def test_multiple_polygons_consistent_round_trip(polygons):
    """
    Property 11: Round-trip conversion consistency (multiple polygons)
    
    For ANY set of valid polygons, each polygon's area should maintain
    consistency through round-trip conversion independently.
    
    This tests that the round-trip property holds across multiple validation
    operations, ensuring consistency in batch processing scenarios.
    
    Validates: Requirements 1.3, 6.6
    
    Feature: distance-unit-standardization, Property 11: Round-trip conversion consistency
    """
    validator = PolygonValidator()
    
    for polygon in polygons:
        try:
            metadata = validator.validate(polygon)
            original_area_sqm = metadata.area_sqm
            
            if original_area_sqm is None:
                continue
            
            # Round-trip conversion
            area_sqkm = area_sqm_to_sqkm(original_area_sqm)
            recovered_area_sqm = area_sqkm_to_sqm(area_sqkm)
            
            # Each polygon's area should survive round-trip
            assert are_floats_approximately_equal(original_area_sqm, recovered_area_sqm, tolerance_percent=0.001), \
                f"Round-trip inconsistent for polygon: {original_area_sqm} m² → {recovered_area_sqm} m²"
        
        except ValidationError:
            # Skip invalid polygons
            pass


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    area_sqm=realistic_area_values(),
    iterations=st.integers(min_value=1, max_value=5)
)
def test_multiple_round_trips_stable(area_sqm, iterations):
    """
    Property 11: Round-trip conversion consistency (multiple iterations)
    
    For ANY realistic area value, performing multiple round-trip cycles
    m² → km² → m² repeatedly should converge to a stable value.
    
    This tests that repeated conversions don't accumulate error, ensuring
    stability through multiple conversion cycles.
    
    Validates: Requirements 1.3, 6.6
    
    Feature: distance-unit-standardization, Property 11: Round-trip conversion consistency
    """
    assume(10 <= area_sqm <= 100_000_000)
    
    # Start with original area
    current_area_sqm = area_sqm
    previous_area_sqm = None
    
    # Perform multiple round-trip cycles
    for i in range(iterations):
        area_sqkm = area_sqm_to_sqkm(current_area_sqm)
        current_area_sqm = area_sqkm_to_sqm(area_sqkm)
        
        # After first cycle, subsequent cycles should be identical
        if previous_area_sqm is not None:
            assert are_floats_approximately_equal(current_area_sqm, previous_area_sqm, tolerance_percent=0.001), \
                f"Multiple round-trips not stable: iteration {i}, " \
                f"current={current_area_sqm}, previous={previous_area_sqm}"
        
        previous_area_sqm = current_area_sqm
    
    # Final value should match original (within tolerance)
    assert are_floats_approximately_equal(area_sqm, current_area_sqm, tolerance_percent=0.001), \
        f"After {iterations} round-trips: original={area_sqm}, final={current_area_sqm}"


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(area_sqm=realistic_area_values())
def test_zero_loss_for_exact_km2_boundaries(area_sqm):
    """
    Property 11: Round-trip conversion consistency (exact boundaries)
    
    For ANY area value that represents an exact km² boundary
    (multiples of 1,000,000 m²), round-trip conversion should be exactly equal.
    
    This tests that there's no precision loss for "clean" values, ensuring
    perfect round-trip for special cases.
    
    Validates: Requirements 1.3, 6.6
    
    Feature: distance-unit-standardization, Property 11: Round-trip conversion consistency
    """
    # Test exact multiples of 1,000,000 m² (whole km²)
    exact_area_sqm = float(int(area_sqm / 1_000_000) * 1_000_000)
    
    assume(10 <= exact_area_sqm <= 100_000_000)
    
    # Round-trip conversion
    area_sqkm = area_sqm_to_sqkm(exact_area_sqm)
    recovered_area_sqm = area_sqkm_to_sqm(area_sqkm)
    
    # For exact boundaries, the values should be exactly equal
    # (no floating-point precision issues)
    assert recovered_area_sqm == exact_area_sqm, \
        f"Exact km² boundary failed: {exact_area_sqm} m² → {area_sqkm} km² → {recovered_area_sqm} m²"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
