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
            feature_count=draw(st.integers(min_value=0, max_value=1000)) if available