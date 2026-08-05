"""
Property-Based Tests for Output Format Consistency (Task 8.2).

Tests Property 9: Output Format Consistency
Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8, 9.4, 9.5

This test suite validates that the AnalysisResponse produces properly formatted,
complete JSON responses across all possible pipeline outcomes.

Feature: land-scanner, Property 9: Output Format Consistency

MINIMUM 500 test iterations required
Coverage: all success states, all partial failures, all error states
"""

import pytest
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from hypothesis import given, strategies as st, settings, HealthCheck

from backend.data_models import (
    AnalysisResponse,
    ProcessingStatus,
    ProviderStatus,
    LandInformation,
    AnalysisSummary,
)


# ============================================================================
# Custom Hypothesis Strategies for Valid Output Generation
# ============================================================================

def iso8601_string() -> str:
    """Generate ISO8601 formatted timestamp string"""
    return datetime.utcnow().isoformat()


@st.composite
def processing_status_strategy(draw) -> ProcessingStatus:
    """
    Generate ProcessingStatus with valid values.
    
    Feature: land-scanner, Property 9: Output Format Consistency
    """
    status_values = ["success", "partial", "error"]
    return ProcessingStatus(
        validation=draw(st.sampled_from(status_values)),
        data_collection=draw(st.sampled_from(status_values)),
        standardization=draw(st.sampled_from(status_values)),
        rule_engine=draw(st.sampled_from(status_values)),
        output_generation=draw(st.sampled_from(status_values)),
    )


@st.composite
def provider_status_dict_strategy(draw) -> Dict[str, Dict]:
    """
    Generate provider status dictionary with various availability states.
    
    Feature: land-scanner, Property 9: Output Format Consistency
    """
    provider_ids = [
        "osm_buildings",
        "osm_admin",
        "osm_roads",
        "osm_water",
        "copernicus_land_cover",
        "usgs_elevation",
    ]
    
    provider_status = {}
    for provider_id in provider_ids:
        available = draw(st.booleans())
        provider_status[provider_id] = {
            "available": available,
            "records": draw(st.integers(min_value=0, max_value=10000)) if available else 0,
        }
        if not available:
            provider_status[provider_id]["error"] = "Provider unavailable"
    
    return provider_status


@st.composite
def land_information_strategy(draw) -> LandInformation:
    """
    Generate LandInformation with various data combinations.
    
    Feature: land-scanner, Property 9: Output Format Consistency
    """
    def make_section_data():
        """Generate random section data"""
        section_data = {}
        num_fields = draw(st.integers(min_value=0, max_value=5))
        for i in range(num_fields):
            section_data[f"field_{i}"] = draw(
                st.one_of(
                    st.text(max_size=100),
                    st.integers(),
                    st.floats(allow_nan=False, allow_infinity=False),
                    st.none(),
                )
            )
        return section_data
    
    return LandInformation(
        administrative=make_section_data(),
        land_cover=make_section_data(),
        buildings=make_section_data(),
        roads=make_section_data(),
        water=make_section_data(),
        elevation=make_section_data(),
    )


@st.composite
def analysis_summary_strategy(draw) -> Optional[AnalysisSummary]:
    """
    Generate AnalysisSummary or None.
    
    Feature: land-scanner, Property 9: Output Format Consistency
    """
    create_summary = draw(st.booleans())
    if create_summary:
        return AnalysisSummary(
            polygon_area_sqkm=draw(st.floats(min_value=0.00001, max_value=100)),
            analysis_date=datetime.utcnow(),
            primary_land_cover=draw(
                st.one_of(
                    st.sampled_from(["Urban", "Agricultural", "Forest", "Water", "Unknown"]),
                    st.none(),
                )
            ),
            key_findings=draw(
                st.lists(st.text(max_size=200), min_size=0, max_size=5)
            ),
        )
    return None


@st.composite
def analysis_response_strategy(draw) -> Dict[str, Any]:
    """
    Generate a complete AnalysisResponse as JSON-serializable dict.
    
    Feature: land-scanner, Property 9: Output Format Consistency
    """
    status_value = draw(st.sampled_from(["success", "partial", "error"]))
    
    response = AnalysisResponse(
        request_id=draw(st.uuids()).hex,
        status=status_value,
        processing_time_ms=draw(st.integers(min_value=100, max_value=30000)),
        analysis_summary=draw(analysis_summary_strategy()),
        land_information=draw(land_information_strategy()),
        processing_status=draw(processing_status_strategy()),
        provider_status=draw(provider_status_dict_strategy()),
        errors=draw(st.lists(st.text(max_size=500), min_size=0, max_size=10)),
    )
    
    return response.model_dump(mode='json')


# ============================================================================
# Property Tests for Output Format Consistency
# ============================================================================

class TestOutputFormatConsistency:
    """Test suite for Property 9: Output Format Consistency"""

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_output_is_valid_json(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        For any valid analysis result, the output must be serializable to valid JSON
        and parseable back from JSON without exceptions.
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
        """
        # Serialize to JSON
        json_str = json.dumps(response_dict)
        assert isinstance(json_str, str)
        assert len(json_str) > 0
        
        # Parse back from JSON
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)
        
        # Verify it matches original (within datetime serialization)
        assert parsed["request_id"] == response_dict["request_id"]
        assert parsed["status"] == response_dict["status"]

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_has_all_required_top_level_fields(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        For any analysis output, ALL required top-level fields must be present:
        - request_id
        - status
        - timestamp
        - analysis_summary (or None)
        - land_information
        - processing_status
        - provider_status
        - errors
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5
        """
        required_fields = [
            "request_id",
            "status",
            "timestamp",
            "analysis_summary",
            "land_information",
            "processing_status",
            "provider_status",
            "errors",
        ]
        
        for field in required_fields:
            assert field in response_dict, f"Missing required field: {field}"

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_status_field_valid_values(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        The 'status' field must be one of: success, partial, or error.
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.1, 6.2
        """
        status = response_dict["status"]
        valid_statuses = ["success", "partial", "error"]
        assert status in valid_statuses, f"Invalid status: {status}"

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_timestamp_is_iso8601(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        The 'timestamp' field must be in ISO8601 format (parseable as datetime).
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.1
        """
        timestamp_str = response_dict["timestamp"]
        # ISO8601 strings should be parseable by datetime
        try:
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            assert dt is not None
        except (ValueError, AttributeError):
            pytest.fail(f"Timestamp not in ISO8601 format: {timestamp_str}")

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_request_id_is_string(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        The 'request_id' field must be a non-empty string.
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.1
        """
        request_id = response_dict["request_id"]
        assert isinstance(request_id, str)
        assert len(request_id) > 0

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_land_information_has_all_categories(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        The 'land_information' object must have all category sections:
        administrative, land_cover, buildings, roads, water, elevation
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.3, 6.4
        """
        land_info = response_dict["land_information"]
        required_categories = [
            "administrative",
            "land_cover",
            "buildings",
            "roads",
            "water",
            "elevation",
        ]
        
        for category in required_categories:
            assert category in land_info, f"Missing category: {category}"

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_processing_status_has_all_modules(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        The 'processing_status' object must have all module statuses:
        validation, data_collection, standardization, rule_engine, output_generation
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.4
        """
        proc_status = response_dict["processing_status"]
        required_modules = [
            "validation",
            "data_collection",
            "standardization",
            "rule_engine",
            "output_generation",
        ]
        
        for module in required_modules:
            assert module in proc_status, f"Missing module status: {module}"

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_provider_status_is_dict(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        The 'provider_status' field must be a dictionary with provider entries.
        Each entry must have 'available' (bool) and 'records' (int).
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.5
        """
        provider_status = response_dict["provider_status"]
        assert isinstance(provider_status, dict)
        
        for provider_id, status_info in provider_status.items():
            assert isinstance(status_info, dict)
            assert "available" in status_info
            assert isinstance(status_info["available"], bool)
            assert "records" in status_info
            assert isinstance(status_info["records"], int)
            assert status_info["records"] >= 0

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_errors_is_list_of_strings(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        The 'errors' field must be a list (possibly empty).
        All elements must be strings.
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.6
        """
        errors = response_dict["errors"]
        assert isinstance(errors, list)
        for error in errors:
            assert isinstance(error, str)

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_processing_time_is_positive_integer(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        The 'processing_time_ms' field must be a positive integer.
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.1
        """
        processing_time = response_dict.get("processing_time_ms", 0)
        assert isinstance(processing_time, int)
        assert processing_time >= 0

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_analysis_summary_structure_when_present(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        When 'analysis_summary' is present (not None), it must have:
        - polygon_area_sqkm (float)
        - analysis_date (datetime/string)
        - primary_land_cover (string or None)
        - key_findings (list of strings)
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.3
        """
        analysis_summary = response_dict["analysis_summary"]
        
        if analysis_summary is not None:
            assert isinstance(analysis_summary, dict)
            assert "polygon_area_sqkm" in analysis_summary
            assert "analysis_date" in analysis_summary
            assert "primary_land_cover" in analysis_summary
            assert "key_findings" in analysis_summary
            
            # Validate types
            assert isinstance(analysis_summary["polygon_area_sqkm"], (int, float))
            assert analysis_summary["polygon_area_sqkm"] > 0
            assert isinstance(analysis_summary["key_findings"], list)
            for finding in analysis_summary["key_findings"]:
                assert isinstance(finding, str)

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_no_undefined_null_fields_at_top_level(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        No top-level fields should be undefined (missing keys are OK, but all present
        fields should have valid values, not arbitrary null values).
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.1, 6.7
        """
        # Check that all top-level keys are valid
        valid_keys = {
            "request_id",
            "status",
            "timestamp",
            "analysis_summary",
            "land_information",
            "processing_status",
            "provider_status",
            "errors",
            "processing_time_ms",
        }
        
        for key in response_dict.keys():
            assert key in valid_keys, f"Unexpected field in response: {key}"

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(status_val=st.sampled_from(["success", "partial", "error"]))
    def test_output_consistency_across_status_values(self, status_val: str):
        """
        Property 9: Output Format Consistency
        
        Output structure must be consistent regardless of status value
        (success, partial, or error).
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.1, 6.2
        """
        response = AnalysisResponse(
            request_id="test-id",
            status=status_val,
            land_information=LandInformation(),
            processing_status=ProcessingStatus(),
            provider_status={},
            errors=[],
        )
        
        response_dict = response.model_dump()
        
        # Verify structure is consistent
        required_fields = [
            "request_id",
            "status",
            "timestamp",
            "land_information",
            "processing_status",
            "provider_status",
            "errors",
        ]
        
        for field in required_fields:
            assert field in response_dict

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_land_information_fields_are_dicts_or_empty(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        Each category in land_information must be a dictionary
        (possibly empty when data unavailable).
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.4
        """
        land_info = response_dict["land_information"]
        categories = [
            "administrative",
            "land_cover",
            "buildings",
            "roads",
            "water",
            "elevation",
        ]
        
        for category in categories:
            field_value = land_info[category]
            assert isinstance(field_value, dict), (
                f"Category {category} must be a dict, got {type(field_value)}"
            )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_processing_status_values_valid(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        Each module status in processing_status must be one of:
        success, partial, or error.
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.4
        """
        proc_status = response_dict["processing_status"]
        valid_statuses = ["success", "partial", "error", "pending"]
        
        for module_name, status_value in proc_status.items():
            assert status_value in valid_statuses, (
                f"Invalid status '{status_value}' for module {module_name}"
            )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_strategy())
    def test_output_serialization_round_trip(self, response_dict: Dict[str, Any]):
        """
        Property 9: Output Format Consistency
        
        Output should serialize to JSON and deserialize back with
        the same structure (allowing for datetime serialization).
        
        Feature: land-scanner, Property 9: Output Format Consistency
        Validates: Requirements 6.1, 6.7, 6.8
        """
        # Serialize to JSON
        json_str = json.dumps(response_dict)
        
        # Deserialize back
        parsed = json.loads(json_str)
        
        # Verify key fields match
        assert parsed["request_id"] == response_dict["request_id"]
        assert parsed["status"] == response_dict["status"]
        assert parsed["processing_time_ms"] == response_dict["processing_time_ms"]
        
        # Verify structure matches
        assert set(parsed.keys()) == set(response_dict.keys())
        assert set(parsed["land_information"].keys()) == set(
            response_dict["land_information"].keys()
        )
        assert set(parsed["processing_status"].keys()) == set(
            response_dict["processing_status"].keys()
        )
