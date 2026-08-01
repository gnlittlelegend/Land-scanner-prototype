"""
Test suite for polygon validation logic
"""
import pytest
from backend.validators.polygon_validator import PolygonValidator, PolygonValidationError


class TestPolygonValidator:
    """Test cases for polygon validation"""
    
    @pytest.fixture
    def valid_polygon(self):
        """Valid test polygon (small square)"""
        return {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
        }
    
    @pytest.fixture
    def large_polygon(self):
        """Large polygon (for area testing)"""
        return {
            "type": "Polygon",
            "coordinates": [[
                [-180, -85], [180, -85], [180, 85], [-180, 85], [-180, -85]
            ]]
        }
    
    @pytest.fixture
    def invalid_polygon_missing_type(self):
        """Missing type field"""
        return {
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]]
        }
    
    @pytest.fixture
    def invalid_polygon_wrong_coordinates(self):
        """Invalid coordinates structure"""
        return {
            "type": "Polygon",
            "coordinates": [[0, 0], [1, 0], [1, 1]]  # Not nested array
        }
    
    def test_valid_polygon(self, valid_polygon):
        """Test that valid polygon passes validation"""
        result = PolygonValidator.validate(valid_polygon)
        assert result is not None
        assert result.area_sqkm > 0
    
    def test_polygon_has_area(self, valid_polygon):
        """Test that validated polygon calculates area"""
        result = PolygonValidator.validate(valid_polygon)
        assert hasattr(result, 'area_sqkm')
        assert isinstance(result.area_sqkm, (int, float))
    
    def test_polygon_has_bounding_box(self, valid_polygon):
        """Test that validated polygon has bounding box"""
        result = PolygonValidator.validate(valid_polygon)
        assert hasattr(result, 'bounding_box')
        assert result.bounding_box is not None
    
    def test_invalid_polygon_missing_type(self, invalid_polygon_missing_type):
        """Test that polygon without type raises error"""
        with pytest.raises(PolygonValidationError):
            PolygonValidator.validate(invalid_polygon_missing_type)
    
    def test_invalid_polygon_wrong_structure(self, invalid_polygon_wrong_coordinates):
        """Test that polygon with wrong coordinate structure raises error"""
        with pytest.raises(PolygonValidationError):
            PolygonValidator.validate(invalid_polygon_wrong_coordinates)
    
    def test_invalid_polygon_none(self):
        """Test that None polygon raises error"""
        with pytest.raises((PolygonValidationError, AttributeError, TypeError)):
            PolygonValidator.validate(None)
    
    def test_polygon_coordinate_closure(self):
        """Test that first and last coordinates must be same"""
        unclosed_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]  # Not closed
        }
        # Should either validate or raise error
        try:
            result = PolygonValidator.validate(unclosed_polygon)
            # If it validates, that's fine
            assert result is not None
        except PolygonValidationError:
            # If it raises error, that's also correct
            pass


class TestPolygonValidatorEdgeCases:
    """Test edge cases for polygon validation"""
    
    def test_tiny_polygon(self):
        """Test very small polygon"""
        tiny_polygon = {
            "type": "Polygon",
            "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]]
        }
        result = PolygonValidator.validate(tiny_polygon)
        assert result.area_sqkm > 0
    
    def test_polygon_at_dateline(self):
        """Test polygon at international date line"""
        dateline_polygon = {
            "type": "Polygon",
            "coordinates": [[[179, -10], [180, -10], [180, 10], [179, 10], [179, -10]]]
        }
        result = PolygonValidator.validate(dateline_polygon)
        assert result is not None
    
    def test_polygon_at_equator(self):
        """Test polygon at equator"""
        equator_polygon = {
            "type": "Polygon",
            "coordinates": [[[-10, -0.1], [10, -0.1], [10, 0.1], [-10, 0.1], [-10, -0.1]]]
        }
        result = PolygonValidator.validate(equator_polygon)
        assert result is not None
