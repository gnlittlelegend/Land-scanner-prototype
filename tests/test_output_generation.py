"""
Property-based tests for output generation module.

Tests verify that output format is consistent and complete across various
inputs, and that data encapsulation requirements are met.
"""

from hypothesis import given, strategies as st, settings
from datetime import datetime
import json
import logging

from backend.output import OutputGenerator
from backend.models import (
    AnalysisResponse,
    ProcessingStatus,
    RuleResult,
    ModuleStatus,
    ErrorInfo,
    Polygon as PolygonModel
)

logger = logging.getLogger(__name__)


# Strategies for generating test data

@st.composite
def rule_result_strategy(draw):
    """Generate a random RuleResult."""
    rule_ids = ["admin", "land_cover", "buildings", "roads", "water", "elevation"]
    statuses = [
        ProcessingStatus.SUCCESS,
        ProcessingStatus.FAILED,
        ProcessingStatus.INSUFFICIENT_DATA,
        ProcessingStatus.SKIPPED
    ]
    
    return RuleResult(
        rule_id=draw(st.sampled_from(rule_ids)),
        rule_name=draw(st.text(min_size=1, max_size=50)),
        status=draw(st.sampled_from(statuses)),
        result=draw(st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.floats(allow_nan=False, allow_infinity=False)),
            max_size=10
        )),
        metadata={
            "execution_time_ms": draw(st.floats(min_value=0, max_value=1000)),
            "data_points_used": draw(st.integers(min_value=0, max_value=10000))
        }
    )


@st.composite
def module_status_strategy(draw):
    """Generate a random ModuleStatus."""
    module_names = ["validation", "data_collection", "standardization", "rule_engine", "output_generation"]
    statuses = [ProcessingStatus.SUCCESS, ProcessingStatus.FAILED, ProcessingStatus.PARTIAL]
    
    status = draw(st.sampled_from(statuses))
    error_msg = None if status == ProcessingStatus.SUCCESS else draw(st.text(min_size=1, max_size=100))
    
    return ModuleStatus(
        module_name=draw(st.sampled_from(module_names)),
        status=status,
        error_message=error_msg,
        execution_time_ms=draw(st.floats(min_value=0, max_value=5000))
    )


@st.composite
def polygon_strategy(draw):
    """Generate a random valid Polygon."""
    return PolygonModel(
        geojson={
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        },
        area_sqkm=draw(st.floats(min_value=0.001, max_value=1000000)),
        bounding_box=(0, 0, 1, 1),
        centroid=(0.5, 0.5),
        crs="EPSG:4326",
        is_valid=True
    )


@st.composite
def provider_status_dict_strategy(draw):
    """Generate a random provider status dictionary."""
    providers = ["osm_buildings", "admin_boundaries", "land_cover", "roads", "water", "elevation"]
    # Randomly select which providers to include (at least 1)
    selected_flags = draw(st.lists(st.booleans(), min_size=6, max_size=6))
    selected_providers = [p for p, include in zip(providers, selected_flags) if include]
    
    # If none selected, select at least one
    if not selected_providers:
        selected_providers = [draw(st.sampled_from(providers))]
    
    result = {}
    for provider in selected_providers:
        has_error = draw(st.booleans())
        result[provider] = {
            "status": draw(st.sampled_from(["available", "unavailable", "error", "success"])),
            "data_retrieved": draw(st.booleans()),
            "error_message": draw(st.text(max_size=50)) if has_error else None,
            "feature_count": draw(st.integers(min_value=0, max_value=10000))
        }
    
    return result


# Property-Based Tests

class TestOutputFormatConsistency:
    """
    Property 9: Output Format Consistency
    
    For any analysis request that completes (successfully or with errors),
    the system should return valid JSON with required fields: request_id,
    status, analysis_summary, land_information, processing_status,
    provider_status.
    
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8
    """
    
    @given(
        rules_results=st.dictionaries(
            keys=st.sampled_from(["admin", "land_cover", "buildings", "roads", "water", "elevation"]),
            values=rule_result_strategy(),
            min_size=1,
            max_size=6
        ),
        processing_status=st.dictionaries(
            keys=st.sampled_from(["validation", "data_collection", "standardization", "rule_engine", "output_generation"]),
            values=module_status_strategy(),
            min_size=1,
            max_size=5
        ),
        provider_status=provider_status_dict_strategy(),
        polygon=polygon_strategy(),
        processing_time_ms=st.floats(min_value=0, max_value=60000)
    )
    @settings(max_examples=100)
    def test_output_has_all_required_fields(
        self,
        rules_results,
        processing_status,
        provider_status,
        polygon,
        processing_time_ms
    ):
        """
        For any combination of rule results, module statuses, and provider statuses,
        the generated output should have all required fields.
        
        Feature: land-scanner, Property 9: Output Format Consistency
        """
        generator = OutputGenerator()
        
        response = generator.generate(
            rules_results=rules_results,
            processing_status=processing_status,
            provider_status=provider_status,
            polygon=polygon,
            processing_time_ms=processing_time_ms
        )
        
        # Verify all required fields exist and are non-None
        assert response.request_id is not None, "request_id must be present"
        assert len(response.request_id) > 0, "request_id must not be empty"
        
        assert response.status is not None, "status must be present"
        assert response.status in [
            ProcessingStatus.SUCCESS,
            ProcessingStatus.PARTIAL,
            ProcessingStatus.FAILED
        ], f"status must be valid, got {response.status}"
        
        assert response.timestamp is not None, "timestamp must be present"
        assert isinstance(response.timestamp, datetime), "timestamp must be datetime"
        
        assert response.processing_time_ms is not None, "processing_time_ms must be present"
        assert isinstance(response.processing_time_ms, (int, float)), "processing_time_ms must be numeric"
        
        assert response.analysis_summary is not None, "analysis_summary must be present"
        assert isinstance(response.analysis_summary, dict), "analysis_summary must be dict"
        
        assert response.land_information is not None, "land_information must be present"
        assert isinstance(response.land_information, dict), "land_information must be dict"
        
        assert response.processing_status is not None, "processing_status must be present"
        assert isinstance(response.processing_status, dict), "processing_status must be dict"
        
        assert response.provider_status is not None, "provider_status must be present"
        assert isinstance(response.provider_status, list), "provider_status must be list"
        
        assert response.errors is not None, "errors must be present"
        assert isinstance(response.errors, list), "errors must be list"
    
    @given(
        rules_results=st.dictionaries(
            keys=st.sampled_from(["admin", "land_cover", "buildings", "roads", "water", "elevation"]),
            values=rule_result_strategy(),
            min_size=1,
            max_size=6
        ),
        processing_status=st.dictionaries(
            keys=st.sampled_from(["validation", "data_collection", "standardization", "rule_engine", "output_generation"]),
            values=module_status_strategy(),
            min_size=1,
            max_size=5
        ),
        provider_status=provider_status_dict_strategy(),
        processing_time_ms=st.floats(min_value=0, max_value=60000)
    )
    @settings(max_examples=100)
    def test_output_is_valid_json(
        self,
        rules_results,
        processing_status,
        provider_status,
        processing_time_ms
    ):
        """
        For any combination of inputs, the generated output should be
        serializable to valid JSON.
        
        Feature: land-scanner, Property 9: Output Format Consistency
        """
        generator = OutputGenerator()
        
        response = generator.generate(
            rules_results=rules_results,
            processing_status=processing_status,
            provider_status=provider_status,
            processing_time_ms=processing_time_ms
        )
        
        # Should be serializable to JSON
        try:
            json_str = response.model_dump_json()
            assert isinstance(json_str, str), "Response should serialize to string"
            assert len(json_str) > 0, "JSON string should not be empty"
            
            # Should be deserializable back
            parsed = json.loads(json_str)
            assert isinstance(parsed, dict), "Parsed JSON should be dictionary"
            assert "request_id" in parsed, "request_id should be in JSON"
            assert "status" in parsed, "status should be in JSON"
        except Exception as e:
            raise AssertionError(f"Response should be valid JSON: {str(e)}")
    
    @given(
        rules_results=st.dictionaries(
            keys=st.sampled_from(["admin", "land_cover", "buildings", "roads", "water", "elevation"]),
            values=rule_result_strategy(),
            min_size=1,
            max_size=6
        ),
        processing_status=st.dictionaries(
            keys=st.sampled_from(["validation", "data_collection", "standardization", "rule_engine", "output_generation"]),
            values=module_status_strategy(),
            min_size=1,
            max_size=5
        ),
        provider_status=provider_status_dict_strategy(),
        processing_time_ms=st.floats(min_value=0, max_value=60000)
    )
    @settings(max_examples=100)
    def test_output_has_valid_status_values(
        self,
        rules_results,
        processing_status,
        provider_status,
        processing_time_ms
    ):
        """
        For any inputs, the response status should be one of the valid
        ProcessingStatus values.
        
        Feature: land-scanner, Property 9: Output Format Consistency
        """
        generator = OutputGenerator()
        
        response = generator.generate(
            rules_results=rules_results,
            processing_status=processing_status,
            provider_status=provider_status,
            processing_time_ms=processing_time_ms
        )
        
        # Status should be valid
        valid_statuses = {
            ProcessingStatus.SUCCESS,
            ProcessingStatus.PARTIAL,
            ProcessingStatus.FAILED
        }
        assert response.status in valid_statuses, \
            f"Response status must be valid, got {response.status}"
        
        # Land information should contain only valid rule results
        for rule_id, rule_result in response.land_information.items():
            assert isinstance(rule_result, RuleResult), \
                f"Land information values must be RuleResult, got {type(rule_result)}"
            valid_rule_statuses = {
                ProcessingStatus.SUCCESS,
                ProcessingStatus.FAILED,
                ProcessingStatus.INSUFFICIENT_DATA,
                ProcessingStatus.SKIPPED
            }
            assert rule_result.status in valid_rule_statuses, \
                f"Rule status must be valid, got {rule_result.status}"


class TestDataEncapsulationInOutput:
    """
    Property 10: Data Encapsulation in Output
    
    For any analysis response returned to the frontend, the response should
    contain only standardized, processed data—never raw provider-specific
    formats or internal implementation details.
    
    Validates: Requirements 6.7
    """
    
    @given(
        rules_results=st.dictionaries(
            keys=st.sampled_from(["admin", "land_cover", "buildings", "roads", "water", "elevation"]),
            values=rule_result_strategy(),
            min_size=1,
            max_size=6
        ),
        processing_status=st.dictionaries(
            keys=st.sampled_from(["validation", "data_collection", "standardization", "rule_engine", "output_generation"]),
            values=module_status_strategy(),
            min_size=1,
            max_size=5
        ),
        provider_status=provider_status_dict_strategy(),
        processing_time_ms=st.floats(min_value=0, max_value=60000)
    )
    @settings(max_examples=100)
    def test_output_does_not_expose_raw_provider_data(
        self,
        rules_results,
        processing_status,
        provider_status,
        processing_time_ms
    ):
        """
        For any combination of inputs, the output should never contain
        raw provider-specific data or internal details.
        
        Feature: land-scanner, Property 10: Data Encapsulation in Output
        """
        generator = OutputGenerator()
        
        response = generator.generate(
            rules_results=rules_results,
            processing_status=processing_status,
            provider_status=provider_status,
            processing_time_ms=processing_time_ms
        )
        
        # Get JSON representation to search for implementation details
        json_str = response.model_dump_json()
        json_lower = json_str.lower()
        
        # Should not contain raw provider-specific implementations
        forbidden_strings = [
            "overpass_api",
            "raw_features",
            "original_format",
            "__internal__",
            "private_",
            "_private",
            "source_code",
            "stack_trace",
            "traceback"
        ]
        
        for forbidden in forbidden_strings:
            assert forbidden not in json_lower, \
                f"Output should not contain '{forbidden}' which exposes implementation details"
        
        # Analysis summary should only contain high-level information
        summary = response.analysis_summary
        if isinstance(summary, dict):
            # Should not contain raw provider responses
            for key, value in summary.items():
                if isinstance(value, str):
                    assert "overpass" not in value.lower(), \
                        "Summary should not reference provider APIs"
                    assert "api" not in value.lower() or "accessible" in value.lower(), \
                        "Summary should not expose raw API responses"
    
    @given(
        rules_results=st.dictionaries(
            keys=st.sampled_from(["admin", "land_cover", "buildings", "roads", "water", "elevation"]),
            values=rule_result_strategy(),
            min_size=1,
            max_size=6
        ),
        processing_status=st.dictionaries(
            keys=st.sampled_from(["validation", "data_collection", "standardization", "rule_engine", "output_generation"]),
            values=module_status_strategy(),
            min_size=1,
            max_size=5
        ),
        provider_status=provider_status_dict_strategy(),
        processing_time_ms=st.floats(min_value=0, max_value=60000)
    )
    @settings(max_examples=100)
    def test_output_contains_only_processed_data(
        self,
        rules_results,
        processing_status,
        provider_status,
        processing_time_ms
    ):
        """
        For any inputs, land_information should contain only processed rule
        results, not raw provider datasets.
        
        Feature: land-scanner, Property 10: Data Encapsulation in Output
        """
        generator = OutputGenerator()
        
        response = generator.generate(
            rules_results=rules_results,
            processing_status=processing_status,
            provider_status=provider_status,
            processing_time_ms=processing_time_ms
        )
        
        # Land information should be all RuleResult objects (processed data)
        for key, value in response.land_information.items():
            assert isinstance(value, RuleResult), \
                f"Land information should contain only RuleResult objects, got {type(value)} for {key}"
            
            # Rule result should have processed data, not raw features
            assert hasattr(value, "result"), "RuleResult should have result field"
            assert hasattr(value, "rule_id"), "RuleResult should have rule_id"
            assert hasattr(value, "status"), "RuleResult should have status"
            
            # Result should be a processed dict, not raw provider data
            if isinstance(value.result, dict):
                # Check that results are processed, not raw
                # Raw data would typically have "features" arrays with raw geometries
                # Processed data should have analyzed summaries
                if "features" in value.result:
                    # If features exist, they should be processed summary, not raw
                    assert isinstance(value.result["features"], (dict, list, str, int, float)), \
                        "Features in result should be processed, not raw dataset"

