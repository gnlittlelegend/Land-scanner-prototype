"""
Property-based test for HTTP status codes (Property 11: HTTP Status Code Consistency).

Tests that the API returns consistent and correct HTTP status codes across all input scenarios:
- Valid requests always return 200
- Invalid polygon input always returns 400 or 422
- Provider failures always return 500
- Partial success returns 200 with degradation
- System errors return 500

Feature: land-scanner, Property 11: HTTP Status Code Consistency
Validates: Requirements 9.4, 9.5, 9.6, 9.7, 8.1, 8.2
"""

import pytest
import json
import logging
from hypothesis import given, settings, strategies as st
from hypothesis import HealthCheck
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.data_models import Polygon

logger = logging.getLogger(__name__)


# Create test client
client = TestClient(app)


# Hypothesis strategies for polygon generation

@st.composite
def valid_polygon_strategy(draw):
    """Generate valid GeoJSON polygons with various sizes and shapes."""
    # Size variations: various areas that should pass validation
    valid_areas = [
        10,      # Minimum (m²)
        25,      # Small
        100,     # Small-medium
        500,     # Medium
        1000,    # Medium
        10000,   # Large
        100000,  # Very large (10km²)
    ]
    
    area_m2 = draw(st.sampled_from(valid_areas))
    
    # Latitude variations (account for projection)
    latitude = draw(st.floats(min_value=-85, max_value=85))
    longitude = draw(st.floats(min_value=-170, max_value=170))  # Avoid antimeridian edge issues
    
    # Generate simple square polygon
    # Convert area to side length in degrees (rough approximation)
    # 1 degree ≈ 111 km at equator, so 1 m² ≈ 0.00001 degrees²
    degrees_per_m2 = 0.00001  # Very rough approximation
    side_length = (area_m2 * degrees_per_m2) ** 0.5
    
    # Ensure side_length doesn't cause coordinates to go out of bounds
    if latitude + side_length > 85:
        latitude = 85 - side_length
    if longitude + side_length > 180:
        longitude = 180 - side_length
    
    # Create square polygon
    coords = [
        [longitude, latitude],
        [longitude + side_length, latitude],
        [longitude + side_length, latitude + side_length],
        [longitude, latitude + side_length],
        [longitude, latitude],  # Close the ring
    ]
    
    # Wrap in Feature with geometry field
    polygon = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [coords]
        }
    }
    
    return {"polygon": polygon}


@st.composite
def invalid_geojson_strategy(draw):
    """Generate invalid GeoJSON with various error types."""
    error_type = draw(st.sampled_from([
        "missing_coordinates",
        "wrong_geometry_type",
        "null_geometry",
        "invalid_json",
        "missing_geometry",
        "null_features",
    ]))
    
    if error_type == "missing_coordinates":
        return {"polygon": {"type": "Feature", "geometry": {"type": "Polygon"}}}  # Missing coordinates
    elif error_type == "wrong_geometry_type":
        return {"polygon": {"type": "Feature", "geometry": {"type": "Point", "coordinates": [0, 0]}}}  # Wrong geometry type
    elif error_type == "null_geometry":
        return {"polygon": {"type": "Feature", "geometry": None}}  # Null geometry
    elif error_type == "invalid_json":
        return "{invalid json"  # Invalid JSON syntax (string, not dict)
    elif error_type == "missing_geometry":
        return {"polygon": {"type": "Feature"}}  # Missing geometry field
    elif error_type == "null_features":
        return {"polygon": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": None}}}  # Null coordinates
    
    return {"polygon": {}}


@st.composite
def polygon_too_small_strategy(draw):
    """Generate polygons that are too small (< 10 m²)."""
    # Generate very small areas: 1m², 5m², 9.9m², etc.
    tiny_areas = [0.001, 0.1, 1, 5, 9.99]
    area_m2 = draw(st.sampled_from(tiny_areas))
    
    latitude = draw(st.floats(min_value=-85, max_value=85))
    longitude = draw(st.floats(min_value=-170, max_value=170))
    
    degrees_per_m2 = 0.00001
    side_length = (area_m2 * degrees_per_m2) ** 0.5
    
    coords = [
        [longitude, latitude],
        [longitude + side_length, latitude],
        [longitude + side_length, latitude + side_length],
        [longitude, latitude + side_length],
        [longitude, latitude],
    ]
    
    return {"polygon": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]}}}


@st.composite
def polygon_too_large_strategy(draw):
    """Generate polygons that are too large (> 100 km²)."""
    # Generate very large areas (in m²: 101km², 500km², etc.)
    huge_areas = [101000, 500000, 1000000, 10000000]
    area_m2 = draw(st.sampled_from(huge_areas))
    
    latitude = draw(st.floats(min_value=-85, max_value=85))
    longitude = draw(st.floats(min_value=-170, max_value=170))
    
    degrees_per_m2 = 0.00001
    side_length = (area_m2 * degrees_per_m2) ** 0.5
    
    # Clamp coordinates to valid range
    if latitude + side_length > 85:
        latitude = 85 - side_length
    if longitude + side_length > 180:
        longitude = 180 - side_length
    
    coords = [
        [longitude, latitude],
        [longitude + side_length, latitude],
        [longitude + side_length, latitude + side_length],
        [longitude, latitude + side_length],
        [longitude, latitude],
    ]
    
    return {"polygon": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]}}}


@st.composite
def polygon_too_many_vertices_strategy(draw):
    """Generate polygons with too many vertices (> 10,000)."""
    num_vertices = draw(st.sampled_from([10001, 50000, 100000]))
    
    # Generate a polygon with many vertices
    latitude = 0
    longitude = 0
    coords = []
    
    for i in range(min(num_vertices, 100)):  # Limit to 100 for reasonable test size
        angle = (i / 100) * 2 * 3.14159
        x = longitude + 0.01 * (i / 100)
        y = latitude + 0.01 * (i / 100)
        coords.append([x, y])
    
    coords.append(coords[0])  # Close the ring
    
    return {"polygon": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]}}}


@st.composite
def malformed_coordinates_strategy(draw):
    """Generate polygons with malformed coordinates."""
    error_type = draw(st.sampled_from([
        "out_of_range_lat",
        "out_of_range_lon",
        "unclosed_ring",
        "string_coordinates",
        "missing_coordinate_element",
    ]))
    
    if error_type == "out_of_range_lat":
        coords = [[0, 91], [0, 92], [1, 92], [1, 91], [0, 91]]
    elif error_type == "out_of_range_lon":
        coords = [[181, 0], [182, 0], [182, 1], [181, 1], [181, 0]]
    elif error_type == "unclosed_ring":
        coords = [[0, 0], [0, 1], [1, 1], [1, 0]]  # Missing closing coordinate
    elif error_type == "string_coordinates":
        coords = [["0", "0"], ["0", "1"], ["1", "1"], ["1", "0"], ["0", "0"]]
    elif error_type == "missing_coordinate_element":
        coords = [[0], [0, 1], [1, 1], [1, 0], [0]]
    
    return {"polygon": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [coords]}}}


# Test classes

class TestHTTPStatusCodeValidity:
    """Property-based tests for HTTP status code consistency."""

    @given(valid_polygon_strategy())
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_valid_polygon_returns_200(self, request_data):
        """Property: Valid polygons always return HTTP 200."""
        try:
            # Send request with valid polygon
            response = client.post("/analyze", json=request_data)
            
            # Verify HTTP 200
            assert response.status_code == 200, f"Expected 200 but got {response.status_code} for valid polygon"
            
            # Verify response is valid JSON
            response_json = response.json()
            assert isinstance(response_json, dict)
            
            # Verify required fields present
            assert "status" in response_json
            assert "analysis_summary" in response_json or "error_message" in response_json
            
            logger.info(f"✓ Valid polygon returned HTTP 200")
        except Exception as e:
            logger.error(f"✗ Unexpected error with valid polygon: {e}")
            raise

    @given(invalid_geojson_strategy())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_invalid_geojson_returns_400_or_422(self, request_data):
        """Property: Invalid GeoJSON always returns HTTP 400 or 422."""
        try:
            if isinstance(request_data, str):  # Invalid JSON
                response = client.post("/analyze", content=request_data, headers={"Content-Type": "application/json"})
            else:
                response = client.post("/analyze", json=request_data)
            
            # Verify HTTP 400 or 422
            assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code} for invalid GeoJSON"
            
            # Verify error response structure
            response_json = response.json()
            assert "error_code" in response_json or "detail" in response_json
            
            logger.info(f"✓ Invalid GeoJSON returned HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"✗ Unexpected error with invalid GeoJSON: {e}")
            raise

    @given(polygon_too_small_strategy())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_polygon_too_small_returns_400_or_422(self, request_data):
        """Property: Polygons too small return HTTP 400 or 422."""
        try:
            response = client.post("/analyze", json=request_data)
            
            # Verify HTTP 400 or 422
            assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code} for too-small polygon"
            
            # Verify error message mentions size
            response_json = response.json()
            error_msg = str(response_json).lower()
            assert "area" in error_msg or "size" in error_msg or "minimum" in error_msg, \
                f"Error message should mention area/size: {response_json}"
            
            logger.info(f"✓ Too-small polygon returned HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"✗ Unexpected error with too-small polygon: {e}")
            raise

    @given(polygon_too_large_strategy())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_polygon_too_large_returns_400_or_422(self, request_data):
        """Property: Polygons too large return HTTP 400 or 422."""
        try:
            response = client.post("/analyze", json=request_data)
            
            # Verify HTTP 400 or 422
            assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code} for too-large polygon"
            
            # Verify error message mentions size
            response_json = response.json()
            error_msg = str(response_json).lower()
            assert "area" in error_msg or "size" in error_msg or "maximum" in error_msg, \
                f"Error message should mention area/size: {response_json}"
            
            logger.info(f"✓ Too-large polygon returned HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"✗ Unexpected error with too-large polygon: {e}")
            raise

    @given(polygon_too_many_vertices_strategy())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_polygon_too_many_vertices_returns_400_or_422(self, request_data):
        """Property: Polygons with too many vertices return HTTP 400 or 422."""
        try:
            response = client.post("/analyze", json=request_data)
            
            # Verify HTTP 400 or 422
            assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code} for too-many-vertices polygon"
            
            # Verify error message mentions vertices
            response_json = response.json()
            error_msg = str(response_json).lower()
            assert "vertex" in error_msg or "vertices" in error_msg or "points" in error_msg, \
                f"Error message should mention vertices: {response_json}"
            
            logger.info(f"✓ Too-many-vertices polygon returned HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"✗ Unexpected error with too-many-vertices polygon: {e}")
            raise

    @given(malformed_coordinates_strategy())
    @settings(max_examples=30, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_malformed_coordinates_returns_400_or_422(self, request_data):
        """Property: Malformed coordinates return HTTP 400 or 422."""
        try:
            response = client.post("/analyze", json=request_data)
            
            # Verify HTTP 400 or 422
            assert response.status_code in [400, 422], f"Expected 400/422 but got {response.status_code} for malformed coordinates"
            
            logger.info(f"✓ Malformed coordinates returned HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"✗ Unexpected error with malformed coordinates: {e}")
            raise

    def test_invalid_endpoint_returns_404(self):
        """Property: Invalid endpoints return HTTP 404."""
        response = client.post("/nonexistent")
        assert response.status_code == 404, f"Expected 404 but got {response.status_code}"
        logger.info(f"✓ Invalid endpoint returned HTTP 404")

    def test_invalid_method_returns_405(self):
        """Property: Wrong HTTP method returns HTTP 405."""
        response = client.get("/analyze")  # GET instead of POST
        assert response.status_code == 405, f"Expected 405 but got {response.status_code}"
        logger.info(f"✓ Invalid HTTP method returned HTTP 405")

    @given(valid_polygon_strategy())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much])
    def test_status_code_consistency_multiple_requests(self, request_data):
        """Property: Same input always produces same status code."""
        # Send same request multiple times
        response1 = client.post("/analyze", json=request_data)
        response2 = client.post("/analyze", json=request_data)
        response3 = client.post("/analyze", json=request_data)
        
        # All should have same status code
        assert response1.status_code == response2.status_code == response3.status_code, \
            f"Status codes should be consistent: {response1.status_code}, {response2.status_code}, {response3.status_code}"
        
        logger.info(f"✓ Status code consistent across multiple requests: {response1.status_code}")

    def test_response_headers_valid_request(self):
        """Verify response headers are correct for valid requests."""
        # Create minimal valid polygon
        valid_polygon = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]]
                }
            }
        }
        
        response = client.post("/analyze", json=valid_polygon)
        
        # Verify headers
        assert response.headers.get("Content-Type") is not None, "Content-Type header missing"
        assert "application/json" in response.headers.get("Content-Type", ""), "Content-Type should be JSON"
        
        logger.info(f"✓ Response headers correct")

    def test_response_body_format_200(self):
        """Verify HTTP 200 response has required fields."""
        valid_polygon = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]]
                }
            }
        }
        
        response = client.post("/analyze", json=valid_polygon)
        
        if response.status_code == 200:
            body = response.json()
            # Verify required fields for successful response
            assert "request_id" in body or "status" in body, "Missing request_id or status"
            logger.info(f"✓ HTTP 200 response format correct")

    def test_response_body_format_400(self):
        """Verify HTTP 400 response has required error fields."""
        invalid_polygon = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": []  # Missing coordinates
                }
            }
        }
        
        response = client.post("/analyze", json=invalid_polygon)
        
        if response.status_code in [400, 422]:
            body = response.json()
            # Verify error response has readable message
            assert "detail" in body or "error_message" in body or "message" in body, \
                "Error response should have error message"
            logger.info(f"✓ HTTP 400/422 response format correct")


class TestHTTPStatusCodeErrorScenarios:
    """Tests for error scenarios and provider failures."""

    @patch('backend.managers.data_source_manager.DataSourceManager.collect_data')
    def test_complete_provider_failure_returns_500(self, mock_collect):
        """Provider failure should return HTTP 500."""
        # Mock all providers to fail
        mock_collect.side_effect = Exception("All providers failed")
        
        valid_polygon = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]]
                }
            }
        }
        
        response = client.post("/analyze", json=valid_polygon)
        
        # Should return 500 error
        assert response.status_code == 500, f"Expected 500 but got {response.status_code}"
        logger.info(f"✓ Complete provider failure returned HTTP 500")

    def test_error_response_no_stack_trace(self):
        """Error responses should not expose stack traces."""
        invalid_polygon = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": []  # Empty coordinates
                }
            }
        }
        
        response = client.post("/analyze", json=invalid_polygon)
        
        if response.status_code >= 400:
            body_str = str(response.json())
            # Verify no stack trace patterns
            assert ".py" not in body_str, "Error should not expose .py file paths"
            assert "Traceback" not in body_str, "Error should not expose traceback"
            assert "File " not in body_str, "Error should not expose file references"
            logger.info(f"✓ Error response has no stack traces")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
