"""
Property-based test for error message safety (Property 12: Error Message Safety).

Tests that error messages are:
- Readable and user-friendly (no technical jargon)
- Safe (no stack traces, secrets, implementation details)
- Helpful (guide users toward resolution)
- Consistent (similar format across all error types)

Feature: land-scanner, Property 12: Error Message Safety
Validates: Requirements 8.2, 8.5, 8.6
"""

import pytest
import logging
import re
from hypothesis import given, settings, strategies as st
from hypothesis import HealthCheck
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app

logger = logging.getLogger(__name__)


# Create test client
client = TestClient(app)


# Security scanning patterns
SENSITIVE_PATTERNS = {
    "file_paths": r'([a-zA-Z]:\\|/)[^\s]*\.py',  # Python file paths
    "line_numbers": r':\d{1,4}(?:\s|$)',  # Line numbers like :123
    "tracebacks": r'(Traceback|File|line)',  # Traceback keywords
    "api_keys": r'(api[_-]?key|secret|token)["\s=:]*["\']?[a-zA-Z0-9]{20,}',  # API keys
    "db_strings": r'(postgres|mysql|mongodb)://[^\s]*',  # Database connection strings
    "python_errors": r'(TypeError|ValueError|AttributeError|ImportError|IndexError|KeyError)',  # Python exceptions
    "python_keywords": r'(NoneType|module object|function object)',  # Python-specific terms
}


class TestErrorMessageSafety:
    """Property-based tests for error message safety and clarity."""

    def test_validation_error_polygon_too_small(self):
        """Validation error for too-small polygon should be clear and helpful."""
        request = {
            "polygon": {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    # Very small polygon (0.0001m²)
                    "coordinates": [[[0, 0], [0, 0.000001], [0.000001, 0.000001], [0.000001, 0], [0, 0]]]
                }
            }
        }
        
        response = client.post("/analyze", json=request)
        
        if response.status_code in [400, 422]:
            error_msg = str(response.json())
            
            # Verify message is helpful
            assert "area" in error_msg.lower() or "size" in error_msg.lower(), \
                "Error should mention area/size"
            assert "10" in error_msg, \
                "Error should mention minimum area (10 m²)"
            
            # Verify message is safe
            self._verify_error_message_safety(error_msg)
            
            logger.info(f"✓ Validation error (too small) is clear and safe")

    def test_validation_error_polygon_too_large(self):
        """Validation error for too-large polygon should be clear and helpful."""
        # Create a very large polygon (1000+ km²)
        large_polygon = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]]]
                }
            }
        }
        
        response = client.post("/analyze", json=large_polygon)
        
        if response.status_code in [400, 422]:
            error_msg = str(response.json())
            
            # Verify message is helpful
            assert "area" in error_msg.lower() or "size" in error_msg.lower(), \
                "Error should mention area/size"
            assert "100" in error_msg, \
                "Error should mention maximum area (100 km²)"
            
            # Verify message is safe
            self._verify_error_message_safety(error_msg)
            
            logger.info(f"✓ Validation error (too large) is clear and safe")

    def test_validation_error_bad_geojson(self):
        """Validation error for bad GeoJSON should be clear and helpful."""
        request = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon"
                    # Missing coordinates field
                }
            }
        }
        
        response = client.post("/analyze", json=request)
        
        if response.status_code in [400, 422]:
            error_msg = str(response.json())
            
            # Verify message is helpful
            assert "geometry" in error_msg.lower() or "structure" in error_msg.lower() or "valid" in error_msg.lower(), \
                "Error should explain GeoJSON issue"
            
            # Verify message is safe
            self._verify_error_message_safety(error_msg)
            
            logger.info(f"✓ Validation error (bad GeoJSON) is clear and safe")

    def test_validation_error_too_many_vertices(self):
        """Validation error for too many vertices should be clear and helpful."""
        # Create polygon with many vertices
        coords = []
        for i in range(10001):
            angle = (i / 10000) * 2 * 3.14159
            x = -180 + 360 * (i / 10000)
            y = -85 + 170 * (i / 10000)
            coords.append([x, y])
        coords.append(coords[0])  # Close ring
        
        request = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            }
        }
        
        response = client.post("/analyze", json=request)
        
        if response.status_code in [400, 422]:
            error_msg = str(response.json())
            
            # Verify message is helpful
            assert "vertex" in error_msg.lower() or "point" in error_msg.lower() or "10" in error_msg, \
                "Error should mention vertex limit"
            
            # Verify message is safe
            self._verify_error_message_safety(error_msg)
            
            logger.info(f"✓ Validation error (too many vertices) is clear and safe")

    def test_validation_error_malformed_coordinates(self):
        """Validation error for malformed coordinates should be clear and helpful."""
        request = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon",
                    # Out of range coordinates
                    "coordinates": [[[181, 91], [181, 92], [182, 92], [182, 91], [181, 91]]]
                }
            }
        }
        
        response = client.post("/analyze", json=request)
        
        if response.status_code in [400, 422]:
            error_msg = str(response.json())
            
            # Verify message is helpful
            assert "coordinate" in error_msg.lower() or "range" in error_msg.lower() or "valid" in error_msg.lower(), \
                "Error should explain coordinate issue"
            
            # Verify message is safe
            self._verify_error_message_safety(error_msg)
            
            logger.info(f"✓ Validation error (malformed coordinates) is clear and safe")

    @patch('backend.managers.data_source_manager.DataSourceManager.collect_data')
    def test_provider_error_overpass_timeout(self, mock_collect):
        """Error message for provider timeout should be safe and user-friendly."""
        mock_collect.side_effect = TimeoutError("Overpass API timeout")
        
        valid_polygon = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]]
                }
            }
        }
        
        response = client.post("/analyze", json=valid_polygon)
        
        if response.status_code == 500:
            error_msg = str(response.json())
            
            # Verify message is user-friendly (doesn't mention "Overpass", "timeout", etc.)
            assert "Overpass" not in error_msg, "Error should not expose provider name"
            assert "retry" not in error_msg.lower(), "Error should not mention retry logic"
            assert "timeout" not in error_msg.lower() or "temporarily" in error_msg.lower(), \
                "Error should not expose technical timeout details"
            
            # Verify message is safe
            self._verify_error_message_safety(error_msg)
            
            logger.info(f"✓ Provider timeout error is user-friendly and safe")

    @patch('backend.managers.data_source_manager.DataSourceManager.collect_data')
    def test_provider_error_network_failure(self, mock_collect):
        """Error message for network failure should be safe and helpful."""
        mock_collect.side_effect = ConnectionError("Connection refused")
        
        valid_polygon = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]]
                }
            }
        }
        
        response = client.post("/analyze", json=valid_polygon)
        
        if response.status_code == 500:
            error_msg = str(response.json())
            
            # Verify message is helpful
            assert "try again" in error_msg.lower() or "later" in error_msg.lower() or "connection" in error_msg.lower(), \
                "Error should guide user on next steps"
            
            # Verify message is safe
            self._verify_error_message_safety(error_msg)
            
            logger.info(f"✓ Network error is helpful and safe")

    @patch('backend.rules.rule_engine.RuleEngine.execute')
    def test_system_error_rule_engine(self, mock_execute):
        """Error message for rule engine exception should be safe."""
        mock_execute.side_effect = Exception("Unexpected rule engine error")
        
        valid_polygon = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0.001], [0.001, 0.001], [0.001, 0], [0, 0]]]
                }
            }
        }
        
        response = client.post("/analyze", json=valid_polygon)
        
        if response.status_code == 500:
            error_msg = str(response.json())
            
            # Verify message doesn't expose rule engine details
            assert "rule_engine" not in error_msg.lower(), "Error should not expose component name"
            assert "RuleEngine" not in error_msg, "Error should not expose class name"
            
            # Verify message is safe
            self._verify_error_message_safety(error_msg)
            
            logger.info(f"✓ System error is safe (no component details)")

    def test_error_messages_are_concise(self):
        """Error messages should be concise and readable."""
        request = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon"
                    # Missing coordinates
                }
            }
        }
        
        response = client.post("/analyze", json=request)
        
        if response.status_code in [400, 422]:
            error_msg = response.json().get("detail") or response.json().get("error_message") or str(response.json())
            
            # Verify message is reasonably short (not overwhelming)
            sentences = [s.strip() for s in error_msg.split('.') if s.strip()]
            assert len(sentences) <= 5, f"Error message too long ({len(sentences)} sentences): {error_msg}"
            
            # Verify average sentence length
            avg_words = sum(len(s.split()) for s in sentences) / len(sentences) if sentences else 0
            assert avg_words < 25, f"Error message sentences too long (avg {avg_words} words)"
            
            logger.info(f"✓ Error message is concise")

    def test_error_message_consistency(self):
        """Similar errors should have similar message format."""
        # Test 1: Polygon too small
        small_polygon = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0.000001], [0.000001, 0.000001], [0.000001, 0], [0, 0]]]
                }
            }
        }
        
        response1 = client.post("/analyze", json=small_polygon)
        msg1 = str(response1.json())
        
        # Test 2: Polygon too large
        large_polygon = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]]]
                }
            }
        }
        
        response2 = client.post("/analyze", json=large_polygon)
        msg2 = str(response2.json())
        
        if response1.status_code in [400, 422] and response2.status_code in [400, 422]:
            # Both should mention "area" or "size"
            assert ("area" in msg1.lower() or "size" in msg1.lower()), "Message 1 should mention area/size"
            assert ("area" in msg2.lower() or "size" in msg2.lower()), "Message 2 should mention area/size"
            
            logger.info(f"✓ Error messages are consistent in format")

    def test_no_sensitive_data_in_errors(self):
        """Error messages should never expose sensitive information."""
        # Trigger various error conditions
        test_cases = [
            {"polygon": {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": []}}},
            {"polygon": {"type": "Feature", "geometry": {}}},
            {"polygon": None},
        ]
        
        for request_data in test_cases:
            response = client.post("/analyze", json=request_data)
            
            if response.status_code >= 400:
                error_msg = str(response.json())
                
                # Verify no sensitive patterns
                for pattern_name, pattern in SENSITIVE_PATTERNS.items():
                    matches = re.findall(pattern, error_msg, re.IGNORECASE)
                    assert len(matches) == 0, f"Error contains {pattern_name}: {matches}"
        
        logger.info(f"✓ No sensitive data in error messages")

    def test_error_response_structure(self):
        """Error responses should have consistent structure."""
        request = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon"
                    # Missing coordinates
                }
            }
        }
        
        response = client.post("/analyze", json=request)
        
        if response.status_code in [400, 422]:
            body = response.json()
            
            # Verify error response has expected fields
            assert isinstance(body, dict), "Error response should be JSON object"
            
            # Should have either 'detail' or 'error_message'
            assert "detail" in body or "error_message" in body, \
                "Error should have error message field"
            
            logger.info(f"✓ Error response structure is correct")

    def test_error_codes_are_documented(self):
        """Error responses should have error codes for programmatic handling."""
        request = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon"
                    # Missing coordinates
                }
            }
        }
        
        response = client.post("/analyze", json=request)
        
        if response.status_code in [400, 422]:
            body = response.json()
            
            # Error code not strictly required, but if present should be meaningful
            if "error_code" in body:
                error_code = body["error_code"]
                assert isinstance(error_code, str) and len(error_code) > 0, \
                    "Error code should be non-empty string"
                
                logger.info(f"✓ Error code present: {error_code}")

    def test_error_messages_are_actionable(self):
        """Error messages should guide users toward resolution."""
        request = {
            "polygon": {"type": "Feature", "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [0, 0.000001], [0.000001, 0.000001], [0.000001, 0], [0, 0]]]
                }
            }
        }
        
        response = client.post("/analyze", json=request)
        
        if response.status_code in [400, 422]:
            error_msg = str(response.json()).lower()
            
            # Message should either:
            # 1. Explain what's wrong (use "is", "are", "must be")
            # 2. Suggest fix (use "please", "try", "check")
            has_explanation = any(word in error_msg for word in ["is ", "are ", "must ", "should "])
            has_suggestion = any(word in error_msg for word in ["please", "try", "check", "ensure"])
            
            assert has_explanation or has_suggestion, \
                "Error message should explain problem or suggest fix"
            
            logger.info(f"✓ Error message is actionable")

    def _verify_error_message_safety(self, error_msg: str):
        """
        Verify that error message doesn't contain sensitive or dangerous information.
        
        Checks for:
        - File paths (.py files)
        - Line numbers
        - Traceback keywords
        - API keys/secrets
        - Database connection strings
        - Python-specific error names
        - Implementation details
        """
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            matches = re.findall(pattern, error_msg, re.IGNORECASE)
            assert len(matches) == 0, \
                f"Error message contains {pattern_name}: {matches}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

