"""
Tests for Administrative Boundary Rule (ADM-001)

This test suite validates that the AdministrativeRule:
- Correctly processes standardized admin boundary data
- Extracts country, state, district information
- Uses spatial intersection to determine administrative regions
- Handles missing admin data gracefully
- Returns structured administrative information
"""

import pytest
from typing import Dict
from unittest.mock import Mock

from backend.rules.admin_rule import AdminBoundaryRule
from backend.models.schemas import (
    StandardizedDataset,
    StandardizedFeature,
    Geometry,
    ProcessingStatus,
    DataCategory
)


class TestAdminBoundaryRule:
    """Tests for the Administrative Boundary Rule."""
    
    @pytest.fixture
    def admin_rule(self):
        """Create an administrative rule instance."""
        return AdminBoundaryRule()
    
    
    @pytest.fixture
    def sample_admin_dataset(self):
        """Create a sample standardized admin dataset."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "name": "France",
                    "country": "France",
                    "admin_level": "2"
                },
                source_provider="OSM",
                source_category="admin"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8], [0.2, 0.2]]]
                ),
                properties={
                    "name": "Île-de-France",
                    "country": "France",
                    "state": "Île-de-France",
                    "admin_level": "4"
                },
                source_provider="OSM",
                source_category="admin"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.3, 0.3], [0.7, 0.3], [0.7, 0.7], [0.3, 0.7], [0.3, 0.3]]]
                ),
                properties={
                    "name": "Paris",
                    "country": "France",
                    "state": "Île-de-France",
                    "district": "Paris",
                    "admin_level": "6"
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
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    
    @pytest.fixture
    def empty_admin_dataset(self):
        """Create an empty standardized admin dataset."""
        return StandardizedDataset(
            features=[],
            source_provider="OSM",
            category=DataCategory.ADMIN,
            feature_count=0,
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    
    def test_admin_rule_initialization(self, admin_rule):
        """Test that AdminBoundaryRule initializes correctly."""
        assert admin_rule.rule_id == "ADM-001"
        assert admin_rule.rule_name == "Administrative Boundary Detection"
        assert DataCategory.ADMIN in admin_rule.required_categories
    
    
    def test_execute_with_valid_data(self, admin_rule, sample_admin_dataset):
        """Test rule execution with valid administrative data."""
        datasets = {DataCategory.ADMIN: sample_admin_dataset}
        
        result = admin_rule.execute(datasets)
        
        # Verify result structure
        assert result.rule_id == "ADM-001"
        assert result.status == ProcessingStatus.SUCCESS
        assert isinstance(result.result, dict)
        assert result.metadata["data_points_used"] == 3
        
        # Verify administrative information extracted
        admin_result = result.result
        assert "administrative_regions" in admin_result
        assert "country" in admin_result
        assert "state" in admin_result
        assert "district" in admin_result
        
        # Verify countries extracted
        assert "France" in admin_result["all_countries"]
        
        # Verify administrative regions
        regions = admin_result["administrative_regions"]
        assert len(regions) >= 1
        assert any(r["name"] == "France" for r in regions)
    
    
    def test_execute_with_empty_data(self, admin_rule, empty_admin_dataset):
        """Test rule execution with empty administrative data."""
        datasets = {DataCategory.ADMIN: empty_admin_dataset}
        
        result = admin_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
        assert result.result == {}
    
    
    def test_execute_without_admin_dataset(self, admin_rule):
        """Test rule execution without admin dataset."""
        datasets = {}
        
        result = admin_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
    
    
    def test_has_required_data_with_admin_data(self, admin_rule, sample_admin_dataset):
        """Test checking for required data with admin data present."""
        datasets = {DataCategory.ADMIN: sample_admin_dataset}
        
        assert admin_rule.has_required_data(datasets) is True
    
    
    def test_has_required_data_without_admin_data(self, admin_rule):
        """Test checking for required data without admin data."""
        datasets = {}
        
        assert admin_rule.has_required_data(datasets) is False
    
    
    def test_has_required_data_with_empty_admin_data(self, admin_rule, empty_admin_dataset):
        """Test checking for required data with empty admin data."""
        datasets = {DataCategory.ADMIN: empty_admin_dataset}
        
        assert admin_rule.has_required_data(datasets) is False
    
    
    def test_execute_with_missing_properties(self, admin_rule):
        """Test execution with features that have missing properties."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={},  # Empty properties
                source_provider="OSM",
                source_category="admin"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8], [0.2, 0.2]]]
                ),
                properties={"country": "France"},  # Only country
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
        
        datasets = {DataCategory.ADMIN: dataset}
        result = admin_rule.execute(datasets)
        
        # Should still succeed with partial data
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 2
        assert "France" in result.result["all_countries"]
    
    
    def test_execute_with_multiple_countries(self, admin_rule):
        """Test execution with features from multiple countries."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={"country": "France"},
                source_provider="OSM",
                source_category="admin"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[1.1, 0], [2, 0], [2, 1], [1.1, 1], [1.1, 0]]]
                ),
                properties={"country": "Germany"},
                source_provider="OSM",
                source_category="admin"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[2.1, 0], [3, 0], [3, 1], [2.1, 1], [2.1, 0]]]
                ),
                properties={"country": "Italy"},
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
        
        datasets = {DataCategory.ADMIN: dataset}
        result = admin_rule.execute(datasets)
        
        # Should succeed with multiple countries
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 3
        assert len(result.result["all_countries"]) == 3
        assert "France" in result.result["all_countries"]
        assert "Germany" in result.result["all_countries"]
        assert "Italy" in result.result["all_countries"]
    
    
    def test_execute_extracts_admin_hierarchy(self, admin_rule, sample_admin_dataset):
        """Test that execution correctly extracts hierarchical admin levels."""
        datasets = {DataCategory.ADMIN: sample_admin_dataset}
        
        result = admin_rule.execute(datasets)
        
        # Verify all levels extracted
        admin_result = result.result
        
        # Country level (admin_level 2)
        assert "France" in admin_result["all_countries"]
        
        # State level (admin_level 4)
        assert "Île-de-France" in admin_result["all_states"]
        
        # District level (admin_level 6)
        assert "Paris" in admin_result["all_districts"]
    
    
    def test_result_includes_first_values(self, admin_rule, sample_admin_dataset):
        """Test that result includes first country, state, district."""
        datasets = {DataCategory.ADMIN: sample_admin_dataset}
        
        result = admin_rule.execute(datasets)
        admin_result = result.result
        
        # Verify first values are extracted
        assert admin_result["country"] is not None
        assert admin_result["country"] == "France"
        assert admin_result["state"] == "Île-de-France"
        assert admin_result["district"] == "Paris"
    
    
    def test_metadata_preserved(self, admin_rule, sample_admin_dataset):
        """Test that metadata is correctly preserved in results."""
        datasets = {DataCategory.ADMIN: sample_admin_dataset}
        
        result = admin_rule.execute(datasets)
        
        # Verify metadata structure
        assert "data_points_used" in result.metadata
        assert result.metadata["data_points_used"] == 3
        assert "execution_time_ms" not in result.metadata  # Added by Rule Engine
    
    
    def test_rule_result_structure(self, admin_rule, sample_admin_dataset):
        """Test that RuleResult has correct structure."""
        datasets = {DataCategory.ADMIN: sample_admin_dataset}
        
        result = admin_rule.execute(datasets)
        
        # Verify RuleResult structure
        assert hasattr(result, 'rule_id')
        assert hasattr(result, 'rule_name')
        assert hasattr(result, 'status')
        assert hasattr(result, 'result')
        assert hasattr(result, 'metadata')
        
        # Verify types
        assert isinstance(result.rule_id, str)
        assert isinstance(result.rule_name, str)
        assert isinstance(result.status, ProcessingStatus)
        assert isinstance(result.result, dict)
        assert isinstance(result.metadata, dict)


class TestAdminRuleWithRuleEngine:
    """Tests for AdminBoundaryRule integration with RuleEngine."""
    
    def test_admin_rule_with_engine(self, sample_admin_dataset):
        """Test AdminBoundaryRule works correctly within Rule Engine."""
        from backend.rules.rule_engine import RuleEngine
        
        engine = RuleEngine()
        engine.register_rule(AdminBoundaryRule())
        
        datasets = {DataCategory.ADMIN: sample_admin_dataset}
        results = engine.execute(datasets)
        
        # Verify rule executed
        assert "ADM-001" in results
        result = results["ADM-001"]
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["country"] == "France"


@pytest.fixture
def sample_admin_dataset():
    """Create a sample standardized admin dataset for module-level use."""
    features = [
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            ),
            properties={
                "name": "France",
                "country": "France",
                "admin_level": "2"
            },
            source_provider="OSM",
            source_category="admin"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8], [0.2, 0.2]]]
            ),
            properties={
                "name": "Île-de-France",
                "country": "France",
                "state": "Île-de-France",
                "admin_level": "4"
            },
            source_provider="OSM",
            source_category="admin"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.3, 0.3], [0.7, 0.3], [0.7, 0.7], [0.3, 0.7], [0.3, 0.3]]]
            ),
            properties={
                "name": "Paris",
                "country": "France",
                "state": "Île-de-France",
                "district": "Paris",
                "admin_level": "6"
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
            "timestamp": "2024-01-15T10:30:00Z"
        }
    )
