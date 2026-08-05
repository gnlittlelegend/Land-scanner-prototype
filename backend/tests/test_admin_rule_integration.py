"""
Integration tests for Administrative Boundary Rule with the full pipeline.

This test suite validates that the AdminBoundaryRule:
- Works correctly within the Rule Engine
- Processes real standardized administrative data
- Returns results compatible with the output generation pipeline
- Handles all expected data states
"""

import pytest
from typing import Dict

from backend.rules.admin_rule import AdminBoundaryRule
from backend.rules.rule_engine import RuleEngine
from backend.models.schemas import (
    StandardizedDataset,
    StandardizedFeature,
    Geometry,
    ProcessingStatus,
    DataCategory
)


class TestAdminRuleIntegration:
    """Integration tests for AdminBoundaryRule in the full pipeline."""
    
    @pytest.fixture
    def real_standardized_admin_data(self):
        """
        Create a realistic standardized administrative dataset
        that mirrors what would come from the Data Standardizer.
        """
        features = [
            # Country level (admin_level 2)
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[
                        [-5.26, 41.26],
                        [8.23, 41.26],
                        [8.23, 51.09],
                        [-5.26, 51.09],
                        [-5.26, 41.26]
                    ]]
                ),
                properties={
                    "name": "France",
                    "country": "France",
                    "admin_level": "2",
                    "boundary": "administrative",
                    "wikidata": "Q142"
                },
                source_provider="OSM",
                source_category="admin"
            ),
            # State/Region level (admin_level 4)
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[
                        [2.38, 48.86],
                        [2.58, 48.86],
                        [2.58, 49.06],
                        [2.38, 49.06],
                        [2.38, 48.86]
                    ]]
                ),
                properties={
                    "name": "Île-de-France",
                    "country": "France",
                    "state": "Île-de-France",
                    "admin_level": "4",
                    "boundary": "administrative",
                    "wikidata": "Q12130"
                },
                source_provider="OSM",
                source_category="admin"
            ),
            # City/District level (admin_level 6)
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[
                        [2.36, 48.86],
                        [2.40, 48.86],
                        [2.40, 48.90],
                        [2.36, 48.90],
                        [2.36, 48.86]
                    ]]
                ),
                properties={
                    "name": "Paris",
                    "country": "France",
                    "state": "Île-de-France",
                    "district": "Paris",
                    "admin_level": "6",
                    "boundary": "administrative",
                    "wikidata": "Q90"
                },
                source_provider="OSM",
                source_category="admin"
            )
        ]
        
        return StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ADMIN,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z",
                "provider_version": "2024-01",
                "bbox": [-5.26, 41.26, 8.23, 51.09]
            }
        )
    
    
    def test_admin_rule_executes_with_rule_engine(self, real_standardized_admin_data):
        """
        Test that AdminBoundaryRule executes correctly within RuleEngine.
        
        Validates: Requirements 5.8
        """
        # Create rule engine and register admin rule
        engine = RuleEngine()
        engine.register_rule(AdminBoundaryRule())
        
        # Execute with standardized admin data
        datasets = {DataCategory.ADMIN: real_standardized_admin_data}
        results = engine.execute(datasets)
        
        # Verify rule executed
        assert "ADM-001" in results
        admin_result = results["ADM-001"]
        
        # Verify result structure
        assert admin_result.rule_id == "ADM-001"
        assert admin_result.status == ProcessingStatus.SUCCESS
        assert admin_result.result is not None
        assert isinstance(admin_result.result, dict)
        
        # Verify administrative information extracted
        assert "administrative_regions" in admin_result.result
        assert "country" in admin_result.result
        assert "state" in admin_result.result
        assert "district" in admin_result.result
        
        # Verify values populated
        assert admin_result.result["country"] == "France"
        assert admin_result.result["state"] == "Île-de-France"
        assert admin_result.result["district"] == "Paris"
    
    
    def test_admin_rule_output_compatible_with_analysis_response(self, real_standardized_admin_data):
        """
        Test that admin rule output is compatible with AnalysisResponse format.
        
        The output should be JSON-serializable and include expected fields.
        """
        # Create and execute rule
        rule = AdminBoundaryRule()
        datasets = {DataCategory.ADMIN: real_standardized_admin_data}
        result = rule.execute(datasets)
        
        # Verify result is JSON-serializable
        import json
        try:
            json_str = json.dumps({
                "rule_id": result.rule_id,
                "rule_name": result.rule_name,
                "status": result.status.value,
                "result": result.result,
                "metadata": result.metadata
            })
            # If we get here, it's serializable
            assert json_str is not None
        except TypeError as e:
            pytest.fail(f"Admin rule result not JSON-serializable: {e}")
        
        # Verify result contains expected analysis fields
        admin_info = result.result
        assert admin_info.get("country") is not None or len(admin_info.get("all_countries", [])) == 0
        assert isinstance(admin_info.get("all_countries", []), list)
        assert isinstance(admin_info.get("all_states", []), list)
        assert isinstance(admin_info.get("all_districts", []), list)
    
    
    def test_admin_rule_handles_partial_administrative_data(self):
        """
        Test that admin rule handles real-world scenario where admin data might be incomplete.
        
        In real scenarios, admin boundaries might not always have all hierarchy levels.
        """
        # Create incomplete admin dataset (only country and state, no district)
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[-5.26, 41.26], [8.23, 41.26], [8.23, 51.09], [-5.26, 51.09], [-5.26, 41.26]]]
                ),
                properties={"name": "France", "country": "France", "admin_level": "2"},
                source_provider="OSM",
                source_category="admin"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[
                        [2.38, 48.86], [2.58, 48.86], [2.58, 49.06], [2.38, 49.06], [2.38, 48.86]
                    ]]
                ),
                properties={"name": "Île-de-France", "country": "France", "state": "Île-de-France", "admin_level": "4"},
                source_provider="OSM",
                source_category="admin"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ADMIN,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        # Execute rule
        rule = AdminBoundaryRule()
        datasets = {DataCategory.ADMIN: dataset}
        result = rule.execute(datasets)
        
        # Should still succeed
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["country"] == "France"
        assert result.result["state"] == "Île-de-France"
        assert result.result["district"] is None  # No district provided
    
    
    def test_admin_rule_with_multiple_providers(self):
        """
        Test that admin rule works when other datasets are available but empty.
        
        This simulates the real scenario where some providers succeed and others fail.
        """
        # Create standardized admin data
        admin_features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[-5.26, 41.26], [8.23, 41.26], [8.23, 51.09], [-5.26, 51.09], [-5.26, 41.26]]]
                ),
                properties={"name": "France", "country": "France", "admin_level": "2"},
                source_provider="OSM",
                source_category="admin"
            )
        ]
        
        admin_dataset = StandardizedDataset(
            features=admin_features,
            source_provider="OSM",
            category=DataCategory.ADMIN,
            feature_count=len(admin_features),
            crs="EPSG:4326",
            metadata={}
        )
        
        # Create empty datasets for other categories
        other_datasets = {}
        for category in [DataCategory.BUILDINGS, DataCategory.ROADS, DataCategory.WATER, 
                         DataCategory.ELEVATION, DataCategory.LAND_COVER]:
            other_datasets[category] = StandardizedDataset(
                features=[],
                source_provider="unavailable",
                category=category,
                feature_count=0,
                crs="EPSG:4326",
                metadata={"reason": "provider_unavailable"}
            )
        
        # Execute with mixed dataset availability
        datasets = {DataCategory.ADMIN: admin_dataset}
        datasets.update(other_datasets)
        
        rule = AdminBoundaryRule()
        result = rule.execute(datasets)
        
        # Admin rule should still work despite other providers being empty
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["country"] == "France"
    
    
    def test_admin_rule_idempotence(self, real_standardized_admin_data):
        """
        Test that executing admin rule multiple times produces identical results (idempotence).
        
        Property: For the same input data, the rule should always produce the same output.
        """
        rule = AdminBoundaryRule()
        datasets = {DataCategory.ADMIN: real_standardized_admin_data}
        
        # Execute multiple times
        result1 = rule.execute(datasets)
        result2 = rule.execute(datasets)
        result3 = rule.execute(datasets)
        
        # Results should be identical
        assert result1.status == result2.status == result3.status
        assert result1.result == result2.result == result3.result
        assert result1.result["country"] == result2.result["country"] == result3.result["country"]


class TestAdminRuleWithOtherRules:
    """Test AdminBoundaryRule alongside other rules in the engine."""
    
    def test_admin_rule_executes_independently_with_other_rules(self, real_standardized_admin_data):
        """
        Test that AdminBoundaryRule executes independently and doesn't affect other rules.
        """
        from backend.tests.test_rule_engine_property import SuccessfulRule, FailingRule
        
        # Create engine with multiple rules
        engine = RuleEngine()
        engine.register_rule(AdminBoundaryRule())
        
        # Create successful rule with no required categories (so it always has data)
        successful_rule = SuccessfulRule("TEST-001", "Test Rule 1", DataCategory.BUILDINGS)
        successful_rule.required_categories = []  # Override to have no required categories
        engine.register_rule(successful_rule)
        
        # Create failing rule with no required categories
        failing_rule = FailingRule("TEST-002", "Test Rule 2", DataCategory.WATER)
        failing_rule.required_categories = []  # Override to have no required categories
        engine.register_rule(failing_rule)
        
        # Execute
        datasets = {DataCategory.ADMIN: real_standardized_admin_data}
        results = engine.execute(datasets)
        
        # Verify all rules were executed
        assert len(results) == 3
        assert "ADM-001" in results
        assert "TEST-001" in results
        assert "TEST-002" in results
        
        # Verify admin rule succeeded
        assert results["ADM-001"].status == ProcessingStatus.SUCCESS
        
        # Verify other rule statuses aren't affected by admin rule
        assert results["TEST-001"].status == ProcessingStatus.SUCCESS
        assert results["TEST-002"].status == ProcessingStatus.FAILED
    
    
    @pytest.fixture
    def real_standardized_admin_data(self):
        """Fixture for real admin data."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[
                        [-5.26, 41.26],
                        [8.23, 41.26],
                        [8.23, 51.09],
                        [-5.26, 51.09],
                        [-5.26, 41.26]
                    ]]
                ),
                properties={
                    "name": "France",
                    "country": "France",
                    "admin_level": "2",
                },
                source_provider="OSM",
                source_category="admin"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[
                        [2.38, 48.86],
                        [2.58, 48.86],
                        [2.58, 49.06],
                        [2.38, 49.06],
                        [2.38, 48.86]
                    ]]
                ),
                properties={
                    "name": "Île-de-France",
                    "country": "France",
                    "state": "Île-de-France",
                    "admin_level": "4",
                },
                source_provider="OSM",
                source_category="admin"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[
                        [2.36, 48.86],
                        [2.40, 48.86],
                        [2.40, 48.90],
                        [2.36, 48.90],
                        [2.36, 48.86]
                    ]]
                ),
                properties={
                    "name": "Paris",
                    "country": "France",
                    "state": "Île-de-France",
                    "district": "Paris",
                    "admin_level": "6",
                },
                source_provider="OSM",
                source_category="admin"
            )
        ]
        
        return StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ADMIN,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z",
            }
        )
