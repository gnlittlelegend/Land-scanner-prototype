"""
Integration tests for complete analysis pipeline
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestAnalysisPipeline:
    """Test complete analysis pipeline"""
    
    @pytest.fixture
    def simple_polygon(self):
        """Simple polygon for testing"""
        return {
            "polygon": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            }
        }
    
    @pytest.fixture
    def northern_polygon(self):
        """Polygon in northern hemisphere"""
        return {
            "polygon": {
                "type": "Polygon",
                "coordinates": [[[-10, 40], [10, 40], [10, 50], [-10, 50], [-10, 40]]]
            }
        }
    
    @pytest.fixture
    def southern_polygon(self):
        """Polygon in southern hemisphere"""
        return {
            "polygon": {
                "type": "Polygon",
                "coordinates": [[[100, -30], [120, -30], [120, -20], [100, -20], [100, -30]]]
            }
        }
    
    def test_simple_polygon_analysis_completes(self, client, simple_polygon):
        """Test that simple polygon analysis completes"""
        response = client.post("/analyze", json=simple_polygon)
        assert response.status_code == 200
        assert response.json()["status"] is not None
    
    def test_analysis_returns_errors_list(self, client, simple_polygon):
        """Test that analysis includes errors list"""
        response = client.post("/analyze", json=simple_polygon)
        assert response.status_code == 200
        data = response.json()
        assert "errors" in data
        assert isinstance(data["errors"], list)
    
    def test_analysis_land_information_structure(self, client, simple_polygon):
        """Test land_information structure in response"""
        response = client.post("/analyze", json=simple_polygon)
        assert response.status_code == 200
        data = response.json()
        
        assert "land_information" in data
        # Can be dict or other structure
        assert data["land_information"] is not None
    
    def test_multiple_analyses_same_polygon(self, client, simple_polygon):
        """Test multiple analyses with same polygon"""
        response1 = client.post("/analyze", json=simple_polygon)
        response2 = client.post("/analyze", json=simple_polygon)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Should have different request IDs
        data1 = response1.json()
        data2 = response2.json()
        assert data1["request_id"] != data2["request_id"]
    
    def test_different_polygons_different_areas(self, client):
        """Test that different polygons have different areas"""
        small_polygon = {
            "polygon": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
            }
        }
        
        large_polygon = {
            "polygon": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]
            }
        }
        
        resp_small = client.post("/analyze", json=small_polygon)
        resp_large = client.post("/analyze", json=large_polygon)
        
        assert resp_small.status_code == 200
        assert resp_large.status_code == 200
        
        data_small = resp_small.json()
        data_large = resp_large.json()
        
        area_small = data_small["analysis_summary"]["polygon_area_sqkm"]
        area_large = data_large["analysis_summary"]["polygon_area_sqkm"]
        
        assert area_large > area_small
    
    def test_analysis_includes_timestamp(self, client, simple_polygon):
        """Test that analysis includes timestamp"""
        response = client.post("/analyze", json=simple_polygon)
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        assert "T" in data["timestamp"]  # ISO format
