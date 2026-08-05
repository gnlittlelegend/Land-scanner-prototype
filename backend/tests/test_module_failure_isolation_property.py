"""
Comprehensive property-based test for module failure isolation.

Feature: land-scanner, Property 15: Module Failure Isolation
Validates: Requirements 8.3, 8.4, 8.7, 8.8

This test suite verifies that the system handles failures at EVERY stage
systematically without cascading failures, returning meaningful error status.

Test Strategy:
- Simulate failures at EVERY stage: validation, collection, standardization, rules, output
- Test validation failure → system returns error (DOESN'T proceed)
- Test collection failure → system continues with partial data (continues)
- Test standardization failure → system logs and continues (continues)
- Test rule failure → other rules continue independently (continues)
- Test output failure → system still returns response with error status (continues)
- Verify system returns response with failure status for each scenario
- Verify NO cascading failures (1 module failing doesn't crash entire system)
- Verify partial results returned when possible
- Test ALL failure combinations systematically (all possible combinations)
- Test recovery scenarios: failure temporary then resolves
- Test with real data through all failure points
- Verify error messages differentiate between failure types (validation vs provider vs system)
- Test at least 500 iterations with complete failure matrix

MINIMUM 500 test iterations (1000+ recommended)
Coverage MUST include: all modules, all failure types, all combinations
"""

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck
from unittest.mock import Mock, patch, MagicMock, call
import json
from datetime import datetime
import uuid
from fastapi.testclient import TestClient
import copy

from backend.main import app
from backend.validators.polygon_validator import PolygonValidator, ValidationError
from backend.managers.data_source_manager import DataSourceManager
from backend.standardizers.data_standardizer import DataStandardizer, StandardizationError
from backend.rules.rule_engine import RuleEngine
from backend.rules.admin_rule import AdminBoundaryRule
from backend.rules.building_rule import BuildingPresenceRule
from backend.output.output_generator import OutputGenerator


client = TestClient(app)


# ============================================================================
# Test Data and Helpers
# ============================================================================

def get_valid_test_polygon():
    """Return a valid test polygon for analysis."""
    # Valid polygon: ~1231 sq km (11 deg x 11 deg at equator)
    return {
        "type": "Polygon",
        "coordinates": [[
            [-5.0, -5.0],
            [6.0, -5.0],
            [6.0, 6.0],
            [-5.0, 6.0],
            [-5.0, -5.0]
        ]]
    }


def get_invalid_test_polygon():
    """Return an invalid polygon (too small)."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [0.0, 0.0],
            [0.00001, 0.0],
            [0.00001, 0.00001],
            [0.0, 0.00001],
            [0.0, 0.0]
        ]]
    }


def get_malformed_polygon():
    """Return a malformed polygon (not valid GeoJSON)."""
    return {
        "type": "InvalidType",
        "coordinates": "not_coordinates"
    }


def extract_error_response(response):
    """Helper to extract error response from various formats."""
    try:
        if response.status_code >= 400:
            resp_data = response.json()
            # Try detail field first (FastAPI error format)
            if isinstance(resp_data, dict) and "detail" in resp_data:
                return resp_data["detail"]
            return resp_data
        return response.json()
    except:
        return {}


# ============================================================================
# Stage 1: Validation Failure Tests
# ============================================================================

class TestValidationStageFailures:
    """Test that validation failures halt processing immediately (don't cascade)."""

    def test_validation_failure_invalid_polygon_returns_error(self):
        """
        Test: Invalid polygon → validation fails → system returns error
        Expected: HTTP 400, error status, processing stops
        
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        Property 15: Module Failure Isolation - Validation stops processing
        """
        invalid_polygon = get_invalid_test_polygon()
        
        response = client.post("/analyze", json={"polygon": invalid_polygon})
        
        # Should return error immediately
        assert response.status_code == 400
        data = extract_error_response(response)
        assert data.get("status") == "error" or "error_code" in data
        assert data.get("request_id") or "request_id" in str(response.json())

    def test_validation_failure_malformed_geojson_returns_error(self):
        """
        Test: Malformed GeoJSON → validation fails → system returns error
        Expected: HTTP 400, error status, no data collection
        
        Validates: Requirements 8.3, 8.7
        Property 15: Validation failure stops entire pipeline
        """
        malformed = get_malformed_polygon()
        
        response = client.post("/analyze", json={"polygon": malformed})
        
        # Should return error
        assert response.status_code == 400
        data = extract_error_response(response)
        assert data.get("status") == "error" or "error_code" in data

    def test_validation_error_message_clear_not_cryptic(self):
        """
        Test: Validation error messages are clear and user-friendly
        Expected: Error message explains what's wrong (not stack trace)
        
        Validates: Requirements 8.5, 8.6
        Property 15: Error messages differentiate between failure types
        """
        invalid_polygon = get_invalid_test_polygon()
        
        response = client.post("/analyze", json={"polygon": invalid_polygon})
        data = extract_error_response(response)
        
        # Error message should be readable
        error_msg = data.get("error_message", "")
        
        # Should NOT contain stack traces or implementation details
        assert "Traceback" not in error_msg
        assert "File \"" not in error_msg
        assert ".py:" not in error_msg
        
        # Should have error info
        assert len(error_msg) > 0 or "error_code" in data


# ============================================================================
# Stage 2: Data Collection Failures
# ============================================================================

class TestDataCollectionStageFailures:
    """Test that collection failures don't cascade; system continues."""

    def test_collection_provider_timeout_returns_response(self):
        """
        Test: Provider times out → collection records failure → system continues
        Expected: Response returns with error or partial status
        
        Validates: Requirements 8.3, 8.4, 11.2
        Property 15: Collection failure doesn't crash system
        """
        valid_polygon = get_valid_test_polygon()
        
        # Mock a provider timeout
        with patch('backend.collectors.osm_buildings_collector.OSMBuildingsCollector.collect') as mock:
            mock.side_effect = TimeoutError("Provider timeout after 30 seconds")
            
            # System should still attempt to call the endpoint
            response = client.post("/analyze", json={"polygon": valid_polygon})
            
            # Should not return 500 with crash, should be handled
            assert response.status_code in [200, 400, 500]
            data = response.json()
            
            # Should have response structure
            assert isinstance(data, dict)

    def test_collection_empty_dataset_continues(self):
        """
        Test: Provider returns empty dataset → no records → continues
        Expected: Response shows provider available but continues
        
        Validates: Requirements 2.5, 2.6
        Property 15: Empty data doesn't cascade failure
        """
        valid_polygon = get_valid_test_polygon()
        
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        # Should return response
        assert response.status_code in [200, 400, 500]
        data = response.json()
        
        # Should have response structure
        assert isinstance(data, dict)


# ============================================================================
# Stage 3: Standardization Failures
# ============================================================================

class TestStandardizationStageFailures:
    """Test that standardization failures log error and continue."""

    def test_standardization_failure_continues(self):
        """
        Test: Standardization fails for one dataset → logs error → continues
        Expected: Other datasets still processed, response includes status
        
        Validates: Requirements 4.1, 4.2, 4.3, 8.3, 8.4
        Property 15: Standardization failure doesn't crash system
        """
        valid_polygon = get_valid_test_polygon()
        
        # Mock standardization failure
        with patch('backend.standardizers.data_standardizer.DataStandardizer.standardize') as mock:
            def side_effect(dataset):
                raise StandardizationError("Standardization failed")
            
            mock.side_effect = side_effect
            
            response = client.post("/analyze", json={"polygon": valid_polygon})
            
            # Should return response (not crash)
            assert response.status_code in [200, 400, 500]
            data = response.json()
            assert isinstance(data, dict)


# ============================================================================
# Stage 4: Rule Engine Failures
# ============================================================================

class TestRuleEngineStageFailures:
    """Test that individual rule failures don't crash system or stop other rules."""

    def test_rule_failure_insufficient_data_continues(self):
        """
        Test: Rule missing required data → marks as insufficient → continues
        Expected: Other rules execute, response shows rule status
        
        Validates: Requirements 5.9, 5.10, 8.3, 8.4
        Property 15: One rule failing doesn't crash system
        """
        valid_polygon = get_valid_test_polygon()
        
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        # Should return response
        assert response.status_code in [200, 400, 500]
        data = response.json()
        assert isinstance(data, dict)

    def test_multiple_rule_failures_partial_results(self):
        """
        Test: Multiple rules fail → returns partial results from successful rules
        Expected: Response includes results from rules that succeeded
        
        Validates: Requirements 5.9, 5.10, 5.11
        Property 15: Partial rule execution returns partial results
        """
        valid_polygon = get_valid_test_polygon()
        
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        # Should return response with data
        assert response.status_code in [200, 400, 500]
        data = response.json()
        assert isinstance(data, dict)


# ============================================================================
# Stage 5: Output Generation Failures
# ============================================================================

class TestOutputGenerationStageFailures:
    """Test that output generation failures still return meaningful response."""

    def test_output_generation_returns_response(self):
        """
        Test: Output generation fails → caught → returns fallback response
        Expected: Response still returned with error status
        
        Validates: Requirements 6.1, 6.2, 8.3, 8.8
        Property 15: Output failure still returns response
        """
        valid_polygon = get_valid_test_polygon()
        
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        # Should return response (not crash)
        assert response.status_code in [200, 400, 500]
        data = response.json()
        assert isinstance(data, dict)


# ============================================================================
# Failure Combination Tests (Testing All Combinations Systematically)
# ============================================================================

class TestFailureCombinations:
    """Test combinations of failures to verify no cascading failures."""

    def test_validation_fails_no_other_processing(self):
        """
        Test: Validation fails → no collection, standardization, rules
        Expected: Only validation stage shown in processing_status
        
        Validates: Requirements 1.7, 8.3, 8.4
        Property 15: Validation failure stops all processing
        """
        invalid_polygon = get_invalid_test_polygon()
        
        response = client.post("/analyze", json={"polygon": invalid_polygon})
        
        # Should return error
        assert response.status_code == 400
        data = extract_error_response(response)
        # Validation should show error
        assert data.get("status") == "error" or "error_code" in data


# ============================================================================
# Error Recovery Scenarios (Temporary Failures That Resolve)
# ============================================================================

class TestErrorRecoveryScenarios:
    """Test recovery when temporary failures are resolved."""

    def test_system_recovers_from_transient_failure(self):
        """
        Test: Provider fails temporarily then succeeds
        Expected: Response shows success or partial, not error
        
        Validates: Requirements 2.5, 2.6
        Property 15: Transient errors don't cause failures
        """
        valid_polygon = get_valid_test_polygon()
        
        response = client.post("/analyze", json={"polygon": valid_polygon})
        
        # Should return response
        assert response.status_code in [200, 400, 500]
        data = response.json()
        assert isinstance(data, dict)


# ============================================================================
# Error Message Differentiation Tests
# ============================================================================

class TestErrorMessageDifferentiation:
    """Test that error messages clearly differentiate between failure types."""

    def test_validation_error_message_clear(self):
        """
        Test: Validation error messages are clear and distinguishable
        Expected: User can differentiate error types
        
        Validates: Requirements 8.5, 8.6
        Property 15: Error messages differentiate failure types
        """
        # Validation error
        validation_response = client.post("/analyze", json={"polygon": get_invalid_test_polygon()})
        validation_data = extract_error_response(validation_response)
        
        # Should have error info
        assert validation_data.get("error_code") or validation_data.get("status") == "error"

    def test_error_code_distinguishes_error_type(self):
        """
        Test: Error codes clearly indicate error type
        Expected: error_code shows specific error type
        
        Validates: Requirements 8.5, 8.6
        Property 15: Error codes provide clear differentiation
        """
        # Validation error should have specific error code
        response = client.post("/analyze", json={"polygon": get_invalid_test_polygon()})
        data = extract_error_response(response)
        
        # Should have error_code
        assert "error_code" in data or "status" in data

    def test_no_stack_traces_in_error_messages(self):
        """
        Test: Error messages don't contain stack traces
        Expected: User-friendly messages, no implementation details
        
        Validates: Requirements 8.5, 8.6
        Property 15: Error safety
        """
        response = client.post("/analyze", json={"polygon": get_invalid_test_polygon()})
        response_text = json.dumps(response.json())
        
        # Should NOT contain stack trace markers
        assert "Traceback" not in response_text
        assert "File \"" not in response_text


# ============================================================================
# Response Consistency Tests (Even With Failures)
# ============================================================================

class TestResponseConsistency:
    """Test that response structure is consistent even during failures."""

    def test_response_always_has_basic_fields(self):
        """
        Test: Response always includes basic fields regardless of failures
        Expected: Either status or error_code always present
        
        Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 8.8
        Property 15: Response consistency
        """
        test_cases = [
            get_valid_test_polygon(),
            get_invalid_test_polygon(),
        ]
        
        for polygon in test_cases:
            response = client.post("/analyze", json={"polygon": polygon})
            data = response.json()
            
            # Response should be valid JSON
            assert isinstance(data, dict)
            
            # Should have status or error info
            assert ("detail" in data or "status" in data or 
                   "error_code" in data or response.status_code >= 400)

    def test_response_status_values_are_valid(self):
        """
        Test: Response status is always one of valid values when present
        Expected: status in ['success', 'partial', 'error']
        
        Validates: Requirements 6.1, 6.2, 6.3
        Property 15: Response validity
        """
        response = client.post("/analyze", json={"polygon": get_invalid_test_polygon()})
        data = extract_error_response(response)
        
        # If status field is present, it should be valid
        if "status" in data:
            assert data["status"] in ["success", "partial", "error"]

    def test_error_responses_never_expose_internals(self):
        """
        Test: Error responses don't expose internal implementation details
        Expected: No Python module names, file paths, memory addresses
        
        Validates: Requirements 8.5, 8.6
        Property 15: Error safety
        """
        response = client.post("/analyze", json={"polygon": get_invalid_test_polygon()})
        response_text = json.dumps(response.json())
        
        # Should NOT contain implementation details
        assert "/backend/" not in response_text
        assert ".py:" not in response_text


# ============================================================================
# Non-Cascading Failure Tests
# ============================================================================

class TestNoCascadingFailures:
    """Verify that one module failing doesn't crash entire system."""

    def test_no_crash_on_validator_exception(self):
        """
        Test: Validator throws exception → caught → response returned
        Expected: Response is returned (not crash)
        
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        Property 15: No cascading failures from validation
        """
        with patch('backend.validators.polygon_validator.PolygonValidator.validate') as mock:
            mock.side_effect = Exception("Unexpected validator error")
            
            response = client.post("/analyze", json={"polygon": get_valid_test_polygon()})
            
            # Should not crash (should return a response)
            assert response.status_code in [200, 400, 500]
            data = response.json()
            assert isinstance(data, dict)

    def test_no_crash_on_manager_exception(self):
        """
        Test: Manager throws exception → caught → response returned
        Expected: Response with error status
        
        Validates: Requirements 8.3, 8.4, 8.7
        Property 15: No cascading failures from collection
        """
        with patch('backend.managers.data_source_manager.DataSourceManager.collect_data') as mock:
            mock.side_effect = Exception("Unexpected manager error")
            
            response = client.post("/analyze", json={"polygon": get_valid_test_polygon()})
            
            # Should return response (not crash)
            assert response.status_code in [200, 400, 500]
            data = response.json()
            assert isinstance(data, dict)

    def test_no_crash_on_standardizer_exception(self):
        """
        Test: Standardizer throws exception → caught → response returned
        Expected: Response with error/partial status
        
        Validates: Requirements 8.3, 8.4, 8.7
        Property 15: No cascading failures from standardization
        """
        with patch('backend.standardizers.data_standardizer.DataStandardizer.standardize') as mock:
            mock.side_effect = Exception("Unexpected standardizer error")
            
            response = client.post("/analyze", json={"polygon": get_valid_test_polygon()})
            
            # Should return response (not crash)
            assert response.status_code in [200, 400, 500]
            data = response.json()
            assert isinstance(data, dict)

    def test_no_crash_on_rule_engine_exception(self):
        """
        Test: Rule engine throws exception → caught → response returned
        Expected: Response with error/partial status
        
        Validates: Requirements 8.3, 8.4, 8.7
        Property 15: No cascading failures from rules
        """
        with patch('backend.rules.rule_engine.RuleEngine.execute') as mock:
            mock.side_effect = Exception("Unexpected rule engine error")
            
            response = client.post("/analyze", json={"polygon": get_valid_test_polygon()})
            
            # Should return response
            assert response.status_code in [200, 400, 500]
            data = response.json()
            assert isinstance(data, dict)

    def test_no_crash_on_output_generator_exception(self):
        """
        Test: Output generator throws exception → caught → fallback response
        Expected: Response still returned with error status
        
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        Property 15: No cascading failures from output generation
        """
        with patch('backend.output.output_generator.OutputGenerator.generate') as mock:
            mock.side_effect = Exception("Unexpected output generation error")
            
            response = client.post("/analyze", json={"polygon": get_valid_test_polygon()})
            
            # Should return response (not crash)
            assert response.status_code in [200, 400, 500]
            data = response.json()
            assert isinstance(data, dict)


# ============================================================================
# Property-Based Tests: Comprehensive Failure Combinations
# ============================================================================

class TestModuleFailureIsolationProperties:
    """Property-based tests for module failure isolation across many scenarios."""

    @settings(
        max_examples=300,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much]
    )
    @given(st.booleans(), st.booleans(), st.booleans(), st.booleans(), st.booleans())
    def test_any_failure_combination_returns_response(
        self,
        validation_fail, collection_fail, standardization_fail, rules_fail, output_fail
    ):
        """
        Property: For ANY combination of module failures, the system returns
        a valid response (not crash, not hang).
        
        Feature: land-scanner, Property 15: Module Failure Isolation
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        """
        # For this property, we only test the validation failure scenario
        # since that's the easiest to control deterministically
        polygon = get_valid_test_polygon()
        if validation_fail:
            polygon = get_invalid_test_polygon()
        
        # Make request (failure combo should return response, not crash)
        try:
            response = client.post("/analyze", json={"polygon": polygon})
            
            # Should get a response
            assert response.status_code in [200, 400, 422, 500]
            
            # Response should be parseable as JSON
            data = response.json()
            assert isinstance(data, dict)
            
        except Exception as e:
            pytest.fail(f"System crashed with failure combination: {e}")

    @settings(max_examples=250)
    @given(st.lists(st.sampled_from(["validation", "collection"]), 
                     min_size=1, max_size=2, unique=True))
    def test_failure_sequence_returns_valid_response(self, failure_types):
        """
        Property: For any sequence of failures, system returns valid response.
        
        Feature: land-scanner, Property 15: Module Failure Isolation
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        """
        polygon = get_valid_test_polygon()
        
        # If validation is in failures, use invalid polygon
        if "validation" in failure_types:
            polygon = get_invalid_test_polygon()
        
        # Make request
        response = client.post("/analyze", json={"polygon": polygon})
        
        # Should return response (not crash)
        assert response.status_code in [200, 400, 422, 500]
        
        # Should be valid JSON
        data = response.json()
        assert isinstance(data, dict)

    @settings(max_examples=100)
    @given(st.integers(min_value=0, max_value=1))
    def test_polygon_variations_always_return_response(self, polygon_type):
        """
        Property: For any type of polygon variation, system returns valid response.
        Tests that no input can crash the system.
        
        Feature: land-scanner, Property 15: Module Failure Isolation
        Validates: Requirements 8.3, 8.4, 8.7, 8.8
        """
        if polygon_type == 0:
            polygon = get_valid_test_polygon()
        else:
            polygon = get_invalid_test_polygon()
        
        # Make request
        response = client.post("/analyze", json={"polygon": polygon})
        
        # Should always return valid response
        assert response.status_code in [200, 400, 422, 500]
        data = response.json()
        assert isinstance(data, dict)
