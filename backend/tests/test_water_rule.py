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
from hypothesis import given, settings, strategies as st

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
        assert "total_water_area_sqm" in water_result
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
        assert water_result["total_water_area_sqm"] == 5000000
    
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
        
        # Total area: 5 + 3 + 0.5 + 0.2 + 0.3 + 1 = 10 sq km = 10,000,000 m²
        expected_sqm = 10_000_000
        assert water_result["total_water_area_sqm"] == expected_sqm
    
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
                    "area": 50000  # 50,000 m² (< 100,000)
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
        
        # With 50,000 m² (< 100,000), coverage should be minimal
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
                    "area": 300000  # 300,000 m² (between 100,000 and 1,000,000)
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
        
        # With 300,000 m² (between 100,000 and 1,000,000), coverage should be moderate
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
                    "area": 2000000  # 2,000,000 m² (> 1,000,000)
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
        
        # With 2,000,000 m² (> 1,000,000), coverage should be significant
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
                    "area": 1500500  # 1,500,500 m²
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
                    "area": 2500750  # 2,500,750 m²
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
        
        # Total area should be 1500500 + 2500750 = 4,001,250 m²
        expected_sqm = round(1500500 + 2500750, 2)
        assert result.result["total_water_area_sqm"] == expected_sqm
    
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
            "total_water_area_sqm",
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
        assert result.result["total_water_area_sqm"] == 0
    
    def test_water_coverage_threshold_boundary_minimal_max(self, water_rule):
        """Test water coverage at maximum boundary of minimal category (just under 100,000 m²)."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "water_type": "pond",
                    "area": 99999  # Just under 100,000 m²
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
        
        # 99,999 m² should be minimal (< 100,000)
        assert result.result["water_coverage_category"] == "minimal"
    
    def test_water_coverage_threshold_boundary_moderate_min(self, water_rule):
        """Test water coverage at minimum boundary of moderate category (exactly 100,000 m²)."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "water_type": "lake",
                    "area": 100000  # Exactly at 100,000 m² boundary
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
        
        # 100,000 m² should be moderate (>= 100,000 and < 1,000,000)
        assert result.result["water_coverage_category"] == "moderate"
    
    def test_water_coverage_threshold_boundary_moderate_max(self, water_rule):
        """Test water coverage at maximum boundary of moderate category (just under 1,000,000 m²)."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "water_type": "lake",
                    "area": 999999  # Just under 1,000,000 m²
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
        
        # 999,999 m² should be moderate (>= 100,000 and < 1,000,000)
        assert result.result["water_coverage_category"] == "moderate"
    
    def test_water_coverage_threshold_boundary_significant_min(self, water_rule):
        """Test water coverage at minimum boundary of significant category (exactly 1,000,000 m²)."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                ),
                properties={
                    "water_type": "lake",
                    "area": 1000000  # Exactly at 1,000,000 m² boundary
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
        
        # 1,000,000 m² should be significant (>= 1,000,000)
        assert result.result["water_coverage_category"] == "significant"


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


class TestWaterRulePropertyBased:
    """Property-based tests using Hypothesis for WaterFeaturesRule
    
    Feature: distance-unit-standardization
    Property 8: Water rule outputs use square metres
    """

    @given(
        num_features=st.integers(min_value=1, max_value=10),
        data=st.data()
    )
    @settings(max_examples=100)
    def test_water_rule_output_uses_square_metres_property(self, num_features, data):
        """Property: For any water feature dataset, output contains total_water_area_sqm (not sqkm).
        
        **Property 8: Water rule outputs use square metres**
        **Validates: Requirements 13.1, 13.2**
        
        This property verifies that:
        1. The water rule output always has 'total_water_area_sqm' field
        2. The water rule output never has 'total_water_area_sqkm' field
        3. The total_water_area_sqm value is correctly calculated from individual feature areas
        """
        from hypothesis import strategies as st
        from hypothesis import settings
        
        # Generate random water features
        features = []
        total_expected_area = 0
        
        for i in range(num_features):
            area_sqm = data.draw(st.floats(
                min_value=1000,  # At least 1000 m²
                max_value=10_000_000,  # Up to 10 km²
                allow_nan=False,
                allow_infinity=False
            ))
            
            water_type = data.draw(st.sampled_from([
                "river", "stream", "lake", "canal", "reservoir",
                "pond", "wetland", "bay"
            ]))
            
            feature = StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[i, 0], [i+1, 0], [i+1, 1], [i, 1], [i, 0]]]
                ),
                properties={
                    "name": f"Water Feature {i}",
                    "water_type": water_type,
                    "area": area_sqm
                },
                source_provider="OSM",
                source_category="water"
            )
            
            features.append(feature)
            total_expected_area += area_sqm
        
        # Create dataset
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        # Execute rule
        rule = WaterFeaturesRule()
        datasets = {DataCategory.WATER: dataset}
        result = rule.execute(datasets)
        
        # Property assertions
        # 1. Status must be success
        assert result.status == ProcessingStatus.SUCCESS, \
            "Water rule should return SUCCESS status"
        
        # 2. Output must contain total_water_area_sqm field
        assert "total_water_area_sqm" in result.result, \
            f"Output must have 'total_water_area_sqm' field. Got keys: {result.result.keys()}"
        
        # 3. Output must NOT contain total_water_area_sqkm field
        assert "total_water_area_sqkm" not in result.result, \
            f"Output should not have 'total_water_area_sqkm' field. Got: {result.result}"
        
        # 4. Verify no km² field names in any output key
        for key in result.result.keys():
            assert "sqkm" not in key.lower() and "km2" not in key.lower() and "km²" not in key, \
                f"Output key '{key}' contains km² terminology, should use m² only"
        
        # 5. Verify total_water_area_sqm is numeric and positive
        total_area = result.result["total_water_area_sqm"]
        assert isinstance(total_area, (int, float)), \
            f"total_water_area_sqm should be numeric, got {type(total_area)}"
        assert total_area >= 0, \
            f"total_water_area_sqm should be non-negative, got {total_area}"
        
        # 6. Verify total_water_area_sqm matches sum of feature areas (within tolerance)
        # Allow for floating point rounding
        tolerance = total_expected_area * 0.01  # 1% tolerance
        assert abs(total_area - total_expected_area) <= tolerance, \
            f"total_water_area_sqm {total_area} doesn't match expected sum {total_expected_area}"

    @given(
        num_features=st.integers(min_value=1, max_value=5),
        data=st.data()
    )
    @settings(max_examples=100)
    def test_water_rule_output_fields_are_metres_only(self, num_features, data):
        """Property: All water rule output fields use metre-based terminology only.
        
        **Property 8: Water rule outputs use square metres**
        **Validates: Requirements 13.1, 13.2**
        
        This property verifies that no kilometre-based field names appear in outputs.
        """
        from hypothesis import strategies as st
        from hypothesis import settings
        
        # Generate random water features
        features = []
        for i in range(num_features):
            area_sqm = data.draw(st.floats(
                min_value=50_000,
                max_value=5_000_000,
                allow_nan=False,
                allow_infinity=False
            ))
            
            feature = StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[i, 0], [i+1, 0], [i+1, 1], [i, 1], [i, 0]]]
                ),
                properties={
                    "water_type": "lake",
                    "area": area_sqm
                },
                source_provider="OSM",
                source_category="water"
            )
            
            features.append(feature)
        
        # Create dataset
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        # Execute rule
        rule = WaterFeaturesRule()
        datasets = {DataCategory.WATER: dataset}
        result = rule.execute(datasets)
        
        # Verify all output field names are metres-based
        for key in result.result.keys():
            # Check that no key contains km² terminology
            assert "sqkm" not in key.lower(), \
                f"Field name '{key}' contains 'sqkm' - should use 'm²' terminology"
            assert "km2" not in key.lower(), \
                f"Field name '{key}' contains 'km2' - should use 'm²' terminology"
            assert "km²" not in key, \
                f"Field name '{key}' contains 'km²' - should use 'm²' terminology"
            assert "square_kilometers" not in key.lower(), \
                f"Field name '{key}' contains 'square_kilometers' - should use metres"
        
        # Verify total_water_area_sqm exists and sqkm version doesn't
        assert "total_water_area_sqm" in result.result, \
            "Output must have 'total_water_area_sqm'"
        assert "total_water_area_sqkm" not in result.result, \
            "Output must not have 'total_water_area_sqkm'"

    @given(
        data=st.data()
    )
    @settings(max_examples=100)
    def test_water_rule_with_various_area_values_uses_metres(self, data):
        """Property: For any area values in water features, output uses square metres consistently.
        
        **Property 8: Water rule outputs use square metres**
        **Validates: Requirements 13.1, 13.2**
        
        This property verifies that the rule correctly processes water features with
        various area values and always outputs in square metres.
        """
        from hypothesis import strategies as st
        from hypothesis import settings
        
        # Generate area values across different scales
        area_scales = [
            (1_000, 10_000),           # Small ponds
            (10_000, 100_000),         # Medium ponds/small lakes
            (100_000, 1_000_000),      # Lakes
            (1_000_000, 10_000_000),   # Large lakes
        ]
        
        scale_idx = data.draw(st.integers(0, len(area_scales) - 1))
        min_area, max_area = area_scales[scale_idx]
        
        area_sqm = data.draw(st.floats(
            min_value=min_area,
            max_value=max_area,
            allow_nan=False,
            allow_infinity=False
        ))
        
        # Create feature with this area
        feature = StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            ),
            properties={
                "water_type": "lake",
                "area": area_sqm
            },
            source_provider="OSM",
            source_category="water"
        )
        
        dataset = StandardizedDataset(
            features=[feature],
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=1,
            crs="EPSG:4326",
            metadata={}
        )
        
        # Execute rule
        rule = WaterFeaturesRule()
        datasets = {DataCategory.WATER: dataset}
        result = rule.execute(datasets)
        
        # Verify output
        assert result.status == ProcessingStatus.SUCCESS
        assert "total_water_area_sqm" in result.result
        assert "total_water_area_sqkm" not in result.result
        
        # Verify area value is reasonable
        total_area = result.result["total_water_area_sqm"]
        assert abs(total_area - area_sqm) < area_sqm * 0.01, \
            f"Area calculation should be accurate: expected ~{area_sqm}, got {total_area}"

    @given(
        data=st.data()
    )
    @settings(max_examples=100)
    def test_water_coverage_categorization_uses_square_metre_thresholds(self, data):
        """Property: For any total water area, coverage category matches m² thresholds.
        
        **Property 9: Coverage categorization uses square metre thresholds**
        **Validates: Requirements 13.3, 13.6**
        
        This property verifies that the water rule correctly categorizes water coverage
        based on square metre thresholds:
        - Minimal: < 100,000 m² (0.1 km²)
        - Moderate: 100,000 - 1,000,000 m² (0.1-1 km²)
        - Significant: > 1,000,000 m² (>1 km²)
        """
        from hypothesis import strategies as st
        from hypothesis import settings
        
        # Define coverage categories and their thresholds in m²
        MINIMAL_MAX = 100_000
        MODERATE_MAX = 1_000_000
        
        # Choose which category to test (0=minimal, 1=moderate, 2=significant)
        category_idx = data.draw(st.integers(0, 2))
        
        if category_idx == 0:
            # Minimal coverage: < 100,000 m²
            area_sqm = data.draw(st.floats(
                min_value=0,
                max_value=MINIMAL_MAX - 0.01,  # Just below threshold
                allow_nan=False,
                allow_infinity=False
            ))
            expected_category = "minimal"
        elif category_idx == 1:
            # Moderate coverage: >= 100,000 and < 1,000,000 m²
            area_sqm = data.draw(st.floats(
                min_value=MINIMAL_MAX,
                max_value=MODERATE_MAX - 0.01,  # Just below significant threshold
                allow_nan=False,
                allow_infinity=False
            ))
            expected_category = "moderate"
        else:
            # Significant coverage: >= 1,000,000 m²
            area_sqm = data.draw(st.floats(
                min_value=MODERATE_MAX,
                max_value=100_000_000,  # Up to 100 km²
                allow_nan=False,
                allow_infinity=False
            ))
            expected_category = "significant"
        
        # Create feature with this area
        feature = StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
            ),
            properties={
                "water_type": "lake",
                "area": area_sqm
            },
            source_provider="OSM",
            source_category="water"
        )
        
        dataset = StandardizedDataset(
            features=[feature],
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=1,
            crs="EPSG:4326",
            metadata={}
        )
        
        # Execute rule
        rule = WaterFeaturesRule()
        datasets = {DataCategory.WATER: dataset}
        result = rule.execute(datasets)
        
        # Verify result structure
        assert result.status == ProcessingStatus.SUCCESS, \
            "Water rule should return SUCCESS status"
        
        # Verify coverage category field exists
        assert "water_coverage_category" in result.result, \
            "Output must have 'water_coverage_category' field"
        
        # Verify category value is one of the valid options
        actual_category = result.result["water_coverage_category"]
        valid_categories = ["minimal", "moderate", "significant"]
        assert actual_category in valid_categories, \
            f"Coverage category '{actual_category}' must be one of {valid_categories}"
        
        # Verify category matches expected based on area
        assert actual_category == expected_category, \
            f"For area {area_sqm} m², expected category '{expected_category}' " \
            f"but got '{actual_category}'"
        
        # Verify boundary conditions
        if area_sqm < 100_000:
            assert actual_category == "minimal", \
                f"Area {area_sqm} m² (< 100,000) should be 'minimal'"
        elif area_sqm < 1_000_000:
            assert actual_category == "moderate", \
                f"Area {area_sqm} m² (100,000-1,000,000) should be 'moderate'"
        else:
            assert actual_category == "significant", \
                f"Area {area_sqm} m² (>= 1,000,000) should be 'significant'"

    @given(
        num_features=st.integers(min_value=1, max_value=8),
        data=st.data()
    )
    @settings(max_examples=100)
    def test_coverage_categorization_with_multiple_features(self, num_features, data):
        """Property: Coverage category is based on total combined area in m².
        
        **Property 9: Coverage categorization uses square metre thresholds**
        **Validates: Requirements 13.3, 13.6**
        
        This property verifies that when multiple water features are combined,
        the total area is correctly categorized based on m² thresholds.
        """
        from hypothesis import strategies as st
        from hypothesis import settings
        
        # Generate multiple features with random areas
        features = []
        total_area = 0
        
        for i in range(num_features):
            area_sqm = data.draw(st.floats(
                min_value=10_000,  # At least 10k m²
                max_value=500_000,  # Up to 0.5 km²
                allow_nan=False,
                allow_infinity=False
            ))
            
            feature = StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[i, 0], [i+1, 0], [i+1, 1], [i, 1], [i, 0]]]
                ),
                properties={
                    "water_type": "lake",
                    "area": area_sqm
                },
                source_provider="OSM",
                source_category="water"
            )
            
            features.append(feature)
            total_area += area_sqm
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="OSM",
            category=DataCategory.WATER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        # Execute rule
        rule = WaterFeaturesRule()
        datasets = {DataCategory.WATER: dataset}
        result = rule.execute(datasets)
        
        # Verify result
        assert result.status == ProcessingStatus.SUCCESS
        
        # Verify total_water_area_sqm matches sum
        actual_total = result.result["total_water_area_sqm"]
        tolerance = total_area * 0.01  # 1% tolerance
        assert abs(actual_total - total_area) <= tolerance, \
            f"Total area should be {total_area} but got {actual_total}"
        
        # Verify coverage category matches total area
        actual_category = result.result["water_coverage_category"]
        
        # Categorization thresholds in m²:
        # Minimal: < 100,000 m²
        # Moderate: >= 100,000 and < 1,000,000 m²
        # Significant: >= 1,000,000 m²
        if actual_total < 100_000:
            assert actual_category == "minimal", \
                f"Total {actual_total} m² (< 100,000) should be 'minimal', got '{actual_category}'"
        elif actual_total < 1_000_000:
            assert actual_category == "moderate", \
                f"Total {actual_total} m² (100,000-999,999) should be 'moderate', got '{actual_category}'"
        else:
            # >= 1,000,000 m²
            assert actual_category == "significant", \
                f"Total {actual_total} m² (>= 1,000,000) should be 'significant', got '{actual_category}'"

