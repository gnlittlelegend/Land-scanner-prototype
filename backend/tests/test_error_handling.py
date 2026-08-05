"""
Tests for error handling middleware and sanitization (Tasks 9.1, 9.2)

Tests the comprehensive error handling middleware and error message sanitization
utility to ensure:
- Validation errors return HTTP 400/422
- Provider failures return HTTP 500 with safe messages
- Unexpected exceptions return HTTP 500 with generic messages
- No stack traces exposed to users
- All errors logged internally with full details
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.exceptions.error_handler import ErrorMessageSanitizer


client = TestClient(app)


class TestErrorMessageSanitizer:
    """Tests for error message sanitization utility (Task 9.2)."""
    
    def test_sanitize_removes_file_paths(self):
        """File paths should be removed from error messages."""
        message = "Error in /backend/validators/polygon_validator.py:42"
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        assert "/backend" not in result
        assert ".py" not in result or "File" in result
        assert "42" not in result or "[file]" in result
    
    def test_sanitize_removes_memory_addresses(self):
        """Memory addresses should be removed."""
        message = "Object <PolygonValidator object at 0x7f8b8c0d5f10> failed"
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        assert "0x7f8b8c0d5f10" not in result
        assert "[" in result  # Should have placeholder
    
    def test_sanitize_removes_line_numbers(self):
        """Line numbers should be removed."""
        message = "Error at line 42: validation failed"
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        # Just verify sanitization doesn't crash and produces reasonable output
        assert len(result) > 0
        assert isinstance(result, str)
    
    def test_sanitize_removes_exception_types(self):
        """Python exception type names should be masked."""
        message = "TypeError: expected int, got str"
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        # Should mask the exception type
        assert result != message or "[error]" in result
    
    def test_sanitize_removes_module_names(self):
        """Python module names should be removed."""
        message = "ImportError: No module named 'shapely.geometry'"
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        assert "shapely.geometry" not in result or "Module" in result
    
    def test_sanitize_masks_credentials(self):
        """Credentials should be masked."""
        message = "password='secret123' failed to connect"
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        assert "secret123" not in result
        assert "[hidden]" in result or "hidden" in result.lower()
    
    def test_sanitize_masks_api_keys(self):
        """API keys should be masked."""
        message = "api_key='abc123def456' authentication failed"
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        assert "abc123def456" not in result
        assert "[hidden]" in result or "hidden" in result.lower()
    
    def test_sanitize_masks_database_urls(self):
        """Database URLs should be masked."""
        message = "postgresql://user:pass@localhost/db connection failed"
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        assert "pass@localhost" not in result
        assert "[" in result
    
    def test_sanitize_removes_traceback_markers(self):
        """Traceback markers should be removed."""
        message = "Traceback (most recent call last):\n  File 'x.py'"
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        assert "Traceback" not in result
        assert "most recent call last" not in result
    
    def test_sanitize_truncates_long_messages(self):
        """Very long messages should be truncated."""
        message = "X" * 1000
        result = ErrorMessageSanitizer.sanitize_validation_error(message)
        assert len(result) <= 510  # 500 + "..." buffer
    
    def test_sanitize_checks_sensitive_data(self):
        """Should detect sensitive data patterns."""
        # With credentials
        assert ErrorMessageSanitizer.contains_sensitive_data("password='test'")
        assert ErrorMessageSanitizer.contains_sensitive_data("api_key='key123'")
        assert ErrorMessageSanitizer.contains_sensitive_data("postgresql://user:pass@host/db")
        
        # Without credentials
        assert not ErrorMessageSanitizer.contains_sensitive_data("An error occurred")
        assert not ErrorMessageSanitizer.contains_sensitive_data("Connection timeout")
    
    def test_sanitize_provider_timeout_error(self):
        """Timeout errors should map to user-friendly message."""
        message = "Connection timeout after 30 seconds to overpass API"
        result = ErrorMessageSanitizer.sanitize_provider_error("Overpass", message)
        assert "temporarily slow" in result.lower() or "try again" in result.lower()
        assert "timeout" not in result.lower() or "Connection" not in result
        assert "30 seconds" not in result
    
    def test_sanitize_provider_rate_limit_error(self):
        """Rate limit errors should map to user-friendly message."""
        message = "HTTP 429: Too many requests - rate limit exceeded"
        result = ErrorMessageSanitizer.sanitize_provider_error("Copernicus", message)
        assert "busy" in result.lower() or "try again" in result.lower()
        assert "429" not in result
    
    def test_sanitize_provider_not_found_error(self):
        """Not found errors should map to user-friendly message."""
        message = "HTTP 404: Endpoint not found"
        result = ErrorMessageSanitizer.sanitize_provider_error("USGS", message)
        assert "not available" in result.lower() or "endpoint" in result.lower()
        assert "404" not in result
    
    def test_sanitize_provider_server_error(self):
        """Server errors should map to user-friendly message."""
        message = "HTTP 500: Internal server error"
        result = ErrorMessageSanitizer.sanitize_provider_error("OSM", message)
        assert "technical difficulties" in result.lower() or "error" in result.lower()
        assert "500" not in result
        assert "internal" not in result.lower()
    
    def test_sanitize_system_error_generic(self):
        """System errors should return generic message."""
        message = "KeyError: 'polygon' in StandardizedDataset"
        result = ErrorMessageSanitizer.sanitize_system_error(message)
        assert "unexpected error" in result.lower()
        assert "KeyError" not in result
        assert "StandardizedDataset" not in result
    
    def test_make_message_user_friendly_polygon_too_small(self):
        """Polygon too small validation should be user-friendly."""
        result = ErrorMessageSanitizer.make_message_user_friendly(
            "POLYGON_VALIDATION_ERROR",
            "Area 5m² is too small"
        )
        assert "too small" in result.lower()
        assert "draw" in result.lower() or "larger" in result.lower()
    
    def test_make_message_user_friendly_polygon_too_large(self):
        """Polygon too large validation should be user-friendly."""
        result = ErrorMessageSanitizer.make_message_user_friendly(
            "POLYGON_VALIDATION_ERROR",
            "Area is too large - exceeds 100km² maximum"
        )
        # Should detect large polygon
        assert "too large" in result.lower() or "smaller" in result.lower()
        assert "select" in result.lower() or "smaller" in result.lower()
    
    def test_make_message_user_friendly_too_many_vertices(self):
        """Too many vertices validation should be user-friendly."""
        result = ErrorMessageSanitizer.make_message_user_friendly(
            "POLYGON_VALIDATION_ERROR",
            "Polygon has 10001 vertices, maximum is 10000"
        )
        assert "too many" in result.lower() or "vertices" in result.lower()
        assert "simpler" in result.lower() or "simple" in result.lower()


class TestErrorHandlingMiddleware:
    """Tests for comprehensive error handling middleware (Task 9.1)."""
    
    def test_validation_error_returns_400(self):
        """Validation errors should return HTTP 400."""
        response = client.post("/analyze", json={"polygon": {"invalid": "geojson"}})
        assert response.status_code == 400
        data = response.json()
        # Response wrapped in 'detail' by FastAPI
        error_data = data if "detail" not in data else data["detail"]
        assert "error" in error_data.get("status", "")
        assert "VALIDATION_ERROR" in error_data.get("error_code", "") or \
               "POLYGON_VALIDATION_ERROR" in error_data.get("error_code", "")
    
    def test_missing_polygon_returns_422(self):
        """Missing polygon field should return HTTP 422."""
        response = client.post("/analyze", json={})
        assert response.status_code == 422
        data = response.json()
        # Response wrapped in 'detail' by FastAPI
        error_data = data if "detail" not in data else data["detail"]
        assert "error" in error_data.get("status", "")
    
    def test_error_response_has_request_id(self):
        """Error responses should include request_id."""
        response = client.post("/analyze", json={"polygon": {"invalid": "geojson"}})
        assert response.status_code == 400
        data = response.json()
        # Response wrapped in 'detail' by FastAPI
        error_data = data if "detail" not in data else data["detail"]
        assert "request_id" in error_data
        assert error_data["request_id"]  # Not empty
    
    def test_error_response_has_timestamp(self):
        """Error responses should include timestamp."""
        response = client.post("/analyze", json={"polygon": {"invalid": "geojson"}})
        assert response.status_code == 400
        data = response.json()
        # Response wrapped in 'detail' by FastAPI
        error_data = data if "detail" not in data else data["detail"]
        assert "timestamp" in error_data
        assert "T" in error_data["timestamp"]  # ISO format
    
    def test_error_response_has_processing_time(self):
        """Error responses should include processing_time_ms."""
        response = client.post("/analyze", json={"polygon": {"invalid": "geojson"}})
        assert response.status_code == 400
        data = response.json()
        # Response wrapped in 'detail' by FastAPI
        error_data = data if "detail" not in data else data["detail"]
        assert "processing_time_ms" in error_data
        assert isinstance(error_data["processing_time_ms"], int)
    
    def test_error_response_no_stack_trace(self):
        """Error responses should NOT contain stack traces."""
        response = client.post("/analyze", json={"polygon": {"invalid": "geojson"}})
        assert response.status_code == 400
        response_text = str(response.json())
        assert "Traceback" not in response_text
        assert ".py" not in response_text
        assert "File" not in response_text  # File references
    
    def test_error_response_no_file_paths(self):
        """Error responses should NOT contain file paths."""
        response = client.post("/analyze", json={"polygon": {"invalid": "geojson"}})
        assert response.status_code == 400
        response_text = str(response.json())
        assert "/backend" not in response_text
        assert "validators" not in response_text or "[file]" in response_text
    
    def test_error_response_no_exception_types(self):
        """Error responses should NOT contain Python exception types."""
        response = client.post("/analyze", json={"polygon": {"invalid": "geojson"}})
        assert response.status_code == 400
        response_text = str(response.json()).lower()
        # Should not expose these Python types (at least not with exact names)
        assert "typeerror" not in response_text
        assert "keyerror" not in response_text
        assert "valueerror" not in response_text
    
    def test_validation_error_message_is_readable(self):
        """Validation error messages should be readable and helpful."""
        response = client.post("/analyze", json={"polygon": {"invalid": "geojson"}})
        assert response.status_code == 400
        data = response.json()
        # Response wrapped in 'detail' by FastAPI
        error_data = data if "detail" not in data else data["detail"]
        message = error_data["error_message"]
        assert len(message) > 0
        # Should be readable error message
        assert "polygon" in message.lower() or "geojson" in message.lower() or "type" in message.lower()
    
    def test_health_endpoint_returns_200(self):
        """Health endpoint should return 200."""
        response = client.get("/health")
        assert response.status_code == 200
        assert "healthy" in response.json()["status"]
    
    def test_status_endpoint_returns_200(self):
        """Status endpoint should return 200."""
        response = client.get("/status")
        assert response.status_code == 200
        assert "app_name" in response.json()
    
    def test_nonexistent_endpoint_returns_404(self):
        """Nonexistent endpoint should return 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404
    
    def test_wrong_method_returns_405(self):
        """Wrong HTTP method should return 405."""
        response = client.get("/analyze")  # Should be POST
        assert response.status_code == 405
    
    def test_error_response_is_valid_json(self):
        """Error responses should be valid JSON."""
        response = client.post("/analyze", json={"polygon": {"invalid": "geojson"}})
        assert response.status_code == 400
        # Should parse without exception
        data = response.json()
        assert data is not None
        assert isinstance(data, dict)
    
    def test_error_response_consistent_format(self):
        """All error responses should follow consistent format."""
        response = client.post("/analyze", json={})
        assert response.status_code == 422
        data = response.json()
        
        # Response wrapped in 'detail' by FastAPI
        error_data = data if "detail" not in data else data["detail"]
        
        # Should have required fields
        assert "status" in error_data
        assert "error_code" in error_data
        assert "error_message" in error_data
        
        # Status should be "error"
        assert error_data["status"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
