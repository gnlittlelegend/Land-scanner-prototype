"""
Tests for Land Cover Summary Rule (LC-001)

This test suite validates that the LandCoverRule:
- Correctly processes standardized land cover data
- Identifies dominant land cover types
- Calculates coverage percentages by category
- Handles missing land cover data gracefully
- Returns structured land cover information

Property: Land Cover Categorization Accuracy
Validates: Requirements 5.3
"""

import pytest
from typing import Dict
from unittest.mock import Mock

from backend.rules.land_cover_rule import LandCoverRule
from backend.models.schemas import (
    StandardizedDataset,
    StandardizedFeature,
    Geometry,
    ProcessingStatus,
    DataCategory
)


class TestLandCoverRule:
    """Tests for the Land Cover Summary Rule."""
    
    @pytest.fixture
    def land_cover_rule(self):
        """Create a land cover rule instance."""
        return LandCoverRule()
    
    
    @pytest.fixture
    def sample_land_cover_dataset(self):
        """Create a sample standardized land cover dataset."""
        features = [
            # Urban features
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={
                    "land_cover_type": "urban",
                    "coverage": 30.0
                },
                source_provider="Copernicus",
                source_category="land_cover"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.1, 0], [0.2, 0], [0.2, 0.1], [0.1, 0.1], [0.1, 0]]]
                ),
                properties={
                    "land_cover_type": "built-up",
                    "coverage": 15.0
                },
                source_provider="Copernicus",
                source_category="land_cover"
            ),
            # Agricultural features
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.2, 0], [0.4, 0], [0.4, 0.2], [0.2, 0.2], [0.2, 0]]]
                ),
                properties={
                    "land_cover_type": "agricultural",
                    "coverage": 35.0
                },
                source_provider="Copernicus",
                source_category="land_cover"
            ),
            # Forest features
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.4, 0], [0.6, 0], [0.6, 0.2], [0.4, 0.2], [0.4, 0]]]
                ),
                properties={
                    "land_cover_type": "forest",
                    "coverage": 15.0
                },
                source_provider="Copernicus",
                source_category="land_cover"
            ),
            # Grassland features
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.6, 0], [0.8, 0], [0.8, 0.2], [0.6, 0.2], [0.6, 0]]]
                ),
                properties={
                    "land_cover_type": "grassland",
                    "coverage": 5.0
                },
                source_provider="Copernicus",
                source_category="land_cover"
            )
        ]
        
        return StandardizedDataset(
            features=features,
            source_provider="Copernicus",
            category=DataCategory.LAND_COVER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={
                "source": "Copernicus GLC",
                "timestamp": "2024-01-15T10:30:00Z",
                "resolution": "100m"
            }
        )
    
    
    @pytest.fixture
    def empty_land_cover_dataset(self):
        """Create an empty standardized land cover dataset."""
        return StandardizedDataset(
            features=[],
            source_provider="Copernicus",
            category=DataCategory.LAND_COVER,
            feature_count=0,
            crs="EPSG:4326",
            metadata={
                "source": "Copernicus GLC",
                "timestamp": "2024-01-15T10:30:00Z"
            }
        )
    
    
    def test_land_cover_rule_initialization(self, land_cover_rule):
        """Test that LandCoverRule initializes correctly."""
        assert land_cover_rule.rule_id == "LC-001"
        assert land_cover_rule.rule_name == "Land Cover Summary"
        assert DataCategory.LAND_COVER in land_cover_rule.required_categories
    
    
    def test_execute_with_valid_data(self, land_cover_rule, sample_land_cover_dataset):
        """Test rule execution with valid land cover data."""
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        
        result = land_cover_rule.execute(datasets)
        
        # Verify result structure
        assert result.rule_id == "LC-001"
        assert result.status == ProcessingStatus.SUCCESS
        assert isinstance(result.result, dict)
        assert result.metadata["data_points_used"] == 5
        
        # Verify land cover information extracted
        lc_result = result.result
        assert "dominant_land_cover" in lc_result
        assert "dominant_coverage_percentage" in lc_result
        assert "land_cover_summary" in lc_result
        assert "land_cover_categories_detected" in lc_result
        assert "total_categories_identified" in lc_result
        
        # Verify dominant cover identified (should be agricultural with 35%)
        assert lc_result["dominant_land_cover"] in ["agricultural", "urban"]
        assert lc_result["dominant_coverage_percentage"] > 0
    
    
    def test_execute_with_empty_data(self, land_cover_rule, empty_land_cover_dataset):
        """Test rule execution with empty land cover data."""
        datasets = {DataCategory.LAND_COVER: empty_land_cover_dataset}
        
        result = land_cover_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
        assert result.result == {}
    
    
    def test_execute_without_land_cover_dataset(self, land_cover_rule):
        """Test rule execution without land cover dataset."""
        datasets = {}
        
        result = land_cover_rule.execute(datasets)
        
        # Verify insufficient data status
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.metadata["data_points_used"] == 0
    
    
    def test_has_required_data_with_land_cover_data(self, land_cover_rule, sample_land_cover_dataset):
        """Test checking for required data with land cover data present."""
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        
        assert land_cover_rule.has_required_data(datasets) is True
    
    
    def test_has_required_data_without_land_cover_data(self, land_cover_rule):
        """Test checking for required data without land cover data."""
        datasets = {}
        
        assert land_cover_rule.has_required_data(datasets) is False
    
    
    def test_has_required_data_with_empty_land_cover_data(self, land_cover_rule, empty_land_cover_dataset):
        """Test checking for required data with empty land cover data."""
        datasets = {DataCategory.LAND_COVER: empty_land_cover_dataset}
        
        assert land_cover_rule.has_required_data(datasets) is False
    
    
    def test_execute_with_missing_properties(self, land_cover_rule):
        """Test execution with features that have missing land cover type properties."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={},  # Empty properties
                source_provider="Copernicus",
                source_category="land_cover"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.1, 0], [0.2, 0], [0.2, 0.1], [0.1, 0.1], [0.1, 0]]]
                ),
                properties={"land_cover_type": "urban"},
                source_provider="Copernicus",
                source_category="land_cover"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="Copernicus",
            category=DataCategory.LAND_COVER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.LAND_COVER: dataset}
        result = land_cover_rule.execute(datasets)
        
        # Should succeed with partial data
        assert result.status == ProcessingStatus.SUCCESS
        assert result.metadata["data_points_used"] == 2
        assert "urban" in result.result["land_cover_categories_detected"]
        assert "unknown" in result.result["land_cover_categories_detected"]
    
    
    def test_execute_extracts_multiple_categories(self, land_cover_rule, sample_land_cover_dataset):
        """Test that execution correctly extracts multiple land cover categories."""
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        
        result = land_cover_rule.execute(datasets)
        
        # Verify multiple categories extracted
        lc_result = result.result
        categories = lc_result["land_cover_categories_detected"]
        
        # Should have at least 4 categories (urban, agricultural, forest, grassland)
        assert len(categories) >= 4
        assert "urban" in categories or "built-up" in categories
        assert "agricultural" in categories
        assert "forest" in categories
        assert "grassland" in categories
    
    
    def test_dominant_land_cover_identification(self, land_cover_rule, sample_land_cover_dataset):
        """Test that dominant land cover type is correctly identified."""
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        
        result = land_cover_rule.execute(datasets)
        lc_result = result.result
        
        # Verify dominant cover identified
        assert lc_result["dominant_land_cover"] is not None
        assert lc_result["dominant_land_cover"] != "Unknown"
        assert lc_result["dominant_coverage_percentage"] > 0
    
    
    def test_coverage_percentage_calculation(self, land_cover_rule, sample_land_cover_dataset):
        """Test that coverage percentages are calculated correctly."""
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        
        result = land_cover_rule.execute(datasets)
        lc_result = result.result
        
        # Verify coverage percentages
        summary = lc_result["land_cover_summary"]
        total_coverage = sum(cat["percentage"] for cat in summary.values())
        
        # Total should be approximately 100 (within rounding error)
        assert 95 <= total_coverage <= 105
    
    
    def test_land_cover_type_normalization(self, land_cover_rule):
        """Test that land cover type normalization works correctly."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={"land_cover_type": "Urban"},  # Capitalized
                source_provider="Copernicus",
                source_category="land_cover"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.1, 0], [0.2, 0], [0.2, 0.1], [0.1, 0.1], [0.1, 0]]]
                ),
                properties={"land_cover_type": "CROPLAND"},  # All caps
                source_provider="Copernicus",
                source_category="land_cover"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.2, 0], [0.3, 0], [0.3, 0.1], [0.2, 0.1], [0.2, 0]]]
                ),
                properties={"land_cover_type": "  forest  "},  # With spaces
                source_provider="Copernicus",
                source_category="land_cover"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="Copernicus",
            category=DataCategory.LAND_COVER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.LAND_COVER: dataset}
        result = land_cover_rule.execute(datasets)
        
        # Should normalize types
        assert result.status == ProcessingStatus.SUCCESS
        categories = result.result["land_cover_categories_detected"]
        assert "urban" in categories
        assert "agricultural" in categories
        assert "forest" in categories
    
    
    def test_alternative_property_names(self, land_cover_rule):
        """Test that rule handles alternative land cover property names."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={"land_cover": "urban"},  # Alternative name
                source_provider="Provider1",
                source_category="land_cover"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.1, 0], [0.2, 0], [0.2, 0.1], [0.1, 0.1], [0.1, 0]]]
                ),
                properties={"type": "forest"},  # Alternative name
                source_provider="Provider2",
                source_category="land_cover"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.2, 0], [0.3, 0], [0.3, 0.1], [0.2, 0.1], [0.2, 0]]]
                ),
                properties={"category": "grassland"},  # Alternative name
                source_provider="Provider3",
                source_category="land_cover"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="Mixed",
            category=DataCategory.LAND_COVER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.LAND_COVER: dataset}
        result = land_cover_rule.execute(datasets)
        
        # Should handle all property names
        assert result.status == ProcessingStatus.SUCCESS
        categories = result.result["land_cover_categories_detected"]
        assert "urban" in categories
        assert "forest" in categories
        assert "grassland" in categories
    
    
    def test_result_includes_category_counts(self, land_cover_rule, sample_land_cover_dataset):
        """Test that result includes feature counts by category."""
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        
        result = land_cover_rule.execute(datasets)
        lc_result = result.result
        
        # Verify category counts included
        summary = lc_result["land_cover_summary"]
        for category, data in summary.items():
            assert "count" in data
            assert "percentage" in data
            assert isinstance(data["count"], int)
            assert isinstance(data["percentage"], (int, float))
    
    
    def test_result_sorted_by_percentage(self, land_cover_rule, sample_land_cover_dataset):
        """Test that land cover summary is sorted by coverage percentage."""
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        
        result = land_cover_rule.execute(datasets)
        lc_result = result.result
        
        # Get ordered list of categories
        summary = lc_result["land_cover_summary"]
        categories = list(summary.keys())
        percentages = [summary[cat]["percentage"] for cat in categories]
        
        # Verify sorted in descending order
        assert percentages == sorted(percentages, reverse=True)
    
    
    def test_execute_with_single_category(self, land_cover_rule):
        """Test execution when all features are same land cover type."""
        features = [
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
                ),
                properties={"land_cover_type": "forest"},
                source_provider="Copernicus",
                source_category="land_cover"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.1, 0], [0.2, 0], [0.2, 0.1], [0.1, 0.1], [0.1, 0]]]
                ),
                properties={"land_cover_type": "forest"},
                source_provider="Copernicus",
                source_category="land_cover"
            ),
            StandardizedFeature(
                geometry=Geometry(
                    type="Polygon",
                    coordinates=[[[0.2, 0], [0.3, 0], [0.3, 0.1], [0.2, 0.1], [0.2, 0]]]
                ),
                properties={"land_cover_type": "forest"},
                source_provider="Copernicus",
                source_category="land_cover"
            )
        ]
        
        dataset = StandardizedDataset(
            features=features,
            source_provider="Copernicus",
            category=DataCategory.LAND_COVER,
            feature_count=len(features),
            crs="EPSG:4326",
            metadata={}
        )
        
        datasets = {DataCategory.LAND_COVER: dataset}
        result = land_cover_rule.execute(datasets)
        
        # Should succeed with single category
        assert result.status == ProcessingStatus.SUCCESS
        lc_result = result.result
        assert lc_result["dominant_land_cover"] == "forest"
        assert lc_result["dominant_coverage_percentage"] == 100.0
        assert len(lc_result["land_cover_categories_detected"]) == 1
    
    
    def test_metadata_preserved(self, land_cover_rule, sample_land_cover_dataset):
        """Test that metadata is correctly preserved in results."""
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        
        result = land_cover_rule.execute(datasets)
        
        # Verify metadata structure
        assert "data_points_used" in result.metadata
        assert result.metadata["data_points_used"] == 5
    
    
    def test_rule_result_structure(self, land_cover_rule, sample_land_cover_dataset):
        """Test that RuleResult has correct structure."""
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        
        result = land_cover_rule.execute(datasets)
        
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


class TestLandCoverRuleWithRuleEngine:
    """Tests for LandCoverRule integration with RuleEngine."""
    
    def test_land_cover_rule_with_engine(self, sample_land_cover_dataset):
        """Test LandCoverRule works correctly within Rule Engine."""
        from backend.rules.rule_engine import RuleEngine
        
        engine = RuleEngine()
        engine.register_rule(LandCoverRule())
        
        datasets = {DataCategory.LAND_COVER: sample_land_cover_dataset}
        results = engine.execute(datasets)
        
        # Verify rule executed
        assert "LC-001" in results
        result = results["LC-001"]
        assert result.status == ProcessingStatus.SUCCESS
        assert result.result["dominant_land_cover"] is not None


@pytest.fixture
def sample_land_cover_dataset():
    """Create a sample standardized land cover dataset for module-level use."""
    features = [
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1], [0, 0]]]
            ),
            properties={
                "land_cover_type": "urban",
                "coverage": 30.0
            },
            source_provider="Copernicus",
            source_category="land_cover"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.1, 0], [0.2, 0], [0.2, 0.1], [0.1, 0.1], [0.1, 0]]]
            ),
            properties={
                "land_cover_type": "built-up",
                "coverage": 15.0
            },
            source_provider="Copernicus",
            source_category="land_cover"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.2, 0], [0.4, 0], [0.4, 0.2], [0.2, 0.2], [0.2, 0]]]
            ),
            properties={
                "land_cover_type": "agricultural",
                "coverage": 35.0
            },
            source_provider="Copernicus",
            source_category="land_cover"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.4, 0], [0.6, 0], [0.6, 0.2], [0.4, 0.2], [0.4, 0]]]
            ),
            properties={
                "land_cover_type": "forest",
                "coverage": 15.0
            },
            source_provider="Copernicus",
            source_category="land_cover"
        ),
        StandardizedFeature(
            geometry=Geometry(
                type="Polygon",
                coordinates=[[[0.6, 0], [0.8, 0], [0.8, 0.2], [0.6, 0.2], [0.6, 0]]]
            ),
            properties={
                "land_cover_type": "grassland",
                "coverage": 5.0
            },
            source_provider="Copernicus",
            source_category="land_cover"
        )
    ]
    
    return StandardizedDataset(
        features=features,
        source_provider="Copernicus",
        category=DataCategory.LAND_COVER,
        feature_count=len(features),
        crs="EPSG:4326",
        metadata={
            "source": "Copernicus GLC",
            "timestamp": "2024-01-15T10:30:00Z",
            "resolution": "100m"
        }
    )
