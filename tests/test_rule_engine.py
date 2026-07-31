"""
Property-based tests for Rule Engine module.

Tests validate:
- Property 7: Rule Independence and Continuation
- Property 8: Rule Result Compilation
"""

import pytest
from hypothesis import given, strategies as st
from datetime import datetime
from typing import Dict, Any, List

from backend.models.schemas import (
    StandardizedDataset,
    Feature,
    RuleResult,
    ProcessingStatus,
    DataCategory
)
from backend.rules import (
    RuleEngine,
    Rule,
    AdminBoundaryRule,
    LandCoverRule,
    BuildingPresenceRule,
    RoadNetworkRule,
    WaterFeaturesRule,
    ElevationRule
)


class FailingRule(Rule):
    """Test rule that simulates a failure."""
    
    def __init__(self):
        super().__init__(
            rule_id="FAIL-001",
            rule_name="Failing Test Rule",
            required_categories=[DataCategory.ADMIN]
        )
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        """Simulate a failure."""
        raise Exception("Intentional test failure")


class PassingRule(Rule):
    """Test rule that always succeeds."""
    
    def __init__(self, rule_id: str = "PASS-001"):
        super().__init__(
            rule_id=rule_id,
            rule_name=f"Passing Test Rule {rule_id}",
            required_categories=[DataCategory.ADMIN]
        )
    
    def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
        """Return success."""
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            status=ProcessingStatus.SUCCESS,
            result={"test_result": "passed"},
            metadata={"data_points_used": 1}
        )


def create_test_standardized_dataset(
    category: DataCategory,
    feature_count: int = 1
) -> StandardizedDataset:
    """Create a test standardized dataset."""
    features = []
    for i in range(feature_count):
        features.append(Feature(
            id=f"feature_{i}",
            geometry={"type": "Point", "coordinates": [0, 0]},
            properties={"test_prop": f"value_{i}"}
        ))
    
    return StandardizedDataset(
        category=category,
        source_provider="test_provider",
        features=features,
        metadata={
            "timestamp": datetime.utcnow(),
            "crs": "EPSG:4326",
            "record_count": feature_count
        }
    )


# Feature strategy for generating test data
@st.composite
def generate_test_standardized_datasets(draw) -> Dict[DataCategory, StandardizedDataset]:
    """Generate a test standardized dataset collection."""
    return {
        DataCategory.ADMIN: create_test_standardized_dataset(DataCategory.ADMIN, draw(st.integers(min_value=1, max_value=5))),
        DataCategory.BUILDINGS: create_test_standardized_dataset(DataCategory.BUILDINGS, draw(st.integers(min_value=0, max_value=10))),
        DataCategory.LAND_COVER: create_test_standardized_dataset(DataCategory.LAND_COVER, draw(st.integers(min_value=0, max_value=5))),
    }


class TestRuleIndependenceAndContinuation:
    """
    Property 7: Rule Independence and Continuation
    
    For any set of rules where one rule fails or encounters insufficient data,
    the remaining rules should continue executing independently and produce their
    results without cascading failure.
    """
    
    @given(generate_test_standardized_datasets())
    def test_engine_continues_despite_rule_failure(self, datasets):
        """
        Test that Rule Engine continues executing remaining rules when one fails.
        **Feature: land-scanner, Property 7: Rule Independence and Continuation**
        **Validates: Requirements 5.9, 5.10**
        """
        engine = RuleEngine()
        
        # Register mix of passing and failing rules
        engine.register_rule(PassingRule("PASS-001"))
        engine.register_rule(FailingRule())
        engine.register_rule(PassingRule("PASS-002"))
        
        # Execute engine
        results = engine.execute(datasets)
        
        # Verify all rules executed
        assert len(results) == 3, "All rules should execute regardless of failures"
        
        # Verify passing rules produced results
        assert "PASS-001" in results
        assert "PASS-002" in results
        
        # Verify passing rules succeeded
        assert results["PASS-001"].status == ProcessingStatus.SUCCESS
        assert results["PASS-002"].status == ProcessingStatus.SUCCESS
        
        # Verify failing rule was handled
        assert "FAIL-001" in results
        assert results["FAIL-001"].status == ProcessingStatus.FAILED
    
    @given(generate_test_standardized_datasets())
    def test_insufficient_data_does_not_cascade(self, datasets):
        """
        Test that insufficient data in one rule doesn't prevent others from executing.
        **Feature: land-scanner, Property 7: Rule Independence and Continuation**
        **Validates: Requirements 5.9, 5.10**
        """
        engine = RuleEngine()
        
        # Create a rule requiring data we don't have
        class InsufficientDataRule(Rule):
            def __init__(self):
                super().__init__(
                    rule_id="INSUF-001",
                    rule_name="Insufficient Data Rule",
                    required_categories=[DataCategory.ELEVATION]  # Not in test data
                )
            
            def execute(self, standardized_datasets: Dict[DataCategory, StandardizedDataset]) -> RuleResult:
                return RuleResult(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    status=ProcessingStatus.INSUFFICIENT_DATA,
                    result={},
                    metadata={}
                )
        
        # Register rules
        engine.register_rule(PassingRule("PASS-001"))
        engine.register_rule(InsufficientDataRule())
        engine.register_rule(PassingRule("PASS-002"))
        
        # Execute
        results = engine.execute(datasets)
        
        # Verify all executed despite insufficient data
        assert len(results) == 3
        assert results["PASS-001"].status == ProcessingStatus.SUCCESS
        assert results["PASS-002"].status == ProcessingStatus.SUCCESS
        assert results["INSUF-001"].status == ProcessingStatus.INSUFFICIENT_DATA


class TestRuleResultCompilation:
    """
    Property 8: Rule Result Compilation
    
    For any Rule Engine execution, regardless of individual rule outcomes,
    the system should compile all rule results (success, failure, insufficient_data,
    skipped) into a single structured analysis output.
    """
    
    @given(generate_test_standardized_datasets())
    def test_all_results_compiled_successfully(self, datasets):
        """
        Test that all rule results are compiled into output.
        **Feature: land-scanner, Property 8: Rule Result Compilation**
        **Validates: Requirements 5.11**
        """
        engine = RuleEngine()
        
        # Create rules with different outcome statuses
        class SuccessRule(Rule):
            def __init__(self):
                super().__init__("SUCCESS-001", "Success Rule", [DataCategory.ADMIN])
            
            def execute(self, standardized_datasets):
                return RuleResult(
                    rule_id="SUCCESS-001",
                    rule_name="Success Rule",
                    status=ProcessingStatus.SUCCESS,
                    result={"data": "success"},
                    metadata={}
                )
        
        class FailedRule(Rule):
            def __init__(self):
                super().__init__("FAILED-001", "Failed Rule", [DataCategory.ADMIN])
            
            def execute(self, standardized_datasets):
                raise Exception("Simulated failure")
        
        class SkippedRule(Rule):
            def __init__(self):
                super().__init__("SKIP-001", "Skipped Rule", [DataCategory.ELEVATION])  # Not available
            
            def execute(self, standardized_datasets):
                return RuleResult(
                    rule_id="SKIP-001",
                    rule_name="Skipped Rule",
                    status=ProcessingStatus.SKIPPED,
                    result={},
                    metadata={}
                )
        
        engine.register_rules([SuccessRule(), FailedRule(), SkippedRule()])
        
        # Execute
        results = engine.execute(datasets)
        
        # Verify all results compiled
        assert len(results) == 3, "All rule results must be compiled"
        assert "SUCCESS-001" in results
        assert "FAILED-001" in results
        assert "SKIP-001" in results
        
        # Verify each has required result structure
        for rule_id, result in results.items():
            assert isinstance(result, RuleResult)
            assert result.rule_id is not None
            assert result.rule_name is not None
            assert result.status is not None
            assert result.result is not None
            assert result.metadata is not None
    
    @given(st.integers(min_value=1, max_value=10))
    def test_no_data_loss_in_compilation(self, rule_count: int):
        """
        Test that no results are lost during compilation.
        **Feature: land-scanner, Property 8: Rule Result Compilation**
        **Validates: Requirements 5.11**
        """
        engine = RuleEngine()
        
        # Register N passing rules
        for i in range(rule_count):
            engine.register_rule(PassingRule(f"PASS-{i:03d}"))
        
        # Create test data
        datasets = {
            DataCategory.ADMIN: create_test_standardized_dataset(DataCategory.ADMIN, 1)
        }
        
        # Execute
        results = engine.execute(datasets)
        
        # Verify no data loss - all rules have results
        assert len(results) == rule_count, f"Expected {rule_count} results, got {len(results)}"
        
        # Verify each rule_id is present
        for i in range(rule_count):
            assert f"PASS-{i:03d}" in results


class TestRuleEngineIntegration:
    """Integration tests for Rule Engine with actual rule implementations."""
    
    def test_actual_rules_execute_independently(self):
        """
        Test that actual rule implementations execute independently.
        """
        engine = RuleEngine()
        
        # Register actual rules
        engine.register_rules([
            AdminBoundaryRule(),
            LandCoverRule(),
            BuildingPresenceRule(),
            RoadNetworkRule(),
            WaterFeaturesRule(),
            ElevationRule(),
        ])
        
        # Create test data with all categories
        datasets = {
            DataCategory.ADMIN: create_test_standardized_dataset(DataCategory.ADMIN, 2),
            DataCategory.LAND_COVER: create_test_standardized_dataset(DataCategory.LAND_COVER, 3),
            DataCategory.BUILDINGS: create_test_standardized_dataset(DataCategory.BUILDINGS, 5),
            DataCategory.ROADS: create_test_standardized_dataset(DataCategory.ROADS, 4),
            DataCategory.WATER: create_test_standardized_dataset(DataCategory.WATER, 2),
            DataCategory.ELEVATION: create_test_standardized_dataset(DataCategory.ELEVATION, 10),
        }
        
        # Execute
        results = engine.execute(datasets)
        
        # Verify all rules executed
        assert len(results) == 6
        assert all(rule_id in results for rule_id in ["ADM-001", "LC-001", "BLD-001", "RD-001", "WT-001", "ELV-001"])
        
        # Verify all succeeded
        assert all(r.status == ProcessingStatus.SUCCESS for r in results.values())
    
    def test_missing_data_for_some_rules(self):
        """
        Test that rules correctly mark insufficient data when required data missing.
        """
        engine = RuleEngine()
        
        # Register all rules
        engine.register_rules([
            AdminBoundaryRule(),
            LandCoverRule(),
            BuildingPresenceRule(),
        ])
        
        # Create minimal test data (only admin)
        datasets = {
            DataCategory.ADMIN: create_test_standardized_dataset(DataCategory.ADMIN, 1),
        }
        
        # Execute
        results = engine.execute(datasets)
        
        # Admin should succeed
        assert results["ADM-001"].status == ProcessingStatus.SUCCESS
        
        # Others should be insufficient
        assert results["LC-001"].status == ProcessingStatus.INSUFFICIENT_DATA
        assert results["BLD-001"].status == ProcessingStatus.INSUFFICIENT_DATA
    
    def test_engine_overall_status(self):
        """Test that engine correctly determines overall status."""
        # All succeed
        engine = RuleEngine()
        engine.register_rules([PassingRule("PASS-001"), PassingRule("PASS-002")])
        datasets = {DataCategory.ADMIN: create_test_standardized_dataset(DataCategory.ADMIN, 1)}
        results = engine.execute(datasets)
        assert engine.get_overall_status(results) == ProcessingStatus.SUCCESS
        
        # Mixed results
        engine = RuleEngine()
        engine.register_rules([PassingRule("PASS-001"), FailingRule()])
        results = engine.execute(datasets)
        assert engine.get_overall_status(results) == ProcessingStatus.PARTIAL
