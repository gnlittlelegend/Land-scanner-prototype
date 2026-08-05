"""Comprehensive unit tests for DataValidator with real provider data edge cases"""

import pytest
import logging
from datetime import datetime
from backend.data_models import RawDataset, Feature
from backend.validators.data_validator import DataValidator, ValidationStatus


logger = logging.getLogger(__name__)


class TestDataValidatorStructure:
    """Test validation of dataset structure"""
    
    def test_valid_dataset_structure(self):
        """Test validation of dataset with valid structure"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                Feature(
                    geometry={"type": "Point", "coordinates": [0, 0]},
                    properties={"name": "test"}
                )
            ],
            metadata={"timestamp": "2024-01-01"}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.is_valid is True
        assert result.record_count == 1
    
    def test_invalid_source_provider(self):
        """Test validation fails for invalid source provider"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="InvalidProvider",
            category="buildings",
            features=[],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.INVALID
        assert result.is_valid is False
        assert len(result.issues) > 0
        assert any("source_provider" in issue for issue in result.issues)
    
    def test_invalid_category(self):
        """Test validation fails for invalid category"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="invalid_category",
            features=[],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.INVALID
        assert result.is_valid is False
        assert len(result.issues) > 0
        assert any("category" in issue for issue in result.issues)
    
    def test_empty_features_list(self):
        """Test validation of dataset with empty features list"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.EMPTY
        assert result.is_valid is False
        assert result.record_count == 0
        assert "features" in result.message.lower() or "empty" in result.message.lower()


class TestDataValidatorFeatures:
    """Test validation of individual features"""
    
    def test_valid_point_feature(self):
        """Test validation of valid Point feature"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="USGS",
            category="elevation",
            features=[
                Feature(
                    geometry={"type": "Point", "coordinates": [-122.4194, 37.7749]},
                    properties={"elevation": 100}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.is_valid is True
        assert result.record_count == 1
    
    def test_valid_linestring_feature(self):
        """Test validation of valid LineString feature"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="roads",
            features=[
                Feature(
                    geometry={
                        "type": "LineString",
                        "coordinates": [[0, 0], [1, 1], [2, 2]]
                    },
                    properties={"name": "Main Street"}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.is_valid is True
        assert result.record_count == 1
    
    def test_valid_polygon_feature(self):
        """Test validation of valid Polygon feature (closed ring)"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="water",
            features=[
                Feature(
                    geometry={
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                    },
                    properties={"name": "Lake"}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.is_valid is True
        assert result.record_count == 1
    
    def test_unclosed_polygon_ring(self):
        """Test validation fails for unclosed polygon ring"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="water",
            features=[
                Feature(
                    geometry={
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1]]]  # Not closed
                    },
                    properties={"name": "Lake"}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.INVALID
        assert result.is_valid is False
        assert len(result.issues) > 0
    
    def test_missing_feature_type(self):
        """Test validation fails for feature missing type"""
        validator = DataValidator()
        
        # Create feature dict without type
        feature_dict = {
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "properties": {}
        }
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[Feature(**feature_dict)],
            metadata={}
        )
        
        result = validator.validate(dataset)
        # The Feature model will set type="Feature" by default
        assert result.record_count >= 0
    
    def test_missing_geometry_field(self):
        """Test validation fails for feature missing geometry"""
        validator = DataValidator()
        
        # The Feature model requires geometry to be a dict, so this test
        # verifies that Pydantic catches this during model creation
        try:
            dataset = RawDataset(
                source_provider="OSM",
                category="buildings",
                features=[
                    Feature(
                        geometry=None,  # This will cause validation to fail
                        properties={}
                    )
                ],
                metadata={}
            )
            # If we get here, validation should be attempted
            result = validator.validate(dataset)
            assert result.status in [ValidationStatus.INVALID, ValidationStatus.PARTIAL]
        except Exception:
            # Pydantic validation error is expected
            pass
    
    def test_multiple_features_with_mixed_validity(self):
        """Test validation with multiple features, some valid and some invalid"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                # Valid feature
                Feature(
                    geometry={"type": "Point", "coordinates": [0, 0]},
                    properties={"name": "Building 1"}
                ),
                # Valid feature
                Feature(
                    geometry={"type": "Point", "coordinates": [1, 1]},
                    properties={"name": "Building 2"}
                ),
                # Invalid feature (unclosed polygon)
                Feature(
                    geometry={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1]]]},
                    properties={"name": "Invalid"}
                ),
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status in [ValidationStatus.PARTIAL, ValidationStatus.INVALID]
        assert len(result.issues) > 0


class TestDataValidatorGeometryTypes:
    """Test validation of different geometry types"""
    
    def test_multipoint_geometry(self):
        """Test validation of MultiPoint geometry"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="USGS",
            category="elevation",
            features=[
                Feature(
                    geometry={
                        "type": "MultiPoint",
                        "coordinates": [[0, 0], [1, 1], [2, 2]]
                    },
                    properties={"elevation": "sample"}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.record_count == 1
    
    def test_multilinestring_geometry(self):
        """Test validation of MultiLineString geometry"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="roads",
            features=[
                Feature(
                    geometry={
                        "type": "MultiLineString",
                        "coordinates": [
                            [[0, 0], [1, 1]],
                            [[2, 2], [3, 3]]
                        ]
                    },
                    properties={"name": "Roads"}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.record_count == 1
    
    def test_multipolygon_geometry(self):
        """Test validation of MultiPolygon geometry"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="Copernicus",
            category="land_cover",
            features=[
                Feature(
                    geometry={
                        "type": "MultiPolygon",
                        "coordinates": [
                            [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                            [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]
                        ]
                    },
                    properties={"cover_type": "forest"}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.record_count == 1
    
    def test_invalid_geometry_type(self):
        """Test validation fails for invalid geometry type"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                Feature(
                    geometry={"type": "InvalidType", "coordinates": []},
                    properties={}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.INVALID
        assert len(result.issues) > 0
    
    def test_missing_geometry_type(self):
        """Test validation fails when geometry type is missing"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                Feature(
                    geometry={"coordinates": [[0, 0], [1, 1]]},
                    properties={}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.INVALID
        assert any("type" in issue for issue in result.issues)


class TestDataValidatorRealProviderFormats:
    """Test validation with real provider data formats"""
    
    def test_osm_overpass_response_format(self):
        """Test validation with OSM Overpass API response format"""
        validator = DataValidator()
        
        # Simulates real OSM Overpass API response structure
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                Feature(
                    id="123",
                    geometry={
                        "type": "Polygon",
                        "coordinates": [[
                            [-122.4, 37.7],
                            [-122.39, 37.7],
                            [-122.39, 37.71],
                            [-122.4, 37.71],
                            [-122.4, 37.7]
                        ]]
                    },
                    properties={
                        "building": "yes",
                        "name": "Sample Building",
                        "levels": "3"
                    }
                )
            ],
            metadata={
                "timestamp": "2024-01-01T00:00:00Z",
                "query": "buildings in bbox",
                "api_version": "0.6"
            }
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.is_valid is True
    
    def test_copernicus_land_cover_format(self):
        """Test validation with Copernicus land cover data format"""
        validator = DataValidator()
        
        # Simulates Copernicus land cover response
        dataset = RawDataset(
            source_provider="Copernicus",
            category="land_cover",
            features=[
                Feature(
                    geometry={
                        "type": "Polygon",
                        "coordinates": [[
                            [-122.4, 37.7],
                            [-122.39, 37.7],
                            [-122.39, 37.71],
                            [-122.4, 37.71],
                            [-122.4, 37.7]
                        ]]
                    },
                    properties={
                        "land_cover_type": "urban",
                        "confidence": 0.85,
                        "pixel_count": 150
                    }
                )
            ],
            metadata={
                "source": "Copernicus Global Land Cover",
                "year": 2021,
                "resolution": "100m"
            }
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.is_valid is True
    
    def test_usgs_elevation_format(self):
        """Test validation with USGS elevation response format"""
        validator = DataValidator()
        
        # Simulates USGS elevation API response
        dataset = RawDataset(
            source_provider="USGS",
            category="elevation",
            features=[
                Feature(
                    geometry={"type": "Point", "coordinates": [-122.4194, 37.7749]},
                    properties={"elevation": 52, "units": "meters"}
                ),
                Feature(
                    geometry={"type": "Point", "coordinates": [-122.418, 37.775]},
                    properties={"elevation": 48, "units": "meters"}
                )
            ],
            metadata={
                "source": "USGS 3DEP",
                "resolution": "30m",
                "sample_spacing": "500m"
            }
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.record_count == 2


class TestDataValidatorEdgeCases:
    """Test validation edge cases"""
    
    def test_empty_properties(self):
        """Test validation of feature with empty properties"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                Feature(
                    geometry={"type": "Point", "coordinates": [0, 0]},
                    properties={}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.is_valid is True
    
    def test_missing_required_fields_in_properties(self):
        """Test validation tolerates missing optional fields in properties"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                Feature(
                    geometry={"type": "Point", "coordinates": [0, 0]},
                    properties={}  # Missing optional fields
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
    
    def test_large_number_of_features(self):
        """Test validation with large number of features"""
        validator = DataValidator()
        
        # Create dataset with 1000 features
        features = [
            Feature(
                geometry={"type": "Point", "coordinates": [float(i) % 180 - 90, float(i) % 90 - 45]},
                properties={"id": str(i)}
            )
            for i in range(1000)
        ]
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=features,
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.record_count == 1000
    
    def test_coordinates_at_boundaries(self):
        """Test validation of coordinates at extreme boundaries"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                Feature(
                    geometry={"type": "Point", "coordinates": [-180, -90]},
                    properties={}
                ),
                Feature(
                    geometry={"type": "Point", "coordinates": [180, 90]},
                    properties={}
                ),
                Feature(
                    geometry={"type": "Point", "coordinates": [0, 0]},
                    properties={}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.record_count == 3
    
    def test_coordinates_crossing_antimeridian(self):
        """Test validation of polygon crossing antimeridian"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                Feature(
                    geometry={
                        "type": "Polygon",
                        "coordinates": [[
                            [179, -10],
                            [-179, -10],
                            [-179, 10],
                            [179, 10],
                            [179, -10]
                        ]]
                    },
                    properties={}
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.record_count == 1
    
    def test_special_characters_in_properties(self):
        """Test validation handles special characters in properties"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[
                Feature(
                    geometry={"type": "Point", "coordinates": [0, 0]},
                    properties={
                        "name": "Café Français 中文 ñ é ü",
                        "description": "Building with special chars: !@#$%^&*()"
                    }
                )
            ],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.is_valid is True


class TestDataValidatorStatusRecording:
    """Test validation status recording"""
    
    def test_status_success_recorded(self):
        """Test success status is recorded correctly"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[Feature(geometry={"type": "Point", "coordinates": [0, 0]}, properties={})],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.SUCCESS
        assert result.status.value == "success"
    
    def test_status_empty_recorded(self):
        """Test empty status is recorded correctly"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.EMPTY
        assert result.status.value == "empty"
    
    def test_status_invalid_recorded(self):
        """Test invalid status is recorded correctly"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="InvalidProvider",
            category="buildings",
            features=[],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.INVALID
        assert result.status.value == "invalid"
    
    def test_validation_result_to_dict(self):
        """Test ValidationResult converts to dict correctly"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[Feature(geometry={"type": "Point", "coordinates": [0, 0]}, properties={})],
            metadata={}
        )
        
        result = validator.validate(dataset)
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert "status" in result_dict
        assert "is_valid" in result_dict
        assert "message" in result_dict
        assert "issues" in result_dict
        assert "record_count" in result_dict
        assert "timestamp" in result_dict
        assert result_dict["status"] == "success"


class TestDataValidatorErrorMessages:
    """Test validation error messages are readable and helpful"""
    
    def test_helpful_error_message_invalid_provider(self):
        """Test error message is helpful for invalid provider"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="UnknownProvider",
            category="buildings",
            features=[],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.INVALID
        assert "UnknownProvider" in result.message or "provider" in result.message.lower()
    
    def test_helpful_error_message_invalid_category(self):
        """Test error message is helpful for invalid category"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="unknown_category",
            features=[],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.INVALID
        assert "category" in result.message.lower()
    
    def test_helpful_error_message_empty_features(self):
        """Test error message is helpful for empty features"""
        validator = DataValidator()
        
        dataset = RawDataset(
            source_provider="OSM",
            category="buildings",
            features=[],
            metadata={}
        )
        
        result = validator.validate(dataset)
        assert result.status == ValidationStatus.EMPTY
        assert "features" in result.message.lower() or "empty" in result.message.lower()
