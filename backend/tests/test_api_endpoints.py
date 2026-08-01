"""
Test suite for backend API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestHealthEndpoint:
    """Test /health endpoint"""
    
    def test_health_check_success(self, client):
        """Test that health endpoint returns 200"""
        response = client.get("/health")
        assert response.status_code == 200
    
    def test_health_check_response_structure(self, client):
        """Test health endpoint response structure"""
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data
    
    def test_health_check_timestamp_format(self, client):
        """Test health endpoint returns valid timestamp"""
        response = client.get("/health")
        data = response.json()
        # Should be ISO format
        assert "T" in data["timestamp"]  # ISO 8601 includes T


class TestStatusEndpoint:
    """Test /status endpoint"""
    
    def test_status_endpoint_success(self, client):
        """Test that status endpoint returns 200"""
        response = client.get("/status")
        assert response.status_code == 200
    
    def test_status_response_structure(self, client):
        """Test status endpoint response structure"""
        response = client.get("/status")
        data = response.json()
        assert "prototype_name" in data
        assert "version" in data
        assert "timestamp" in data
        assert "enabled_providers" in data
        assert "provider_count" in data
        assert "debug_mode" in data
    
    def test_status_enabled_providers_is_list(self, client):
        """Test that enabled_providers is a list"""
        response = client.get("/status")
        data = response.json()
        assert isinstance(data["enabled_providers"], list)
    
    def test_status_provider_count_matches_list(self, client):
        """Test that provider count matches enabled providers list"""
        response = client.get("/status")
        data = response.json()
        assert data["provider_count"] == len(data["enabled_providers"])


class TestAnalyzeEndpointValidation:
    """Test /analyze endpoint validation"""
    
    def test_analyze_missing_polygon(self, client):
        """Test analyze with missing polygon field"""
        response = client.post("/analyze", json={})
        assert response.status_code in [422, 400]
    
    def test_analyze_empty_request(self, client):
        """Test analyze with empty request"""
        response = client.post("/analyze", json=None)
        assert response.status_code in [422, 400, 500]
    
    def test_analyze_with_invalid_polygon_type(self, client):
        """Test analyze with invalid polygon type"""
        response = client.post("/analyze", json={
            "polygon": {
                "type": "Point",
                "coordinates": [0, 0]
            }
        })
        assert response.status_code in [400, 422]


class TestAnalyzeEndpointStructure:
    """Test analyze endpoint response structure"""
    
    @pytest.fixture
    def valid_polygon_request(self):
        """Valid polygon for testing"""
        return {
            "polygon": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            }
        }
    
    def test_analyze_response_has_required_fields(self, client, valid_polygon_request):
        """Test that response has required fields"""
        response = client.post("/analyze", json=valid_polygon_request)
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "request_id", "status", "timestamp", 
            "processing_time_ms", "analysis_summary"
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
    
    def test_analyze_response_status_valid(self, client, valid_polygon_request):
        """Test that response status is valid"""
        response = client.post("/analyze", json=valid_polygon_request)
        assert response.status_code == 200
        data = response.json()
        valid_statuses = ["success", "failed", "partial", "skipped", "pending"]
        assert data["status"] in valid_statuses
    
    def test_analyze_response_processing_time_positive(self, client, valid_polygon_request):
        """Test that processing time is positive"""
        response = client.post("/analyze", json=valid_polygon_request)
        assert response.status_code == 200
        data = response.json()
        assert data["processing_time_ms"] > 0
    
    def test_analyze_response_request_id_present(self, client, valid_polygon_request):
        """Test that response has request_id"""
        response = client.post("/analyze", json=valid_polygon_request)
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] is not None
        assert len(data["request_id"]) > 0
    
    def test_analyze_analysis_summary_has_area(self, client, valid_polygon_request):
        """Test that analysis summary includes polygon area"""
        response = client.post("/analyze", json=valid_polygon_request)
        assert response.status_code == 200
        data = response.json()
        summary = data.get("analysis_summary", {})
        assert "polygon_area_sqkm" in summary
        assert summary["polygon_area_sqkm"] > 0


class TestAnalyzeEndpointProcessingStatus:
    """Test processing status in analyze response"""
    
    @pytest.fixture
    def valid_polygon_request(self):
        return {
            "polygon": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            }
        }
    
    def test_processing_status_structure(self, client, valid_polygon_request):
        """Test processing status has correct structure"""
        response = client.post("/analyze", json=valid_polygon_request)
        assert response.status_code == 200
        data = response.json()
        
        processing_status = data.get("processing_status")
        assert processing_status is not None
        
        # Should have status for each module
        expected_modules = [
            "validation", "data_collection", "data_validation",
            "standardization", "rule_engine", "output_generation"
        ]
        
        for module in expected_modules:
            # Can be dict or list
            if isinstance(processing_status, dict):
                assert module in processing_status
            elif isinstance(processing_status, list):
                module_names = [item.get("module_name") for item in processing_status]
                assert module in module_names
    
    def test_provider_status_present(self, client, valid_polygon_request):
        """Test that provider status is included"""
        response = client.post("/analyze", json=valid_polygon_request)
        assert response.status_code == 200
        data = response.json()
        
        assert "provider_status" in data
        # Can be dict, list, or empty
        assert data["provider_status"] is not None
