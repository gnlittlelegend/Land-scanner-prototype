"""
Tests for Road Network Rule (RD-001)

This test suite validates that the RoadNetworkRule:
- Correctly processes standardized road data
- Detects road access within the polygon area
- Categorizes road types present
- Estimates road accessibility
- Handles missing road data gracefully
- Returns structured road information
"""

import pytest
from typing import Dict
from unittest.mock import Mock

from backend.rules.road_rule import RoadNetworkRule
from backend.models.schemas import (
    StandardizedDataset,
    StandardizedFeature,
    Geometry,
    ProcessingStatus,
    DataCategory
)


class TestRoadNetworkRule:
    """Tests for the Road Network Rule."""
    
    @pytest.fixture
    def road_rule(self):
        """Create a road network rule instance."""
        return RoadNetworkRule()
    
    @pytest.fixture
    def sample_road_dataset(self):
        """Create a sample standardized road dataset."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0, 0], [0.1, 0.1], [0.2, 0.2]]
                ),
                properties={
                    "name": "Main Street",
                    "road_type": "primary",
                    "classification": "primary",
                    "length": 5000
                },
                source_provider="OSM",
                source_category="roads"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0.05, 0], [0.15, 0.1], [0.25, 0.2]]
                ),
                properties={
                    "name": "Secondary Road",
                    "road_type": "secondary",
                    "classification": "secondary",
                    "length": 4000
                },
                source_provider="OSM",
                source_category="roads"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0, 0.05], [0.1, 0.15], [0.2, 0.25]]
                ),
                properties={
                    "name": "Tertiary Road",
                    "road_type": "tertiary",
                    "classification": "tertiary",
                    "length": 3000
                },
                source_provider="OSM",
                source_category="roads"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0.1, 0], [0.2, 0.1]]
                ),
                properties={
                    "road_type": "residential",
                    "classification": "residential",
                    "length": 2000
                },
                source_provider="OSM",
                source_category="roads"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0, 0.1], [0.1, 0.2]]
                ),
                properties={
                    "road_type": "service",
                    "classification": "service",
                    "length": 1500
                },
                source_provider="OSM",
                source_category="roads"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0.15, 0], [0.25, 0.1]]
                ),
                properties={
                    "road_type": "primary",
                    "classification": "primary",
                    "length": 3500
                },
                source_provider="OSM",
                source_category="roads"
            ),
        ]
        
        return StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ROADS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    @pytest.fixture
    def empty_road_dataset(self):
        """Create an empty standardized road dataset."""
        return StandardizedDataset(
            features=[],
            source_provider="OSM",
            category=DataCategory.ROADS,
            feature_count=0,
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    @pytest.fixture
    def single_road_dataset(self):
        """Create a dataset with a single road."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0, 0], [0.1, 0.1], [0.2, 0.2]]
                ),
                properties={
                    "name": "Main Street",
                    "road_type": "primary",
                    "classification": "primary",
                    "length": 5000
                },
                source_provider="OSM",
                source_category="roads"
            )
        ]
        
        return StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ROADS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    def test_road_rule_initialization(self, road_rule):
        """Test that RoadNetworkRule initializes correctly."""
        assert road_rule.rule_id == "RD-001"
        assert road_rule.rule_name == "Road Network Analysis"
        assert DataCategory.ROADS in road_rule.required_categories
    
    def test_execute_with_valid_data(self, road_rule, sample_road_dataset):
        """Test rule execution with valid road data."""
        datasets = {DataCategory.ROADS: sample_road_dataset}
        
        result = road_rule.execute(datasets)
        
        # Verify result structure
        assert result.rule_id == "RD-001"
        assert result.status == ProcessingStatus.SUCCESS
        assert isinstance(result.result, dict)
        assert result.metadata["data_points_used"] == 6
        
        # Verify road information extracted
        road_result = result.result
        assert "road_access" in road_result
        assert road_result["road_access"] is True
        assert "total_road_segments" in road_result
        assert road_result["total_road_segments"] == 6
        assert "total_road_length_km" in road_result
        assert "road_types" in road_result
        assert "primary_road_type" in road_result
        assert "accessibility" in road_result
        assert "connectivity_estimate" in road_result
    
    def test_execute_with_empty_data(self, road_rule, empty_road_dataset):
        """Test rule execution with empty road data."""
        datasets = {DataCategory.ROADS: empty_road_dataset}
        
        result = road_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
        assert result.result == {}
    
    def test_execute_without_road_dataset(self, road_rule):
        """Test rule execution without road dataset."""
        datasets = {}
        
        result = road_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
    
    def test_has_required_data_with_road_data(self, road_rule, sample_road_dataset):
        """Test checking for required data with road data present."""
        datasets = {DataCategory.ROADS: sample_road_dataset}
        
        assert road_rule.has_required_data(datasets) is True
    
    def test_has_required_data_without_road_data(self, road_rule):
        """Test checking for required data without road data."""
        datasets = {}
        
        assert road_rule.has_required_data(datasets) is False
    
    def test_has_required_data_with_empty_road_data(self, road_rule, empty_road_dataset):
        """Test checking for required data with empty road data."""
        datasets = {DataCategory.ROADS: empty_road_dataset}
        
        assert road_rule.has_required_data(datasets) is False
    
    def test_execute_with_single_road(self, road_rule, single_road_dataset):
        """Test execution with a single road."""
        datasets = {DataCategory.ROADS: single_road_dataset}
        
        result = road_rule.execute(datasets)
        
        # Verify success
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 1
        
        # Verify road detection
        road_result = result.result
        assert road_result["road_access"] is True
        assert road_result["total_road_segments"] == 1
        assert road_result["primary_road_type"] == "primary"
        assert road_result["accessibility"] == "low"
    
    def test_road_type_distribution(self, road_rule, sample_road_dataset):
        """Test that road types are correctly counted and distributed."""
        datasets = {DataCategory.ROADS: sample_road_dataset}
        
        result = road_rule.execute(datasets)
        road_result = result.result
        
        # Verify road types
        road_types = road_result["road_types"]
        
        # Should have 5 types
        assert "primary" in road_types
        assert "secondary" in road_types
        assert "tertiary" in road_types
        assert "residential" in road_types
        assert "service" in road_types
        
        # Verify counts
        assert road_types["primary"]["count"] == 2
        assert road_types["secondary"]["count"] == 1
        assert road_types["tertiary"]["count"] == 1
        assert road_types["residential"]["count"] == 1
        assert road_types["service"]["count"] == 1
    
    def test_primary_road_type_detection(self, road_rule, sample_road_dataset):
        """Test that primary road type is correctly identified."""
        datasets = {DataCategory.ROADS: sample_road_dataset}
        
        result = road_rule.execute(datasets)
        road_result = result.result
        
        # Primary should be "primary" (2 out of 6)
        assert road_result["primary_road_type"] == "primary"
    
    def test_total_road_length_calculation(self, road_rule, sample_road_dataset):
        """Test that total road length is correctly calculated."""
        datasets = {DataCategory.ROADS: sample_road_dataset}
        
        result = road_rule.execute(datasets)
        road_result = result.result
        
        # Total length: 5000 + 4000 + 3000 + 2000 + 1500 + 3500 = 19000m = 19km
        expected_km = round(19000 / 1000, 2)
        assert road_result["total_road_length_km"] == expected_km
    
    def test_accessibility_low(self, road_rule):
        """Test accessibility categorization for low accessibility."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0, 0], [0.1, 0.1]]
                ),
                properties={
                    "classification": "primary",
                    "length": 1000
                },
                source_provider="OSM",
                source_category="roads"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ROADS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.ROADS: dataset}
        result = road_rule.execute(datasets)
        
        # With 1 road, accessibility should be low
        assert result.result["accessibility"] == "low"
        assert result.result["connectivity_estimate"] == "moderate"
    
    def test_accessibility_moderate(self, road_rule):
        """Test accessibility categorization for moderate accessibility."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[i*0.01, 0], [i*0.01+0.01, 0.1]]
                ),
                properties={
                    "classification": "primary",
                    "length": 1000
                },
                source_provider="OSM",
                source_category="roads"
            )
            for i in range(5)  # 5 roads
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ROADS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.ROADS: dataset}
        result = road_rule.execute(datasets)
        
        # With 5 roads, accessibility should be moderate
        assert result.result["accessibility"] == "moderate"
        assert result.result["connectivity_estimate"] == "moderate"
    
    def test_accessibility_high(self, road_rule):
        """Test accessibility categorization for high accessibility."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[i*0.01, 0], [i*0.01+0.01, 0.1]]
                ),
                properties={
                    "classification": "primary",
                    "length": 1000
                },
                source_provider="OSM",
                source_category="roads"
            )
            for i in range(15)  # 15 roads
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ROADS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.ROADS: dataset}
        result = road_rule.execute(datasets)
        
        # With 15 roads, accessibility should be high
        assert result.result["accessibility"] == "high"
        assert result.result["connectivity_estimate"] == "good"
    
    def test_no_road_access(self, road_rule, empty_road_dataset):
        """Test that no road access is correctly detected."""
        # Create dataset with no roads
        features = []
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ROADS,
            feature_count=0,
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.ROADS: dataset}
        result = road_rule.execute(datasets)
        
        # Should return insufficient data, not process
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
    
    def test_execute_with_missing_classification(self, road_rule):
        """Test execution with roads missing classification."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0, 0], [0.1, 0.1]]
                ),
                properties={},  # No classification
                source_provider="OSM",
                source_category="roads"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0.15, 0], [0.25, 0.1]]
                ),
                properties={"classification": "primary"},
                source_provider="OSM",
                source_category="roads"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ROADS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.ROADS: dataset}
        result = road_rule.execute(datasets)
        
        # Should still succeed with partial data
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 2
        assert result.result["total_road_segments"] == 2
    
    def test_execute_with_length_calculation(self, road_rule):
        """Test length calculation with various road lengths."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0, 0], [0.1, 0.1]]
                ),
                properties={
                    "classification": "primary",
                    "length": 1500.5
                },
                source_provider="OSM",
                source_category="roads"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0.15, 0], [0.25, 0.1]]
                ),
                properties={
                    "classification": "secondary",
                    "length": 2500.75
                },
                source_provider="OSM",
                source_category="roads"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.ROADS,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.ROADS: dataset}
        result = road_rule.execute(datasets)
        
        # Total length should be (1500.5 + 2500.75) / 1000 = 4.00125 km
        expected_km = round((1500.5 + 2500.75) / 1000, 2)
        assert result.result["total_road_length_km"] == expected_km
    
    def test_result_includes_all_required_fields(self, road_rule, sample_road_dataset):
        """Test that result includes all required output fields."""
        datasets = {DataCategory.ROADS: sample_road_dataset}
        
        result = road_rule.execute(datasets)
        road_result = result.result
        
        # Verify all required fields present
        required_fields = [
            "road_access",
            "total_road_segments",
            "total_road_length_km",
            "road_types",
            "primary_road_type",
            "accessibility",
            "connectivity_estimate"
        ]
        
        for field in required_fields:
            assert field in road_result, f"Missing field: {field}"
    
    def test_metadata_preserved(self, road_rule, sample_road_dataset):
        """Test that metadata is correctly preserved in results."""
        datasets = {DataCategory.ROADS: sample_road_dataset}
        
        result = road_rule.execute(datasets)
        
        # Verify metadata structure
        assert "data_points_used" in result.metadata
        assert result.metadata["data_points_used"] == 6
    
    def test_rule_result_structure(self, road_rule, sample_road_dataset):
        """Test that RuleResult has correct structure."""
        datasets = {DataCategory.ROADS: sample_road_dataset}
        
        result = road_rule.execute(datasets)
        
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


class TestRoadNetworkRuleWithRuleEngine:
    """Tests for RoadNetworkRule integration with RuleEngine."""
    
    def test_road_rule_with_engine(self, sample_road_dataset):
        """Test RoadNetworkRule works correctly within Rule Engine."""
        from backend.rules.rule_engine import RuleEngine
        
        engine = RuleEngine()
        engine.register_rule(RoadNetworkRule())
        
        datasets = {DataCategory.ROADS: sample_road_dataset}
        results = engine.execute(datasets)
        
        # Verify rule executed
        assert "RD-001" in results
        result = results["RD-001"]
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["road_access"] is True
        assert result.result["total_road_segments"] == 6


@pytest.fixture
def sample_road_dataset():
    """Create a sample standardized road dataset for module-level use."""
    features = [
        StandardizedFeature(
            geometry=Geometry(
                type="LineString",
                coordinates=[[0, 0], [0.1, 0.1], [0.2, 0.2]]
            ),
            properties={
                "name": "Main Street",
                "road_type": "primary",
                "classification": "primary",
                "length": 5000
            },
            source_provider="OSM",
            source_category="roads"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="LineString",
                coordinates=[[0.05, 0], [0.15, 0.1], [0.25, 0.2]]
            ),
            properties={
                "name": "Secondary Road",
                "road_type": "secondary",
                "classification": "secondary",
                "length": 4000
            },
            source_provider="OSM",
            source_category="roads"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="LineString",
                coordinates=[[0, 0.05], [0.1, 0.15], [0.2, 0.25]]
            ),
            properties={
                "name": "Tertiary Road",
                "road_type": "tertiary",
                "classification": "tertiary",
                "length": 3000
            },
            source_provider="OSM",
            source_category="roads"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="LineString",
                coordinates=[[0.1, 0], [0.2, 0.1]]
            ),
            properties={
                "road_type": "residential",
                "classification": "residential",
                "length": 2000
            },
            source_provider="OSM",
            source_category="roads"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="LineString",
                coordinates=[[0, 0.1], [0.1, 0.2]]
            ),
            properties={
                "road_type": "service",
                "classification": "service",
                "length": 1500
            },
            source_provider="OSM",
            source_category="roads"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="LineString",
                coordinates=[[0.15, 0], [0.25, 0.1]]
            ),
            properties={
                "road_type": "primary",
                "classification": "primary",
                "length": 3500
            },
            source_provider="OSM",
            source_category="roads"
        ),
    ]
    
    return StandardizedDataset(
        features=features,
        source_provider="OSM",
        category=DataCategory.ROADS,
        feature_count=len(features),
        crs="EPSG:4326",
        metadata={
            "source": "OpenStreetMap",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    )
