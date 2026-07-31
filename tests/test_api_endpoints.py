"""
Integration tests for FastAPI endpoints.

Tests the /analyze endpoint with valid and invalid polygon inputs.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

# Create test client
client = TestClient(app)


class TestAnalyzeEndpoint:
    """Tests for POST /analyze endpoint."""
    
    def test_analyze_with_valid_polygon(self):
        """Test /analyze endpoint with valid polygon."""
        valid_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [0, 0],
                    [10, 0],
                    [10, 10],
                    [0, 10],
                    [0, 0]
                ]
            ]
        }
        
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        assert response.status_code == 200
        data = response.json()
        # Status can be success or partial (partial when some data isn't collected in test env)
        assert data["status"] in ["success", "partial"]
        assert "request_id" in data
        assert "analysis_summary" in data
        assert data["analysis_summary"]["polygon_area_sqkm"] > 0
    
    def test_analyze_with_missing_polygon_field(self):
        """Test /analyze endpoint with missing polygon field."""
        response = client.post("/analyze", json={})
        
        # FastAPI returns 422 for missing required fields (Unprocessable Entity)
        assert response.status_code in [400, 422]
        data = response.json()
        # Either detail format depends on whether it's caught by Pydantic or our handler
        if "detail" in data and isinstance(data["detail"], dict):
            assert data["detail"]["status"] == "error"
            assert "VALIDATION_ERROR" in data["detail"]["error_code"]
        else:
            # FastAPI's built-in validation error
            assert "detail" in data
    
    def test_analyze_with_invalid_polygon_missing_type(self):
        """Test /analyze endpoint with invalid polygon missing type field."""
        invalid_polygon = {
            "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
        }
        
        response = client.post("/analyze", json={"polygon": invalid_polygon})
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["status"] == "error"
        assert "POLYGON_VALIDATION_ERROR" in data["detail"]["error_code"]
    
    def test_analyze_with_invalid_polygon_out_of_range(self):
        """Test /analyze endpoint with invalid polygon coordinates out of range."""
        invalid_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [0, 0],
                    [200, 0],
                    [200, 10],
                    [0, 10],
                    [0, 0]
                ]
            ]
        }
        
        response = client.post("/analyze", json={"polygon": invalid_polygon})
        
        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["status"] == "error"
        assert "POLYGON_VALIDATION_ERROR" in data["detail"]["error_code"]
    
    def test_analyze_response_structure(self):
        """Test /analyze endpoint response has correct structure."""
        valid_polygon = {
            "type": "Polygon",
            "coordinates": [
                [
                    [0, 0],
                    [5, 0],
                    [5, 5],
                    [0, 5],
                    [0, 0]
                ]
            ]
        }
        
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "request_id" in data
        assert "status" in data
        assert "timestamp" in data
        assert "processing_time_ms" in data
        assert "analysis_summary" in data
        assert "land_information" in data
        assert "processing_status" in data
        assert "provider_status" in data
        assert "errors" in data


class TestHealthEndpoint:
    """Tests for GET /health endpoint."""
    
    def test_health_check(self):
        """Test /health endpoint returns service status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data


class TestStatusEndpoint:
    """Tests for GET /status endpoint."""
    
    def test_status_endpoint(self):
        """Test /status endpoint returns prototype information."""
        response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "prototype_name" in data
        assert "version" in data
        assert "enabled_providers" in data
        assert "provider_count" in data
        assert isinstance(data["enabled_providers"], list)
