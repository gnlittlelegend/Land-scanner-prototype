"""
Property-based tests for data standardization module.

Feature: land-scanner
Tests: Property 4 and Property 5

These tests verify that the standardization process correctly normalizes
diverse provider formats into a common internal schema while preserving
data integrity and ensuring consistent output regardless of source.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from datetime import datetime

from backend.models.schemas import (
    RawDataset,
    StandardizedDataset,
    DataCategory,
    Feature,
)
from backend.standardizers.standardizer import Standardizer, StandardizationError


# ============================================================================
# Strategy Definitions for Hypothesis
# ============================================================================

# Simplified strategies that generate data quickly
@st.composite
def geojson_point_geometry(draw):
    """Generate random GeoJSON Point geometries."""
    lon = draw(st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False))
    lat = draw(st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False))
    return {
        "type": "Point",
        "coordinates": [lon, lat]
    }


@st.composite
def geojson_linestring_geometry(draw):
    """Generate random GeoJSON LineString geometries."""
    num_points = draw(st.integers(min_value=2, max_value=5))
    coords = []
    for _ in range(num_points):
        lon = draw(st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False))
        lat = draw(st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False))
        coords.append([lon, lat])
    
    return {
        "type": "LineString",
        "coordinates": coords
    }


@st.composite
def geojson_polygon_geometry(draw):
    """Generate random GeoJSON Polygon geometries."""
    # Create a simple polygon (4-5 points in a ring)
    coords = []
    for _ in range(4):
        lon = draw(st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False))
        lat = draw(st.floats(min_value=-10, max_value=10, allow_nan=False, allow_infinity=False))
        coords.append([lon, lat])
    
    # Close the ring
    coords.append(coords[0])
    
    return {
        "type": "Polygon",
        "coordinates": [coords]
    }


@st.composite
def geojson_geometry(draw):
    """Generate random GeoJSON geometries."""
    geom_type = draw(st.sampled_from([
        geojson_point_geometry(),
        geojson_linestring_geometry(),
        geojson_polygon_geometry(),
    ]))
    return geom_type


@st.composite
def raw_feature(draw):
    """Generate a single raw feature."""
    feature_id = draw(st.one_of(
        st.integers(min_value=0, max_value=10000),
        st.text(min_size=1, max_size=10, alphabet=st.characters(blacklist_categories=('Cc', 'Cs'), blacklist_characters='/:'))
    ))
    
    geometry = draw(st.one_of(
        geojson_point_geometry(),
        geojson_linestring_geometry(),
        geojson_polygon_geometry(),
    ))
    
    # Simple properties - use valid characters only
    properties = {}
    for i in range(draw(st.integers(min_value=1, max_value=3))):
        # Only use alphanumeric characters for keys, must start with letter
        key = draw(st.text(
            min_size=2, 
            max_size=15, 
            alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
        ).filter(lambda k: k and k[0].isalpha()))  # Ensure non-empty and starts with letter
        value = draw(st.one_of(
            st.text(max_size=20),
            st.integers(),
            st.booleans(),
        ))
        # Only add non-empty values
        if value != "" and key:
            properties[key] = value
    
    return {
        "id": feature_id,
        "geometry": geometry,
        "properties": properties
    }


@st.composite
def raw_dataset(draw):
    """Generate a random raw dataset from a provider."""
    provider = draw(st.sampled_from([
        "osm_buildings",
        "copernicus_landcover",
        "usgs_elevation",
        "esa_landcover",
        "admin_boundaries",
    ]))
    
    category = draw(st.sampled_from(list(DataCategory)))
    
    # Generate 1-5 features
    num_features = draw(st.integers(min_value=1, max_value=5))
    features = [draw(raw_feature()) for _ in range(num_features)]
    
    return RawDataset(
        source_provider=provider,
        category=category,
        geometry_type=draw(st.sampled_from(["Point", "LineString", "Polygon"])),
        features=features,
        metadata={
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


# ============================================================================
# Property 4: Data Standardization Normalization
# ============================================================================

class TestDataStandardizationNormalization:
    """
    Property 4: Data Standardization Normalization
    
    For any raw dataset from any provider, after standardization, all
    coordinate systems should be normalized to WGS84 (EPSG:4326), and
    all field names should use consistent lowercase underscore convention
    regardless of the original provider format.
    
    Feature: land-scanner, Property 4: Data Standardization Normalization
    Validates: Requirements 4.2, 4.3, 4.4
    """

    @given(raw_dataset())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_all_standardized_datasets_use_wgs84(self, dataset):
        """
        All standardized datasets should use WGS84 (EPSG:4326) coordinates.
        
        This property verifies that after standardization:
        - The metadata includes crs="EPSG:4326"
        - All coordinate values are within WGS84 valid ranges
        """
        standardizer = Standardizer()
        standardized = standardizer.standardize(dataset)
        
        # Verify CRS is WGS84
        assert standardized.metadata.get("crs") == "EPSG:4326"
        
        # Verify all coordinates are in WGS84 range
        for feature in standardized.features:
            geometry = feature.geometry
            self._verify_wgs84_coordinates(geometry)

    def _verify_wgs84_coordinates(self, geometry):
        """Verify all coordinates in geometry are within WGS84 valid ranges."""
        coords = geometry.get("coordinates", [])
        geom_type = geometry.get("type")
        
        if geom_type == "Point":
            lon, lat = coords
            assert -180 <= lon <= 180
            assert -90 <= lat <= 90
        
        elif geom_type == "LineString":
            for lon, lat in coords:
                assert -180 <= lon <= 180
                assert -90 <= lat <= 90
        
        elif geom_type == "Polygon":
            for ring in coords:
                for lon, lat in ring:
                    assert -180 <= lon <= 180
                    assert -90 <= lat <= 90

    @given(raw_dataset())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_all_property_names_normalized_to_lowercase_underscore(self, dataset):
        """
        All property field names should be normalized to lowercase with underscores.
        """
        standardizer = Standardizer()
        standardized = standardizer.standardize(dataset)
        
        for feature in standardized.features:
            properties = feature.properties
            
            for key in properties.keys():
                # Property names should be lowercase
                assert key == key.lower()
                
                # Property names should not contain spaces
                assert " " not in key
                
                # Property names should not contain hyphens
                assert "-" not in key
                
                # All valid characters
                assert all(c.isalnum() or c == "_" for c in key)

    @given(raw_dataset())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_standardized_output_field_consistency_across_providers(self, dataset):
        """
        Field names should be normalized consistently regardless of source provider.
        """
        standardizer = Standardizer()
        standardized = standardizer.standardize(dataset)
        
        for feature in standardized.features:
            properties = feature.properties
            
            # Should have source provider attribution
            assert "_source_provider" in properties
            
            # Should have category
            assert "_category" in properties
            
            # All property keys should follow lowercase_underscore pattern
            for key in properties.keys():
                if key.startswith("_"):
                    continue
                
                assert key.islower() or "_" in key or key.isdigit()


# ============================================================================
# Property 5: Standardized Data Model Consistency
# ============================================================================

class TestStandardizedDataModelConsistency:
    """
    Property 5: Standardized Data Model Consistency
    
    For any standardized dataset regardless of source provider, the output
    should conform to the StandardizedDataset schema with category,
    source_provider, features array, and metadata fields always present
    and correctly formatted.
    
    Feature: land-scanner, Property 5: Standardized Data Model Consistency
    Validates: Requirements 4.1, 4.5, 4.6
    """

    @given(raw_dataset())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_standardized_dataset_schema_compliance(self, dataset):
        """
        All standardized datasets must conform to StandardizedDataset schema.
        """
        standardizer = Standardizer()
        standardized = standardizer.standardize(dataset)
        
        # Verify type
        assert isinstance(standardized, StandardizedDataset)
        
        # Verify all required fields present
        assert standardized.category is not None
        assert standardized.source_provider is not None
        assert standardized.features is not None
        assert standardized.metadata is not None
        
        # Verify field types
        assert isinstance(standardized.category, DataCategory)
        assert isinstance(standardized.source_provider, str)
        assert isinstance(standardized.features, list)
        assert isinstance(standardized.metadata, dict)

    @given(raw_dataset())
    @settings(deadline=None, max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_standardized_features_conform_to_feature_schema(self, dataset):
        """
        All features must conform to the Feature schema.
        """
        standardizer = Standardizer()
        standardized = standardizer.standardize(dataset)
        
        for feature in standardized.features:
            # Verify type
            assert isinstance(feature, Feature)
            
            # Verify required fields
            assert feature.id is not None and feature.id != ""
            assert feature.geometry is not None
            assert feature.properties is not None
            
            # Verify field types
            assert isinstance(feature.id, str)
            assert isinstance(feature.geometry, dict)
            assert isinstance(feature.properties, dict)
            
            # Verify geometry structure
            assert "type" in feature.geometry
            assert "coordinates" in feature.geometry
            assert feature.geometry["type"] in [
                "Point", "LineString", "Polygon",
                "MultiPoint", "MultiLineString", "MultiPolygon"
            ]

    @given(raw_dataset())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_metadata_contains_required_fields(self, dataset):
        """
        All metadata must contain required standardized fields.
        """
        standardizer = Standardizer()
        standardized = standardizer.standardize(dataset)
        
        metadata = standardized.metadata
        
        # Verify required fields
        assert "timestamp" in metadata
        assert "crs" in metadata
        assert "record_count" in metadata
        assert "source_provider" in metadata
        
        # Verify CRS is WGS84
        assert metadata["crs"] == "EPSG:4326"
        
        # Verify record_count matches features
        assert metadata["record_count"] == len(standardized.features)
        
        # Verify source_provider matches input
        assert metadata["source_provider"] == dataset.source_provider

    @given(raw_dataset())
    @settings(deadline=None, max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_category_never_exposes_raw_provider_formats(self, dataset):
        """
        Standardized output should never expose raw provider-specific formats.
        """
        standardizer = Standardizer()
        standardized = standardizer.standardize(dataset)
        
        # Verify category is standardized
        assert standardized.category in DataCategory.__members__.values()
        
        # Verify no raw provider-specific markers in features
        for feature in standardized.features:
            properties = feature.properties
            
            # Check property names are normalized
            for key in properties.keys():
                if key.startswith("_"):
                    continue
                
                # Should not have provider-specific prefixes
                assert not key.startswith("osm_") or key == "osm_id"
                assert not key.startswith("copernicus_")
                assert not key.startswith("esa_")
                assert not key.startswith("usgs_")

    @given(raw_dataset())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_standardized_output_is_consistent_across_invocations(self, dataset):
        """
        Standardizing the same dataset multiple times should produce consistent results.
        """
        standardizer = Standardizer()
        
        # Standardize twice
        standardized_1 = standardizer.standardize(dataset)
        standardized_2 = standardizer.standardize(dataset)
        
        # Verify same structure
        assert len(standardized_1.features) == len(standardized_2.features)
        assert standardized_1.category == standardized_2.category
        assert standardized_1.source_provider == standardized_2.source_provider
        
        # Verify features have same property keys
        for f1, f2 in zip(standardized_1.features, standardized_2.features):
            assert set(f1.properties.keys()) == set(f2.properties.keys())
            assert set(f1.geometry.keys()) == set(f2.geometry.keys())


# ============================================================================
# Integration Tests
# ============================================================================

class TestStandardizationIntegration:
    """Integration tests for standardization with realistic data."""

    def test_standardizer_handles_empty_features_gracefully(self):
        """Standardizer should handle datasets with empty feature lists."""
        standardizer = Standardizer()
        
        raw_dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Polygon",
            features=[],
            metadata={"version": "1.0"}
        )
        
        standardized = standardizer.standardize(raw_dataset)
        
        assert standardized.features == []
        assert standardized.metadata["record_count"] == 0

    def test_standardizer_preserves_source_attribution(self):
        """Standardizer should preserve provider attribution in output."""
        standardizer = Standardizer()
        
        raw_dataset = RawDataset(
            source_provider="osm_buildings",
            category=DataCategory.BUILDINGS,
            geometry_type="Polygon",
            features=[{
                "id": "test_1",
                "geometry": {
                    "type": "Point",
                    "coordinates": [0.0, 0.0]
                },
                "properties": {"name": "Test Building"}
            }],
            metadata={"version": "1.0"}
        )
        
        standardized = standardizer.standardize(raw_dataset)
        
        assert standardized.source_provider == "osm_buildings"
        assert standardized.features[0].properties["_source_provider"] == "osm_buildings"

    def test_standardizer_handles_mixed_property_types(self):
        """Standardizer should handle mixed property value types correctly."""
        standardizer = Standardizer()
        
        raw_dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Polygon",
            features=[{
                "id": "test_1",
                "geometry": {
                    "type": "Point",
                    "coordinates": [0.0, 0.0]
                },
                "properties": {
                    "name": "Test",
                    "count": 42,
                    "ratio": 3.14,
                    "active": True,
                }
            }],
            metadata={"version": "1.0"}
        )
        
        standardized = standardizer.standardize(raw_dataset)
        
        props = standardized.features[0].properties
        assert isinstance(props["name"], str)
        assert isinstance(props["count"], int)
        assert isinstance(props["ratio"], float)
        assert isinstance(props["active"], bool)

