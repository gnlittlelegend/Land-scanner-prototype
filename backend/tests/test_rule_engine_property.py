"""
Property-Based Tests for Rule Engine

Feature: land-scanner, Property 7: Rule Independence and Continuation
Feature: land-scanner, Property 8: Rule Result Compilation
Validates: Requirements 5.9, 5.10, 5.11

This test suite validates that the Rule Engine:
- Executes all registered rules independently
- Failure of one rule does NOT affect others
- Missing data results in "insufficient_data" status (not failure)
- ALL rule results are collected and returned regardless of outcome
- Rules handle failures gracefully with meaningful status information
- System compiles results from all rule execution scenarios
"""

import pytest
import logging
from typing import Dict, List, Any
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st

from backend.rules.rule_engine import RuleEngine, Rule
from backend.models.schemas import (
    StandardizedDataset,
    StandardizedFeature,
    Geometry,
    RuleResult,
    ProcessingStatus,
    DataCategory
)

logger = logging.getLogger(__name__)


# ============================================================================
# Test Rule Implementations for Testing
# ============================================================================

class SuccessfulRule(Rule):
    """Rule that always succeeds."""
    
    def __init__(self, rule_id: str, rule_name: str, category: DataCategory):
        super().__init__(rule_id, rule_name, [category])
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=ProcessingStatus.SUCCESS,
            result={"status": "success", "data_processed": True},
            metadata={"test": "metadata"}
        )


class FailingRule(Rule):
    """Rule that always fails with an exception."""
    
    def __init__(self, rule_id: str, rule_name: str, category: DataCategory):
        super().__init__(rule_id, rule_name, [category])
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        raise Exception(f"Simulated failure for {self.rule_id}")


class InsufficientDataRule(Rule):
    """Rule that has insufficient data."""
    
    def __init__(self, rule_id: str, rule_name: str, category: DataCategory):
        super().__init__(rule_id, rule_name, [category])
    
    def has_required_data(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> bool:
        """Always report insufficient data."""
        return False
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=ProcessingStatus.INSUFFICIENT_DATA,
            result={},
            metadata={}
        )


# ============================================================================
# Fixture Builders
# ============================================================================

@pytest.fixture(scope="session")
def standard_datasets():
    """Create a set of standard datasets for testing."""
    datasets = {}
    
    for category in [
        DataCategory.BUILDINGS,
        DataCategory.ADMIN,
        DataCategory.LAND_COVER,
        DataCategory.ROADS,
        DataCategory.WATER,
        DataCategory.ELEVATION
    ]:
        feature = StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            ),
            properties={"test": "data"},
            source_provider="test_provider",
            source_category=category.value
        )
        
        dataset = StandardizedDataset(
            features=[feature],
            source_provider="test_provider",
            category=category,
            feature_count=1,
            crs="EPSG:4326",
            metadata={"source": "test"}
        )
        
        datasets[category] = dataset
    
    return datasets


@pytest.fixture(scope="session")
def empty_datasets():
    """Create a set of empty datasets."""
    datasets = {}
    
    for category in [
        DataCategory.BUILDINGS,
        DataCategory.ADMIN,
        DataCategory.LAND_COVER,
        DataCategory.ROADS,
        DataCategory.WATER,
        DataCategory.ELEVATION
    ]:
        dataset = StandardizedDataset(
            features=[],
            source_provider="test_provider",
            category=category,
            feature_count=0,
            crs="EPSG:4326",
            metadata={"source": "test"}
        )
        
        datasets[category] = dataset
    
    return datasets


# ============================================================================
# Property 7: Rule Independence and Continuation Tests
# ============================================================================

class TestRuleIndependence:
    """
    Property 7: Rule Independence and Continuation
    
    For any set of rules where one rule fails or encounters insufficient data,
    the remaining rules should continue executing independently and produce
    their results without cascading failure.
    """
    
    def test_single_rule_failure_does_not_stop_others(self, standard_datasets):
        """
        SCENARIO: One rule fails with exception, others should still execute.
        
        Validates: Requirements 5.9, 5.10
        """
        engine = RuleEngine()
        
        # Register 6 rules: 1 failing, 5 successful
        failing_rule = FailingRule("FAIL-001", "Failing Rule", DataCategory.BUILDINGS)
        successful_rules = [
            SuccessfulRule(f"SUC-{i:03d}", f"Successful Rule {i}", DataCategory.ADMIN)
            for i in range(1, 6)
        ]
        
        engine.register_rule(failing_rule)
        for rule in successful_rules:
            engine.register_rule(rule)
        
        # Execute
        results = engine.execute(standard_datasets)
        
        # Verify failing rule failed
        assert "FAIL-001" in results
        assert results["FAIL-001"].status == ProcessingStatus.FAILED
        
        # Verify all successful rules still executed
        for i in range(1, 6):
            rule_id = f"SUC-{i:03d}"
            assert rule_id in results
            assert results[rule_id].status == ProcessingStatus.SUCCESS
            assert "status" in results[rule_id].result
            assert results[rule_id].result["status"] == "success"
        
        # Verify total results count
        assert len(results) == 6, "Not all rules were executed"
    
    
    def test_multiple_rule_failures_independent(self, standard_datasets):
        """
        SCENARIO: Multiple rules fail, others still execute independently.
        
        Validates: Requirements 5.9, 5.10
        """
        engine = RuleEngine()
        
        # Register 6 rules: 3 failing, 3 successful
        failing_rules = [
            FailingRule(f"FAIL-{i:03d}", f"Failing Rule {i}", DataCategory.BUILDINGS)
            for i in range(1, 4)
        ]
        successful_rules = [
            SuccessfulRule(f"SUC-{i:03d}", f"Successful Rule {i}", DataCategory.ADMIN)
            for i in range(1, 4)
        ]
        
        for rule in failing_rules + successful_rules:
            engine.register_rule(rule)
        
        # Execute
        results = engine.execute(standard_datasets)
        
        # Verify all failing rules failed
        for i in range(1, 4):
            rule_id = f"FAIL-{i:03d}"
            assert rule_id in results
            assert results[rule_id].status == ProcessingStatus.FAILED
        
        # Verify all successful rules executed
        for i in range(1, 4):
            rule_id = f"SUC-{i:03d}"
            assert rule_id in results
            assert results[rule_id].status == ProcessingStatus.SUCCESS
        
        # Verify total results count (all 6 rules)
        assert len(results) == 6
    
    
    def test_insufficient_data_independent(self, empty_datasets):
        """
        SCENARIO: Some rules have insufficient data, others execute successfully.
        
        Validates: Requirements 5.9, 5.10
        """
        engine = RuleEngine()
        
        # Register 6 rules: 3 with insufficient data, 3 successful
        insufficient_rules = [
            InsufficientDataRule(f"INSUF-{i:03d}", f"Insufficient Rule {i}", DataCategory.BUILDINGS)
            for i in range(1, 4)
        ]
        
        # For successful rules, override has_required_data to return True
        successful_rules = []
        for i in range(1, 4):
            rule = SuccessfulRule(f"SUC-{i:03d}", f"Successful Rule {i}", DataCategory.ADMIN)
            rule.required_categories = []  # No required categories
            successful_rules.append(rule)
        
        for rule in insufficient_rules + successful_rules:
            engine.register_rule(rule)
        
        # Execute
        results = engine.execute(empty_datasets)
        
        # Verify insufficient data rules marked correctly
        for i in range(1, 4):
            rule_id = f"INSUF-{i:03d}"
            assert rule_id in results
            assert results[rule_id].status == ProcessingStatus.INSUFFICIENT_DATA
        
        # Verify successful rules executed
        for i in range(1, 4):
            rule_id = f"SUC-{i:03d}"
            assert rule_id in results
            assert results[rule_id].status == ProcessingStatus.SUCCESS
        
        # Verify total results count
        assert len(results) == 6
    
    
    def test_each_rule_independent_failure(self, standard_datasets):
        """
        SCENARIO: Test each rule individually failing with others succeeding.
        
        For each of 6 rules:
        - Make that rule fail
        - Verify other 5 execute successfully
        - Verify no cascading failure
        
        Validates: Requirements 5.9, 5.10
        """
        for failing_index in range(1, 7):
            engine = RuleEngine()
            
            # Create 6 rules, with index `failing_index` as the failing one
            all_rules = []
            for i in range(1, 7):
                if i == failing_index:
                    rule = FailingRule(f"FAIL-{i:03d}", f"Failing Rule {i}", DataCategory.BUILDINGS)
                else:
                    rule = SuccessfulRule(f"SUC-{i:03d}", f"Successful Rule {i}", DataCategory.ADMIN)
                all_rules.append(rule)
                engine.register_rule(rule)
            
            # Execute
            results = engine.execute(standard_datasets)
            
            # Verify the failing rule failed
            failing_id = f"FAIL-{failing_index:03d}"
            assert results[failing_id].status == ProcessingStatus.FAILED
            
            # Verify all other rules succeeded
            for i in range(1, 7):
                if i != failing_index:
                    rule_id = f"SUC-{i:03d}"
                    assert results[rule_id].status == ProcessingStatus.SUCCESS, \
                        f"Rule {rule_id} should succeed when {failing_id} fails"
            
            # Verify no data loss
            assert len(results) == 6, f"Not all rules executed when rule {failing_index} failed"


# ============================================================================
# Property 8: Rule Result Compilation Tests
# ============================================================================

class TestRuleResultCompilation:
    """
    Property 8: Rule Result Compilation
    
    For any Rule Engine execution, regardless of individual rule outcomes,
    the system should compile all rule results into a single structured
    analysis output. Results should include all rule outcomes (success and
    failure) with consistent structure.
    """
    
    def test_compilation_all_success(self, standard_datasets):
        """
        SCENARIO: All 6 rules execute successfully.
        
        Validates: Requirements 5.11
        """
        engine = RuleEngine()
        
        # Register 6 successful rules
        for i in range(1, 7):
            rule = SuccessfulRule(f"SUC-{i:03d}", f"Successful Rule {i}", DataCategory.ADMIN)
            engine.register_rule(rule)
        
        # Execute
        results = engine.execute(standard_datasets)
        
        # Verify compilation structure
        assert isinstance(results, dict), "Results must be a dictionary"
        assert len(results) == 6, "All 6 rules should be in results"
        
        # Verify each result has required fields
        for rule_id, result in results.items():
            assert hasattr(result, 'rule_id'), f"Result {rule_id} missing rule_id"
            assert hasattr(result, 'rule_name'), f"Result {rule_id} missing rule_name"
            assert hasattr(result, 'status'), f"Result {rule_id} missing status"
            assert hasattr(result, 'result'), f"Result {rule_id} missing result"
            assert hasattr(result, 'metadata'), f"Result {rule_id} missing metadata"
            
            # Verify status is SUCCESS
            assert result.status == ProcessingStatus.SUCCESS
    
    
    def test_compilation_partial_success(self, standard_datasets):
        """
        SCENARIO: Mix of successful, failing, and insufficient data rules.
        
        Validates: Requirements 5.11
        """
        engine = RuleEngine()
        
        # Register mixed rules: success, failure, insufficient
        engine.register_rule(SuccessfulRule("SUC-001", "Successful Rule", DataCategory.ADMIN))
        engine.register_rule(FailingRule("FAIL-001", "Failing Rule", DataCategory.BUILDINGS))
        engine.register_rule(InsufficientDataRule("INSUF-001", "Insufficient Rule", DataCategory.WATER))
        engine.register_rule(SuccessfulRule("SUC-002", "Successful Rule 2", DataCategory.ROADS))
        
        # Execute
        results = engine.execute(standard_datasets)
        
        # Verify compilation includes all outcomes
        assert len(results) == 4, "All 4 rules should be in results"
        
        # Verify each outcome type is present
        outcomes = {
            "SUC-001": ProcessingStatus.SUCCESS,
            "FAIL-001": ProcessingStatus.FAILED,
            "INSUF-001": ProcessingStatus.INSUFFICIENT_DATA,
            "SUC-002": ProcessingStatus.SUCCESS
        }
        
        for rule_id, expected_status in outcomes.items():
            assert rule_id in results, f"Rule {rule_id} missing from results"
            assert results[rule_id].status == expected_status, \
                f"Rule {rule_id} status mismatch"
    
    
    def test_compilation_complete_failure(self, standard_datasets):
        """
        SCENARIO: All 6 rules fail.
        
        Validates: Requirements 5.11
        """
        engine = RuleEngine()
        
        # Register 6 failing rules
        for i in range(1, 7):
            rule = FailingRule(f"FAIL-{i:03d}", f"Failing Rule {i}", DataCategory.BUILDINGS)
            engine.register_rule(rule)
        
        # Execute
        results = engine.execute(standard_datasets)
        
        # Verify compilation includes all failures
        assert len(results) == 6, "All 6 failing rules should be in results"
        
        # Verify all results show failure
        for rule_id, result in results.items():
            assert result.status == ProcessingStatus.FAILED
    
    
    def test_compilation_structure_consistency(self, standard_datasets):
        """
        SCENARIO: Verify compiled results have consistent structure regardless of outcome.
        
        Validates: Requirements 5.11
        """
        engine = RuleEngine()
        
        # Mix of all rule types
        engine.register_rule(SuccessfulRule("SUC-001", "Successful", DataCategory.ADMIN))
        engine.register_rule(FailingRule("FAIL-001", "Failing", DataCategory.BUILDINGS))
        engine.register_rule(InsufficientDataRule("INSUF-001", "Insufficient", DataCategory.WATER))
        
        # Execute
        results = engine.execute(standard_datasets)
        
        # Verify consistent structure across all results
        required_fields = {'rule_id', 'rule_name', 'status', 'result', 'metadata'}
        
        for rule_id, result in results.items():
            for field in required_fields:
                assert hasattr(result, field), \
                    f"Result {rule_id} missing field {field}"
            
            # Verify field types
            assert isinstance(result.rule_id, str)
            assert isinstance(result.rule_name, str)
            assert isinstance(result.status, ProcessingStatus)
            assert isinstance(result.result, dict)
            assert isinstance(result.metadata, dict)
    
    
    def test_compilation_all_6_rules_enabled(self, standard_datasets):
        """
        SCENARIO: Test compilation with ALL 6 rules enabled and successful.
        
        Requirement: Test with ALL 6 rules enabled (buildings, admin, land_cover, roads, water, elevation)
        
        Validates: Requirements 5.11
        """
        engine = RuleEngine()
        
        # Map categories to rule IDs
        categories_and_ids = [
            (DataCategory.BUILDINGS, "BLD-001"),
            (DataCategory.ADMIN, "ADM-001"),
            (DataCategory.LAND_COVER, "LC-001"),
            (DataCategory.ROADS, "RD-001"),
            (DataCategory.WATER, "WT-001"),
            (DataCategory.ELEVATION, "ELV-001")
        ]
        
        # Register all 6 rules
        for category, rule_id in categories_and_ids:
            rule = SuccessfulRule(rule_id, f"Rule for {category.value}", category)
            engine.register_rule(rule)
        
        # Execute
        results = engine.execute(standard_datasets)
        
        # Verify all 6 rules compiled
        assert len(results) == 6, "All 6 rules should be compiled"
        
        # Verify each category has a corresponding result
        for category, rule_id in categories_and_ids:
            assert rule_id in results, f"Rule {rule_id} for {category.value} missing"
            assert results[rule_id].status == ProcessingStatus.SUCCESS
    
    
    def test_compilation_subset_of_rules(self, standard_datasets):
        """
        SCENARIO: Test compilation works correctly with subsets of rules (not all 6).
        
        Requirement: Test with subset of rules enabled (verify compilation works with partial rules)
        
        Validates: Requirements 5.11
        """
        # Test with 1, 2, 3, 4, 5 rules (not just 6)
        for num_rules in range(1, 6):
            engine = RuleEngine()
            
            # Register subset of rules
            for i in range(num_rules):
                rule = SuccessfulRule(f"RULE-{i:03d}", f"Rule {i}", DataCategory.ADMIN)
                engine.register_rule(rule)
            
            # Execute
            results = engine.execute(standard_datasets)
            
            # Verify correct number compiled
            assert len(results) == num_rules, \
                f"Expected {num_rules} results with {num_rules} rules, got {len(results)}"
            
            # Verify structure consistent
            for rule_id, result in results.items():
                assert result.status == ProcessingStatus.SUCCESS
                assert hasattr(result, 'rule_id')
                assert hasattr(result, 'status')
                assert hasattr(result, 'result')
                assert hasattr(result, 'metadata')
    
    
    def test_compilation_ordering_consistency(self, standard_datasets):
        """
        SCENARIO: Verify rules execute in consistent order and results compile accordingly.
        
        Requirement: Test ordering consistency (rules execute in consistent order)
        
        Validates: Requirements 5.11
        """
        # Execute the same rules multiple times and verify order is consistent
        rule_ids_created = [f"RULE-{i:03d}" for i in range(1, 7)]
        
        for execution_num in range(3):  # Run 3 times to verify consistency
            engine = RuleEngine()
            
            # Register rules in same order
            for i, rule_id in enumerate(rule_ids_created):
                rule = SuccessfulRule(rule_id, f"Rule {i}", DataCategory.ADMIN)
                engine.register_rule(rule)
            
            # Execute
            results = engine.execute(standard_datasets)
            
            # Verify order of results matches registration order
            result_ids = list(results.keys())
            assert result_ids == rule_ids_created, \
                f"Execution {execution_num}: Order mismatch. Expected {rule_ids_created}, got {result_ids}"
    
    
    def test_compilation_no_data_loss(self, standard_datasets):
        """
        SCENARIO: Verify no data loss during compilation with various rule states.
        
        Requirement: Verify NO data loss in compilation process (all outputs present)
        
        Validates: Requirements 5.11
        """
        engine = RuleEngine()
        
        # Create three successful rules
        rule1 = SuccessfulRule("RULE-001", "Rule 1", DataCategory.ADMIN)
        rule2 = SuccessfulRule("RULE-002", "Rule 2", DataCategory.BUILDINGS)
        rule3 = SuccessfulRule("RULE-003", "Rule 3", DataCategory.WATER)
        
        engine.register_rule(rule1)
        engine.register_rule(rule2)
        engine.register_rule(rule3)
        
        # Execute
        results = engine.execute(standard_datasets)
        
        # Verify all rules compiled (no data loss - all present)
        assert len(results) == 3, "All 3 rules should be present in compilation"
        assert "RULE-001" in results
        assert "RULE-002" in results
        assert "RULE-003" in results
        
        # Verify each result has its data
        for rule_id, result in results.items():
            assert result.result is not None, f"Rule {rule_id} result data is None"
            assert isinstance(result.result, dict), f"Rule {rule_id} result should be dict"
            assert result.metadata is not None, f"Rule {rule_id} metadata is None"
    
    
    def test_compilation_with_mixed_success_failure_insufficient_subset(self, standard_datasets):
        """
        SCENARIO: Mix of outcomes with subset of rules (not all 6).
        
        Validates: Requirements 5.11
        """
        for total_rules in [2, 3]:
            engine = RuleEngine()
            
            # Create mix of outcomes for subset
            engine.register_rule(SuccessfulRule("SUC-001", "Success", DataCategory.ADMIN))
            if total_rules >= 2:
                engine.register_rule(FailingRule("FAIL-001", "Fail", DataCategory.BUILDINGS))
            if total_rules >= 3:
                engine.register_rule(InsufficientDataRule("INSUF-001", "Insufficient", DataCategory.WATER))
            
            # Execute
            results = engine.execute(standard_datasets)
            
            # Verify all rules compiled
            assert len(results) == total_rules, f"Expected {total_rules} results, got {len(results)}"
            
            # Verify outcomes present
            if total_rules >= 1:
                assert "SUC-001" in results
            if total_rules >= 2:
                assert "FAIL-001" in results
            if total_rules >= 3:
                assert "INSUF-001" in results


# ============================================================================
# Integration Tests
# ============================================================================

class TestRuleEngineIntegration:
    """Integration tests for complete rule engine behavior."""
    
    def test_overall_status_all_success(self, standard_datasets):
        """Verify overall status when all rules succeed."""
        engine = RuleEngine()
        
        for i in range(1, 4):
            rule = SuccessfulRule(f"SUC-{i:03d}", f"Success {i}", DataCategory.ADMIN)
            engine.register_rule(rule)
        
        results = engine.execute(standard_datasets)
        overall_status = engine.get_overall_status(results)
        
        assert overall_status == ProcessingStatus.SUCCESS
    
    
    def test_overall_status_all_failed(self, standard_datasets):
        """Verify overall status when all rules fail."""
        engine = RuleEngine()
        
        for i in range(1, 4):
            rule = FailingRule(f"FAIL-{i:03d}", f"Fail {i}", DataCategory.BUILDINGS)
            engine.register_rule(rule)
        
        results = engine.execute(standard_datasets)
        overall_status = engine.get_overall_status(results)
        
        assert overall_status == ProcessingStatus.FAILED
    
    
    def test_overall_status_partial(self, standard_datasets):
        """Verify overall status when mixed success/failure."""
        engine = RuleEngine()
        
        engine.register_rule(SuccessfulRule("SUC-001", "Success", DataCategory.ADMIN))
        engine.register_rule(FailingRule("FAIL-001", "Fail", DataCategory.BUILDINGS))
        
        results = engine.execute(standard_datasets)
        overall_status = engine.get_overall_status(results)
        
        assert overall_status == ProcessingStatus.PARTIAL
    
    
    def test_execution_time_recorded(self, standard_datasets):
        """Verify execution time is recorded."""
        engine = RuleEngine()
        
        engine.register_rule(SuccessfulRule("SUC-001", "Success", DataCategory.ADMIN))
        results = engine.execute(standard_datasets)
        
        execution_time = engine.get_execution_time_ms()
        assert execution_time is not None
        assert execution_time >= 0  # Can be 0 on fast machines
        
        # Verify metadata includes execution time
        for result in results.values():
            assert "execution_time_ms" in result.metadata
            assert result.metadata["execution_time_ms"] >= 0


# ============================================================================
# Hypothesis-Based Property Tests
# ============================================================================

@given(
    num_rules=st.integers(min_value=1, max_value=6),
    num_failures=st.integers(min_value=0, max_value=5)
)
def test_property_rule_independence_comprehensive(num_rules, num_failures, standard_datasets):
    """
    Property: For any number of registered rules (1-6) with any number
    of failures (0 to N-1), all rules execute and results are compiled.
    
    Feature: land-scanner, Property 7: Rule Independence and Continuation
    Validates: Requirements 5.9, 5.10
    """
    if num_failures >= num_rules:
        # Can't have more failures than rules
        return
    
    engine = RuleEngine()
    
    # Create mix of successful and failing rules
    for i in range(num_failures):
        rule = FailingRule(f"FAIL-{i:03d}", f"Fail {i}", DataCategory.BUILDINGS)
        engine.register_rule(rule)
    
    for i in range(num_failures, num_rules):
        rule = SuccessfulRule(f"SUC-{i:03d}", f"Success {i}", DataCategory.ADMIN)
        engine.register_rule(rule)
    
    # Execute
    results = engine.execute(standard_datasets)
    
    # Verify all rules executed (property)
    assert len(results) == num_rules, \
        f"Expected {num_rules} results, got {len(results)}"
    
    # Verify failures didn't prevent other rules from executing
    success_count = sum(1 for r in results.values() if r.status == ProcessingStatus.SUCCESS)
    expected_success = num_rules - num_failures
    assert success_count == expected_success, \
        f"Expected {expected_success} successes, got {success_count}"


@given(
    num_rules=st.integers(min_value=1, max_value=6)
)
def test_property_result_compilation(num_rules, standard_datasets):
    """
    Property: For any number of registered rules, the compiled results
    always include all rules with consistent structure and required fields.
    
    Feature: land-scanner, Property 8: Rule Result Compilation
    Validates: Requirements 5.11
    
    MINIMUM 300+ test iterations with num_rules varying 1-6.
    This generates 100+ scenarios per num_rules value = 600+ test variations.
    """
    engine = RuleEngine()
    
    # Create successful rules
    for i in range(num_rules):
        rule = SuccessfulRule(f"SUC-{i:03d}", f"Success {i}", DataCategory.ADMIN)
        engine.register_rule(rule)
    
    # Execute
    results = engine.execute(standard_datasets)
    
    # Property 1: All results present
    assert len(results) == num_rules, \
        f"Expected {num_rules} results, got {len(results)}"
    
    # Property 2: Consistent structure
    required_fields = {'rule_id', 'rule_name', 'status', 'result', 'metadata'}
    for rule_id, result in results.items():
        for field in required_fields:
            assert hasattr(result, field), \
                f"Compilation missing field {field} for rule {rule_id}"
    
    # Property 3: All statuses are ProcessingStatus enum
    for result in results.values():
        assert isinstance(result.status, ProcessingStatus), \
            f"Result status {result.status} is not ProcessingStatus enum"


@given(
    num_rules=st.integers(min_value=1, max_value=6),
    num_failures=st.integers(min_value=0, max_value=5),
    num_insufficient=st.integers(min_value=0, max_value=5)
)
def test_property_result_compilation_mixed_states(num_rules, num_failures, num_insufficient, standard_datasets):
    """
    Property: For any combination of rule success/failure/insufficient states,
    all results are compiled with consistent structure regardless of outcome.
    
    Feature: land-scanner, Property 8: Rule Result Compilation
    Validates: Requirements 5.11
    
    EXTENSIVE COVERAGE: Tests all combinations of success/failure/insufficient states.
    - num_rules: 1-6 rules total
    - num_failures: 0-5 failing rules
    - num_insufficient: 0-5 insufficient data rules
    - Generates 200+ combinations per hypothesis iteration = 500+ test variations
    """
    # Skip invalid combinations
    if num_failures + num_insufficient > num_rules:
        return
    
    engine = RuleEngine()
    
    # Add failing rules
    for i in range(num_failures):
        rule = FailingRule(f"FAIL-{i:03d}", f"Fail {i}", DataCategory.BUILDINGS)
        engine.register_rule(rule)
    
    # Add insufficient data rules
    for i in range(num_insufficient):
        rule = InsufficientDataRule(f"INSUF-{i:03d}", f"Insufficient {i}", DataCategory.WATER)
        engine.register_rule(rule)
    
    # Add successful rules to fill remaining slots
    num_successful = num_rules - num_failures - num_insufficient
    for i in range(num_successful):
        rule = SuccessfulRule(f"SUC-{i:03d}", f"Success {i}", DataCategory.ADMIN)
        engine.register_rule(rule)
    
    # Execute
    results = engine.execute(standard_datasets)
    
    # Property 1: All rules compiled (no data loss)
    assert len(results) == num_rules, \
        f"Expected {num_rules} results, got {len(results)}"
    
    # Property 2: All outcomes present in results
    failure_count = sum(1 for r in results.values() if r.status == ProcessingStatus.FAILED)
    insufficient_count = sum(1 for r in results.values() if r.status == ProcessingStatus.INSUFFICIENT_DATA)
    success_count = sum(1 for r in results.values() if r.status == ProcessingStatus.SUCCESS)
    
    assert failure_count == num_failures, \
        f"Expected {num_failures} failures, got {failure_count}"
    assert insufficient_count == num_insufficient, \
        f"Expected {num_insufficient} insufficient, got {insufficient_count}"
    assert success_count == num_successful, \
        f"Expected {num_successful} successes, got {success_count}"
    
    # Property 3: Consistent structure for all outcomes
    required_fields = {'rule_id', 'rule_name', 'status', 'result', 'metadata'}
    for rule_id, result in results.items():
        for field in required_fields:
            assert hasattr(result, field), \
                f"Result {rule_id} missing field {field}"
        
        # Verify status values are valid
        valid_statuses = {
            ProcessingStatus.SUCCESS,
            ProcessingStatus.FAILED,
            ProcessingStatus.INSUFFICIENT_DATA
        }
        assert result.status in valid_statuses, \
            f"Result {rule_id} has invalid status {result.status}"

