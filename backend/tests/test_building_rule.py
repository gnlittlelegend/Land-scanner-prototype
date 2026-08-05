"""
Tests for Building Presence Rule (BLD-001)

This test suite validates that the BuildingPresenceRule:
- Correctly processes standardized building data
- Detects presence of buildings in the polygon
- Counts buildings and estimates coverage percentage
- Categorizes building types
- Handles missing building data gracefully
- Returns structured building information
"""

import pytest
from typing import Dict
from unittest.mock import Mock

from backend.rules.building_rule import BuildingPresenceRule
from backend.models.schemas import (
    StandardizedDataset,
    StandardizedFeature,
    Geometry,
    ProcessingStatus,
    DataCategory
)


class TestBuildingPresenceRule:
    """Tests for the Building Presence Rule."""
    
    @pytest.fixture
    def building_rule(self):
        """Create a building presence rule instance."""
        return BuildingPresenceRule()
    
    
    @pytest.fixture
    def sample_building_dataset(self):
        """Create a sample standardized building dataset."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={
                    "name": "Town Hall",
                    "building_type": "civic",
                    "type": "civic",
                    "area": 5000
                },
                source_provider="OSM",
                source_category="buildings"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.15, 0], [0.25, 0], [0.25, 0.1], [0.15, 0.1], [0.15, 0]]]
                ),
                properties={
                    "name": "Residential Building A",
                    "building_type": "residential",
                    "type": "residential",
                    "area": 3000
                },
                source_provider="OSM",
                source_category="buildings"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.3, 0], [0.4, 0], [0.4, 0.1], [0.3, 0.1], [0.3, 0]]]
                ),
                properties={
                    "name": "Commercial Building",
                    "building_type": "commercial",
                    "type": "commercial",
                    "area": 8000
                },
                source_provider="OSM",
                source_category="buildings"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.45, 0], [0.55, 0], [0.55, 0.1], [0.45, 0.1], [0.45, 0]]]
                ),
                properties={
                    "building_type": "residential",
                    "type": "residential",
                    "area": 2500
                },
                source_provider="OSM",
                source_category="buildings"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.6, 0], [0.7, 0], [0.7, 0.1], [0.6, 0.1], [0.6, 0]]]
                ),
                properties={
                    "building_type": "residential",
                    "type": "residential",
                    "area": 3500
                },
                source_provider="OSM",
                source_category="buildings"
            )
        ]
        
        return StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.BUILDINGS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    
    @pytest.fixture
    def empty_building_dataset(self):
        """Create an empty standardized building dataset."""
        return StandardizedDataset(
            features=[],
            source_provider="OSM",
            category=DataCategory.BUILDINGS,
            feature_count=0,
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    
    @pytest.fixture
    def single_building_dataset(self):
        """Create a dataset with a single building."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={
                    "name": "Only Building",
                    "building_type": "residential",
                    "type": "residential",
                    "area": 5000
                },
                source_provider="OSM",
                source_category="buildings"
            )
        ]
        
        return StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.BUILDINGS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    
    def test_building_rule_initialization(self, building_rule):
        """Test that BuildingPresenceRule initializes correctly."""
        assert building_rule.rule_id == "BLD-001"
        assert building_rule.rule_name == "Building Presence Detection"
        assert DataCategory.BUILDINGS in building_rule.required_categories
    
    
    def test_execute_with_valid_data(self, building_rule, sample_building_dataset):
        """Test rule execution with valid building data."""
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        
        result = building_rule.execute(datasets)
        
        # Verify result structure
        assert result.rule_id == "BLD-001"
        assert result.status == ProcessingStatus.SUCCESS
        assert isinstance(result.result, dict)
        assert result.metadata["data_points_used"] == 5
        
        # Verify building information extracted
        building_result = result.result
        assert "buildings_detected" in building_result
        assert building_result["buildings_detected"] is True
        assert "total_building_count" in building_result
        assert building_result["total_building_count"] == 5
        assert "building_types" in building_result
        assert "primary_building_type" in building_result
        assert "infrastructure_present" in building_result
        assert building_result["infrastructure_present"] is True
    
    
    def test_execute_with_empty_data(self, building_rule, empty_building_dataset):
        """Test rule execution with empty building data."""
        datasets = {DataCategory.BUILDINGS: empty_building_dataset}
        
        result = building_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
        assert result.result == {}
    
    
    def test_execute_without_building_dataset(self, building_rule):
        """Test rule execution without building dataset."""
        datasets = {}
        
        result = building_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
    
    
    def test_has_required_data_with_building_data(self, building_rule, sample_building_dataset):
        """Test checking for required data with building data present."""
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        
        assert building_rule.has_required_data(datasets) is True
    
    
    def test_has_required_data_without_building_data(self, building_rule):
        """Test checking for required data without building data."""
        datasets = {}
        
        assert building_rule.has_required_data(datasets) is False
    
    
    def test_has_required_data_with_empty_building_data(self, building_rule, empty_building_dataset):
        """Test checking for required data with empty building data."""
        datasets = {DataCategory.BUILDINGS: empty_building_dataset}
        
        assert building_rule.has_required_data(datasets) is False
    
    
    def test_execute_with_single_building(self, building_rule, single_building_dataset):
        """Test execution with a single building."""
        datasets = {DataCategory.BUILDINGS: single_building_dataset}
        
        result = building_rule.execute(datasets)
        
        # Verify success
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 1
        
        # Verify building detection
        building_result = result.result
        assert building_result["buildings_detected"] is True
        assert building_result["total_building_count"] == 1
        assert building_result["primary_building_type"] == "residential"
    
    
    def test_building_type_distribution(self, building_rule, sample_building_dataset):
        """Test that building types are correctly counted and distributed."""
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        
        result = building_rule.execute(datasets)
        building_result = result.result
        
        # Verify building types
        building_types = building_result["building_types"]
        
        # Should have 3 types: civic, residential, commercial
        assert len(building_types) == 3
        assert "civic" in building_types
        assert "residential" in building_types
        assert "commercial" in building_types
        
        # Verify counts for each type
        assert building_types["civic"]["count"] == 1
        assert building_types["residential"]["count"] == 3
        assert building_types["commercial"]["count"] == 1
        
        # Verify percentages
        assert building_types["civic"]["percentage"] == 20.0
        assert building_types["residential"]["percentage"] == 60.0
        assert building_types["commercial"]["percentage"] == 20.0
    
    
    def test_primary_building_type_detection(self, building_rule, sample_building_dataset):
        """Test that primary building type is correctly identified."""
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        
        result = building_rule.execute(datasets)
        building_result = result.result
        
        # Primary should be residential (3 out of 5)
        assert building_result["primary_building_type"] == "residential"
    
    
    def test_total_building_area_calculation(self, building_rule, sample_building_dataset):
        """Test that total building area is correctly calculated."""
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        
        result = building_rule.execute(datasets)
        building_result = result.result
        
        # Total area should be 5000 + 3000 + 8000 + 2500 + 3500 = 22000
        assert building_result["total_building_area_sqm"] == 22000.0
    
    
    def test_building_density_low(self, building_rule):
        """Test building density categorization for low density."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={
                    "building_type": "residential",
                    "type": "residential"
                },
                source_provider="OSM",
                source_category="buildings"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.BUILDINGS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.BUILDINGS: dataset}
        result = building_rule.execute(datasets)
        
        # With 1 building, density should be low
        assert result.result["building_density_estimate"] == "low"
    
    
    def test_building_density_medium(self, building_rule):
        """Test building density categorization for medium density."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[i*0.01, 0], [i*0.01+0.01, 0], [i*0.01+0.01, 0.1], [i*0.01, 0.1], [i*0.01, 0]]]
                ),
                properties={
                    "building_type": "residential",
                    "type": "residential"
                },
                source_provider="OSM",
                source_category="buildings"
            )
            for i in range(50)  # 50 buildings
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.BUILDINGS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.BUILDINGS: dataset}
        result = building_rule.execute(datasets)
        
        # With 50 buildings, density should be medium
        assert result.result["building_density_estimate"] == "medium"
    
    
    def test_building_density_high(self, building_rule):
        """Test building density categorization for high density."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[i*0.005, 0], [i*0.005+0.005, 0], [i*0.005+0.005, 0.1], [i*0.005, 0.1], [i*0.005, 0]]]
                ),
                properties={
                    "building_type": "residential",
                    "type": "residential"
                },
                source_provider="OSM",
                source_category="buildings"
            )
            for i in range(150)  # 150 buildings
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.BUILDINGS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.BUILDINGS: dataset}
        result = building_rule.execute(datasets)
        
        # With 150 buildings, density should be high
        assert result.result["building_density_estimate"] == "high"
    
    
    def test_execute_with_missing_building_type(self, building_rule):
        """Test execution with features that have missing building_type."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={},  # No building_type
                source_provider="OSM",
                source_category="buildings"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.15, 0], [0.25, 0], [0.25, 0.1], [0.15, 0.1], [0.15, 0]]]
                ),
                properties={"building_type": "commercial"},
                source_provider="OSM",
                source_category="buildings"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.BUILDINGS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.BUILDINGS: dataset}
        result = building_rule.execute(datasets)
        
        # Should still succeed with partial data
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 2
        assert result.result["total_building_count"] == 2
    
    
    def test_execute_with_named_buildings(self, building_rule, sample_building_dataset):
        """Test that named buildings are tracked."""
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        
        result = building_rule.execute(datasets)
        building_result = result.result
        
        # Check that civic building name is captured
        building_types = building_result["building_types"]
        assert building_types["civic"]["count"] == 1
    
    
    def test_execute_with_area_calculation(self, building_rule):
        """Test area calculation with various building areas."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={
                    "building_type": "residential",
                    "area": 1000.5
                },
                source_provider="OSM",
                source_category="buildings"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.15, 0], [0.25, 0], [0.25, 0.1], [0.15, 0.1], [0.15, 0]]]
                ),
                properties={
                    "building_type": "commercial",
                    "area": 2500.75
                },
                source_provider="OSM",
                source_category="buildings"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.BUILDINGS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.BUILDINGS: dataset}
        result = building_rule.execute(datasets)
        
        # Total area should be 1000.5 + 2500.75 = 3501.25
        expected_area = round(1000.5 + 2500.75, 2)
        assert result.result["total_building_area_sqm"] == expected_area
    
    
    def test_result_includes_all_required_fields(self, building_rule, sample_building_dataset):
        """Test that result includes all required output fields."""
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        
        result = building_rule.execute(datasets)
        building_result = result.result
        
        # Verify all required fields present
        required_fields = [
            "buildings_detected",
            "total_building_count",
            "building_types",
            "primary_building_type",
            "total_building_area_sqm",
            "building_density_estimate",
            "infrastructure_present"
        ]
        
        for field in required_fields:
            assert field in building_result, f"Missing field: {field}"
    
    
    def test_metadata_preserved(self, building_rule, sample_building_dataset):
        """Test that metadata is correctly preserved in results."""
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        
        result = building_rule.execute(datasets)
        
        # Verify metadata structure
        assert "data_points_used" in result.metadata
        assert result.metadata["data_points_used"] == 5
    
    
    def test_rule_result_structure(self, building_rule, sample_building_dataset):
        """Test that RuleResult has correct structure."""
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        
        result = building_rule.execute(datasets)
        
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


class TestBuildingRuleWithRuleEngine:
    """Tests for BuildingPresenceRule integration with RuleEngine."""
    
    def test_building_rule_with_engine(self, sample_building_dataset):
        """Test BuildingPresenceRule works correctly within Rule Engine."""
        from backend.rules.rule_engine import RuleEngine
        
        engine = RuleEngine()
        engine.register_rule(BuildingPresenceRule())
        
        datasets = {DataCategory.BUILDINGS: sample_building_dataset}
        results = engine.execute(datasets)
        
        # Verify rule executed
        assert "BLD-001" in results
        result = results["BLD-001"]
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["buildings_detected"] is True
        assert result.result["total_building_count"] == 5


@pytest.fixture
def sample_building_dataset():
    """Create a sample standardized building dataset for module-level use."""
    features = [
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
            ),
            properties={
                "name": "Town Hall",
                "building_type": "civic",
                "type": "civic",
                "area": 5000
            },
            source_provider="OSM",
            source_category="buildings"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.15, 0], [0.25, 0], [0.25, 0.1], [0.15, 0.1], [0.15, 0]]]
            ),
            properties={
                "name": "Residential Building A",
                "building_type": "residential",
                "type": "residential",
                "area": 3000
            },
            source_provider="OSM",
            source_category="buildings"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.3, 0], [0.4, 0], [0.4, 0.1], [0.3, 0.1], [0.3, 0]]]
            ),
            properties={
                "name": "Commercial Building",
                "building_type": "commercial",
                "type": "commercial",
                "area": 8000
            },
            source_provider="OSM",
            source_category="buildings"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.45, 0], [0.55, 0], [0.55, 0.1], [0.45, 0.1], [0.45, 0]]]
            ),
            properties={
                "building_type": "residential",
                "type": "residential",
                "area": 2500
            },
            source_provider="OSM",
            source_category="buildings"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.6, 0], [0.7, 0], [0.7, 0.1], [0.6, 0.1], [0.6, 0]]]
            ),
            properties={
                "building_type": "residential",
                "type": "residential",
                "area": 3500
            },
            source_provider="OSM",
            source_category="buildings"
        )
    ]
    
    return StandardizedDataset(
        features=features,
        source_provider="OSM",
        category=DataCategory.BUILDINGS,
        feature_count=len(features),
        crs="EPSG:4326",
        metadata={
            "source": "OpenStreetMap",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    )
