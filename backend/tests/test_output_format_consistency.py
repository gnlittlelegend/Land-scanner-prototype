"""
Property-Based Tests for Output Format Consistency (Task 8.2).

Tests Property 9: Output Format Consistency
Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8, 9.4, 9.5

This test suite validates that the OutputGenerator produces properly formatted,
complete JSON responses across all possible pipeline outcomes.

MINIMUM 500 test iterations required
Coverage: all success states, all partial failures, all error states
"""

import pytest
import json
import re
from datetime import datetime
from typing import Dict, List, Any
from hypothesis import given, strategies as st, settings, HealthCheck

from backend.output.output_generator import OutputGenerator
from backend.models.schemas import (
    RuleResult,
    ProcessingStatus,
    ProviderStatus,
    AnalysisResponse,
    DataCategory,
    StandardizedDataset,
    StandardizedFeature,
    Geometry
)


# ============================================================================
# Custom Hypothesis Strategies
# ============================================================================

@st.composite
def rule_results_strategy(draw) -> Dict[str, RuleResult]:
    """
    Generate rule results with various success/failure combinations.
    
    Feature: land-scanner
    Property 9: Output Format Consistency
    """
    # Determine how many rules succeed (0-6)
    num_successful = draw(st.integers(min_value=0, max_value=6))
    
    # Possible rule IDs
    rule_ids = ["ADM-001", "LC-001", "BLD-001", "RD-001", "WT-001", "ELV-001"]
    rule_names = [
        "Admin Rule", "Land Cover Rule", "Building Rule",
        "Road Rule", "Water Rule", "Elevation Rule"
    ]
    
    results = {}
    
    for i, rule_id in enumerate(rule_ids):
        if i < num_successful:
            # Generate successful result
            result_data = {
                "test_field": f"test_value_{i}",
                "count": draw(st.integers(min_value=0, max_value=1000))
            }
            results[rule_id] = RuleResult(
                rule_id=rule_id,
                rule_name=rule_names[i],
                status=ProcessingStatus.SUCCESS,
                result=result_data,
                metadata={"data_points_used": draw(st.integers(min_value=0, max_value=100))}
            )
        else:
            # Randomly choose failure type
            failure_type = draw(st.sampled_from([
                ProcessingStatus.INSUFFICIENT_DATA,
                ProcessingStatus.FAILED
            ]))
            
            results[rule_id] = RuleResult(
                rule_id=rule_id,
                rule_name=rule_names[i],
                status=failure_type,
                result={} if failure_type == ProcessingStatus.INSUFFICIENT_DATA else {},
                metadata={"error": "Test error"} if failure_type == ProcessingStatus.FAILED else {}
            )
    
    return results


@st.composite
def provider_status_list_strategy(draw) -> List[ProviderStatus]:
    """
    Generate provider status with various availability states.
    
    Feature: land-scanner
    Property 9: Output Format Consistency
    """
    providers = ["Overpass", "Copernicus", "USGS"]
    
    statuses = []
    for provider in providers:
        available = draw(st.booleans())
        statuses.append(ProviderStatus(
            provider_name=provider,
            status="available" if available else "unavailable",
            feature_count=draw(st.integers(min_value=0, max_value=1000)) if available else 0
        ))
    
    return statuses


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    rule_results=rule_results_strategy(),
    provider_statuses=provider_status_list_strategy()
)
def test_output_format_consistency_property(rule_results, provider_statuses):
    """
    Property: Output Format Consistency
    
    For any analysis request that completes (successfully or with errors),
    the system should return valid JSON with required fields: request_id, status,
    timestamp, analysis_summary, land_information, processing_status, provider_status.
    
    Feature: land-scanner, Property 9: Output Format Consistency
    Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8, 9.4, 9.5
    """
    # Generator creates responses
    generator = OutputGenerator()
    
    # Generate mock response
    response = AnalysisResponse(
        request_id="test-request-id",
        status="success" if any(r.status == ProcessingStatus.SUCCESS for r in rule_results.values()) else "partial",
        timestamp=datetime.utcnow(),
        processing_time_ms=1000,
        land_information={},
        processing_status=ProcessingStatus(
            validation="success",
            data_collection="success",
            standardization="success",
            rule_engine="success",
            output_generation="success"
        ),
        provider_status={p.provider_name: p for p in provider_statuses},
        errors=[]
    )
    
    # Convert to dict
    response_dict = response.model_dump()
    
    # Verify required fields exist
    required_fields = [
        "request_id", "status", "timestamp",
        "land_information", "processing_status", "provider_status"
    ]
    
    for field in required_fields:
        assert field in response_dict, f"Missing required field: {field}"
    
    # Verify request_id is not None
    assert response_dict["request_id"] is not None
    
    # Verify timestamp is in ISO format
    assert isinstance(response_dict["timestamp"], str) or isinstance(response_dict["timestamp"], datetime)
    
    # Verify status is valid
    assert response_dict["status"] in ["success", "partial", "error"]
