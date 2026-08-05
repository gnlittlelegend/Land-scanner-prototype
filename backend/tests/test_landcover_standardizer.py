"""
Unit tests for Land Cover Standardizer.

Tests the LandCoverStandardizer implementation that normalizes
land cover properties from Copernicus and other providers.

Requirements: 4.2, 4.4
"""

import pytest
from backend.standardizers.landcover_standardizer import LandCoverStandardizer


class TestLandCoverStandardizerInitialization:
    """Test LandCoverStandardizer initialization and class constants."""

    def test_land_cover_classes_defined(self):
        """Land cover classes should be properly defined."""
        assert LandCoverStandardizer.LAND_COVER_CLASSES is not None
        assert len(LandCoverStandardizer.LAND_COVER_CLASSES) > 0
        assert "water" in LandCoverStandardizer.LAND_COVER_CLASSES.values()
        assert "built_up" in LandCoverStandardizer.LAND_COVER_CLASSES.values()
        assert "crops" in LandCoverStandardizer.LAND_COVER_CLASSES.values()

    def test_copernicus_code_mapping_defined(self):
        """Copernicus code mapping should be defined."""
        assert LandCoverStandardizer.COPERNICUS_CODE_MAPPING is not None
        assert len(LandCoverStandardizer.COPERNICUS_CODE_MAPPING) > 0

    def test_esa_code_mapping_defined(self):
        """ESA code mapping should be defined."""
        assert LandCoverStandardizer.ESA_CODE_MAPPING is not None
        assert len(LandCoverStandardizer.ESA_CODE_MAPPING) > 0

    def test_field_mappings_defined(self):
        """Field mappings should be defined."""
        assert LandCoverStandardizer.FIELD_MAPPINGS is not None
        assert len(LandCoverStandardizer.FIELD_MAPPINGS) > 0


class TestCopernicusCodeMapping:
    """Test Copernicus-specific land cover code normalization."""

    def test_copernicus_code_0_no_data(self):
        """Code 0 should map to no_data."""
        result = LandCoverStandardizer._normalize_lc_code("0", provider="copernicus")
        assert result == "no_data"

    def test_copernicus_code_1_tree_cover(self):
        """Code 1 should map to tree_cover."""
        result = LandCoverStandardizer._normalize_lc_code("1", provider="copernicus")
        assert result == "tree_cover"

    def test_copernicus_code_5_built_up(self):
        """Code 5 should map to built_up."""
        result = LandCoverStandardizer._normalize_lc_code("5", provider="copernicus")
        assert result == "built_up"

    def test_copernicus_code_4_crops(self):
        """Code 4 should map to crops."""
        result = LandCoverStandardizer._normalize_lc_code("4", provider="copernicus")
        assert result == "crops"

    def test_copernicus_code_8_water(self):
        """Code 8 should map to water."""
        result = LandCoverStandardizer._normalize_lc_code("8", provider="copernicus")
        assert result == "water"

    def test_copernicus_code_all_mappings(self):
        """All Copernicus codes should have valid mappings."""
        for code in LandCoverStandardizer.COPERNICUS_CODE_MAPPING.keys():
            result = LandCoverStandardizer._normalize_lc_code(
                code, provider="copernicus"
            )
            assert result is not None
            assert result in LandCoverStandardizer.LAND_COVER_CLASSES.values()


class TestESACodeMapping:
    """Test ESA WorldCover code normalization."""

    def test_esa_code_10_tree_cover(self):
        """ESA code 10 should map to tree_cover."""
        result = LandCoverStandardizer._normalize_lc_code("10", provider="esa")
        assert result == "tree_cover"

    def test_esa_code_50_built_up(self):
        """ESA code 50 should map to built_up."""
        result = LandCoverStandardizer._normalize_lc_code("50", provider="esa")
        assert result == "built_up"

    def test_esa_code_40_crops(self):
        """ESA code 40 should map to crops."""
        result = LandCoverStandardizer._normalize_lc_code("40", provider="esa")
        assert result == "crops"

    def test_esa_code_80_water(self):
        """ESA code 80 should map to water."""
        result = LandCoverStandardizer._normalize_lc_code("80", provider="esa")
        assert result == "water"

    def test_esa_code_all_mappings(self):
        """All ESA codes should have valid mappings."""
        for code in LandCoverStandardizer.ESA_CODE_MAPPING.keys():
            result = LandCoverStandardizer._normalize_lc_code(
                code, provider="esa"
            )
            assert result is not None
            assert result in LandCoverStandardizer.LAND_COVER_CLASSES.values()


class TestFieldMapping:
    """Test field name normalization."""

    def test_lc_class_field_mapping(self):
        """'lc_classes' should map to 'lc_class'."""
        key = LandCoverStandardizer._get_standardized_key("lc_classes")
        assert key == "lc_class"

    def test_classification_field_mapping(self):
        """'classification' should map to 'lc_class'."""
        key = LandCoverStandardizer._get_standardized_key("classification")
        assert key == "lc_class"

    def test_lc_code_field_mapping(self):
        """'lc_code' should map to 'lc_code'."""
        key = LandCoverStandardizer._get_standardized_key("lc_code")
        assert key == "lc_code"

    def test_confidence_field_mapping(self):
        """'confidence' should map to 'confidence'."""
        key = LandCoverStandardizer._get_standardized_key("confidence")
        assert key == "confidence"

    def test_confidence_pct_field_mapping(self):
        """'confidence_pct' should map to 'confidence_percent'."""
        key = LandCoverStandardizer._get_standardized_key("confidence_pct")
        assert key == "confidence_percent"

    def test_source_field_mapping(self):
        """'source' should map to 'source'."""
        key = LandCoverStandardizer._get_standardized_key("source")
        assert key == "source"

    def test_version_field_mapping(self):
        """'version' should map to 'version'."""
        key = LandCoverStandardizer._get_standardized_key("version")
        assert key == "version"

    def test_percent_water_field_mapping(self):
        """'percent_water' should map to 'percent_water'."""
        key = LandCoverStandardizer._get_standardized_key("percent_water")
        assert key == "percent_water"

    def test_resolution_field_mapping(self):
        """'pixel_size' should map to 'resolution_m'."""
        key = LandCoverStandardizer._get_standardized_key("pixel_size")
        assert key == "resolution_m"


class TestConfidenceNormalization:
    """Test confidence value normalization."""

    def test_confidence_valid_50(self):
        """Confidence value 50 should be returned as 50.0."""
        result = LandCoverStandardizer._normalize_confidence(50)
        assert result == 50.0

    def test_confidence_valid_100(self):
        """Confidence value 100 should be returned as 100.0."""
        result = LandCoverStandardizer._normalize_confidence(100)
        assert result == 100.0

    def test_confidence_valid_0(self):
        """Confidence value 0 should be returned as 0.0."""
        result = LandCoverStandardizer._normalize_confidence(0)
        assert result == 0.0

    def test_confidence_clamped_above_100(self):
        """Confidence values above 100 should be clamped to 100."""
        result = LandCoverStandardizer._normalize_confidence(150)
        assert result == 100.0

    def test_confidence_clamped_below_0(self):
        """Confidence values below 0 should be clamped to 0."""
        result = LandCoverStandardizer._normalize_confidence(-50)
        assert result == 0.0

    def test_confidence_string_number(self):
        """String numbers should be converted."""
        result = LandCoverStandardizer._normalize_confidence("75")
        assert result == 75.0

    def test_confidence_invalid_string(self):
        """Invalid strings should return None."""
        result = LandCoverStandardizer._normalize_confidence("invalid")
        assert result is None

    def test_confidence_none(self):
        """None should return None."""
        result = LandCoverStandardizer._normalize_confidence(None)
        assert result is None


class TestPercentageNormalization:
    """Test percentage value normalization."""

    def test_percentage_25_percent(self):
        """25% should be returned as 25.0."""
        result = LandCoverStandardizer._normalize_percentage(25)
        assert result == 25.0

    def test_percentage_100_percent(self):
        """100% should be returned as 100.0."""
        result = LandCoverStandardizer._normalize_percentage(100)
        assert result == 100.0

    def test_percentage_clamped_above_100(self):
        """Percentages above 100 should be clamped to 100."""
        result = LandCoverStandardizer._normalize_percentage(150)
        assert result == 100.0

    def test_percentage_multiple_values(self):
        """Multiple percentage values should all normalize correctly."""
        for percent in [0, 10, 25, 50, 75, 100]:
            result = LandCoverStandardizer._normalize_percentage(percent)
            assert result == float(percent)


class TestLandCoverClassNormalization:
    """Test land cover class name normalization."""

    def test_class_water(self):
        """'water' should map to 'water'."""
        result = LandCoverStandardizer._normalize_lc_class("water")
        assert result == "water"

    def test_class_built_up(self):
        """'built_up' should map to 'built_up'."""
        result = LandCoverStandardizer._normalize_lc_class("built_up")
        assert result == "built_up"

    def test_class_with_spaces(self):
        """Classes with spaces should be normalized."""
        result = LandCoverStandardizer._normalize_lc_class("Tree Cover")
        assert result == "tree_cover"

    def test_class_with_hyphens(self):
        """Classes with hyphens should be normalized."""
        result = LandCoverStandardizer._normalize_lc_class("snow-ice")
        assert result == "snow_ice"

    def test_class_uppercase(self):
        """Uppercase classes should be normalized to lowercase."""
        result = LandCoverStandardizer._normalize_lc_class("WATER")
        assert result == "water"

    def test_class_unknown(self):
        """Unknown classes should map to 'no_data'."""
        result = LandCoverStandardizer._normalize_lc_class("unknown_class")
        assert result == "no_data"

    def test_class_none(self):
        """None should return None."""
        result = LandCoverStandardizer._normalize_lc_class(None)
        assert result is None


class TestPropertiesStandardization:
    """Test complete properties standardization."""

    def test_standardize_copernicus_properties(self):
        """Copernicus properties should be standardized correctly."""
        raw_props = {
            "lc_code": 5,
            "confidence": 85,
            "pixel_size": 100,
            "source": "Copernicus GLC",
            "year": 2021
        }
        result = LandCoverStandardizer.standardize_properties(
            raw_props, provider="copernicus"
        )
        assert "lc_code" in result
        assert result["lc_code"] == "built_up"  # Code 5 maps to built_up in Copernicus
        assert "confidence" in result
        assert result["confidence"] == 85.0
        assert "resolution_m" in result
        assert result["resolution_m"] == 100.0

    def test_standardize_mixed_field_names(self):
        """Mixed field names should be normalized."""
        raw_props = {
            "lc_classes": "built_up",
            "Confidence": 90,
            "CLASSIFICATION_CODE": "5",
        }
        result = LandCoverStandardizer.standardize_properties(
            raw_props, provider="copernicus"
        )
        assert "lc_class" in result
        assert "confidence" in result

    def test_standardize_with_percentages(self):
        """Percentage fields should be normalized."""
        raw_props = {
            "percent_water": 15,
            "percent_built": 35,
            "percent_crops": 50,
        }
        result = LandCoverStandardizer.standardize_properties(raw_props)
        assert result["percent_water"] == 15.0
        assert result["percent_built"] == 35.0
        assert result["percent_crops"] == 50.0

    def test_standardize_with_confidence_percentages(self):
        """Confidence percentages should be normalized."""
        raw_props = {
            "lc_code": 1,
            "confidence_percent": 95,
        }
        result = LandCoverStandardizer.standardize_properties(raw_props)
        assert result["confidence_percent"] == 95.0

    def test_standardize_removes_unknown_fields(self):
        """Unknown fields should not be included."""
        raw_props = {
            "lc_code": 3,
            "confidence": 80,
            "unknown_field": "should_not_appear",
        }
        result = LandCoverStandardizer.standardize_properties(raw_props)
        assert "unknown_field" not in result
        assert "lc_code" in result
        assert "confidence" in result

    def test_standardize_empty_properties(self):
        """Empty properties should return empty dict."""
        result = LandCoverStandardizer.standardize_properties({})
        assert result == {}

    def test_standardize_with_none_values(self):
        """None values should be filtered out."""
        raw_props = {
            "lc_code": 5,
            "confidence": None,
            "source": None,
        }
        result = LandCoverStandardizer.standardize_properties(raw_props)
        assert "lc_code" in result
        assert "confidence" not in result or result["confidence"] is None


class TestEpochNormalization:
    """Test epoch/year value normalization."""

    def test_epoch_year_2021(self):
        """Year 2021 should be preserved."""
        result = LandCoverStandardizer._normalize_epoch(2021)
        assert result == "2021"

    def test_epoch_year_string(self):
        """Year as string should be preserved."""
        result = LandCoverStandardizer._normalize_epoch("2021")
        assert result == "2021"

    def test_epoch_date_string(self):
        """Date string should be preserved."""
        result = LandCoverStandardizer._normalize_epoch("2021-06-15")
        assert result == "2021-06-15"

    def test_epoch_none(self):
        """None should return None."""
        result = LandCoverStandardizer._normalize_epoch(None)
        assert result is None


class TestBooleanNormalization:
    """Test boolean value normalization."""

    def test_boolean_true(self):
        """True should return True."""
        result = LandCoverStandardizer._normalize_boolean(True)
        assert result is True

    def test_boolean_false(self):
        """False should return False."""
        result = LandCoverStandardizer._normalize_boolean(False)
        assert result is False

    def test_string_true(self):
        """String 'true' should return True."""
        result = LandCoverStandardizer._normalize_boolean("true")
        assert result is True

    def test_string_yes(self):
        """String 'yes' should return True."""
        result = LandCoverStandardizer._normalize_boolean("yes")
        assert result is True

    def test_string_1(self):
        """String '1' should return True."""
        result = LandCoverStandardizer._normalize_boolean("1")
        assert result is True

    def test_string_false(self):
        """String 'false' should return False."""
        result = LandCoverStandardizer._normalize_boolean("false")
        assert result is False

    def test_string_no(self):
        """String 'no' should return False."""
        result = LandCoverStandardizer._normalize_boolean("no")
        assert result is False

    def test_string_0(self):
        """String '0' should return False."""
        result = LandCoverStandardizer._normalize_boolean("0")
        assert result is False

    def test_int_1(self):
        """Integer 1 should return True."""
        result = LandCoverStandardizer._normalize_boolean(1)
        assert result is True

    def test_int_0(self):
        """Integer 0 should return False."""
        result = LandCoverStandardizer._normalize_boolean(0)
        assert result is False

    def test_float_1_0(self):
        """Float 1.0 should return True."""
        result = LandCoverStandardizer._normalize_boolean(1.0)
        assert result is True

    def test_float_0_0(self):
        """Float 0.0 should return False."""
        result = LandCoverStandardizer._normalize_boolean(0.0)
        assert result is False


class TestNumericNormalization:
    """Test numeric value normalization."""

    def test_numeric_integer(self):
        """Integer should be converted to float."""
        result = LandCoverStandardizer._normalize_numeric(100)
        assert result == 100.0
        assert isinstance(result, float)

    def test_numeric_float(self):
        """Float should be returned as-is."""
        result = LandCoverStandardizer._normalize_numeric(100.5)
        assert result == 100.5

    def test_numeric_string(self):
        """String number should be converted."""
        result = LandCoverStandardizer._normalize_numeric("100")
        assert result == 100.0

    def test_numeric_invalid_string(self):
        """Invalid string should return None."""
        result = LandCoverStandardizer._normalize_numeric("invalid")
        assert result is None

    def test_numeric_none(self):
        """None should return None."""
        result = LandCoverStandardizer._normalize_numeric(None)
        assert result is None


class TestRasterVectorConversion:
    """Test handling of raster-to-vector conversion scenarios."""

    def test_raster_pixel_properties(self):
        """Raster pixel properties should be normalized."""
        raw_props = {
            "pixel_size": 30,
            "pixel_value": 5,
            "lc_code": 5,
            "confidence": 92,
        }
        result = LandCoverStandardizer.standardize_properties(raw_props)
        assert "resolution_m" in result
        assert result["resolution_m"] == 30.0
        assert "lc_code" in result

    def test_vector_feature_properties(self):
        """Vector feature properties should be normalized."""
        raw_props = {
            "lc_code": 3,
            "area_sqkm": 25.5,
            "percent_of_polygon": 45,
            "confidence": 88,
        }
        result = LandCoverStandardizer.standardize_properties(raw_props)
        assert "lc_code" in result
        assert "confidence" in result
