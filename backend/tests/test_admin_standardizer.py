"""
Tests for OSM Administrative Boundary data field normalization (Task 6.3)

Tests the AdminStandardizer with real OSM admin boundary field mappings.
"""

import pytest
from backend.standardizers.admin_standardizer import AdminStandardizer


class TestAdminFieldNormalization:
    """Test OSM administrative boundary field normalization"""

    def test_admin_level_normalization(self):
        """Test OSM admin_level field normalization to standard hierarchy"""
        test_cases = [
            ("2", 2),
            (2, 2),
            ("4", 4),
            (4, 4),
            ("6", 6),
            ("8", 8),
            ("invalid", None),
        ]
        
        for input_level, expected_level in test_cases:
            properties = {"admin_level": input_level}
            result = AdminStandardizer.standardize_properties(properties)
            assert result.get("admin_level") == expected_level, \
                f"Failed for {input_level}: expected {expected_level}, got {result.get('admin_level')}"

    def test_admin_level_name_mapping(self):
        """Test OSM admin_level to jurisdiction name mapping"""
        test_cases = [
            (2, "country"),
            (3, "region"),
            (4, "state"),
            (5, "county"),
            (6, "district"),
            (8, "municipality"),
            (9, "city"),
        ]
        
        for level, expected_name in test_cases:
            properties = {"admin_level": str(level)}
            result = AdminStandardizer.standardize_properties(properties)
            assert result.get("admin_level_name") == expected_name, \
                f"Failed for level {level}: expected {expected_name}, got {result.get('admin_level_name')}"

    def test_country_code_normalization(self):
        """Test country code normalization and validation"""
        test_cases = [
            ("us", "US"),
            ("gb", "GB"),
            ("fr", "FR"),
            ("de", "DE"),
            ("USA", "USA"),  # Will be preserved as-is (uppercase)
            ("invalid", "INVALID"),  # Will be preserved as-is (uppercase)
        ]
        
        for input_code, expected_code in test_cases:
            properties = {"country_code": input_code}
            result = AdminStandardizer.standardize_properties(properties)
            assert result.get("country_code") == expected_code, \
                f"Failed for {input_code}: expected {expected_code}, got {result.get('country_code')}"

    def test_comprehensive_country_properties(self):
        """Test comprehensive country-level admin properties"""
        osm_properties = {
            "name": "United States",
            "admin_level": "2",
            "boundary": "administrative",
            "country": "United States",
            "country_code": "us",
            "wikidata": "Q30",
            "population": "331000000",
            "area_sqkm": "9834000",
        }
        
        result = AdminStandardizer.standardize_properties(osm_properties)
        
        # Verify key fields are normalized
        assert result.get("name") == "United States"
        assert result.get("admin_level") == 2
        assert result.get("admin_level_name") == "country"
        assert result.get("country_code") == "US"
        assert result.get("population") == 331000000.0
        assert result.get("area_sqkm") == 9834000.0

    def test_comprehensive_state_properties(self):
        """Test comprehensive state-level admin properties"""
        osm_properties = {
            "name": "California",
            "admin_level": "4",
            "boundary": "administrative",
            "country": "United States",
            "country_code": "us",
            "state": "California",
            "state_code": "CA",
            "population": "39538223",
            "area_sqkm": "423970",
        }
        
        result = AdminStandardizer.standardize_properties(osm_properties)
        
        # Verify key fields
        assert result.get("name") == "California"
        assert result.get("admin_level") == 4
        assert result.get("admin_level_name") == "state"
        assert result.get("country_code") == "US"
        assert result.get("state") == "California"
        assert result.get("state_code") == "CA"
        assert result.get("population") == 39538223.0

    def test_district_properties(self):
        """Test district-level administrative properties"""
        osm_properties = {
            "name": "Los Angeles County",
            "admin_level": "6",
            "boundary": "administrative",
            "country": "United States",
            "country_code": "us",
            "state": "California",
            "district": "Los Angeles County",
            "population": "9818605",
            "area_sqkm": "12562",
        }
        
        result = AdminStandardizer.standardize_properties(osm_properties)
        
        assert result.get("name") == "Los Angeles County"
        assert result.get("admin_level") == 6
        assert result.get("admin_level_name") == "district"
        assert result.get("district") == "Los Angeles County"

    def test_multilingual_names(self):
        """Test handling of multilingual name tags"""
        osm_properties = {
            "name": "München",
            "name:en": "Munich",
            "name:fr": "Munich",
            "name:de": "München",
            "name:es": "Múnich",
        }
        
        result = AdminStandardizer.standardize_properties(osm_properties)
        
        # Name should be present
        assert result.get("name") == "München"
        # Language-specific names should be preserved
        assert result.get("name_en") == "Munich"
        assert result.get("name_de") == "München"
        assert result.get("name_fr") == "Munich"
        assert result.get("name_es") == "Múnich"

    def test_administrative_references(self):
        """Test administrative reference fields"""
        osm_properties = {
            "name": "Test Region",
            "ref": "ABC123",
            "ref:wikidata": "Q12345",
            "ref:wikipedia": "en:Test_Region",
            "ref:fips": "12345",
            "ref:hasc": "US.CA.XX",
        }
        
        result = AdminStandardizer.standardize_properties(osm_properties)
        
        assert result.get("reference_id") == "ABC123"
        assert result.get("wikidata_id") == "Q12345"
        assert result.get("wikipedia") == "en:Test_Region"
        assert result.get("fips_code") == "12345"
        assert result.get("hasc_code") == "US.CA.XX"

    def test_numeric_field_handling(self):
        """Test numeric field parsing"""
        osm_properties = {
            "population": "1000000",
            "area_sqkm": "10000.5",
            "area_sqmi": "3861.02",
            "population_density": "100.5",
        }
        
        result = AdminStandardizer.standardize_properties(osm_properties)
        
        assert result.get("population") == 1000000.0
        assert result.get("area_sqkm") == 10000.5
        assert result.get("area_sqmi") == 3861.02
        assert result.get("population_density") == 100.5

    def test_boolean_field_handling(self):
        """Test boolean field normalization"""
        test_cases = [
            ("yes", True),
            ("no", False),
            ("true", True),
            ("false", False),
            ("1", True),
            ("0", False),
        ]
        
        for input_val, expected_bool in test_cases:
            properties = {"capital": input_val}
            result = AdminStandardizer.standardize_properties(properties)
            capital = result.get("capital")
            assert capital == expected_bool, \
                f"Failed for {input_val}: expected {expected_bool}, got {capital}"

    def test_field_name_standardization(self):
        """Test field name conversion to lowercase_underscore"""
        osm_properties = {
            "admin_level": "4",
            "country_code": "US",
            "admin-status": "complete",
            "adminLevel": "4",
            "BOUNDARY_TYPE": "administrative",
        }
        
        result = AdminStandardizer.standardize_properties(osm_properties)
        
        # All keys should be lowercase
        for key in result.keys():
            assert key == key.lower(), f"Key {key} contains uppercase letters"

    def test_missing_fields_handling(self):
        """Test handling of missing optional fields"""
        properties = {
            "name": "Simple Region",
            "admin_level": "4",
        }
        
        result = AdminStandardizer.standardize_properties(properties)
        
        # Required fields should be present
        assert "name" in result
        assert "admin_level" in result
        assert "admin_level_name" in result
        # Missing fields should not cause errors
        assert "population" not in result or result.get("population") is None

    def test_null_and_empty_handling(self):
        """Test handling of null and empty values"""
        test_cases = [
            {"admin_level": None},
            {"name": ""},
            {"name": "   "},
        ]
        
        for properties in test_cases:
            result = AdminStandardizer.standardize_properties(properties)
            # Should handle gracefully without errors
            assert isinstance(result, dict)

    def test_provider_specification(self):
        """Test that provider parameter is accepted"""
        properties = {"admin_level": "4", "name": "Test"}
        
        # Should accept provider parameter without error
        result = AdminStandardizer.standardize_properties(properties, provider="OSM")
        assert "admin_level" in result
        
        result = AdminStandardizer.standardize_properties(properties, provider="other")
        assert "admin_level" in result


class TestAdminStandardizerIntegration:
    """Integration tests with the main standardizer"""

    def test_admin_standardizer_in_main_pipeline(self):
        """Test that admin standardizer integrates with main DataStandardizer"""
        from backend.data_models import RawDataset, Feature
        from backend.standardizers.standardizer import DataStandardizer
        
        # Create raw OSM admin boundary data
        raw_feature = Feature(
            id="osm_admin_123",
            type="Feature",
            geometry={
                "type": "Polygon",
                "coordinates": [[[-120, 30], [-119, 30], [-119, 31], [-120, 31], [-120, 30]]]
            },
            properties={
                "name": "California",
                "admin_level": "4",
                "boundary": "administrative",
                "country": "United States",
                "country_code": "us",
                "state": "California",
                "population": "39000000",
                "area_sqkm": "423970",
            }
        )
        
        raw_dataset = RawDataset(
            source_provider="OSM",
            category="admin",
            features=[raw_feature],
            metadata={"version": "2024-01"}
        )
        
        # Standardize
        standardizer = DataStandardizer()
        result = standardizer.standardize(raw_dataset)
        
        # Verify result
        assert result.source_provider == "OSM"
        assert result.category == "admin"
        assert len(result.features) == 1
        
        standardized_feature = result.features[0]
        assert standardized_feature.properties.get("name") == "California"
        assert standardized_feature.properties.get("admin_level") == 4
        assert standardized_feature.properties.get("admin_level_name") == "state"
        assert standardized_feature.properties.get("country_code") == "US"
        assert standardized_feature.properties.get("population") == 39000000.0

    def test_multiple_admin_levels(self):
        """Test standardization of multiple admin level features"""
        from backend.data_models import RawDataset, Feature
        from backend.standardizers.standardizer import DataStandardizer
        
        # Create features at different admin levels
        features = [
            Feature(
                id="country",
                type="Feature",
                geometry={"type": "Polygon", "coordinates": [[[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]]},
                properties={"name": "TestCountry", "admin_level": "2", "country_code": "TC"}
            ),
            Feature(
                id="state",
                type="Feature",
                geometry={"type": "Polygon", "coordinates": [[[0, 0], [5, 0], [5, 5], [0, 5], [0, 0]]]},
                properties={"name": "TestState", "admin_level": "4", "country": "TestCountry", "state": "TestState"}
            ),
            Feature(
                id="district",
                type="Feature",
                geometry={"type": "Polygon", "coordinates": [[[0, 0], [2, 0], [2, 2], [0, 2], [0, 0]]]},
                properties={"name": "TestDistrict", "admin_level": "6", "district": "TestDistrict"}
            ),
        ]
        
        raw_dataset = RawDataset(
            source_provider="OSM",
            category="admin",
            features=features,
            metadata={"version": "2024-01"}
        )
        
        # Standardize
        standardizer = DataStandardizer()
        result = standardizer.standardize(raw_dataset)
        
        # Verify all features processed
        assert len(result.features) == 3
        
        # Verify each level
        country_props = result.features[0].properties
        assert country_props.get("admin_level_name") == "country"
        
        state_props = result.features[1].properties
        assert state_props.get("admin_level_name") == "state"
        
        district_props = result.features[2].properties
        assert district_props.get("admin_level_name") == "district"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
