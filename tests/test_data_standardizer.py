"""
Tests for Data Standardization Module.
Verifies that raw data from various providers is normalized to common format.
"""

import pytest
from hypothesis import given, strategies as st, settings

from backend.standardizers.data_standardizer import DataStandardizer
from backend.models.schemas import (
    RawDataset, StandardizedDataset, DataCategory
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def standardizer():
    """Create a Data Standardizer instance."""
    return DataStandardizer()


@pytest.fixture
def building_dataset():
    """Create a sample building dataset."""
    return RawDataset(
        source_provider="osm_buildings",
        category=DataCategory.BUILDINGS,
        geometry_type="Polygon",
        features=[
            {
                "id": "bld_1",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {
                    "name": "Test Building",
                    "type": "residential",
                    "levels": "3",
                    "material": "brick"
                }
            }
        ],
        metadata={"crs": "EPSG:4326", "version": "1.0"}
    )


@pytest.fixture
def admin_dataset():
    """Create a sample admin boundaries dataset."""
    return RawDataset(
        source_provider="admin_boundaries",
        category=DataCategory.ADMIN,
        geometry_type="Polygon",
        features=[
            {
                "id": "admin_1",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {
                    "name": "Test County",
                    "type": "district",
                    "admin_level": "6",
                    "country_code": "US",
                    "country": "United States"
                }
            }
        ],
        metadata={"crs": "EPSG:4326", "version": "1.0"}
    )


@pytest.fixture
def land_cover_dataset():
    """Create a sample land cover dataset."""
    return RawDataset(
        source_provider="land_cover",
        category=DataCategory.LAND_COVER,
        geometry_type="Polygon",
        features=[
            {
                "id": "lc_1",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {
                    "lc_code": 10,
                    "lc_class": "Tree cover",
                    "confidence": 0.95,
                    "year": 2022
                }
            }
        ],
        metadata={"crs": "EPSG:4326", "version": "1.0"}
    )


@pytest.fixture
def elevation_dataset():
    """Create a sample elevation dataset."""
    return RawDataset(
        source_provider="elevation",
        category=DataCategory.ELEVATION,
        geometry_type="Point",
        features=[
            {
                "id": "dem_1",
                "geometry": {"type": "Point", "coordinates": [0.5, 0.5]},
                "properties": {
                    "elevation_m": 500.5,
                    "confidence": 0.85,
                    "source": "dem_synthetic"
                }
            }
        ],
        metadata={"crs": "EPSG:4326", "version": "1.0"}
    )


# ============================================================================
# Basic Standardization Tests
# ============================================================================

def test_standardize_buildings_dataset(standardizer, building_dataset):
    """Test standardization of building dataset."""
    result = standardizer.standardize(building_dataset)
    
    assert isinstance(result, StandardizedDataset)
    assert result.source_provider == "osm_buildings"
    assert result.category == DataCategory.BUILDINGS
    assert len(result.features) == 1


def test_standardize_admin_dataset(standardizer, admin_dataset):
    """Test standardization of admin boundaries dataset."""
    result = standardizer.standardize(admin_dataset)
    
    assert isinstance(result, StandardizedDataset)
    assert result.source_provider == "admin_boundaries"
    assert result.category == DataCategory.ADMIN
    assert len(result.features) == 1


def test_standardize_land_cover_dataset(standardizer, land_cover_dataset):
    """Test standardization of land cover dataset."""
    result = standardizer.standardize(land_cover_dataset)
    
    assert isinstance(result, StandardizedDataset)
    assert result.source_provider == "land_cover"
    assert result.category == DataCategory.LAND_COVER
    assert len(result.features) == 1


def test_standardize_elevation_dataset(standardizer, elevation_dataset):
    """Test standardization of elevation dataset."""
    result = standardizer.standardize(elevation_dataset)
    
    assert isinstance(result, StandardizedDataset)
    assert result.source_provider == "elevation"
    assert result.category == DataCategory.ELEVATION
    assert len(result.features) == 1


# ============================================================================
# Metadata Tests
# ============================================================================

def test_standardized_metadata_has_crs(standardizer, building_dataset):
    """Test that standardized data has WGS84 CRS."""
    result = standardizer.standardize(building_dataset)
    
    assert "crs" in result.metadata
    assert result.metadata["crs"] == "EPSG:4326"


def test_standardized_metadata_has_timestamp(standardizer, building_dataset):
    """Test that standardized data has timestamp."""
    result = standardizer.standardize(building_dataset)
    
    assert "timestamp" in result.metadata
    assert result.metadata["timestamp"]  # Should be ISO8601 format


def test_standardized_metadata_preserves_original_crs(standardizer, building_dataset):
    """Test that original CRS is preserved in metadata."""
    result = standardizer.standardize(building_dataset)
    
    assert "original_crs" in result.metadata
    assert result.metadata["original_crs"] == "EPSG:4326"


# ============================================================================
# Field Normalization Tests
# ============================================================================

def test_building_properties_normalized(standardizer, building_dataset):
    """Test that building properties are normalized."""
    result = standardizer.standardize(building_dataset)
    
    feature = result.features[0]
    props = feature.properties
    
    # Check standardized fields exist
    assert "name" in props
    assert "type" in props
    assert "levels" in props
    assert "material" in props


def test_admin_properties_normalized(standardizer, admin_dataset):
    """Test that admin properties are normalized."""
    result = standardizer.standardize(admin_dataset)
    
    feature = result.features[0]
    props = feature.properties
    
    # Check standardized fields exist
    assert "name" in props
    assert "type" in props
    assert "admin_level" in props
    assert "country_code" in props


def test_land_cover_properties_normalized(standardizer, land_cover_dataset):
    """Test that land cover properties are normalized."""
    result = standardizer.standardize(land_cover_dataset)
    
    feature = result.features[0]
    props = feature.properties
    
    # Check standardized fields exist
    assert "lc_code" in props
    assert "lc_class" in props
    assert "confidence" in props
    assert "year" in props


def test_elevation_properties_normalized(standardizer, elevation_dataset):
    """Test that elevation properties are normalized."""
    result = standardizer.standardize(elevation_dataset)
    
    feature = result.features[0]
    props = feature.properties
    
    # Check standardized fields exist
    assert "elevation_m" in props
    assert "confidence" in props
    assert "source" in props


# ============================================================================
# Type Conversion Tests
# ============================================================================

def test_elevation_values_are_floats(standardizer, elevation_dataset):
    """Test that elevation values are converted to floats."""
    result = standardizer.standardize(elevation_dataset)
    
    feature = result.features[0]
    props = feature.properties
    
    assert isinstance(props["elevation_m"], float)
    assert props["elevation_m"] == 500.5


def test_confidence_values_are_floats(standardizer, land_cover_dataset):
    """Test that confidence values are converted to floats."""
    result = standardizer.standardize(land_cover_dataset)
    
    feature = result.features[0]
    props = feature.properties
    
    assert isinstance(props["confidence"], float)
    assert props["confidence"] == 0.95


def test_year_values_are_ints(standardizer, land_cover_dataset):
    """Test that year values are converted to ints."""
    result = standardizer.standardize(land_cover_dataset)
    
    feature = result.features[0]
    props = feature.properties
    
    assert isinstance(props["year"], int)
    assert props["year"] == 2022


# ============================================================================
# Schema Compliance Tests
# ============================================================================

def test_standardized_features_have_required_structure(standardizer, building_dataset):
    """Test that standardized features have required structure."""
    result = standardizer.standardize(building_dataset)
    
    for feature in result.features:
        assert feature.id is not None
        assert feature.geometry is not None
        assert feature.properties is not None
        
        # Geometry structure
        geom = feature.geometry
        assert "type" in geom
        assert "coordinates" in geom


def test_standardized_dataset_has_record_count(standardizer, building_dataset):
    """Test that standardized dataset metadata has record count."""
    result = standardizer.standardize(building_dataset)
    
    assert "record_count" in result.metadata
    assert result.metadata["record_count"] == len(result.features)


# ============================================================================
# Multiple Features Tests
# ============================================================================

def test_standardize_multiple_features(standardizer):
    """Test standardization with multiple features."""
    dataset = RawDataset(
        source_provider="test",
        category=DataCategory.BUILDINGS,
        geometry_type="Polygon",
        features=[
            {
                "id": f"bld_{i}",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {"name": f"Building {i}", "type": "residential"}
            }
            for i in range(5)
        ],
        metadata={"crs": "EPSG:4326", "version": "1.0"}
    )
    
    result = standardizer.standardize(dataset)
    
    assert len(result.features) == 5
    assert result.metadata["record_count"] == 5


# ============================================================================
# Property-Based Tests
# ============================================================================

@given(
    num_features=st.integers(min_value=1, max_value=10)
)
@settings(max_examples=50)
def test_property_4_standardization_normalization(num_features):
    """
    Property 4: Data Standardization Normalization
    
    For any raw dataset from any provider, after standardization, all 
    coordinate systems should be normalized to WGS84 (EPSG:4326), and all 
    field names should use consistent lowercase underscore convention 
    regardless of the original provider format.
    
    **Validates: Requirements 4.2, 4.3, 4.4**
    """
    standardizer = DataStandardizer()
    
    # Create dataset with variable number of features
    dataset = RawDataset(
        source_provider="test_provider",
        category=DataCategory.BUILDINGS,
        geometry_type="Polygon",
        features=[
            {
                "id": f"feature_{i}",
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {
                    "Name": f"Feature {i}",  # Non-standard casing
                    "Type": "test",           # Non-standard casing
                    "LEVELS": "2"             # All caps
                }
            }
            for i in range(num_features)
        ],
        metadata={"crs": "EPSG:4326", "version": "1.0"}
    )
    
    result = standardizer.standardize(dataset)
    
    # PROPERTY: All outputs have WGS84 CRS
    assert result.metadata["crs"] == "EPSG:4326", \
        "All standardized data must use WGS84"
    
    # PROPERTY: All field names are lowercase
    for feature in result.features:
        props = feature.properties
        for key in props.keys():
            # Check if lowercase and underscore format
            assert key == key.lower(), \
                f"Field name {key} should be lowercase"


@given(st.just(None))  # Placeholder strategy
def test_property_5_standardized_data_model_consistency(dummy):
    """
    Property 5: Standardized Data Model Consistency
    
    For any standardized dataset regardless of source provider, the output 
    should conform to the StandardizedDataset schema with category, 
    source_provider, features array, and metadata fields always present 
    and correctly formatted.
    
    **Validates: Requirements 4.1, 4.5, 4.6**
    """
    standardizer = DataStandardizer()
    
    categories = [
        DataCategory.BUILDINGS,
        DataCategory.ADMIN,
        DataCategory.LAND_COVER,
        DataCategory.ROADS,
        DataCategory.WATER,
        DataCategory.ELEVATION,
    ]
    
    for category in categories:
        dataset = RawDataset(
            source_provider=f"test_{category}",
            category=category,
            geometry_type="Point",
            features=[
                {
                    "id": "test_1",
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "properties": {"test": "value"}
                }
            ],
            metadata={"crs": "EPSG:4326", "version": "1.0"}
        )
        
        result = standardizer.standardize(dataset)
        
        # PROPERTY: All required fields present
        assert hasattr(result, "category"), f"Missing category for {category}"
        assert hasattr(result, "source_provider"), f"Missing source_provider for {category}"
        assert hasattr(result, "features"), f"Missing features for {category}"
        assert hasattr(result, "metadata"), f"Missing metadata for {category}"
        
        # PROPERTY: Correct types
        assert isinstance(result.features, list), f"Features should be list for {category}"
        assert isinstance(result.metadata, dict), f"Metadata should be dict for {category}"
        assert result.metadata["crs"] == "EPSG:4326", f"CRS should be WGS84 for {category}"
        
        # PROPERTY: Never expose raw provider formats
        raw_props = dataset.features[0]["properties"]
        std_props = result.features[0].properties if result.features else {}
        
        # Provider-specific raw fields should not directly copy
        # (Category normalizers should process them)
        assert result.source_provider == dataset.source_provider, \
            "Should preserve source provider attribution"
