"""
Tests for OSM Building data field normalization (Task 6.2)

Tests the BuildingsStandardizer with real OSM building field mappings.
"""

import pytest
from backend.standardizers.buildings_standardizer import BuildingsStandardizer


class TestBuildingsFieldNormalization:
    """Test OSM building field normalization"""

    def test_osm_building_type_mapping(self):
        """Test OSM building type normalization to standardized types"""
        test_cases = [
            ("residential", "residential"),
            ("house", "residential"),
            ("apartment", "residential"),
            ("commercial", "commercial"),
            ("office", "commercial"),
            ("industrial", "industrial"),
            ("warehouse", "industrial"),
            ("yes", "unclassified"),  # Default OSM value
            ("other", "other"),
        ]
        
        for input_type, expected_type in test_cases:
            properties = {"building": input_type}
            result = BuildingsStandardizer.standardize_properties(properties)
            assert result.get("building_type") == expected_type, \
                f"Failed for {input_type}: expected {expected_type}, got {result.get('building_type')}"

    def test_osm_height_normalization(self):
        """Test OSM height field parsing and normalization"""
        test_cases = [
            ({"height": "30"}, 30.0),
            ({"height": "30m"}, 30.0),
            ({"building:height": "25.5"}, 25.5),
            ({"height": "invalid"}, None),
        ]
        
        for properties, expected_height in test_cases:
            result = BuildingsStandardizer.standardize_properties(properties)
            height = result.get("building_height_m")
            assert height == expected_height, \
                f"Failed for {properties}: expected {expected_height}, got {height}"

    def test_osm_levels_normalization(self):
        """Test OSM building:levels field normalization"""
        test_cases = [
            ({"building:levels": "3"}, 3),
            ({"levels": "5"}, 5),
            ({"stories": "2"}, 2),
            ({"building:levels": "invalid"}, None),
        ]
        
        for properties, expected_levels in test_cases:
            result = BuildingsStandardizer.standardize_properties(properties)
            levels = result.get("building_levels")
            assert levels == expected_levels, \
                f"Failed for {properties}: expected {expected_levels}, got {levels}"

    def test_osm_material_mapping(self):
        """Test OSM material field normalization"""
        test_cases = [
            ("brick", "brick"),
            ("stone", "stone"),
            ("concrete", "concrete"),
            ("wood", "wood"),
            ("unknown_material", "unknown"),
        ]
        
        for input_material, expected_material in test_cases:
            properties = {"material": input_material}
            result = BuildingsStandardizer.standardize_properties(properties)
            material = result.get("building_material")
            assert material == expected_material, \
                f"Failed for {input_material}: expected {expected_material}, got {material}"

    def test_comprehensive_osm_building_normalization(self):
        """Test comprehensive OSM building properties normalization"""
        osm_properties = {
            "name": "Main Street Building",
            "building": "residential",
            "building:levels": "5",
            "height": "15.5m",
            "material": "brick",
            "roof_type": "pitched",
            "occupied": "yes",
            "residents": "120",
            "start_date": "2000",
            "access": "public",
        }
        
        result = BuildingsStandardizer.standardize_properties(osm_properties)
        
        # Verify key fields are normalized
        assert result.get("name") == "Main Street Building"
        assert result.get("building_type") == "residential"
        assert result.get("building_levels") == 5
        assert result.get("building_height_m") == 15.5
        assert result.get("building_material") == "brick"
        assert result.get("occupied") is True
        assert result.get("residents") == 120

    def test_field_name_standardization(self):
        """Test field name conversion to lowercase_underscore"""
        osm_properties = {
            "building:type": "commercial",
            "building-height": "40",
            "ROOF_TYPE": "flat",
            "buildingLevels": "8",
        }
        
        result = BuildingsStandardizer.standardize_properties(osm_properties)
        
        # Verify all fields are properly standardized
        # Lowercase underscore format should be used
        standardized_keys = set(result.keys())
        
        # All keys should be lowercase
        for key in standardized_keys:
            assert key == key.lower(), f"Key {key} contains uppercase letters"
            # All keys should use underscores, not hyphens or camelCase
            assert "_" in key or "name" in key or "access" in key, \
                f"Key {key} doesn't follow standardized naming"

    def test_missing_fields_handling(self):
        """Test handling of missing optional fields"""
        properties = {
            "name": "Simple Building",
            "building": "yes",
        }
        
        result = BuildingsStandardizer.standardize_properties(properties)
        
        # Required field should be present
        assert "building_type" in result
        assert "name" in result
        # Missing fields should not cause errors
        assert "building_levels" not in result or result.get("building_levels") is None
        assert "building_height_m" not in result or result.get("building_height_m") is None

    def test_boolean_field_normalization(self):
        """Test boolean field normalization"""
        test_cases = [
            ("yes", True),
            ("no", False),
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
            (1, True),
            (0, False),
        ]
        
        for input_val, expected_bool in test_cases:
            properties = {"occupied": input_val}
            result = BuildingsStandardizer.standardize_properties(properties)
            occupied = result.get("occupied")
            assert occupied == expected_bool, \
                f"Failed for {input_val}: expected {expected_bool}, got {occupied}"

    def test_null_and_empty_handling(self):
        """Test handling of null and empty values"""
        test_cases = [
            {"building": None},
            {"building": ""},
            {"building": "   "},
            {"name": None},
        ]
        
        for properties in test_cases:
            result = BuildingsStandardizer.standardize_properties(properties)
            # Empty/null values should not appear in result or be None
            for key, value in result.items():
                assert value is not None or value == "", \
                    f"Got None for key {key} in {properties}"

    def test_provider_specification(self):
        """Test that provider parameter is accepted"""
        properties = {"building": "residential", "name": "Test"}
        
        # Should accept provider parameter without error
        result = BuildingsStandardizer.standardize_properties(properties, provider="OSM")
        assert "building_type" in result
        
        result = BuildingsStandardizer.standardize_properties(properties, provider="other")
        assert "building_type" in result


class TestBuildingsStandardizerIntegration:
    """Integration tests with the main standardizer"""

    def test_buildings_standardizer_in_main_pipeline(self):
        """Test that buildings standardizer integrates with main DataStandardizer"""
        from backend.data_models import RawDataset, Feature
        from backend.standardizers.standardizer import DataStandardizer
        
        # Create raw OSM building data
        raw_feature = Feature(
            id="osm_building_123",
            type="Feature",
            geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            properties={
                "building": "residential",
                "name": "Test House",
                "building:levels": "2",
                "height": "8m",
                "material": "brick",
            }
        )
        
        raw_dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[raw_feature],
            metadata={"version": "2024-01"}
        )
        
        # Standardize
        standardizer = DataStandardizer()
        result = standardizer.standardize(raw_dataset)
        
        # Verify result
        assert result.source_provider == "OSM"
        assert result.category == "buildings"
        assert len(result.features) == 1
        
        standardized_feature = result.features[0]
        assert standardized_feature.properties.get("building_type") == "residential"
        assert standardized_feature.properties.get("name") == "Test House"
        assert standardized_feature.properties.get("building_levels") == 2
        assert standardized_feature.properties.get("building_height_m") == 8.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
