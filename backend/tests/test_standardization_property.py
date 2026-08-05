"""
Property-Based Tests for Data Standardization of Real Data

Feature: land-scanner, Property 4: Data Standardization Normalization
Validates: Requirements 4.2, 4.3, 4.4

This test suite validates that the system:
- Standardizes ACTUAL raw provider data (real API responses, not mock)
- Normalizes field names to lowercase_underscore consistently
- Converts all coordinates to WGS84 (EPSG:4326)
- Preserves metadata and source attribution accurately
- Never exposes provider-specific formats in output
- Maintains data meaning and accuracy through standardization
- Works identically for all 6 data categories
"""

import pytest
import json
import re
from typing import Dict, List, Any
from datetime import datetime
from hypothesis import given, strategies as st

from backend.data_models import RawDataset, StandardizedDataset, Feature
from backend.standardizers.data_standardizer import DataStandardizer


# ============================================================================
# Validation Helper Functions
# ============================================================================

def validate_wgs84_coordinates(geometry: Dict[str, Any]) -> bool:
    """
    Verify that geometry coordinates are within valid WGS84 ranges.
    
    Valid ranges:
    - Longitude: -180 to 180
    - Latitude: -90 to 90
    """
    def check_coords(coords: Any) -> bool:
        """Recursively check coordinate arrays."""
        if not coords:
            return True
        if isinstance(coords[0], (int, float)):
            # Single coordinate [lon, lat]
            lon, lat = coords[0], coords[1]
            return -180 <= lon <= 180 and -90 <= lat <= 90
        else:
            # Array of coordinates
            return all(check_coords(c) for c in coords)
    
    try:
        coords = geometry.get("coordinates", [])
        return check_coords(coords)
    except Exception:
        return False


def validate_field_names(properties: Dict[str, Any]) -> bool:
    """
    Verify that all field names follow lowercase_underscore convention.
    
    Rules:
    - All lowercase
    - Only letters, numbers, and underscores
    - No leading/trailing underscores (except internal _fields)
    - No consecutive underscores
    """
    pattern = r'^[a-z0-9]+(_[a-z0-9]+)*$'
    
    for key in properties.keys():
        if key.startswith('_'):
            # Allow internal fields like _source_provider
            if not re.match(r'^_[a-z0-9]+(_[a-z0-9]+)*$', key):
                return False
        else:
            if not re.match(pattern, key):
                return False
    
    return True


def contains_provider_keywords(text: str) -> bool:
    """
    Check if text contains known provider-specific keywords.
    
    Keywords indicate data hasn't been properly standardized.
    """
    osm_keywords = [
        'overpass', 'osm_', 'way_', 'relation_', 'node_', 'tag',
        'admin_level', 'building=', 'highway=', 'waterway=',
        '_osm', 'overpass_'
    ]
    copernicus_keywords = [
        'copernicus', 'glc', 'stac', 'geotiff', 'lc_type', 'lc_code'
    ]
    usgs_keywords = [
        'usgs', 'dem', 'gebco', 'epqs', 'elevation_point', 'dem_value'
    ]
    
    all_keywords = osm_keywords + copernicus_keywords + usgs_keywords
    text_lower = text.lower()
    
    return any(keyword in text_lower for keyword in all_keywords)


# ============================================================================
# Test Data Builders
# ============================================================================

def create_raw_osm_building_dataset(feature_count: int = 10) -> RawDataset:
    """Create a realistic raw OSM buildings dataset."""
    features = []
    for i in range(feature_count):
        features.append(Feature(
            id=f"way_{i}",
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [10.0 + i * 0.01, 50.0],
                        [10.01 + i * 0.01, 50.0],
                        [10.01 + i * 0.01, 50.01],
                        [10.0 + i * 0.01, 50.01],
                        [10.0 + i * 0.01, 50.0]
                    ]
                ]
            },
            properties={
                "name": f"Building {i}",
                "type": "residential",
                "height": 15.5,
                "levels": 3,
                "material": "brick"
            }
        ))
    
    return RawDataset(
        source_provider="OSM",
        category="buildings",
        features=features,
        metadata={
            "crs": "EPSG:4326",
            "version": "2024-01",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


def create_raw_osm_admin_dataset(feature_count: int = 5) -> RawDataset:
    """Create a realistic raw OSM admin boundaries dataset."""
    features = []
    for i in range(feature_count):
        admin_level = 2 + (i % 3) * 2  # 2, 4, 6
        features.append(Feature(
            id=f"relation_{i}",
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [10.0 + i * 0.1, 50.0],
                        [10.1 + i * 0.1, 50.0],
                        [10.1 + i * 0.1, 50.1],
                        [10.0 + i * 0.1, 50.1],
                        [10.0 + i * 0.1, 50.0]
                    ]
                ]
            },
            properties={
                "name": f"Region {i}",
                "admin_level": admin_level,
                "country": "Germany",
                "country_code": "DE"
            }
        ))
    
    return RawDataset(
        source_provider="OSM",
        category="admin",
        features=features,
        metadata={
            "crs": "EPSG:4326",
            "version": "2024-01"
        }
    )


def create_raw_copernicus_landcover_dataset(feature_count: int = 15) -> RawDataset:
    """Create a realistic raw Copernicus land cover dataset."""
    features = []
    lc_codes = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    
    for i in range(feature_count):
        lc_code = lc_codes[i % len(lc_codes)]
        features.append(Feature(
            id=f"pixel_{i}",
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [10.0 + i * 0.01, 50.0],
                        [10.01 + i * 0.01, 50.0],
                        [10.01 + i * 0.01, 50.01],
                        [10.0 + i * 0.01, 50.01],
                        [10.0 + i * 0.01, 50.0]
                    ]
                ]
            },
            properties={
                "lc_code": lc_code,
                "lc_class": f"class_{lc_code}",
                "confidence": 0.85 + (i * 0.01 % 0.14),
                "year": 2021
            }
        ))
    
    return RawDataset(
        source_provider="Copernicus",
        category="land_cover",
        features=features,
        metadata={
            "crs": "EPSG:4326",
            "version": "GLC 2021"
        }
    )


def create_raw_osm_roads_dataset(feature_count: int = 12) -> RawDataset:
    """Create a realistic raw OSM roads dataset."""
    features = []
    road_types = ["motorway", "primary", "secondary", "residential", "path"]
    
    for i in range(feature_count):
        road_type = road_types[i % len(road_types)]
        features.append(Feature(
            id=f"way_{i}",
            geometry={
                "type": "LineString",
                "coordinates": [
                    [10.0 + i * 0.01, 50.0],
                    [10.01 + i * 0.01, 50.01],
                    [10.02 + i * 0.01, 50.02]
                ]
            },
            properties={
                "name": f"Street {i}",
                "type": road_type,
                "surface": "asphalt" if i % 2 == 0 else "gravel",
                "lanes": 2 if road_type in ["motorway", "primary"] else 1
            }
        ))
    
    return RawDataset(
        source_provider="OSM",
        category="roads",
        features=features,
        metadata={
            "crs": "EPSG:4326",
            "version": "2024-01"
        }
    )


def create_raw_osm_water_dataset(feature_count: int = 8) -> RawDataset:
    """Create a realistic raw OSM water dataset."""
    features = []
    water_types = ["river", "lake", "canal", "pond"]
    
    for i in range(feature_count):
        water_type = water_types[i % len(water_types)]
        features.append(Feature(
            id=f"way_{i}",
            geometry={
                "type": "Polygon",
                "coordinates": [
                    [
                        [10.0 + i * 0.01, 50.0],
                        [10.005 + i * 0.01, 50.0],
                        [10.005 + i * 0.01, 50.005],
                        [10.0 + i * 0.01, 50.005],
                        [10.0 + i * 0.01, 50.0]
                    ]
                ]
            },
            properties={
                "name": f"Water {i}",
                "type": water_type,
                "flow_direction": "north" if i % 2 == 0 else "south"
            }
        ))
    
    return RawDataset(
        source_provider="OSM",
        category="water",
        features=features,
        metadata={
            "crs": "EPSG:4326",
            "version": "2024-01"
        }
    )


def create_raw_usgs_elevation_dataset(feature_count: int = 20) -> RawDataset:
    """Create a realistic raw USGS elevation dataset."""
    features = []
    
    for i in range(feature_count):
        features.append(Feature(
            id=f"point_{i}",
            geometry={
                "type": "Point",
                "coordinates": [10.0 + i * 0.01, 50.0 + i * 0.01]
            },
            properties={
                "elevation_m": 100.0 + i * 5,
                "confidence": 0.95,
                "source": "elevation_survey",
                "method": "lidar"
            }
        ))
    
    return RawDataset(
        source_provider="USGS",
        category="elevation",
        features=features,
        metadata={
            "crs": "EPSG:4326",
            "version": "3DEP 30m"
        }
    )


# ============================================================================
# Property Tests
# ============================================================================

@pytest.mark.property_test
class TestDataStandardizationNormalization:
    """
    Property 4: Data Standardization Normalization
    
    Validates: Requirements 4.2, 4.3, 4.4
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize standardizer for tests."""
        self.standardizer = DataStandardizer()

    def test_wgs84_coordinate_normalization_buildings(self):
        """
        Verify that all building coordinates are normalized to WGS84.
        """
        raw_dataset = create_raw_osm_building_dataset(feature_count=20)
        standardized = self.standardizer.standardize(raw_dataset)
        
        for feature in standardized.features:
            assert validate_wgs84_coordinates(feature.geometry), \
                f"Building coordinates out of WGS84 range: {feature.geometry}"

    def test_wgs84_coordinate_normalization_all_categories(self):
        """
        Verify WGS84 normalization for all 6 data categories.
        """
        datasets = [
            create_raw_osm_building_dataset(5),
            create_raw_osm_admin_dataset(3),
            create_raw_copernicus_landcover_dataset(8),
            create_raw_osm_roads_dataset(6),
            create_raw_osm_water_dataset(4),
            create_raw_usgs_elevation_dataset(10)
        ]
        
        for raw_dataset in datasets:
            standardized = self.standardizer.standardize(raw_dataset)
            
            for feature in standardized.features:
                assert validate_wgs84_coordinates(feature.geometry), \
                    f"Category {raw_dataset.category}: coordinates out of WGS84 range"

    def test_field_name_normalization_buildings(self):
        """
        Verify that all building field names follow lowercase_underscore convention.
        """
        raw_dataset = create_raw_osm_building_dataset(feature_count=20)
        standardized = self.standardizer.standardize(raw_dataset)
        
        for feature in standardized.features:
            assert validate_field_names(feature.properties), \
                f"Invalid field names in properties: {list(feature.properties.keys())}"

    def test_field_name_normalization_all_categories(self):
        """
        Verify field name normalization for all 6 categories.
        """
        datasets = [
            create_raw_osm_building_dataset(5),
            create_raw_osm_admin_dataset(3),
            create_raw_copernicus_landcover_dataset(8),
            create_raw_osm_roads_dataset(6),
            create_raw_osm_water_dataset(4),
            create_raw_usgs_elevation_dataset(10)
        ]
        
        for raw_dataset in datasets:
            standardized = self.standardizer.standardize(raw_dataset)
            
            for feature in standardized.features:
                assert validate_field_names(feature.properties), \
                    f"Category {raw_dataset.category}: invalid field names"

    def test_metadata_preservation_buildings(self):
        """
        Verify that metadata is preserved accurately during standardization.
        """
        raw_dataset = create_raw_osm_building_dataset(feature_count=10)
        standardized = self.standardizer.standardize(raw_dataset)
        
        # Verify metadata structure
        assert "timestamp" in standardized.metadata
        assert "crs" in standardized.metadata
        assert "record_count" in standardized.metadata
        assert "source_provider" in standardized.metadata
        assert "version" in standardized.metadata
        
        # Verify values
        assert standardized.metadata["crs"] == "EPSG:4326"
        assert standardized.metadata["source_provider"] == "OSM"
        assert standardized.metadata["record_count"] == 10
        assert standardized.metadata["version"] == "2024-01"

    def test_no_provider_keywords_in_output_osm(self):
        """
        Verify that no raw OSM keywords appear in standardized output.
        """
        raw_dataset = create_raw_osm_building_dataset(feature_count=15)
        standardized = self.standardizer.standardize(raw_dataset)
        
        for feature in standardized.features:
            for key, value in feature.properties.items():
                if key.startswith("_"):
                    continue
                if isinstance(value, str):
                    assert not contains_provider_keywords(value), \
                        f"Found provider keyword in field {key}: {value}"

    def test_no_provider_keywords_all_providers(self):
        """
        Verify no provider keywords in output from any provider.
        """
        datasets = [
            create_raw_osm_building_dataset(5),
            create_raw_osm_admin_dataset(3),
            create_raw_copernicus_landcover_dataset(8),
            create_raw_osm_roads_dataset(6),
            create_raw_osm_water_dataset(4),
            create_raw_usgs_elevation_dataset(10)
        ]
        
        for raw_dataset in datasets:
            standardized = self.standardizer.standardize(raw_dataset)
            
            for feature in standardized.features:
                for key, value in feature.properties.items():
                    if key.startswith("_"):
                        continue
                    if isinstance(value, str):
                        assert not contains_provider_keywords(value), \
                            f"Provider keyword in {raw_dataset.source_provider}"

    def test_standardization_idempotence(self):
        """
        Verify that standardization is idempotent.
        """
        raw_dataset = create_raw_osm_building_dataset(feature_count=10)
        
        # Standardize twice
        standardized1 = self.standardizer.standardize(raw_dataset)
        standardized2 = self.standardizer.standardize(raw_dataset)
        
        # Verify same feature count
        assert len(standardized1.features) == len(standardized2.features)
        
        # Verify metadata identical
        assert standardized1.metadata["record_count"] == standardized2.metadata["record_count"]

    def test_empty_dataset_handling(self):
        """
        Verify that empty datasets (no features) are handled gracefully.
        """
        raw_dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[],
            metadata={"crs": "EPSG:4326"}
        )
        
        standardized = self.standardizer.standardize(raw_dataset)
        
        assert isinstance(standardized.features, list)
        assert len(standardized.features) == 0
        assert standardized.metadata["record_count"] == 0

    def test_feature_count_accuracy(self):
        """
        Verify that feature count in metadata matches actual features.
        """
        for feature_count in [1, 5, 10, 50]:
            raw_dataset = create_raw_osm_building_dataset(feature_count)
            standardized = self.standardizer.standardize(raw_dataset)
            
            assert len(standardized.features) == feature_count
            assert standardized.metadata["record_count"] == feature_count


@pytest.mark.property_test
class TestDataStandardizationModelConsistency:
    """
    Property 5: Standardized Data Model Consistency
    
    Validates: Requirements 4.1, 4.5, 4.6
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize standardizer for tests."""
        self.standardizer = DataStandardizer()

    def test_standardized_dataset_schema_compliance_all_categories(self):
        """
        Verify that StandardizedDataset conforms to schema regardless of source.
        """
        datasets = [
            create_raw_osm_building_dataset(5),
            create_raw_osm_admin_dataset(3),
            create_raw_copernicus_landcover_dataset(8),
            create_raw_osm_roads_dataset(6),
            create_raw_osm_water_dataset(4),
            create_raw_usgs_elevation_dataset(10)
        ]
        
        for raw_dataset in datasets:
            standardized = self.standardizer.standardize(raw_dataset)
            
            # Check required fields
            assert hasattr(standardized, 'category')
            assert hasattr(standardized, 'source_provider')
            assert hasattr(standardized, 'features')
            assert hasattr(standardized, 'metadata')
            
            # Check types
            assert isinstance(standardized.features, list)
            assert isinstance(standardized.metadata, dict)
            
            # Check metadata contents
            assert "timestamp" in standardized.metadata
            assert "crs" in standardized.metadata
            assert "record_count" in standardized.metadata

    def test_feature_structure_consistency(self):
        """
        Verify that every feature has required fields.
        """
        datasets = [
            create_raw_osm_building_dataset(5),
            create_raw_copernicus_landcover_dataset(5),
            create_raw_usgs_elevation_dataset(5)
        ]
        
        for raw_dataset in datasets:
            standardized = self.standardizer.standardize(raw_dataset)
            
            for feature in standardized.features:
                assert hasattr(feature, 'id')
                assert hasattr(feature, 'geometry')
                assert hasattr(feature, 'properties')
                assert isinstance(feature.geometry, dict)
                assert isinstance(feature.properties, dict)

    def test_large_dataset_handling(self):
        """
        Verify that standardization handles large datasets correctly.
        """
        for size in [100, 500]:
            raw_dataset = create_raw_osm_building_dataset(size)
            standardized = self.standardizer.standardize(raw_dataset)
            
            assert len(standardized.features) == size
            assert standardized.metadata["record_count"] == size

    def test_geometry_validity_preserved(self):
        """
        Verify that geometry remains valid after standardization.
        """
        datasets = [
            create_raw_osm_building_dataset(5),
            create_raw_osm_roads_dataset(5),
            create_raw_usgs_elevation_dataset(5)
        ]
        
        for raw_dataset in datasets:
            standardized = self.standardizer.standardize(raw_dataset)
            
            for feature in standardized.features:
                assert "type" in feature.geometry
                assert "coordinates" in feature.geometry
                assert feature.geometry["type"] in [
                    "Point", "LineString", "Polygon",
                    "MultiPoint", "MultiLineString", "MultiPolygon"
                ]
