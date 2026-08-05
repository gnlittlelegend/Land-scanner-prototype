"""
Tests for Water Features Rule (WT-001)

This test suite validates that the WaterFeaturesRule:
- Correctly processes standardized water data
- Identifies water features (rivers, lakes, canals, ponds)
- Estimates water coverage percentage
- Categorizes water types present
- Handles missing water data gracefully
- Returns structured water information
"""

import pytest
from typing import Dict
from unittest.mock import Mock

from backend.rules.water_rule import WaterFeaturesRule
from backend.models.schemas import (
    StandardizedDataset,
    StandardizedFeature,
    Geometry,
    ProcessingStatus,
    DataCategory
)


class TestWaterFeaturesRule:
    """Tests for the Water Features Rule."""
    
    @pytest.fixture
    def water_rule(self):
        """Create a water features rule instance."""
        return WaterFeaturesRule()
    
    @pytest.fixture
    def sample_water_dataset(self):
        """Create a sample standardized water dataset."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0, 0], [0.1, 0.1], [0.2, 0.2]]
                ),
                properties={
                    "name": "Main River",
                    "water_type": "river",
                    "type": "river",
                    "area": 5000000  # 5 sq km in sq meters
                },
                source_provider="OSM",
                source_category="water"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.05, 0], [0.15, 0], [0.15, 0.1], [0.05, 0.1], [0.05, 0]]]
                ),
                properties={
                    "name": "Mountain Lake",
                    "water_type": "lake",
                    "type": "lake",
                    "area": 3000000  # 3 sq km in sq meters
                },
                source_provider="OSM",
                source_category="water"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0.1, 0], [0.2, 0.1]]
                ),
                properties={
                    "water_type": "canal",
                    "type": "canal",
                    "area": 500000  # 0.5 sq km
                },
                source_provider="OSM",
                source_category="water"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0.05], [0.05, 0.05], [0.05, 0.1], [0, 0.1], [0, 0.05]]]
                ),
                properties={
                    "water_type": "pond",
                    "type": "pond",
                    "area": 200000  # 0.2 sq km
                },
                source_provider="OSM",
                source_category="water"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="LineString",
                    coordinates=[[0.15, 0.05], [0.25, 0.15]]
                ),
                properties={
                    "water_type": "stream",
                    "type": "stream",
                    "area": 300000  # 0.3 sq km
                },
                source_provider="OSM",
                source_category="water"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.1, 0.15], [0.15, 0.15], [0.15, 0.2], [0.1, 0.2], [0.1, 0.15]]]
                ),
                properties={
                    "water_type": "reservoir",
                    "type": "reservoir",
                    "area": 1000000  # 1 sq km
                },
                source_provider="OSM",
                source_category="water"
            ),
        ]
        
        return StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    @pytest.fixture
    def empty_water_dataset(self):
        """Create an empty standardized water dataset."""
        return StandardizedDataset(
            features=[],
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=0,
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    @pytest.fixture
    def single_water_feature_dataset(self):
        """Create a dataset with a single water feature."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={
                    "name": "Large Lake",
                    "water_type": "lake",
                    "type": "lake",
                    "area": 5000000
                },
                source_provider="OSM",
                source_category="water"
            )
        ]
        
        return StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={
                "source": "OpenStreetMap",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    def test_water_rule_initialization(self, water_rule):
        """Test that WaterFeaturesRule initializes correctly."""
        assert water_rule.rule_id == "WT-001"
        assert water_rule.rule_name == "Water Features Analysis"
        assert DataCategory.WATER in water_rule.required_categories
    
    def test_execute_with_valid_data(self, water_rule, sample_water_dataset):
        """Test rule execution with valid water data."""
        datasets = {DataCategory.WATER: sample_water_dataset}
        
        result = water_rule.execute(datasets)
        
        # Verify result structure
        assert result.rule_id == "WT-001"
        assert result.status == ProcessingStatus.SUCCESS
        assert isinstance(result.result, dict)
        assert result.metadata["data_points_used"] == 6
        
        # Verify water information extracted
        water_result = result.result
        assert "water_features_detected" in water_result
        assert water_result["water_features_detected"] is True
        assert "total_water_features" in water_result
        assert water_result["total_water_features"] == 6
        assert "water_types" in water_result
        assert "primary_water_type" in water_result
        assert "total_water_area_sqkm" in water_result
        assert "water_coverage_category" in water_result
        assert "hydrological_features" in water_result
    
    def test_execute_with_empty_data(self, water_rule, empty_water_dataset):
        """Test rule execution with empty water data."""
        datasets = {DataCategory.WATER: empty_water_dataset}
        
        result = water_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
        assert result.result == {}
    
    def test_execute_without_water_dataset(self, water_rule):
        """Test rule execution without water dataset."""
        datasets = {}
        
        result = water_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
    
    def test_has_required_data_with_water_data(self, water_rule, sample_water_dataset):
        """Test checking for required data with water data present."""
        datasets = {DataCategory.WATER: sample_water_dataset}
        
        assert water_rule.has_required_data(datasets) is True
    
    def test_has_required_data_without_water_data(self, water_rule):
        """Test checking for required data without water data."""
        datasets = {}
        
        assert water_rule.has_required_data(datasets) is False
    
    def test_has_required_data_with_empty_water_data(self, water_rule, empty_water_dataset):
        """Test checking for required data with empty water data."""
        datasets = {DataCategory.WATER: empty_water_dataset}
        
        assert water_rule.has_required_data(datasets) is False
    
    def test_execute_with_single_water_feature(self, water_rule, single_water_feature_dataset):
        """Test execution with a single water feature."""
        datasets = {DataCategory.WATER: single_water_feature_dataset}
        
        result = water_rule.execute(datasets)
        
        # Verify success
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 1
        
        # Verify water detection
        water_result = result.result
        assert water_result["water_features_detected"] is True
        assert water_result["total_water_features"] == 1
        assert water_result["primary_water_type"] == "lake"
        assert water_result["total_water_area_sqkm"] == 5.0
    
    def test_water_type_distribution(self, water_rule, sample_water_dataset):
        """Test that water types are correctly counted and distributed."""
        datasets = {DataCategory.WATER: sample_water_dataset}
        
        result = water_rule.execute(datasets)
        water_result = result.result
        
        # Verify water types
        water_types = water_result["water_types"]
        
        # Should have 6 types
        assert "river" in water_types
        assert "lake" in water_types
        assert "canal" in water_types
        assert "pond" in water_types
        assert "stream" in water_types
        assert "reservoir" in water_types
        
        # Verify counts
        assert water_types["river"]["count"] == 1
        assert water_types["lake"]["count"] == 1
        assert water_types["canal"]["count"] == 1
        assert water_types["pond"]["count"] == 1
        assert water_types["stream"]["count"] == 1
        assert water_types["reservoir"]["count"] == 1
    
    def test_primary_water_type_detection(self, water_rule):
        """Test that primary water type is correctly identified."""
        # Create dataset with multiple water types (lake repeated)
        features = [
            StandardizedFeature(
                geometry=Geometry(type="Polygon", coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]),
                properties={"water_type": "lake", "area": 5000000},
                source_provider="OSM",
                source_category="water"
            ),
            StandardizedFeature(
                geometry=Geometry(type="Polygon", coordinates=[[[2, 0], [3, 0], [3, 1], [2, 1], [2, 0]]]),
                properties={"water_type": "lake", "area": 4000000},
                source_provider="OSM",
                source_category="water"
            ),
            StandardizedFeature(
                geometry=Geometry(type="LineString", coordinates=[[0, 0], [1, 1]]),
                properties={"water_type": "river", "area": 1000000},
                source_provider="OSM",
                source_category="water"
            ),
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.WATER: dataset}
        result = water_rule.execute(datasets)
        water_result = result.result
        
        # Lake should be primary (2 out of 3)
        assert water_result["primary_water_type"] == "lake"
    
    def test_total_water_area_calculation(self, water_rule, sample_water_dataset):
        """Test that total water area is correctly calculated."""
        datasets = {DataCategory.WATER: sample_water_dataset}
        
        result = water_rule.execute(datasets)
        water_result = result.result
        
        # Total area: 5 + 3 + 0.5 + 0.2 + 0.3 + 1 = 10 sq km
        expected_sqkm = 10.0
        assert water_result["total_water_area_sqkm"] == expected_sqkm
    
    def test_water_coverage_category_minimal(self, water_rule):
        """Test water coverage categorization for minimal coverage."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "water_type": "pond",
                    "area": 50000  # 0.05 sq km (< 0.1)
                },
                source_provider="OSM",
                source_category="water"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.WATER: dataset}
        result = water_rule.execute(datasets)
        
        # With 0.05 sq km, coverage should be minimal
        assert result.result["water_coverage_category"] == "minimal"
    
    def test_water_coverage_category_moderate(self, water_rule):
        """Test water coverage categorization for moderate coverage."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "water_type": "lake",
                    "area": 300000  # 0.3 sq km (between 0.1 and 1.0)
                },
                source_provider="OSM",
                source_category="water"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.WATER: dataset}
        result = water_rule.execute(datasets)
        
        # With 0.3 sq km, coverage should be moderate
        assert result.result["water_coverage_category"] == "moderate"
    
    def test_water_coverage_category_significant(self, water_rule):
        """Test water coverage categorization for significant coverage."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "water_type": "lake",
                    "area": 2000000  # 2 sq km (> 1.0)
                },
                source_provider="OSM",
                source_category="water"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.WATER: dataset}
        result = water_rule.execute(datasets)
        
        # With 2 sq km, coverage should be significant
        assert result.result["water_coverage_category"] == "significant"
    
    def test_hydrological_features_identification(self, water_rule, sample_water_dataset):
        """Test that hydrological features are correctly identified."""
        datasets = {DataCategory.WATER: sample_water_dataset}
        
        result = water_rule.execute(datasets)
        water_result = result.result
        
        features = water_result["hydrological_features"]
        
        # Should identify various water features
        assert "River" in features
        assert "Lake" in features
        assert "Canal" in features
        assert "Pond" in features
        assert "Stream" in features
        assert "Reservoir" in features
    
    def test_water_features_not_detected_with_empty_data(self, water_rule):
        """Test that water features not detected with empty data."""
        dataset = StandardizedDataset(
            features=[],
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=0,
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.WATER: dataset}
        result = water_rule.execute(datasets)
        
        # Should return insufficient data, not process
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
    
    def test_execute_with_missing_water_type(self, water_rule):
        """Test execution with water features missing water_type."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={},  # No water_type
                source_provider="OSM",
                source_category="water"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[2, 0], [3, 0], [3, 1], [2, 1], [2, 0]]]
                ),
                properties={"water_type": "lake", "area": 5000000},
                source_provider="OSM",
                source_category="water"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.WATER: dataset}
        result = water_rule.execute(datasets)
        
        # Should still succeed with partial data
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 2
        assert result.result["total_water_features"] == 2
    
    def test_execute_with_area_calculation(self, water_rule):
        """Test area calculation with various water areas."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "water_type": "lake",
                    "area": 1500500  # 1.5005 sq km
                },
                source_provider="OSM",
                source_category="water"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[2, 0], [3, 0], [3, 1], [2, 1], [2, 0]]]
                ),
                properties={
                    "water_type": "river",
                    "area": 2500750  # 2.50075 sq km
                },
                source_provider="OSM",
                source_category="water"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.WATER: dataset}
        result = water_rule.execute(datasets)
        
        # Total area should be (1500500 + 2500750) / 1000000 = 4.00125 sq km
        expected_sqkm = round((1500500 + 2500750) / 1_000_000, 2)
        assert result.result["total_water_area_sqkm"] == expected_sqkm
    
    def test_result_includes_all_required_fields(self, water_rule, sample_water_dataset):
        """Test that result includes all required output fields."""
        datasets = {DataCategory.WATER: sample_water_dataset}
        
        result = water_rule.execute(datasets)
        water_result = result.result
        
        # Verify all required fields present
        required_fields = [
            "water_features_detected",
            "total_water_features",
            "water_types",
            "primary_water_type",
            "total_water_area_sqkm",
            "water_coverage_category",
            "hydrological_features"
        ]
        
        for field in required_fields:
            assert field in water_result, f"Missing field: {field}"
    
    def test_metadata_preserved(self, water_rule, sample_water_dataset):
        """Test that metadata is correctly preserved in results."""
        datasets = {DataCategory.WATER: sample_water_dataset}
        
        result = water_rule.execute(datasets)
        
        # Verify metadata structure
        assert "data_points_used" in result.metadata
        assert result.metadata["data_points_used"] == 6
    
    def test_rule_result_structure(self, water_rule, sample_water_dataset):
        """Test that RuleResult has correct structure."""
        datasets = {DataCategory.WATER: sample_water_dataset}
        
        result = water_rule.execute(datasets)
        
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
    
    def test_water_type_with_fallback_type_field(self, water_rule):
        """Test water type extraction with fallback to 'type' field."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "type": "lake",  # Using 'type' field instead of 'water_type'
                    "area": 5000000
                },
                source_provider="OSM",
                source_category="water"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.WATER: dataset}
        result = water_rule.execute(datasets)
        
        # Should still work with 'type' field
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["water_types"]["lake"]["count"] == 1
    
    def test_water_area_without_area_field(self, water_rule):
        """Test water feature without area field."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "water_type": "lake"
                    # No area field
                },
                source_provider="OSM",
                source_category="water"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.WATER: dataset}
        result = water_rule.execute(datasets)
        
        # Should still succeed but with zero area
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["total_water_area_sqkm"] == 0


class TestWaterFeaturesRuleWithRuleEngine:
    """Tests for WaterFeaturesRule integration with RuleEngine."""
    
    def test_water_rule_with_engine(self, sample_water_dataset):
        """Test WaterFeaturesRule works correctly within Rule Engine."""
        from backend.rules.rule_engine import RuleEngine
        
        engine = RuleEngine()
        engine.register_rule(WaterFeaturesRule())
        
        datasets = {DataCategory.WATER: sample_water_dataset}
        results = engine.execute(datasets)
        
        # Verify rule executed
        assert "WT-001" in results
        result = results["WT-001"]
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["water_features_detected"] is True
        assert result.result["total_water_features"] == 6


@pytest.fixture
def sample_water_dataset():
    """Create a sample standardized water dataset for module-level use."""
    features = [
        StandardizedFeature(
            geometry=Geometry(
                type="LineString",
                coordinates=[[0, 0], [0.1, 0.1], [0.2, 0.2]]
            ),
            properties={
                "name": "Main River",
                "water_type": "river",
                "type": "river",
                "area": 5000000
            },
            source_provider="OSM",
            source_category="water"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.05, 0], [0.15, 0], [0.15, 0.1], [0.05, 0.1], [0.05, 0]]]
            ),
            properties={
                "name": "Mountain Lake",
                "water_type": "lake",
                "type": "lake",
                "area": 3000000
            },
            source_provider="OSM",
            source_category="water"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="LineString",
                coordinates=[[0.1, 0], [0.2, 0.1]]
            ),
            properties={
                "water_type": "canal",
                "type": "canal",
                "area": 500000
            },
            source_provider="OSM",
            source_category="water"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0, 0.05], [0.05, 0.05], [0.05, 0.1], [0, 0.1], [0, 0.05]]]
            ),
            properties={
                "water_type": "pond",
                "type": "pond",
                "area": 200000
            },
            source_provider="OSM",
            source_category="water"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="LineString",
                coordinates=[[0.15, 0.05], [0.25, 0.15]]
            ),
            properties={
                "water_type": "stream",
                "type": "stream",
                "area": 300000
            },
            source_provider="OSM",
            source_category="water"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.1, 0.15], [0.15, 0.15], [0.15, 0.2], [0.1, 0.2], [0.1, 0.15]]]
            ),
            properties={
                "water_type": "reservoir",
                "type": "reservoir",
                "area": 1000000
            },
            source_provider="OSM",
            source_category="water"
        ),
    ]
    
    return StandardizedDataset(
        features=features,
        source_provider="OSM",
        category=DataCategory.WATER,
        feature_count=len(features),
        crs="EPSG:4326",
        metadata={
            "source": "OpenStreetMap",
            "timestamp": "2024-01-15T10:30:00Z"
        }
    )
