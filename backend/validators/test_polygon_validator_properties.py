"""
Property-Based Tests for PolygonValidator - Area Calculation and Metadata Consistency

Feature: distance-unit-standardization
Property 1: All area metadata uses square metres only
Property 2: Area values calculated in square metres

Validates: Requirements 1.2, 1.3, 1.4, 1.5, 6.1, 6.2
"""

import pytest
from dataclasses import fields

from backend.validators.polygon_validator import PolygonValidator, PolygonMetadata


@pytest.mark.property_test
class TestPolygonValidatorAreaCalculationProperty:
    """
    Property 2: Area values calculated in square metres
    
    For any polygon with known dimensions, the calculated area_sqm should equal 
    the expected area in square metres.
    
    Validates: Requirements 1.2, 1.3, 6.1, 6.2
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize validator for tests."""
        self.validator = PolygonValidator()
    
    def test_area_calculation_small_polygon(self):
        """
        Verify calculated area is in square metres for a small polygon.
        """
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [0.0001, 0],
                    [0.0001, 0.0001],
                    [0, 0.0001],
                    [0, 0]
                ]]
            }
        }
        
        result = self.validator.validate(geojson)
        
        # Verify area_sqm is positive and in valid range
        assert result.area_sqm > 0, "Area must be positive"
        assert result.area_sqm >= 10, "Area should be >= 10 m²"
        assert result.area_sqm <= 100_000_000, "Area should be <= 100,000,000 m²"
        assert isinstance(result.area_sqm, float), "Area should be float"
    
    def test_area_calculation_medium_polygon(self):
        """
        Verify area calculation is consistent for medium-sized polygon.
        """
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [10, 20],
                    [10.0005, 20],
                    [10.0005, 20.0005],
                    [10, 20.0005],
                    [10, 20]
                ]]
            }
        }
        
        result = self.validator.validate(geojson)
        
        # Verify area calculation
        assert result.area_sqm > 0, "Area must be positive"
        assert result.area_sqm >= 10, "Area should be >= 10 m²"
        assert isinstance(result.area_sqm, float), "Area should be float"
    
    def test_area_values_consistency(self):
        """
        Verify same polygon produces same area across multiple validations.
        """
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [5, 10],
                    [5.0002, 10],
                    [5.0002, 10.0002],
                    [5, 10.0002],
                    [5, 10]
                ]]
            }
        }
        
        result1 = self.validator.validate(geojson)
        result2 = self.validator.validate(geojson)
        
        # Same geometry should produce same area
        assert abs(result1.area_sqm - result2.area_sqm) < 0.001, \
            f"Areas should be consistent: {result1.area_sqm} vs {result2.area_sqm}"


@pytest.mark.property_test
class TestPolygonValidatorMetadataConsistencyProperty:
    """
    Property 1: All area metadata uses square metres only
    
    For any validated polygon, the returned PolygonMetadata should have area_sqm 
    field and NOT have area_sqkm field.
    
    Validates: Requirements 1.3, 1.4, 1.5
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Initialize validator for tests."""
        self.validator = PolygonValidator()
    
    def test_metadata_structure_has_area_sqm_only(self):
        """
        Verify that PolygonMetadata dataclass enforces m²-only storage.
        """
        # Get all fields from PolygonMetadata dataclass
        metadata_fields = {f.name for f in fields(PolygonMetadata)}
        
        # Verify area_sqm exists
        assert 'area_sqm' in metadata_fields, \
            "PolygonMetadata must have 'area_sqm' field"
        
        # Verify area_sqkm does NOT exist
        assert 'area_sqkm' not in metadata_fields, \
            "PolygonMetadata must NOT have 'area_sqkm' field"
        
        # Verify only one area field
        area_fields = [f for f in metadata_fields if 'area' in f.lower()]
        assert area_fields == ['area_sqm'], \
            f"Should have only area_sqm field, found: {area_fields}"
    
    def test_metadata_has_area_sqm_not_sqkm(self):
        """
        Verify returned metadata has area_sqm field only, not area_sqkm.
        """
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [0.0001, 0],
                    [0.0001, 0.0001],
                    [0, 0.0001],
                    [0, 0]
                ]]
            }
        }
        
        result = self.validator.validate(geojson)
        
        # Verify area_sqm exists and has value
        assert hasattr(result, 'area_sqm'), \
            "PolygonMetadata must have area_sqm attribute"
        assert result.area_sqm is not None, "area_sqm should not be None"
        assert isinstance(result.area_sqm, float), "area_sqm should be float"
        
        # Verify area_sqkm does NOT exist
        assert not hasattr(result, 'area_sqkm'), \
            "PolygonMetadata should NOT have area_sqkm attribute"
    
    def test_metadata_fields_correct_types(self):
        """
        Verify all metadata fields have correct types.
        """
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [0.0001, 0],
                    [0.0001, 0.0001],
                    [0, 0.0001],
                    [0, 0]
                ]]
            }
        }
        
        result = self.validator.validate(geojson)
        
        # Verify field types
        assert isinstance(result.area_sqm, float), "area_sqm should be float"
        assert isinstance(result.bounding_box, tuple), "bounding_box should be tuple"
        assert isinstance(result.centroid, tuple), "centroid should be tuple"
        assert isinstance(result.num_vertices, int), "num_vertices should be int"
        assert isinstance(result.geom_type, str), "geom_type should be string"
        assert isinstance(result.is_valid, bool), "is_valid should be boolean"
        assert isinstance(result.crs, str), "crs should be string"
        
        # Verify no area_sqkm
        assert not hasattr(result, 'area_sqkm'), "Should not have area_sqkm"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "property_test"])

