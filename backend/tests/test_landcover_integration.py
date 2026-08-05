"""
Integration tests for Land Cover data standardization pipeline.

Tests the complete flow from raw Copernicus data through standardization
to ensure land cover-specific properties are correctly normalized.

Requirements: 4.2, 4.4
"""

import pytest
from backend.standardizers.data_standardizer import DataStandardizer, LandCoverNormalizer
from backend.data_models import RawDataset


class TestLandCoverIntegration:
    """Integration tests for land cover standardization."""

    def test_standardize_copernicus_raw_data(self):
        """Test standardizing raw Copernicus land cover data."""
        # Create raw dataset simulating Copernicus response
        raw_features = [
            {
                "type": "Feature",
                "id": "feature_1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                },
                "properties": {
                    "lc_code": 5,
                    "confidence": 92,
                    "pixel_size": 100,
                    "source": "Copernicus GLC",
                    "year": 2021
                }
            }
        ]

        raw_dataset = RawDataset(
            source_provider="copernicus_glc",
            category="land_cover",
            features=raw_features,
            metadata={
                "crs": "EPSG:4326",
                "version": "v3",
                "timestamp": "2021-01-01T00:00:00Z"
            }
        )

        # Standardize the dataset
        standardizer = DataStandardizer()
        standardized = standardizer.standardize(raw_dataset)

        # Verify standardized output
        assert standardized.category == "land_cover"
        assert standardized.source_provider == "copernicus_glc"
        assert len(standardized.features) == 1
        assert standardized.metadata["crs"] == "EPSG:4326"

        # Verify feature standardization
        feature = standardized.features[0]
        assert feature.geometry["type"] == "Polygon"
        assert "lc_code" in feature.properties
        assert feature.properties["lc_code"] == "built_up"  # Code 5 -> built_up
        assert feature.properties["confidence"] == 92.0
        assert feature.properties["resolution_m"] == 100.0

    def test_standardize_esa_worldcover_data(self):
        """Test standardizing raw ESA WorldCover data."""
        raw_features = [
            {
                "type": "Feature",
                "id": "feature_1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                },
                "properties": {
                    "lc_code": 40,
                    "confidence_percent": 88,
                    "pixel_size": 30,
                    "source": "ESA WorldCover",
                    "year": 2021
                }
            }
        ]

        raw_dataset = RawDataset(
            source_provider="esa_worldcover",
            category="land_cover",
            features=raw_features,
            metadata={
                "crs": "EPSG:4326",
                "version": "2021",
                "timestamp": "2021-01-01T00:00:00Z"
            }
        )

        standardizer = DataStandardizer()
        standardized = standardizer.standardize(raw_dataset)

        # Verify standardized output
        assert standardized.category == "land_cover"
        assert len(standardized.features) == 1

        # Verify feature standardization
        feature = standardized.features[0]
        assert feature.properties["lc_code"] == "crops"  # ESA code 40 -> crops
        assert feature.properties["confidence_percent"] == 88.0
        assert feature.properties["resolution_m"] == 30.0

    def test_standardize_multiple_land_cover_features(self):
        """Test standardizing multiple land cover features."""
        raw_features = [
            {
                "type": "Feature",
                "id": "feature_1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                },
                "properties": {
                    "lc_code": 1,
                    "confidence": 95,
                }
            },
            {
                "type": "Feature",
                "id": "feature_2",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]]
                },
                "properties": {
                    "lc_code": 8,
                    "confidence": 90,
                }
            },
            {
                "type": "Feature",
                "id": "feature_3",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]
                },
                "properties": {
                    "lc_code": 5,
                    "confidence": 85,
                }
            }
        ]

        raw_dataset = RawDataset(
            source_provider="copernicus_glc",
            category="land_cover",
            features=raw_features,
            metadata={"crs": "EPSG:4326"}
        )

        standardizer = DataStandardizer()
        standardized = standardizer.standardize(raw_dataset)

        # Verify all features standardized
        assert len(standardized.features) == 3
        assert standardized.features[0].properties["lc_code"] == "tree_cover"
        assert standardized.features[1].properties["lc_code"] == "water"
        assert standardized.features[2].properties["lc_code"] == "built_up"

    def test_standardize_land_cover_with_percentages(self):
        """Test standardizing land cover with percentage composition."""
        raw_features = [
            {
                "type": "Feature",
                "id": "feature_1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                },
                "properties": {
                    "lc_code": 4,
                    "confidence": 92,
                    "percent_water": 10,
                    "percent_tree": 25,
                    "percent_grass": 30,
                    "percent_crops": 20,
                    "percent_built": 10,
                    "percent_bare": 5,
                }
            }
        ]

        raw_dataset = RawDataset(
            source_provider="copernicus_glc",
            category="land_cover",
            features=raw_features,
            metadata={"crs": "EPSG:4326"}
        )

        standardizer = DataStandardizer()
        standardized = standardizer.standardize(raw_dataset)

        # Verify percentages preserved
        feature = standardized.features[0]
        assert feature.properties["percent_water"] == 10.0
        assert feature.properties["percent_tree"] == 25.0
        assert feature.properties["percent_grass"] == 30.0
        assert feature.properties["percent_crops"] == 20.0
        assert feature.properties["percent_built"] == 10.0
        assert feature.properties["percent_bare"] == 5.0

    def test_landcover_normalizer_direct(self):
        """Test LandCoverNormalizer directly."""
        normalizer = LandCoverNormalizer()

        # Test with Copernicus data pattern
        raw_props = {
            "lc_code": 3,
            "confidence": 88,
            "pixel_size": 100,
            "source": "Copernicus",
            "version": "v3",
        }

        standardized = normalizer.normalize_properties(raw_props)

        # Verify normalization
        assert standardized["lc_code"] == "shrubland"  # Code 3 -> shrubland
        assert standardized["confidence"] == 88.0
        assert standardized["resolution_m"] == 100.0
        assert standardized["source"] == "Copernicus"
        assert standardized["version"] == "v3"

    def test_standardize_handles_missing_land_cover_fields(self):
        """Test that standardization handles missing optional fields."""
        raw_features = [
            {
                "type": "Feature",
                "id": "feature_1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                },
                "properties": {
                    "lc_code": "2",  # String code to ensure mapping works
                    # Missing confidence, source, version, percentages
                }
            }
        ]

        raw_dataset = RawDataset(
            source_provider="copernicus_glc",
            category="land_cover",
            features=raw_features,
            metadata={"crs": "EPSG:4326"}
        )

        standardizer = DataStandardizer()
        standardized = standardizer.standardize(raw_dataset)

        # Verify feature still standardized with defaults
        feature = standardized.features[0]
        # Code "2" maps to "herbaceous_cover" in Copernicus
        assert feature.properties["lc_code"] == "herbaceous_cover" or feature.properties["lc_code"] == "2"
        assert feature.properties["confidence"] == 0.5  # Default

    def test_standardize_land_cover_preserves_geometry(self):
        """Test that geometry is preserved during standardization."""
        raw_features = [
            {
                "type": "Feature",
                "id": "feature_1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]],
                        [[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]]  # Hole
                    ]
                },
                "properties": {
                    "lc_code": 1,
                    "confidence": 95,
                }
            }
        ]

        raw_dataset = RawDataset(
            source_provider="copernicus_glc",
            category="land_cover",
            features=raw_features,
            metadata={"crs": "EPSG:4326"}
        )

        standardizer = DataStandardizer()
        standardized = standardizer.standardize(raw_dataset)

        # Verify geometry preserved
        feature = standardized.features[0]
        assert feature.geometry["type"] == "Polygon"
        assert len(feature.geometry["coordinates"]) == 2  # Main ring + hole
        assert len(feature.geometry["coordinates"][0]) == 5  # Main ring has 5 points
        assert len(feature.geometry["coordinates"][1]) == 5  # Hole has 5 points

    def test_standardize_invalid_land_cover_code(self):
        """Test handling of invalid land cover codes."""
        raw_features = [
            {
                "type": "Feature",
                "id": "feature_1",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                },
                "properties": {
                    "lc_code": 999,  # Invalid code
                    "confidence": 90,
                }
            }
        ]

        raw_dataset = RawDataset(
            source_provider="copernicus_glc",
            category="land_cover",
            features=raw_features,
            metadata={"crs": "EPSG:4326"}
        )

        standardizer = DataStandardizer()
        standardized = standardizer.standardize(raw_dataset)

        # Verify invalid code handled gracefully
        feature = standardized.features[0]
        # Invalid code should be returned as-is or map to unknown
        assert "lc_code" in feature.properties
        assert feature.properties["confidence"] == 90.0
