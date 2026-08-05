"""Unit tests for PolygonValidator."""

import pytest
import math
from backend.validators.polygon_validator import PolygonValidator, ValidationError, PolygonMetadata


@pytest.fixture
def validator():
    """Create a validator instance for testing."""
    return PolygonValidator()


class TestPolygonValidatorBasics:
    """Test basic polygon validation functionality."""
    
    def test_valid_simple_polygon(self, validator):
        """Test validation of a simple valid polygon."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-122.4, 37.8],
                    [-122.4, 37.7],
                    [-122.3, 37.7],
                    [-122.3, 37.8],
                    [-122.4, 37.8]
                ]]
            }
        }
        
        result = validator.validate(geojson)
        
        assert isinstance(result, PolygonMetadata)
        assert result.is_valid
        assert result.geom_type == "Polygon"
        assert result.num_vertices == 4
        assert result.crs == "EPSG:4326"
        assert result.area_sqkm > 0
    
    def test_valid_multipolygon(self, validator):
        """Test validation of a valid MultiPolygon."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [[
                        [0, 0],
                        [0.01, 0],
                        [0.01, 0.01],
                        [0, 0.01],
                        [0, 0]
                    ]],
                    [[
                        [0.1, 0.1],
                        [0.11, 0.1],
                        [0.11, 0.11],
                        [0.1, 0.11],
                        [0.1, 0.1]
                    ]]
                ]
            }
        }
        
        result = validator.validate(geojson)
        
        assert result.geom_type == "MultiPolygon"
        assert result.is_valid


class TestGeoJSONStructure:
    """Test GeoJSON structure validation."""
    
    def test_missing_type_field(self, validator):
        """Test that missing type field raises error."""
        geojson = {
            "geometry": {"type": "Polygon", "coordinates": []}
        }
        
        with pytest.raises(ValidationError, match="Missing 'type'"):
            validator.validate(geojson)
    
    def test_missing_geometry_field(self, validator):
        """Test that missing geometry field raises error."""
        geojson = {
            "type": "Feature"
        }
        
        with pytest.raises(ValidationError, match="missing 'geometry'"):
            validator.validate(geojson)
    
    def test_missing_coordinates_field(self, validator):
        """Test that missing coordinates raises error."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon"
            }
        }
        
        with pytest.raises(ValidationError, match="Missing 'coordinates'"):
            validator.validate(geojson)
    
    def test_invalid_input_type(self, validator):
        """Test that non-dict input raises error."""
        with pytest.raises(ValidationError, match="must be a JSON object"):
            validator.validate("not a dict")


class TestGeometryTypes:
    """Test geometry type validation."""
    
    def test_invalid_geometry_type_point(self, validator):
        """Test that Point geometry is rejected."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [0, 0]
            }
        }
        
        with pytest.raises(ValidationError, match="Invalid geometry type"):
            validator.validate(geojson)
    
    def test_invalid_geometry_type_linestring(self, validator):
        """Test that LineString geometry is rejected."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [[0, 0], [1, 1]]
            }
        }
        
        with pytest.raises(ValidationError, match="Invalid geometry type"):
            validator.validate(geojson)


class TestCoordinateValidation:
    """Test coordinate validation."""
    
    def test_valid_coordinate_bounds(self, validator):
        """Test that valid coordinate bounds are accepted."""
        # Test each boundary value with small polygons
        coords_tests = [
            [-180, -89],  # Min lon, near min lat
            [179, 89],    # Near max lon, near max lat
            [0, 0],       # Equator
            [-90, 45],    # Random valid
        ]
        
        for lon, lat in coords_tests:
            geojson = {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon, lat],
                        [lon + 0.01, lat],
                        [lon + 0.01, lat + 0.01],
                        [lon, lat + 0.01],
                        [lon, lat]
                    ]]
                }
            }
            
            # Should not raise
            result = validator.validate(geojson)
            assert result.is_valid
    
    def test_invalid_latitude_bounds(self, validator):
        """Test that out-of-bounds latitude is rejected."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 91],
                    [1, 91],
                    [1, 92],
                    [0, 92],
                    [0, 91]
                ]]
            }
        }
        
        with pytest.raises(ValidationError, match="Latitude"):
            validator.validate(geojson)
    
    def test_invalid_longitude_bounds(self, validator):
        """Test that out-of-bounds longitude is rejected."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [181, 0],
                    [182, 0],
                    [182, 1],
                    [181, 1],
                    [181, 0]
                ]]
            }
        }
        
        with pytest.raises(ValidationError, match="Longitude"):
            validator.validate(geojson)


class TestRingClosure:
    """Test linear ring closure validation."""
    
    def test_properly_closed_ring(self, validator):
        """Test that properly closed rings pass validation."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [0.01, 0],
                    [0.01, 0.01],
                    [0, 0.01],
                    [0, 0]  # Properly closed
                ]]
            }
        }
        
        # Should not raise
        result = validator.validate(geojson)
        assert result.is_valid
    
    def test_unclosed_ring(self, validator):
        """Test that unclosed rings are rejected."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [1, 0],
                    [1, 1],
                    [0, 1]
                    # Missing [0, 0] to close
                ]]
            }
        }
        
        with pytest.raises(ValidationError, match="not closed"):
            validator.validate(geojson)


class TestPolygonArea:
    """Test polygon area validation."""
    
    def test_minimum_area_boundary(self, validator):
        """Test polygon at minimum area boundary."""
        # Create a small polygon ~10 m² (approximately 0.000015 degrees²)
        # This is approximately a square ~3.16m x 3.16m at equator
        small_delta = 0.00003  # ~3.3 meters at equator
        
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [small_delta, 0],
                    [small_delta, small_delta],
                    [0, small_delta],
                    [0, 0]
                ]]
            }
        }
        
        # Should not raise - at or above minimum
        result = validator.validate(geojson)
        assert result.is_valid
        assert result.area_sqm >= validator.MIN_AREA_SQM * 0.99  # Allow small rounding error
    
    def test_too_small_area(self, validator):
        """Test that polygon below minimum area is rejected."""
        # Create very tiny polygon < 10 m²
        tiny_delta = 0.0001  # ~11 meters, but we need even smaller
        tiny_delta = 0.00001  # ~1.1 meters
        
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [tiny_delta, 0],
                    [tiny_delta, tiny_delta],
                    [0, tiny_delta],
                    [0, 0]
                ]]
            }
        }
        
        with pytest.raises(ValidationError, match="below minimum"):
            validator.validate(geojson)
    
    def test_maximum_area_boundary(self, validator):
        """Test polygon at maximum area boundary."""
        # Create polygon just under 100 km²
        # At equator: 1 degree ≈ 111 km
        # So for ~99 km²: sqrt(99) ≈ 9.95 km ≈ 0.0895 degrees
        size_delta = 0.089
        
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [size_delta, 0],
                    [size_delta, size_delta],
                    [0, size_delta],
                    [0, 0]
                ]]
            }
        }
        
        # Should not raise - at or below maximum
        result = validator.validate(geojson)
        assert result.is_valid
        assert result.area_sqkm <= validator.MAX_AREA_SQKM
    
    def test_too_large_area(self, validator):
        """Test that polygon above maximum area is rejected."""
        # Create very large polygon > 100 km²
        large_delta = 1.5  # ~166 km, definitely > 100 km²
        
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [large_delta, 0],
                    [large_delta, large_delta],
                    [0, large_delta],
                    [0, 0]
                ]]
            }
        }
        
        with pytest.raises(ValidationError, match="exceeds maximum"):
            validator.validate(geojson)


class TestVertexValidation:
    """Test vertex count validation."""
    
    def test_minimum_vertices(self, validator):
        """Test polygon with minimum 3 vertices."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [0.01, 0],
                    [0.005, 0.01],
                    [0, 0]  # Closed ring, so 3 unique vertices
                ]]
            }
        }
        
        result = validator.validate(geojson)
        assert result.is_valid
        assert result.num_vertices == 3
    
    def test_too_few_vertices(self, validator):
        """Test that polygon with < 3 vertices is rejected."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [1, 1],
                    [0, 0]  # Only 2 unique vertices (line, not polygon)
                ]]
            }
        }
        
        with pytest.raises(ValidationError):
            validator.validate(geojson)
    
    def test_high_vertex_count_at_limit(self, validator):
        """Test polygon with high vertex count at limit."""
        # Create polygon with many vertices (but not over limit)
        # Use small radius to keep area small
        num_vertices = 100
        vertices = []
        radius = 0.001  # ~100 meters at equator
        for i in range(num_vertices):
            angle = 2 * math.pi * i / num_vertices
            x = 0 + radius * math.cos(angle)
            y = 0 + radius * math.sin(angle)
            vertices.append([x, y])
        vertices.append(vertices[0])  # Close the ring
        
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [vertices]
            }
        }
        
        result = validator.validate(geojson)
        assert result.is_valid
        assert result.num_vertices == num_vertices
    
    def test_too_many_vertices(self, validator):
        """Test that polygon exceeding max vertices is rejected."""
        # Create polygon with too many vertices
        num_vertices = validator.MAX_VERTICES + 1
        vertices = []
        radius = 0.001  # Keep polygon small
        for i in range(num_vertices):
            angle = 2 * math.pi * i / num_vertices
            x = 0 + radius * math.cos(angle)
            y = 0 + radius * math.sin(angle)
            vertices.append([x, y])
        vertices.append(vertices[0])
        
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [vertices]
            }
        }
        
        with pytest.raises(ValidationError, match="exceeds maximum"):
            validator.validate(geojson)


class TestPolygonMetadata:
    """Test polygon metadata extraction."""
    
    def test_metadata_extraction(self, validator):
        """Test that metadata is correctly extracted."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [0, 0],
                    [0.01, 0],
                    [0.01, 0.01],
                    [0, 0.01],
                    [0, 0]
                ]]
            }
        }
        
        result = validator.validate(geojson)
        
        # Verify all metadata fields are present
        assert result.area_sqkm > 0
        assert result.area_sqm > 0
        assert len(result.bounding_box) == 4  # (minx, miny, maxx, maxy)
        assert len(result.centroid) == 2  # (lon, lat)
        assert result.num_vertices == 4
        assert result.geom_type == "Polygon"
        assert result.is_valid
        assert result.crs == "EPSG:4326"
    
    def test_bounding_box_correctness(self, validator):
        """Test that bounding box is calculated correctly."""
        geojson = {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [10, 20],
                    [10.01, 20],
                    [10.01, 20.01],
                    [10, 20.01],
                    [10, 20]
                ]]
            }
        }
        
        result = validator.validate(geojson)
        minx, miny, maxx, maxy = result.bounding_box
        
        # Allow small floating point differences
        assert abs(minx - 10) < 0.0001
        assert abs(miny - 20) < 0.0001
        assert abs(maxx - 10.01) < 0.0001
        assert abs(maxy - 20.01) < 0.0001


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
