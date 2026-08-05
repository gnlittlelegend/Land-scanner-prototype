"""
Tests for OSM Water data field normalization (Task 6.6)

Tests the WaterStandardizer with real OSM water field mappings.
Validates that water-specific standardization rules map OSM waterway tags
to standardized water types and normalize all water properties correctly.
"""

import pytest
from backend.standardizers.water_standardizer import WaterStandardizer


class TestWaterFieldNormalization:
    """Test OSM water feature field normalization"""

    def test_osm_waterway_type_mapping(self):
        """Test OSM waterway tag normalization to standardized water types"""
        test_cases = [
            # Natural flowing water
            ("river", "river"),
            ("stream", "stream"),
            ("creek", "stream"),
            ("brook", "stream"),
            ("tributary", "stream"),
            ("wadi", "stream"),
            
            # Man-made flowing water
            ("canal", "canal"),
            ("drain", "drain"),
            ("ditch", "ditch"),
            ("channel", "channel"),
            
            # Still water bodies
            ("lake", "lake"),
            ("pond", "pond"),
            ("reservoir", "reservoir"),
            ("water_tank", "water_tank"),
            
            # Wetlands
            ("wetland", "wetland"),
            ("marsh", "wetland"),
            ("swamp", "wetland"),
            ("bog", "wetland"),
            ("mangrove", "wetland"),
            
            # Coastal
            ("bay", "bay"),
            ("estuary", "estuary"),
            ("lagoon", "lagoon"),
        ]
        
        for input_type, expected_type in test_cases:
            properties = {"waterway": input_type}
            result = WaterStandardizer.standardize_properties(properties)
            assert result.get("water_type") == expected_type, \
                f"Failed for {input_type}: expected {expected_type}, got {result.get('water_type')}"

    def test_osm_water_depth_normalization(self):
        """Test OSM depth field parsing and normalization"""
        test_cases = [
            ({"depth": "5"}, 5.0),
            ({"depth": "5.5"}, 5.5),
            ({"depth": "5m"}, 5.0),
            ({"depth_m": "10"}, 10.0),
            ({"max_depth": "25"}, 25.0),
            ({"depth": "invalid"}, None),
            ({"depth": ""}, None),
        ]
        
        for properties, expected_depth in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            depth = result.get("depth_m")
            assert depth == expected_depth, \
                f"Failed for {properties}: expected {expected_depth}, got {depth}"

    def test_osm_water_width_normalization(self):
        """Test OSM width field normalization"""
        test_cases = [
            ({"width": "10"}, 10.0),
            ({"width_m": "15.5"}, 15.5),
            ({"width": "20m"}, 20.0),
            ({"width": "invalid"}, None),
        ]
        
        for properties, expected_width in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            width = result.get("width_m")
            assert width == expected_width, \
                f"Failed for {properties}: expected {expected_width}, got {width}"

    def test_osm_water_area_normalization(self):
        """Test OSM area field normalization"""
        test_cases = [
            ({"area": "50"}, 50.0),
            ({"area_sqkm": "100.5"}, 100.5),
            ({"area_km2": "250"}, 250.0),
            ({"area": "invalid"}, None),
        ]
        
        for properties, expected_area in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            area = result.get("area_sqkm")
            assert area == expected_area, \
                f"Failed for {properties}: expected {expected_area}, got {area}"

    def test_osm_flow_type_normalization(self):
        """Test OSM flow type normalization"""
        test_cases = [
            ({"intermittent": "no"}, "permanent"),
            ({"intermittent": "yes"}, "intermittent"),
            ({"seasonal": "yes"}, "seasonal"),
            ({"flow": "permanent"}, "permanent"),
            ({"flow": "intermittent"}, "intermittent"),
            ({"tidal": "yes"}, None),  # tidal is separate boolean field
        ]
        
        for properties, expected_flow in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            flow = result.get("flow_type")
            assert flow == expected_flow, \
                f"Failed for {properties}: expected {expected_flow}, got {flow}"

    def test_osm_tidal_normalization(self):
        """Test OSM tidal property normalization (boolean)"""
        test_cases = [
            ({"tidal": "yes"}, True),
            ({"tidal": "no"}, False),
            ({"is_tidal": "true"}, True),
            ({"is_tidal": "false"}, False),
            ({"tidal": "1"}, True),
            ({"tidal": "0"}, False),
        ]
        
        for properties, expected_tidal in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            tidal = result.get("tidal")
            assert tidal == expected_tidal, \
                f"Failed for {properties}: expected {expected_tidal}, got {tidal}"

    def test_osm_saline_water_normalization(self):
        """Test OSM saline/saltwater property normalization"""
        test_cases = [
            ({"saline": "yes"}, True),
            ({"salt_water": "true"}, True),
            ({"is_saline": "1"}, True),
            ({"saline": "no"}, False),
            ({"salt_water": "false"}, False),
        ]
        
        for properties, expected_saline in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            saline = result.get("saline")
            assert saline == expected_saline, \
                f"Failed for {properties}: expected {expected_saline}, got {saline}"

    def test_osm_water_use_normalization(self):
        """Test OSM water use normalization"""
        test_cases = [
            ({"use": "drinking_water"}, "drinking_water"),
            ({"water_use": "irrigation"}, "irrigation"),
            ({"usage": "recreation"}, "recreation"),
            ({"use": "navigation"}, "navigation"),
            ({"use": "power_generation"}, "power_generation"),
            ({"use": "aquaculture"}, "aquaculture"),
            ({"use": "unknown_use"}, "unknown_use"),
        ]
        
        for properties, expected_use in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            use = result.get("use")
            assert use == expected_use, \
                f"Failed for {properties}: expected {expected_use}, got {use}"

    def test_osm_access_normalization(self):
        """Test OSM access property normalization"""
        test_cases = [
            ({"access": "public"}, "public"),
            ({"access": "private"}, "private"),
            ({"access": "permit"}, "permit"),
            ({"access": "restricted"}, "restricted"),
        ]
        
        for properties, expected_access in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            access = result.get("access")
            assert access == expected_access, \
                f"Failed for {properties}: expected {expected_access}, got {access}"

    def test_osm_swimming_fishing_boating_normalization(self):
        """Test OSM recreational use properties normalization"""
        test_cases = [
            ({"swimming": "yes"}, True),
            ({"swimming": "no"}, False),
            ({"is_swimmable": "true"}, True),
            ({"fishing": "yes"}, True),
            ({"fishing": "no"}, False),
            ({"boating": "true"}, True),
            ({"boating": "false"}, False),
        ]
        
        for properties, expected_value in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            key = list(properties.keys())[0]
            if "swim" in key.lower():
                field = "swimming"
            elif "fish" in key.lower():
                field = "fishing"
            elif "boat" in key.lower():
                field = "boating"
            else:
                continue
            
            value = result.get(field)
            assert value == expected_value, \
                f"Failed for {properties}: expected {expected_value}, got {value}"

    def test_osm_water_temperature_normalization(self):
        """Test OSM water temperature normalization"""
        test_cases = [
            ({"temperature": "25"}, 25.0),
            ({"temperature_c": "18.5"}, 18.5),
            ({"temp_c": "15"}, 15.0),
            ({"temperature": "invalid"}, None),
        ]
        
        for properties, expected_temp in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            temp = result.get("temperature_c")
            assert temp == expected_temp, \
                f"Failed for {properties}: expected {expected_temp}, got {temp}"

    def test_osm_water_ph_normalization(self):
        """Test OSM water pH normalization"""
        test_cases = [
            ({"ph": "7.0"}, 7.0),
            ({"ph_value": "7.5"}, 7.5),
            ({"ph": "6"}, 6.0),
            ({"ph": "invalid"}, None),
        ]
        
        for properties, expected_ph in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            ph = result.get("ph")
            assert ph == expected_ph, \
                f"Failed for {properties}: expected {expected_ph}, got {ph}"

    def test_comprehensive_osm_water_normalization(self):
        """Test comprehensive OSM water feature normalization"""
        osm_properties = {
            "name": "River Test",
            "waterway": "river",
            "flow": "permanent",
            "width": "50",
            "depth": "8",
            "saline": "no",
            "swimming": "yes",
            "fishing": "yes",
            "boating": "no",
            "access": "public",
            "temperature": "18",
            "ph": "7.2",
            "use": "recreation",
            "source": "OSM",
        }
        
        result = WaterStandardizer.standardize_properties(osm_properties)
        
        # Verify key fields are normalized
        assert result.get("name") == "River Test"
        assert result.get("water_type") == "river"
        assert result.get("flow_type") == "permanent"
        assert result.get("width_m") == 50.0
        assert result.get("depth_m") == 8.0
        assert result.get("saline") is False
        assert result.get("swimming") is True
        assert result.get("fishing") is True
        assert result.get("boating") is False
        assert result.get("access") == "public"
        assert result.get("temperature_c") == 18.0
        assert result.get("ph") == 7.2
        assert result.get("use") == "recreation"
        assert result.get("source") == "OSM"

    def test_field_name_standardization(self):
        """Test field name conversion to lowercase_underscore"""
        osm_properties = {
            "waterway:type": "canal",
            "water-depth": "5",
            "WATER_AREA": "100",
            "flowType": "permanent",
            "water quality": "good",
        }
        
        result = WaterStandardizer.standardize_properties(osm_properties)
        
        # Verify all fields are properly standardized
        # Lowercase underscore format should be used
        standardized_keys = set(result.keys())
        
        # All keys should be lowercase
        for key in standardized_keys:
            assert key == key.lower(), f"Key {key} contains uppercase letters"
            # All keys should use underscores, not hyphens or camelCase
            assert "_" in key or key == "name", \
                f"Key {key} doesn't follow standardized naming"

    def test_missing_fields_handling(self):
        """Test handling of missing optional fields"""
        properties = {
            "name": "Small Stream",
            "waterway": "stream",
        }
        
        result = WaterStandardizer.standardize_properties(properties)
        
        # Required fields should be present
        assert "water_type" in result
        assert "name" in result
        # Missing fields should not cause errors
        assert "depth_m" not in result or result.get("depth_m") is None
        assert "width_m" not in result or result.get("width_m") is None

    def test_null_and_empty_handling(self):
        """Test handling of null and empty values"""
        test_cases = [
            {"waterway": None},
            {"waterway": ""},
            {"waterway": "   "},
            {"name": None},
            {"name": "   "},
        ]
        
        for properties in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            # Empty/null values should be handled gracefully
            # Should not crash
            assert isinstance(result, dict)

    def test_provider_specification(self):
        """Test that provider parameter is accepted"""
        properties = {"waterway": "river", "name": "Test River"}
        
        # Should accept provider parameter without error
        result = WaterStandardizer.standardize_properties(properties, provider="OSM")
        assert "water_type" in result
        
        result = WaterStandardizer.standardize_properties(properties, provider="other")
        assert "water_type" in result

    def test_complex_osm_tags_normalization(self):
        """Test handling of complex OSM tag combinations"""
        # OSM uses complex tag hierarchies like water:type, waterway:intermittent, etc.
        osm_properties = {
            "water:type": "river",
            "water:intermittent": "yes",
            "water:saline": "no",
            "water:use": "irrigation",
            "water:temperature": "20",
            "waterway": "river",  # Fallback tag
        }
        
        result = WaterStandardizer.standardize_properties(osm_properties)
        
        # Should normalize complex tags
        assert result.get("water_type") in ["river", "stream", "unknown"]
        assert result.get("flow_type") in ["permanent", "intermittent", "seasonal", None]

    def test_water_feature_types(self):
        """Test different water feature types"""
        test_cases = [
            ({"feature_type": "waterway"}, "waterway"),
            ({"feature": "natural"}, "natural"),
            ({"primary_tag": "water"}, "water"),
            ({"feature_type": "man_made"}, "man_made"),
        ]
        
        for properties, expected_feature_type in test_cases:
            result = WaterStandardizer.standardize_properties(properties)
            feature_type = result.get("feature_type")
            assert feature_type == expected_feature_type, \
                f"Failed for {properties}: expected {expected_feature_type}, got {feature_type}"


class TestWaterStandardizerIntegration:
    """Integration tests with the main standardizer"""

    def test_water_standardizer_in_main_pipeline(self):
        """Test that water standardizer integrates with main DataStandardizer"""
        from backend.data_models import RawDataset, Feature
        from backend.standardizers.standardizer import DataStandardizer
        
        # Create raw OSM water data
        raw_feature = Feature(
            id="osm_river_123",
            type="Feature",
            geometry={"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
            properties={
                "waterway": "river",
                "name": "Test River",
                "flow": "permanent",
                "width": "50",
                "depth": "8",
                "swimming": "yes",
                "use": "recreation",
            }
        )
        
        raw_dataset = RawDataset(
            source_provider="OSM",
            category="water",
            features=[raw_feature],
            metadata={"version": "2024-01"}
        )
        
        # Standardize
        standardizer = DataStandardizer()
        result = standardizer.standardize(raw_dataset)
        
        # Verify result
        assert result.source_provider == "OSM"
        assert result.category == "water"
        assert len(result.features) == 1
        
        standardized_feature = result.features[0]
        assert standardized_feature.properties.get("water_type") == "river"
        assert standardized_feature.properties.get("name") == "Test River"
        assert standardized_feature.properties.get("flow_type") == "permanent"
        assert standardized_feature.properties.get("width_m") == 50.0
        assert standardized_feature.properties.get("depth_m") == 8.0
        assert standardized_feature.properties.get("swimming") is True
        assert standardized_feature.properties.get("use") == "recreation"

    def test_multiple_water_types_in_dataset(self):
        """Test standardization of datasets with multiple water type features"""
        from backend.data_models import RawDataset, Feature
        from backend.standardizers.standardizer import DataStandardizer
        
        # Multiple water features of different types
        raw_features = [
            Feature(
                id="river_1",
                type="Feature",
                geometry={"type": "LineString", "coordinates": [[0, 0], [1, 1]]},
                properties={"waterway": "river", "name": "Big River"}
            ),
            Feature(
                id="stream_1",
                type="Feature",
                geometry={"type": "LineString", "coordinates": [[1, 1], [2, 2]]},
                properties={"waterway": "stream", "name": "Small Stream"}
            ),
            Feature(
                id="lake_1",
                type="Feature",
                geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                properties={"waterway": "lake", "name": "Test Lake"}
            ),
        ]
        
        raw_dataset = RawDataset(
            source_provider="OSM",
            category="water",
            features=raw_features,
            metadata={"version": "2024-01"}
        )
        
        # Standardize
        standardizer = DataStandardizer()
        result = standardizer.standardize(raw_dataset)
        
        # Verify all features standardized
        assert len(result.features) == 3
        
        # Check each feature type
        assert result.features[0].properties.get("water_type") == "river"
        assert result.features[1].properties.get("water_type") == "stream"
        assert result.features[2].properties.get("water_type") == "lake"
        
        # Verify names preserved
        assert result.features[0].properties.get("name") == "Big River"
        assert result.features[1].properties.get("name") == "Small Stream"
        assert result.features[2].properties.get("name") == "Test Lake"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
