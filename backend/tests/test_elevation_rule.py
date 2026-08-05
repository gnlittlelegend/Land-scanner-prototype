"""
Comprehensive test suite for Elevation Rule (ELV-001).

Tests verify elevation data processing, statistics calculation, terrain
categorization, and graceful handling of missing/invalid data.
"""

import pytest
from typing import List

from backend.models.schemas import (
    StandardizedDataset,
    StandardizedFeature,
    Geometry,
    RuleResult,
    ProcessingStatus,
    DataCategory
)
from backend.rules.elevation_rule import ElevationRule


@pytest.fixture
def elevation_rule():
    """Fixture providing an ElevationRule instance."""
    return ElevationRule()


def create_elevation_feature(feature_id: str, elevation: float, slope: float = None, 
                             lon: float = 0, lat: float = 0) -> StandardizedFeature:
    """Helper to create elevation features."""
    props = {"elevation": elevation}
    if slope is not None:
        props["slope"] = slope
    
    return StandardizedFeature(
        type="Feature",
        geometry=Geometry(type="Point", coordinates=[lon, lat]),
        properties=props,
        source_provider="USGS",
        source_category="elevation"
    )


def create_elevation_dataset(features: List[StandardizedFeature]) -> StandardizedDataset:
    """Helper to create elevation datasets."""
    return StandardizedDataset(
        category=DataCategory.ELEVATION,
        source_provider="USGS",
        features=features,
        feature_count=len(features),
        metadata={
            "timestamp": "2024-01-15T10:00:00Z",
            "crs": "EPSG:4326",
            "record_count": len(features)
        }
    )


@pytest.fixture
def valid_elevation_features():
    """Fixture with valid elevation features."""
    features = [
        create_elevation_feature("elev_1", 100.0, 2.5, 0, 0),
        create_elevation_feature("elev_2", 150.0, 4.2, 0.1, 0.1),
        create_elevation_feature("elev_3", 200.0, 6.8, 0.2, 0.2),
    ]
    return features


@pytest.fixture
def valid_elevation_dataset(valid_elevation_features):
    """Fixture providing a valid StandardizedDataset for elevation."""
    return create_elevation_dataset(valid_elevation_features)


class TestElevationRuleInitialization:
    """Tests for ElevationRule initialization."""
    
    def test_rule_initialization(self, elevation_rule):
        """Verify ElevationRule initializes with correct ID and name."""
        assert elevation_rule.rule_id == "ELV-001"
        assert elevation_rule.rule_name == "Elevation Analysis"
    
    def test_required_categories(self, elevation_rule):
        """Verify ElevationRule requires only ELEVATION category."""
        assert DataCategory.ELEVATION in elevation_rule.required_categories
        assert len(elevation_rule.required_categories) == 1


class TestElevationRuleDataProcessing:
    """Tests for data processing and execution."""
    
    def test_execute_with_valid_data(self, elevation_rule, valid_elevation_dataset):
        """Verify execution with valid elevation data returns SUCCESS."""
        datasets = {DataCategory.ELEVATION: valid_elevation_dataset}
        result = elevation_rule.execute(datasets)
        
        assert result.status == ProcessingStatus.SUCCESS
        assert result.rule_id == "ELV-001"
        assert isinstance(result.result, dict)
        assert result.metadata["data_points_used"] == 3
    
    def test_execute_with_empty_dataset(self, elevation_rule):
        """Verify execution with empty features array returns INSUFFICIENT_DATA."""
        dataset = create_elevation_dataset([])
        datasets = {DataCategory.ELEVATION: dataset}
        result = elevation_rule.execute(datasets)
        
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
    
    def test_execute_without_elevation_dataset(self, elevation_rule):
        """Verify execution without ELEVATION dataset returns INSUFFICIENT_DATA."""
        datasets = {}  # No elevation dataset
        result = elevation_rule.execute(datasets)
        
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
    
    def test_execute_with_none_dataset(self, elevation_rule):
        """Verify execution with None elevation dataset returns INSUFFICIENT_DATA."""
        datasets = {DataCategory.ELEVATION: None}
        result = elevation_rule.execute(datasets)
        
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA


class TestElevationStatisticsCalculation:
    """Tests for elevation statistics calculations."""
    
    def test_calculate_min_max_mean(self, elevation_rule, valid_elevation_dataset):
        """Verify min, max, mean elevation calculations are accurate."""
        datasets = {DataCategory.ELEVATION: valid_elevation_dataset}
        result = elevation_rule.execute(datasets)
        
        assert result.result["min_elevation_m"] == 100.0
        assert result.result["max_elevation_m"] == 200.0
        assert result.result["mean_elevation_m"] == 150.0  # (100+150+200)/3
    
    def test_calculate_elevation_range(self, elevation_rule, valid_elevation_dataset):
        """Verify elevation range calculation."""
        datasets = {DataCategory.ELEVATION: valid_elevation_dataset}
        result = elevation_rule.execute(datasets)
        
        assert result.result["elevation_range_m"] == 100.0  # 200-100
    
    def test_calculate_median_elevation(self, elevation_rule, valid_elevation_dataset):
        """Verify median elevation calculation with multiple points."""
        datasets = {DataCategory.ELEVATION: valid_elevation_dataset}
        result = elevation_rule.execute(datasets)
        
        assert result.result["median_elevation_m"] == 150.0  # Middle of [100, 150, 200]
    
    def test_single_elevation_point(self, elevation_rule):
        """Verify statistics with single elevation point."""
        features = [create_elevation_feature("elev_1", 500.0)]
        dataset = create_elevation_dataset(features)
        datasets = {DataCategory.ELEVATION: dataset}
        result = elevation_rule.execute(datasets)
        
        assert result.result["min_elevation_m"] == 500.0
        assert result.result["max_elevation_m"] == 500.0
        assert result.result["mean_elevation_m"] == 500.0
        assert result.result["elevation_range_m"] == 0.0
    
    def test_large_elevation_values(self, elevation_rule):
        """Verify statistics with large elevation values (mountains)."""
        features = [
            create_elevation_feature("elev_1", 3000.0),
            create_elevation_feature("elev_2", 5000.0, lon=0.1, lat=0.1),
            create_elevation_feature("elev_3", 4000.0, lon=0.2, lat=0.2),
        ]
        dataset = create_elevation_dataset(features)
        datasets = {DataCategory.ELEVATION: dataset}
        result = elevation_rule.execute(datasets)
        
        assert result.result["min_elevation_m"] == 3000.0
        assert result.result["max_elevation_m"] == 5000.0
        assert result.result["mean_elevation_m"] == 4000.0


class TestTerrainCategorization:
    """Tests for terrain categorization based on elevation range."""
    
    def test_categorize_flat_terrain(self, elevation_rule):
        """Verify terrain categorized as 'flat' for small elevation ranges."""
        features = [
            create_elevation_feature("e1", 100.0, 2.0, 0, 0),
            create_elevation_feature("e2", 110.0, 3.0, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.result["terrain_category"] == "flat"
        assert result.result["elevation_range_m"] < 50
    
    def test_categorize_rolling_terrain(self, elevation_rule):
        """Verify terrain categorized as 'rolling' for moderate elevation ranges."""
        features = [
            create_elevation_feature("e1", 100.0, None, 0, 0),
            create_elevation_feature("e2", 250.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.result["terrain_category"] == "rolling"
        assert 50 <= result.result["elevation_range_m"] < 500
    
    def test_categorize_mountainous_terrain(self, elevation_rule):
        """Verify terrain categorized as 'mountainous' for large elevation ranges."""
        features = [
            create_elevation_feature("e1", 500.0, None, 0, 0),
            create_elevation_feature("e2", 2500.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.result["terrain_category"] == "mountainous"
        assert result.result["elevation_range_m"] >= 500


class TestSlopeCategorization:
    """Tests for slope categorization."""
    
    def test_categorize_low_slope(self, elevation_rule):
        """Verify slope categorized as 'low' for gentle slopes."""
        features = [
            create_elevation_feature("e1", 100.0, 2.0, 0, 0),
            create_elevation_feature("e2", 110.0, 3.0, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.result["slope_category"] == "low"
        assert result.result["slope_average"] < 5
    
    def test_categorize_moderate_slope(self, elevation_rule):
        """Verify slope categorized as 'moderate' for medium slopes."""
        features = [
            create_elevation_feature("e1", 100.0, 8.0, 0, 0),
            create_elevation_feature("e2", 110.0, 10.0, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.result["slope_category"] == "moderate"
        assert 5 <= result.result["slope_average"] < 15
    
    def test_categorize_steep_slope(self, elevation_rule):
        """Verify slope categorized as 'steep' for steep slopes."""
        features = [
            create_elevation_feature("e1", 100.0, 20.0, 0, 0),
            create_elevation_feature("e2", 110.0, 25.0, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.result["slope_category"] == "steep"
        assert result.result["slope_average"] >= 15


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_negative_elevation_values(self, elevation_rule):
        """Verify handling of negative elevation (below sea level)."""
        features = [
            create_elevation_feature("e1", -100.0, None, 0, 0),
            create_elevation_feature("e2", 100.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["min_elevation_m"] == -100.0
        assert result.result["max_elevation_m"] == 100.0
    
    def test_zero_elevation(self, elevation_rule):
        """Verify handling of zero elevation (sea level)."""
        features = [create_elevation_feature("e1", 0.0)]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.result["min_elevation_m"] == 0.0
        assert result.result["mean_elevation_m"] == 0.0
    
    def test_floating_point_precision(self, elevation_rule):
        """Verify floating point values are handled and rounded correctly."""
        features = [
            create_elevation_feature("e1", 123.456789, None, 0, 0),
            create_elevation_feature("e2", 234.567891, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        # Results should be rounded to 2 decimal places
        assert isinstance(result.result["min_elevation_m"], (int, float))
        assert len(str(result.result["min_elevation_m"]).split('.')[-1]) <= 2
    
    def test_features_without_elevation_property(self, elevation_rule):
        """Verify handling of features missing elevation property."""
        features = [
            StandardizedFeature(
                type="Feature",
                geometry=Geometry(type="Point", coordinates=[0, 0]),
                properties={"slope": 5.0},  # No elevation
                source_provider="USGS",
                source_category="elevation"
            ),
            create_elevation_feature("e2", 100.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        # Should process the one feature with elevation
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["elevation_data_available"] is True
        assert result.result["min_elevation_m"] == 100.0
    
    def test_features_with_invalid_elevation_values(self, elevation_rule):
        """Verify handling of non-numeric elevation values."""
        features = [
            StandardizedFeature(
                type="Feature",
                geometry=Geometry(type="Point", coordinates=[0, 0]),
                properties={"elevation": "not_a_number"},
                source_provider="USGS",
                source_category="elevation"
            ),
            create_elevation_feature("e2", 150.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        # Should skip invalid and process valid
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["min_elevation_m"] == 150.0


class TestMissingDataHandling:
    """Tests for handling missing or incomplete data."""
    
    def test_no_slope_data(self, elevation_rule):
        """Verify execution without slope data still processes elevation."""
        features = [
            create_elevation_feature("e1", 100.0, None, 0, 0),
            create_elevation_feature("e2", 200.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["elevation_data_available"] is True
        assert result.result["slope_average"] is None
        assert result.result["slope_category"] == "low"  # Default
    
    def test_features_with_empty_properties(self, elevation_rule):
        """Verify handling of features with empty properties."""
        features = [
            StandardizedFeature(
                type="Feature",
                geometry=Geometry(type="Point", coordinates=[0, 0]),
                properties={},
                source_provider="USGS",
                source_category="elevation"
            ),
            create_elevation_feature("e2", 100.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 2


class TestResultStructure:
    """Tests for result structure and format."""
    
    def test_result_format_success(self, elevation_rule, valid_elevation_dataset):
        """Verify RuleResult structure on success."""
        datasets = {DataCategory.ELEVATION: valid_elevation_dataset}
        result = elevation_rule.execute(datasets)
        
        assert isinstance(result, RuleResult)
        assert result.rule_id == "ELV-001"
        assert result.rule_name == "Elevation Analysis"
        assert result.status == ProcessingStatus.SUCCESS
        assert isinstance(result.result, dict)
        assert isinstance(result.metadata, dict)
    
    def test_result_contains_all_fields(self, elevation_rule, valid_elevation_dataset):
        """Verify all expected fields are in result."""
        datasets = {DataCategory.ELEVATION: valid_elevation_dataset}
        result = elevation_rule.execute(datasets)
        
        expected_fields = [
            "elevation_data_available",
            "min_elevation_m",
            "max_elevation_m",
            "mean_elevation_m",
            "median_elevation_m",
            "elevation_range_m",
            "terrain_category",
            "slope_average",
            "slope_category"
        ]
        
        for field in expected_fields:
            assert field in result.result
    
    def test_metadata_includes_data_points(self, elevation_rule, valid_elevation_dataset):
        """Verify metadata includes count of data points used."""
        datasets = {DataCategory.ELEVATION: valid_elevation_dataset}
        result = elevation_rule.execute(datasets)
        
        assert "data_points_used" in result.metadata
        assert result.metadata["data_points_used"] == 3


class TestBoundaryConditions:
    """Tests for boundary condition values."""
    
    def test_exact_flat_boundary(self, elevation_rule):
        """Test terrain categorization at exact flat boundary (50m)."""
        features = [
            create_elevation_feature("e1", 100.0, None, 0, 0),
            create_elevation_feature("e2", 150.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        # 50m range should be rolling (not flat)
        assert result.result["elevation_range_m"] == 50.0
        assert result.result["terrain_category"] == "rolling"
    
    def test_exact_rolling_boundary(self, elevation_rule):
        """Test terrain categorization at exact rolling boundary (500m)."""
        features = [
            create_elevation_feature("e1", 0.0, None, 0, 0),
            create_elevation_feature("e2", 500.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        # 500m range should be mountainous (not rolling)
        assert result.result["elevation_range_m"] == 500.0
        assert result.result["terrain_category"] == "mountainous"
    
    def test_exact_low_slope_boundary(self, elevation_rule):
        """Test slope categorization at exact low boundary (5°)."""
        features = [create_elevation_feature("e1", 100.0, 5.0)]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        # 5° should be moderate (not low)
        assert result.result["slope_average"] == 5.0
        assert result.result["slope_category"] == "moderate"
    
    def test_exact_moderate_slope_boundary(self, elevation_rule):
        """Test slope categorization at exact moderate boundary (15°)."""
        features = [create_elevation_feature("e1", 100.0, 15.0)]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        # 15° should be steep (not moderate)
        assert result.result["slope_average"] == 15.0
        assert result.result["slope_category"] == "steep"


class TestMetadataPreservation:
    """Tests for metadata handling and preservation."""
    
    def test_metadata_records_data_points(self, elevation_rule):
        """Verify metadata correctly records number of data points processed."""
        features = [
            create_elevation_feature("e1", 100.0, None, 0, 0),
            create_elevation_feature("e2", 150.0, None, 0.1, 0.1),
        ]
        dataset = create_elevation_dataset(features)
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.metadata["data_points_used"] == 2
    
    def test_metadata_includes_insufficient_data_info(self, elevation_rule):
        """Verify metadata includes info when data insufficient."""
        dataset = create_elevation_dataset([])
        result = elevation_rule.execute({DataCategory.ELEVATION: dataset})
        
        assert result.metadata["data_points_used"] == 0
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
