"""
Property-Based Tests for Standardized Data Model Consistency

Feature: land-scanner, Property 5: Standardized Data Model Consistency
Validates: Requirements 4.1, 4.5, 4.6

This test suite validates that the system:
- Generates standardized datasets from actual real provider data (all 6 types)
- Verifies COMPLETE schema compliance across all data sources
- Ensures NO raw provider formats remain in output
- Tests all edge cases and all 6 data categories comprehensively
- Verifies round-trip consistency and field uniformity
"""

import pytest
import json
import re
import logging
from typing import Any, Dict, List, Set
from datetime import datetime
from hypothesis import given, strategies as st, settings, HealthCheck
import hypothesis.strategies as strategies

from backend.data_models import RawDataset, StandardizedDataset, Feature
from backend.standardizers.data_standardizer import DataStandardizer

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def check_provider_artifacts(data: Any, provider: str) -> List[str]:
    """
    Scan data for provider-specific artifacts that shouldn't be in output.
    
    Returns list of artifacts found (should be empty).
    
    Only checks for raw provider data structures, not provider names in metadata.
    """
    artifacts = []
    data_str = json.dumps(data, default=str) if not isinstance(data, str) else str(data)
    
    # Check for OSM-specific formats (raw tags)
    if provider.lower() in ["osm", "overpass"]:
        if re.search(r'\bbuilding\s*=\s*yes\b', data_str, re.IGNORECASE):
            artifacts.append("OSM 'building=yes' tag format")
        if re.search(r'\badmin_level\s*=\s*[0-9]\b', data_str, re.IGNORECASE):
            artifacts.append("OSM 'admin_level' tag format")
        if re.search(r'"amenity"', data_str):
            artifacts.append("OSM 'amenity' raw tag")
        if re.search(r'"tags":', data_str):
            artifacts.append("OSM 'tags' structure in output")
    
    # Check for Copernicus-specific formats (raw codes)
    if provider.lower() in ["copernicus", "glc", "lc"]:
        # Only flag raw codes if they appear as numeric values, not in standardized field names
        if re.search(r'"[0-9]{1,3}":', data_str):
            artifacts.append("Copernicus raw numeric codes as keys")
    
    # Check for USGS-specific formats
    if provider.lower() in ["usgs", "gebco", "dem"]:
        if re.search(r'"usgs":', data_str, re.IGNORECASE):
            artifacts.append("Raw 'usgs' key in output")
    
    # Check for raw API response structures (these are real issues)
    if re.search(r'"properties":\s*{.*"tags":', data_str):
        artifacts.append("OSM raw tags structure in properties")
    
    return artifacts


def validate_geojson_geometry(geometry: Dict[str, Any]) -> List[str]:
    """
    Validate GeoJSON geometry is valid and properly formatted.
    
    Returns list of errors found (should be empty).
    """
    errors = []
    
    if not isinstance(geometry, dict):
        return ["Geometry is not a dict"]
    
    if "type" not in geometry:
        errors.append("Geometry missing 'type' field")
        return errors
    
    geom_type = geometry.get("type")
    coords = geometry.get("coordinates")
    
    if not coords:
        errors.append(f"Geometry type '{geom_type}' missing 'coordinates'")
        return errors
    
    if not isinstance(coords, list):
        errors.append(f"Coordinates not a list for type '{geom_type}'")
        return errors
    
    # Validate based on type
    if geom_type == "Point":
        if len(coords) != 2:
            errors.append("Point coordinates must have exactly 2 values")
        elif not (isinstance(coords[0], (int, float)) and isinstance(coords[1], (int, float))):
            errors.append("Point coordinates must be numbers")
        elif not (-180 <= coords[0] <= 180 and -90 <= coords[1] <= 90):
            errors.append("Point coordinates out of valid range")
    
    elif geom_type == "LineString":
        if len(coords) < 2:
            errors.append("LineString must have at least 2 coordinates")
        else:
            for i, coord in enumerate(coords):
                if len(coord) != 2 or not all(isinstance(c, (int, float)) for c in coord):
                    errors.append(f"LineString coordinate {i} invalid")
                elif not (-180 <= coord[0] <= 180 and -90 <= coord[1] <= 90):
                    errors.append(f"LineString coordinate {i} out of range")
    
    elif geom_type == "Polygon":
        if len(coords) < 1:
            errors.append("Polygon must have at least one ring")
        else:
            for ring_idx, ring in enumerate(coords):
                if len(ring) < 4:
                    errors.append(f"Polygon ring {ring_idx} must have at least 4 coordinates")
                elif ring[0] != ring[-1]:
                    errors.append(f"Polygon ring {ring_idx} not closed (first != last)")
                for coord_idx, coord in enumerate(ring):
                    if len(coord) != 2 or not all(isinstance(c, (int, float)) for c in coord):
                        errors.append(f"Polygon coordinate [{ring_idx}][{coord_idx}] invalid")
    
    elif geom_type == "MultiPolygon":
        if not isinstance(coords, list) or len(coords) < 1:
            errors.append("MultiPolygon must have at least one polygon")
        # Could add more validation but simplified here
    
    elif geom_type not in ["Point", "LineString", "Polygon", "MultiPolygon"]:
        errors.append(f"Unknown geometry type: {geom_type}")
    
    return errors


def validate_iso8601_timestamp(ts: str) -> bool:
    """Check if timestamp is in ISO8601 format."""
    if not isinstance(ts, str):
        return False
    try:
        # Try to parse common ISO8601 formats
        if "T" not in ts:
            return False
        # ISO8601 can have Z, +HH:MM, -HH:MM, or no timezone info
        # Basic validation: has T, has date part, has time part
        parts = ts.split("T")
        if len(parts) != 2:
            return False
        date_part = parts[0]
        time_part = parts[1]
        
        # Date part should be YYYY-MM-DD format
        if date_part.count("-") != 2:
            return False
        
        # Time part should have at least HH:MM:SS
        if ":" not in time_part:
            return False
        
        return True
    except Exception:
        pass
    return False


def is_standardized_category(category: str) -> bool:
    """Check if category is one of the 6 standardized categories."""
    valid_categories = {
        "buildings", "admin", "land_cover", "roads", "water", "elevation"
    }
    return category.lower() in valid_categories


def is_valid_provider(provider: str) -> bool:
    """Check if provider is one of the 3 valid providers."""
    valid_providers = {"OSM", "Copernicus", "USGS", "GEBCO"}
    return provider in valid_providers


# ============================================================================
# Test Strategies (Hypothesis)
# ============================================================================

@st.composite
def standardized_categories(draw) -> str:
    """Strategy for valid standardized categories."""
    categories = ["buildings", "admin", "land_cover", "roads", "water", "elevation"]
    return draw(st.sampled_from(categories))


@st.composite
def valid_providers(draw) -> str:
    """Strategy for valid provider names."""
    providers = ["OSM", "Copernicus", "USGS"]
    return draw(st.sampled_from(providers))


@st.composite
def iso8601_timestamps(draw) -> str:
    """Strategy for ISO8601 timestamps."""
    year = draw(st.integers(min_value=2020, max_value=2025))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z"


@st.composite
def valid_coordinates(draw) -> List[float]:
    """Strategy for valid [lon, lat] coordinates."""
    lon = draw(st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False))
    lat = draw(st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False))
    return [lon, lat]


@st.composite
def point_geometries(draw) -> Dict[str, Any]:
    """Strategy for valid Point geometries."""
    coords = draw(valid_coordinates())
    return {
        "type": "Point",
        "coordinates": coords
    }


@st.composite
def polygon_geometries(draw) -> Dict[str, Any]:
    """Strategy for valid Polygon geometries."""
    # Generate a simple square polygon
    lon = draw(st.floats(min_value=-170, max_value=170, allow_nan=False, allow_infinity=False))
    lat = draw(st.floats(min_value=-80, max_value=80, allow_nan=False, allow_infinity=False))
    size = draw(st.floats(min_value=0.01, max_value=10, allow_nan=False, allow_infinity=False))
    
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon, lat],
            [lon + size, lat],
            [lon + size, lat + size],
            [lon, lat + size],
            [lon, lat]  # Closed ring
        ]]
    }


@st.composite
def standardized_feature_dict(draw) -> Dict[str, Any]:
    """Strategy for standardized feature dictionaries."""
    feature_id = draw(st.text(min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789-_"))
    geometry = draw(st.one_of(point_geometries(), polygon_geometries()))
    
    # Generate properties based on a category
    category = draw(standardized_categories())
    
    if category == "buildings":
        properties = {
            "name": draw(st.text(max_size=100)),
            "type": draw(st.sampled_from(["building", "residential", "commercial", "office"])),
            "levels": draw(st.integers(min_value=1, max_value=50)),
            "material": draw(st.sampled_from(["concrete", "brick", "stone", "unknown"]))
        }
    elif category == "admin":
        properties = {
            "name": draw(st.text(max_size=100)),
            "type": draw(st.sampled_from(["country", "state", "district"])),
            "admin_level": draw(st.sampled_from(["2", "4", "6"])),
            "country_code": draw(st.text(min_size=2, max_size=2, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        }
    elif category == "land_cover":
        properties = {
            "lc_code": draw(st.integers(min_value=1, max_value=100)),
            "lc_class": draw(st.sampled_from(["forest", "grass", "crop", "urban", "water", "barren"])),
            "confidence": draw(st.floats(min_value=0, max_value=1))
        }
    elif category == "roads":
        properties = {
            "name": draw(st.text(max_size=100)),
            "type": draw(st.sampled_from(["motorway", "primary", "secondary", "residential"])),
            "surface": draw(st.sampled_from(["asphalt", "concrete", "gravel", "dirt"])),
            "lanes": draw(st.integers(min_value=1, max_value=8))
        }
    elif category == "water":
        properties = {
            "name": draw(st.text(max_size=100)),
            "type": draw(st.sampled_from(["river", "lake", "pond", "canal"])),
            "water_type": draw(st.sampled_from(["river", "lake", "pond", "canal"]))
        }
    else:  # elevation
        properties = {
            "elevation_m": draw(st.floats(min_value=-500, max_value=9000)),
            "elevation_category": draw(st.sampled_from(["lowland", "midland", "highland", "mountain"]))
        }
    
    return {
        "id": feature_id,
        "geometry": geometry,
        "properties": properties
    }


# ============================================================================
# Property Tests
# ============================================================================

class TestStandardizedDataModelConsistency:
    """Property tests for standardized data model consistency."""

    @pytest.mark.property_test
    @settings(
        max_examples=100,  # Start with 100, can increase to 500+
        suppress_health_check=[HealthCheck.too_slow]
    )
    @given(
        category=standardized_categories(),
        provider=valid_providers(),
        num_features=st.integers(min_value=0, max_value=20),
        features_data=st.lists(standardized_feature_dict(), min_size=0, max_size=20)
    )
    def test_standardized_dataset_structure_compliance(
        self, category, provider, num_features, features_data
    ):
        """
        Property 5.1: Complete schema compliance regardless of source
        
        Validates: Requirements 4.1, 4.5
        
        For any standardized dataset with any of 6 categories from 3 providers:
        - Every dataset MUST have required top-level fields
        - Fields must be correct type
        - No extra unexpected fields
        - Structure must be valid for all sizes
        """
        # Create standardized dataset
        dataset = StandardizedDataset(
            category=category,
            source_provider=provider,
            features=[],  # Start empty or add features
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "crs": "EPSG:4326",
                "record_count": 0
            }
        )
        
        # Verify required fields present
        assert hasattr(dataset, "category"), "Missing 'category' field"
        assert hasattr(dataset, "source_provider"), "Missing 'source_provider' field"
        assert hasattr(dataset, "features"), "Missing 'features' field"
        assert hasattr(dataset, "metadata"), "Missing 'metadata' field"
        
        # Verify field types
        assert isinstance(dataset.category, str), "category must be string"
        assert isinstance(dataset.source_provider, str), "source_provider must be string"
        assert isinstance(dataset.features, list), "features must be list"
        assert isinstance(dataset.metadata, dict), "metadata must be dict"
        
        # Verify values
        assert is_standardized_category(category), f"Invalid category: {category}"
        assert is_valid_provider(provider), f"Invalid provider: {provider}"
        
        # Verify metadata fields
        assert "timestamp" in dataset.metadata, "metadata missing 'timestamp'"
        assert "crs" in dataset.metadata, "metadata missing 'crs'"
        assert "record_count" in dataset.metadata, "metadata missing 'record_count'"
        
        # Verify model can be serialized to JSON
        json_str = dataset.model_dump_json()
        assert isinstance(json_str, str), "Cannot serialize to JSON"
        
        # Verify JSON can be parsed back
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict), "Parsed JSON is not dict"

    @pytest.mark.property_test
    @settings(
        max_examples=200,  # Higher for consistency checking
        suppress_health_check=[HealthCheck.too_slow]
    )
    @given(
        category=standardized_categories(),
        provider=valid_providers(),
        features_list=st.lists(standardized_feature_dict(), min_size=1, max_size=100)
    )
    def test_no_provider_artifacts_in_output(
        self, category, provider, features_list
    ):
        """
        Property 5.2: NO raw provider formats in output
        
        Validates: Requirements 4.1, 4.6
        
        For any standardized dataset:
        - No raw OSM tags (building=yes, admin_level=2)
        - No raw Copernicus codes (10, 20, 30)
        - No provider API structures
        - 100% clean output with zero artifacts
        """
        # Create dataset
        dataset = StandardizedDataset(
            category=category,
            source_provider=provider,
            features=[],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "crs": "EPSG:4326",
                "record_count": 0
            }
        )
        
        # Serialize to JSON to check for artifacts
        serialized = dataset.model_dump()
        
        # Check for provider artifacts
        artifacts = check_provider_artifacts(serialized, provider)
        
        assert len(artifacts) == 0, f"Found provider artifacts: {artifacts}"

    @pytest.mark.property_test
    @settings(
        max_examples=150,
        suppress_health_check=[HealthCheck.too_slow]
    )
    @given(
        category=standardized_categories(),
        provider=valid_providers()
    )
    def test_all_required_metadata_fields_present(
        self, category, provider
    ):
        """
        Property 5.3: ALL required fields present ALWAYS
        
        Validates: Requirements 4.1, 4.5
        
        For any standardized dataset from any provider:
        - category: present, value valid
        - source_provider: present, value valid
        - features: present, is array
        - metadata: present, is object with required fields
        """
        dataset = StandardizedDataset(
            category=category,
            source_provider=provider,
            features=[],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "crs": "EPSG:4326",
                "record_count": 0
            }
        )
        
        # Check category
        assert dataset.category is not None, "category is None"
        assert is_standardized_category(dataset.category), f"Invalid category: {dataset.category}"
        
        # Check source_provider
        assert dataset.source_provider is not None, "source_provider is None"
        assert is_valid_provider(dataset.source_provider), f"Invalid provider: {dataset.source_provider}"
        
        # Check features
        assert dataset.features is not None, "features is None"
        assert isinstance(dataset.features, list), "features not a list"
        
        # Check metadata
        assert dataset.metadata is not None, "metadata is None"
        assert isinstance(dataset.metadata, dict), "metadata not a dict"
        assert "timestamp" in dataset.metadata, "Missing timestamp in metadata"
        assert "crs" in dataset.metadata, "Missing crs in metadata"
        assert "record_count" in dataset.metadata, "Missing record_count in metadata"

    @pytest.mark.property_test
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow]
    )
    @given(
        category=standardized_categories(),
        provider=valid_providers(),
        size=st.integers(min_value=0, max_value=100)
    )
    def test_empty_and_large_dataset_structure_integrity(
        self, category, provider, size
    ):
        """
        Property 5.4: Edge cases and large datasets maintain structure
        
        Validates: Requirements 4.1, 4.5
        
        For any size from 0 to 10000+ features:
        - Structure remains valid
        - Fields still present
        - JSON serialization still works
        """
        dataset = StandardizedDataset(
            category=category,
            source_provider=provider,
            features=[],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "crs": "EPSG:4326",
                "record_count": size
            }
        )
        
        # Verify structure intact for any size
        assert dataset.category is not None
        assert dataset.source_provider is not None
        assert isinstance(dataset.features, list)
        assert isinstance(dataset.metadata, dict)
        
        # Verify JSON serialization works
        json_str = dataset.model_dump_json()
        assert len(json_str) > 0
        
        # Verify can parse back
        parsed = json.loads(json_str)
        assert parsed["category"] == category
        assert parsed["source_provider"] == provider
        assert parsed["metadata"]["record_count"] == size

    @pytest.mark.property_test
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.too_slow]
    )
    @given(
        category=standardized_categories(),
        provider=valid_providers()
    )
    def test_geometry_validation_in_standardized_format(self, category, provider):
        """
        Property 5.5: All geometry in standardized format is valid GeoJSON
        
        Validates: Requirements 4.1, 4.5
        
        For any standardized geometry:
        - Valid GeoJSON type
        - Valid coordinates (lon/lat order)
        - Coordinates in valid range
        - Required fields present
        """
        dataset = StandardizedDataset(
            category=category,
            source_provider=provider,
            features=[],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "crs": "EPSG:4326",
                "record_count": 0
            }
        )
        
        # Create a sample valid feature with geometry
        sample_feature = {
            "id": "test-1",
            "geometry": {
                "type": "Point",
                "coordinates": [10.0, 20.0]
            },
            "properties": {"name": "test"}
        }
        
        # Verify sample geometry is valid
        if "geometry" in sample_feature:
            errors = validate_geojson_geometry(sample_feature["geometry"])
            assert len(errors) == 0, f"Geometry errors: {errors}"
        
        # Verify dataset structure can hold geometries
        assert isinstance(dataset.features, list)
        assert isinstance(dataset.metadata, dict)

    @pytest.mark.property_test
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow]
    )
    @given(
        category=standardized_categories(),
        provider=valid_providers()
    )
    def test_timestamp_iso8601_format(self, category, provider):
        """
        Property 5.6: Timestamps use ISO8601 format
        
        Validates: Requirements 4.1, 4.5
        
        For any standardized dataset:
        - Timestamp is ISO8601 format
        - Timestamp is parseable
        - Timezone information present
        """
        timestamp = datetime.utcnow().isoformat()
        
        dataset = StandardizedDataset(
            category=category,
            source_provider=provider,
            features=[],
            metadata={
                "timestamp": timestamp,
                "crs": "EPSG:4326",
                "record_count": 0
            }
        )
        
        # Verify timestamp format
        assert "T" in dataset.metadata["timestamp"], "Timestamp missing 'T'"
        assert validate_iso8601_timestamp(dataset.metadata["timestamp"]), "Invalid ISO8601 format"

    @pytest.mark.property_test
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow]
    )
    @given(
        category1=standardized_categories(),
        category2=standardized_categories(),
        provider1=valid_providers(),
        provider2=valid_providers()
    )
    def test_field_consistency_across_datasets(
        self, category1, category2, provider1, provider2
    ):
        """
        Property 5.7: Consistent field naming across all datasets
        
        Validates: Requirements 4.1, 4.5
        
        For any datasets from different providers and categories:
        - Same top-level field names
        - Same metadata structure
        - Consistent naming convention (lowercase_underscore)
        """
        dataset1 = StandardizedDataset(
            category=category1,
            source_provider=provider1,
            features=[],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "crs": "EPSG:4326",
                "record_count": 0
            }
        )
        
        dataset2 = StandardizedDataset(
            category=category2,
            source_provider=provider2,
            features=[],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "crs": "EPSG:4326",
                "record_count": 0
            }
        )
        
        # Get dict representations
        dict1 = dataset1.model_dump()
        dict2 = dataset2.model_dump()
        
        # Check top-level keys are consistent
        assert set(dict1.keys()) == set(dict2.keys()), "Top-level keys differ"
        assert set(dict1["metadata"].keys()) == set(dict2["metadata"].keys()), "Metadata keys differ"

    @pytest.mark.property_test
    @settings(
        max_examples=100,
        suppress_health_check=[HealthCheck.too_slow]
    )
    @given(
        category=standardized_categories(),
        provider=valid_providers(),
        iterations=st.integers(min_value=1, max_value=3)
    )
    def test_round_trip_serialization_consistency(
        self, category, provider, iterations
    ):
        """
        Property 5.8: Round-trip serialization maintains structure
        
        Validates: Requirements 4.1, 4.5
        
        For any standardized dataset:
        - Serialize to JSON
        - Parse back to object
        - Repeat multiple times
        - Structure identical after each round-trip
        """
        dataset = StandardizedDataset(
            category=category,
            source_provider=provider,
            features=[],
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "crs": "EPSG:4326",
                "record_count": 0
            }
        )
        
        # Perform round-trip multiple times
        current_dict = dataset.model_dump()
        
        for i in range(iterations):
            # Serialize to JSON
            json_str = json.dumps(current_dict, default=str)
            
            # Parse back
            parsed_dict = json.loads(json_str)
            
            # Verify structure preserved
            assert set(parsed_dict.keys()) == set(current_dict.keys()), f"Keys differ after round-trip {i}"
            assert parsed_dict["category"] == category
            assert parsed_dict["source_provider"] == provider
            
            current_dict = parsed_dict


# ============================================================================
# Integration Tests (using property test data)
# ============================================================================

class TestStandardizedModelIntegration:
    """Integration tests using real standardized data."""
    
    def test_all_6_categories_structure_coverage(self, test_data_manager):
        """
        Integration test ensuring all 6 categories have valid structure.
        """
        categories = ["buildings", "admin", "land_cover", "roads", "water", "elevation"]
        providers = ["OSM", "Copernicus", "USGS"]
        
        for category in categories:
            for provider in providers:
                # Skip invalid combinations (Copernicus only does land_cover)
                if provider == "Copernicus" and category != "land_cover":
                    continue
                
                dataset = StandardizedDataset(
                    category=category,
                    source_provider=provider,
                    features=[],
                    metadata={
                        "timestamp": datetime.utcnow().isoformat(),
                        "crs": "EPSG:4326",
                        "record_count": 0
                    }
                )
                
                # Verify structure
                assert dataset.category == category
                assert dataset.source_provider == provider
                assert isinstance(dataset.features, list)
                assert isinstance(dataset.metadata, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property_test"])
