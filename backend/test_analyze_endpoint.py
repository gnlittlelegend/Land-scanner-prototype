"""Tests for the /analyze endpoint with polygon validation"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


class TestAnalyzeEndpoint:
    """Test the POST /analyze endpoint"""
    
    def test_valid_polygon_analysis(self, client):
        """Test analysis with a valid polygon"""
        payload = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [0.01, 0],
                        [0.01, 0.01],
                        [0, 0.01],
                        [0, 0]
                    ]]
                }
            }
        }
        
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "request_id" in data
        assert "status" in data
        assert "timestamp" in data
        assert "processing_time_ms" in data
        assert "processing_status" in data
        assert "land_information" in data
        
        # Verify status
        assert data["status"] in ["success", "partial", "error"]
        
        # Verify processing status
        assert "validation" in data["processing_status"]
    
    def test_missing_polygon_field(self, client):
        """Test that missing polygon field returns error"""
        payload = {}
        
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 422
    
    def test_invalid_polygon_too_small(self, client):
        """Test that polygon below minimum area is rejected"""
        # Very tiny polygon < 10 m²
        payload = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [0.00001, 0],
                        [0.00001, 0.00001],
                        [0, 0.00001],
                        [0, 0]
                    ]]
                }
            }
        }
        
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 400
        assert "error" in response.json() or "detail" in response.json()
    
    def test_invalid_polygon_too_large(self, client):
        """Test that polygon above maximum area is rejected"""
        # Very large polygon > 100 km²
        payload = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [1.5, 0],
                        [1.5, 1.5],
                        [0, 1.5],
                        [0, 0]
                    ]]
                }
            }
        }
        
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 400
    
    def test_invalid_geometry_type(self, client):
        """Test that Point geometry is rejected"""
        payload = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [0, 0]
                }
            }
        }
        
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 400
    
    def test_unclosed_ring(self, client):
        """Test that unclosed ring is rejected"""
        payload = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [0.01, 0],
                        [0.01, 0.01],
                        [0, 0.01]
                        # Missing [0, 0] to close
                    ]]
                }
            }
        }
        
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 400
    
    def test_invalid_coordinates(self, client):
        """Test that out-of-bounds coordinates are rejected"""
        payload = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 91],  # Latitude > 90
                        [1, 91],
                        [1, 92],
                        [0, 92],
                        [0, 91]
                    ]]
                }
            }
        }
        
        response = client.post("/analyze", json=payload)
        
        assert response.status_code == 400


class TestHealthEndpoints:
    """Test the health and status endpoints"""
    
    def test_health_check(self, client):
        """Test /health endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data
        assert "timestamp" in data
    
    def test_status_endpoint(self, client):
        """Test /status endpoint"""
        response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "app_name" in data
        assert "version" in data
        assert "environment" in data
        assert "timestamp" in data
        assert "enabled_providers" in data
        assert "total_providers" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
