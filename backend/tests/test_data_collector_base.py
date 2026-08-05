"""
Tests for DataCollector abstract base class.

Verifies that the base collector provides correct HTTP handling,
retry logic, and error handling for all concrete collectors.

Requirements from Task 3.1:
- Abstract collector interface: collect(polygon) -> RawDataset
- RawDataset model with required fields
- HTTP request handling with timeout management
- Exponential backoff retry logic
- Generic error handling for provider failures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import time
import requests

from backend.collectors.base_collector import (
    DataCollector,
    CollectionError,
    TimeoutError as CollectorTimeoutError,
    RateLimitError
)


class MockCollector(DataCollector):
    """Concrete implementation for testing."""
    
    def collect(self, polygon):
        """Implement abstract method for testing."""
        return self._build_raw_dataset(
            category="test",
            features=[],
            status="success"
        )


class TestDataCollectorInitialization:
    """Test DataCollector initialization."""
    
    def test_initialization_with_defaults(self):
        """Collectors should initialize with default values."""
        collector = MockCollector(
            provider_name="Test Provider",
            endpoint="https://api.example.com"
        )
        
        assert collector.provider_name == "Test Provider"
        assert collector.endpoint == "https://api.example.com"
        assert collector.timeout == 30
        assert collector.max_retries == 2
        assert collector.retry_delay_base == 2.0
    
    def test_initialization_with_custom_values(self):
        """Collectors should accept custom timeout and retry values."""
        collector = MockCollector(
            provider_name="Custom Provider",
            endpoint="https://api.custom.com",
            timeout=60,
            max_retries=5,
            retry_delay_base=3.0
        )
        
        assert collector.timeout == 60
        assert collector.max_retries == 5
        assert collector.retry_delay_base == 3.0
    
    def test_session_created(self):
        """Collectors should create HTTP session."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com"
        )
        
        assert collector.session is not None
        assert isinstance(collector.session, requests.Session)


class TestHTTPRequestHandling:
    """Test _make_request method."""
    
    def test_successful_request(self):
        """Successful requests should return response."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com"
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"test data"
            mock_request.return_value = mock_response
            
            result = collector._make_request("GET", "https://api.example.com/data")
            
            assert result == mock_response
            mock_request.assert_called_once()
    
    def test_rate_limit_retry(self):
        """Rate limit (429) should retry with backoff."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com",
            max_retries=2,
            retry_delay_base=0.1  # Use small delay for testing
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            # First attempt: rate limited, second attempt: success
            mock_response_429 = Mock()
            mock_response_429.status_code = 429
            
            mock_response_200 = Mock()
            mock_response_200.status_code = 200
            mock_response_200.content = b"success"
            
            mock_request.side_effect = [mock_response_429, mock_response_200]
            
            with patch('time.sleep') as mock_sleep:
                result = collector._make_request("GET", "https://api.example.com/data")
            
            # Should succeed after retry
            assert result == mock_response_200
            # Should have called sleep for backoff
            mock_sleep.assert_called()
    
    def test_timeout_retry(self):
        """Timeout should retry with backoff."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com",
            max_retries=2,
            retry_delay_base=0.1
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            # First attempt: timeout, second attempt: success
            mock_response_200 = Mock()
            mock_response_200.status_code = 200
            mock_response_200.content = b"success"
            
            mock_request.side_effect = [
                requests.Timeout("Connection timed out"),
                mock_response_200
            ]
            
            with patch('time.sleep'):
                result = collector._make_request("GET", "https://api.example.com/data")
            
            assert result == mock_response_200
    
    def test_connection_error_retry(self):
        """Connection errors should retry with backoff."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com",
            max_retries=2,
            retry_delay_base=0.1
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.content = b"success"
            
            mock_request.side_effect = [
                requests.ConnectionError("Connection refused"),
                mock_response
            ]
            
            with patch('time.sleep'):
                result = collector._make_request("GET", "https://api.example.com/data")
            
            assert result == mock_response
    
    def test_server_error_retry(self):
        """Server errors (5xx) should retry with backoff."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com",
            max_retries=2,
            retry_delay_base=0.1
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            mock_response_500 = Mock()
            mock_response_500.status_code = 500
            
            mock_response_200 = Mock()
            mock_response_200.status_code = 200
            mock_response_200.content = b"success"
            
            mock_request.side_effect = [mock_response_500, mock_response_200]
            
            with patch('time.sleep'):
                result = collector._make_request("GET", "https://api.example.com/data")
            
            assert result == mock_response_200
    
    def test_exponential_backoff_delays(self):
        """Retry delays should follow exponential backoff pattern."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com",
            max_retries=2,
            retry_delay_base=2.0
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            mock_request.side_effect = requests.Timeout()
            
            with patch('time.sleep') as mock_sleep:
                result = collector._make_request("GET", "https://api.example.com/data")
            
            # Should have called sleep with exponential delays
            # First retry: 2 * (2^0) = 2
            # Second retry: 2 * (2^1) = 4
            calls = mock_sleep.call_args_list
            assert len(calls) == 2
            assert calls[0][0][0] == 2.0
            assert calls[1][0][0] == 4.0


class TestRawDatasetBuilding:
    """Test _build_raw_dataset method."""
    
    def test_build_raw_dataset_structure(self):
        """Built datasets should have correct structure."""
        collector = MockCollector(
            provider_name="Test Provider",
            endpoint="https://api.example.com"
        )
        
        features = [
            {"id": "1", "type": "Feature", "geometry": {}, "properties": {}}
        ]
        
        dataset = collector._build_raw_dataset(
            category="buildings",
            features=features,
            attempt_count=1,
            collection_time_ms=100.5,
            status="success"
        )
        
        assert dataset["source_provider"] == "Test Provider"
        assert dataset["category"] == "buildings"
        assert len(dataset["features"]) == 1
        assert dataset["metadata"]["feature_count"] == 1
        assert dataset["metadata"]["status"] == "success"
        assert dataset["metadata"]["attempt_count"] == 1
        assert dataset["metadata"]["collection_time_ms"] == 100.5
        assert dataset["metadata"]["provider_endpoint"] == "https://api.example.com"
        assert dataset["metadata"]["timeout_seconds"] == 30
    
    def test_empty_dataset(self):
        """Should handle empty feature lists."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com"
        )
        
        dataset = collector._build_raw_dataset(
            category="roads",
            features=[],
            status="empty"
        )
        
        assert dataset["metadata"]["feature_count"] == 0
        assert dataset["metadata"]["status"] == "empty"
    
    def test_error_status_with_message(self):
        """Should include error message in metadata."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com"
        )
        
        dataset = collector._build_raw_dataset(
            category="elevation",
            features=[],
            status="error",
            error_message="Provider unavailable"
        )
        
        assert dataset["metadata"]["status"] == "error"
        assert dataset["metadata"]["error_message"] == "Provider unavailable"


class TestGetBoundingBox:
    """Test _get_bbox method."""
    
    def test_extract_bbox_from_polygon(self):
        """Should extract bounding box from polygon."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com"
        )
        
        polygon = {
            "properties": {
                "bounding_box": {
                    "min_lon": -74.0,
                    "min_lat": 40.0,
                    "max_lon": -73.0,
                    "max_lat": 41.0
                }
            }
        }
        
        bbox = collector._get_bbox(polygon)
        
        assert bbox == (-74.0, 40.0, -73.0, 41.0)


class TestCollectorInterface:
    """Test abstract interface requirements."""
    
    def test_collect_is_abstract(self):
        """collect() should be abstract."""
        with pytest.raises(TypeError):
            DataCollector(
                provider_name="Test",
                endpoint="https://api.example.com"
            )
    
    def test_concrete_implementation(self):
        """Concrete implementations should be instantiable."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com"
        )
        
        assert isinstance(collector, DataCollector)


class TestMaxRetriesExhausted:
    """Test behavior when max retries exceeded."""
    
    def test_max_retries_exhausted_timeout(self):
        """Should return None when max retries exhausted (timeout)."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com",
            max_retries=2
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            mock_request.side_effect = requests.Timeout()
            
            with patch('time.sleep'):
                result = collector._make_request("GET", "https://api.example.com/data")
            
            assert result is None
    
    def test_max_retries_exhausted_429(self):
        """Should return None when max retries exhausted (rate limit)."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com",
            max_retries=2
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 429
            mock_request.return_value = mock_response
            
            with patch('time.sleep'):
                result = collector._make_request("GET", "https://api.example.com/data")
            
            assert result is None


class TestClientErrors:
    """Test handling of client errors (4xx)."""
    
    def test_404_not_retried(self):
        """404 errors should not be retried."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com",
            max_retries=2
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Not found"
            mock_request.return_value = mock_response
            
            result = collector._make_request("GET", "https://api.example.com/data")
            
            # Should only be called once (no retry for 4xx)
            assert mock_request.call_count == 1
            assert result is None
    
    def test_400_not_retried(self):
        """400 errors should not be retried."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com"
        )
        
        with patch.object(collector.session, 'request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            mock_request.return_value = mock_response
            
            result = collector._make_request("GET", "https://api.example.com/data")
            
            assert mock_request.call_count == 1
            assert result is None


class TestSession:
    """Test session management."""
    
    def test_close_session(self):
        """Should close session."""
        collector = MockCollector(
            provider_name="Test",
            endpoint="https://api.example.com"
        )
        
        with patch.object(collector.session, 'close') as mock_close:
            collector.close()
            mock_close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
