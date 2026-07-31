"""
Unit tests for DataValidator module.

Tests data validation for collected datasets, including:
- Empty datasets
- Datasets with errors
- Missing critical fields
- Error message readability
"""

import pytest
from datetime import datetime

from backend.models import RawDataset, DataCategory, ProcessingStatus
from backend.validators import DataValidator, DataValidationError, DatasetValidationResult


class TestDataValidatorBasic:
    """Test basic data validator functionality."""
    
    def test_validate_valid_dataset_success(self):
        """Test that valid datasets pass validation."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [0, 0]
                    },
                    "properties": {
                        "name": "Building 1",
                        "height": 10
                    }
                }
            ],
            metadata={"timestamp": datetime.utcnow().isoformat()}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.status == ProcessingStatus.SUCCESS
        assert not result.has_errors
        assert result.feature_count == 1
        assert not result.is_empty
        assert len(result.error_messages) == 0
    
    def test_validate_multiple_features(self):
        """Test validation with multiple features."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.ROADS,
            geometry_type="LineString",
            features=[
                {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[0, 0], [1, 1]]
                    },
                    "properties": {"name": "Road 1"}
                },
                {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[2, 2], [3, 3]]
                    },
                    "properties": {"name": "Road 2"}
                },
                {
                    "geometry": {
                        "type": "LineString",
                        "coordinates": [[4, 4], [5, 5]]
                    },
                    "properties": {"name": "Road 3"}
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.status == ProcessingStatus.SUCCESS
        assert result.feature_count == 3
        assert not result.has_errors


class TestEmptyDatasets:
    """Test handling of empty datasets."""
    
    def test_validate_empty_features_list(self):
        """Test that empty feature list is detected."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.status == ProcessingStatus.INSUFFICIENT_DATA
        assert result.is_empty
        assert result.feature_count == 0
        assert len(result.warning_messages) > 0
    
    def test_validate_empty_dataset_different_categories(self):
        """Test empty datasets across different categories."""
        for category in [
            DataCategory.BUILDINGS,
            DataCategory.LAND_COVER,
            DataCategory.ROADS,
            DataCategory.WATER,
            DataCategory.ELEVATION,
            DataCategory.ADMIN
        ]:
            dataset = RawDataset(
                source_provider=f"provider_{category.value}",
                category=category,
                geometry_type="Point",
                features=[],
                metadata={}
            )
            
            result = DataValidator.validate(dataset)
            
            assert result.is_empty
            assert result.status == ProcessingStatus.INSUFFICIENT_DATA


class TestDatasetsWithErrors:
    """Test handling of datasets with errors."""
    
    def test_validate_feature_missing_geometry(self):
        """Test that features missing geometry are recorded as errors."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "properties": {"name": "Building 1"}
                    # Missing geometry
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.has_errors
        assert result.status == ProcessingStatus.PARTIAL
        assert len(result.error_messages) > 0
        assert "geometry" in result.error_messages[0]
    
    def test_validate_feature_missing_properties(self):
        """Test that features missing properties are recorded as errors."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "geometry": {
                        "type": "Point",
                        "coordinates": [0, 0]
                    }
                    # Missing properties
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.has_errors
        assert result.status == ProcessingStatus.PARTIAL
        assert len(result.error_messages) > 0
        assert "properties" in result.error_messages[0]
    
    def test_validate_feature_invalid_geometry_type(self):
        """Test that features with invalid geometry are recorded as errors."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "geometry": "not a dict",  # Invalid: should be dictionary
                    "properties": {"name": "Building 1"}
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.has_errors
        assert len(result.error_messages) > 0
    
    def test_validate_feature_with_invalid_properties_type(self):
        """Test that features with invalid properties type are recorded as errors."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "properties": "not a dict"  # Invalid: should be dict
                },
                {
                    "geometry": {"type": "Point", "coordinates": [1, 1]},
                    "properties": {"name": "Building 2"}
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.has_errors
        assert result.feature_count == 2  # Both features counted
        assert len(result.error_messages) > 0
    
    def test_validate_mixed_valid_invalid_features(self):
        """Test validation with mix of valid and invalid features."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "properties": {"name": "Building 1"}
                },
                {
                    "properties": {"name": "Building 2"}
                    # Missing geometry
                },
                {
                    "geometry": {"type": "Point", "coordinates": [2, 2]},
                    "properties": {"name": "Building 3"}
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.has_errors
        assert result.status == ProcessingStatus.PARTIAL
        assert result.feature_count == 3
        assert len(result.error_messages) > 0


class TestMissingFields:
    """Test handling of missing required fields."""
    
    def test_validate_missing_geometry_type_field(self):
        """Test that missing geometry type is detected."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "geometry": {
                        # Missing type
                        "coordinates": [0, 0]
                    },
                    "properties": {"name": "Building 1"}
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.has_errors
        assert len(result.error_messages) > 0
    
    def test_validate_missing_coordinates_field(self):
        """Test that missing coordinates are detected."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "geometry": {
                        "type": "Point"
                        # Missing coordinates
                    },
                    "properties": {"name": "Building 1"}
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.has_errors
        assert len(result.error_messages) > 0
    
    def test_validate_tracking_missing_fields(self):
        """Test that missing fields are tracked."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "properties": {"name": "Building 1"}
                    # Missing geometry
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert len(result.missing_fields) > 0
        assert "feature[0].geometry" in result.missing_fields


class TestErrorMessageReadability:
    """Test that error messages are readable and descriptive."""
    
    def test_error_messages_are_strings(self):
        """Test that error messages are readable strings."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "geometry": "invalid",
                    "properties": {"name": "Building 1"}
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.has_errors
        for error_msg in result.error_messages:
            assert isinstance(error_msg, str)
            assert len(error_msg) > 0
            assert error_msg[0].isupper()  # Starts with capital letter
    
    def test_error_messages_include_context(self):
        """Test that error messages include context (e.g., feature index)."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[
                {
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                    "properties": {"name": "Building 1"}
                },
                {
                    "geometry": "invalid",
                    "properties": {"name": "Building 2"}
                }
            ],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert any("Feature" in msg and "1" in msg for msg in result.error_messages)
    
    def test_warning_messages_readable(self):
        """Test that warning messages are readable."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        for warning_msg in result.warning_messages:
            assert isinstance(warning_msg, str)
            assert len(warning_msg) > 0


class TestDatasetStructureValidation:
    """Test validation of dataset structure."""
    
    def test_invalid_dataset_type(self):
        """Test that invalid dataset type is rejected."""
        # Pass a dict instead of RawDataset
        result = DataValidator.validate({"invalid": "data"})
        
        assert result.status == ProcessingStatus.FAILED
        assert result.has_errors
    
    def test_validate_invalid_source_provider(self):
        """Test validation of source_provider field."""
        dataset = RawDataset(
            source_provider="",  # Empty provider
            category=DataCategory.BUILDINGS,
            geometry_type="Point",
            features=[],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.status == ProcessingStatus.FAILED
        assert result.has_errors
    
    def test_validate_invalid_geometry_type(self):
        """Test validation of geometry_type field."""
        dataset = RawDataset(
            source_provider="test_provider",
            category=DataCategory.BUILDINGS,
            geometry_type="InvalidType",
            features=[],
            metadata={}
        )
        
        result = DataValidator.validate(dataset)
        
        assert result.status == ProcessingStatus.FAILED
        assert result.has_errors


class TestValidationCollection:
    """Test validation of multiple datasets."""
    
    def test_validate_collection_of_datasets(self):
        """Test validating a collection of datasets."""
        datasets = [
            RawDataset(
                source_provider="provider1",
                category=DataCategory.BUILDINGS,
                geometry_type="Point",
                features=[{"geometry": {"type": "Point", "coordinates": [0, 0]}, "properties": {}}],
                metadata={}
            ),
            RawDataset(
                source_provider="provider2",
                category=DataCategory.ROADS,
                geometry_type="LineString",
                features=[],
                metadata={}
            ),
            RawDataset(
                source_provider="provider3",
                category=DataCategory.WATER,
                geometry_type="Polygon",
                features=[{"geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 1], [1, 0], [0, 0]]]}, "properties": {}}],
                metadata={}
            )
        ]
        
        results = DataValidator.validate_collection(datasets)
        
        assert len(results) == 3
        assert "provider1" in results
        assert "provider2" in results
        assert "provider3" in results
        assert results["provider1"].status == ProcessingStatus.SUCCESS
        assert results["provider2"].status == ProcessingStatus.INSUFFICIENT_DATA
        assert results["provider3"].status == ProcessingStatus.SUCCESS


class TestCriticalDataCheck:
    """Test critical data availability checking."""
    
    def test_check_critical_data_available_success(self):
        """Test that critical data available check passes."""
        validation_results = {
            "provider1": DatasetValidationResult(),
            "provider2": DatasetValidationResult()
        }
        validation_results["provider1"].status = ProcessingStatus.SUCCESS
        validation_results["provider2"].status = ProcessingStatus.FAILED
        
        # Should return True because provider1 succeeded
        assert DataValidator.check_critical_data_available(validation_results)
    
    def test_check_critical_data_all_failed(self):
        """Test that critical data check fails when all providers fail."""
        validation_results = {
            "provider1": DatasetValidationResult(),
            "provider2": DatasetValidationResult()
        }
        validation_results["provider1"].status = ProcessingStatus.FAILED
        validation_results["provider2"].status = ProcessingStatus.FAILED
        
        assert not DataValidator.check_critical_data_available(validation_results)
    
    def test_check_specific_critical_providers(self):
        """Test checking specific critical providers."""
        validation_results = {
            "provider1": DatasetValidationResult(),
            "provider2": DatasetValidationResult(),
            "provider3": DatasetValidationResult()
        }
        validation_results["provider1"].status = ProcessingStatus.FAILED
        validation_results["provider2"].status = ProcessingStatus.SUCCESS
        validation_results["provider3"].status = ProcessingStatus.FAILED
        
        # Check with provider2 as critical
        assert DataValidator.check_critical_data_available(
            validation_results,
            critical_providers=["provider2"]
        )
        
        # Check with provider1 as critical (should fail)
        assert not DataValidator.check_critical_data_available(
            validation_results,
            critical_providers=["provider1"]
        )


class TestValidationSummary:
    """Test validation summary generation."""
    
    def test_get_validation_summary(self):
        """Test generating validation summary."""
        validation_results = {
            "provider1": DatasetValidationResult(),
            "provider2": DatasetValidationResult(),
            "provider3": DatasetValidationResult()
        }
        validation_results["provider1"].status = ProcessingStatus.SUCCESS
        validation_results["provider1"].feature_count = 100
        
        validation_results["provider2"].status = ProcessingStatus.PARTIAL
        validation_results["provider2"].feature_count = 50
        
        validation_results["provider3"].status = ProcessingStatus.FAILED
        validation_results["provider3"].feature_count = 0
        
        summary = DataValidator.get_validation_summary(validation_results)
        
        assert summary["total_datasets"] == 3
        assert summary["successful_datasets"] == 1
        assert summary["partial_datasets"] == 1
        assert summary["failed_datasets"] == 1
        assert summary["total_features"] == 150
        assert summary["overall_status"] == ProcessingStatus.PARTIAL.value
    
    def test_summary_with_insufficient_data(self):
        """Test summary with insufficient_data status."""
        validation_results = {
            "provider1": DatasetValidationResult(),
            "provider2": DatasetValidationResult()
        }
        validation_results["provider1"].status = ProcessingStatus.SUCCESS
        validation_results["provider2"].status = ProcessingStatus.INSUFFICIENT_DATA
        
        summary = DataValidator.get_validation_summary(validation_results)
        
        assert summary["insufficient_data_datasets"] == 1
        assert summary["overall_status"] == ProcessingStatus.PARTIAL.value


class TestValidationResultConversion:
    """Test DatasetValidationResult conversion."""
    
    def test_result_to_dict(self):
        """Test converting validation result to dictionary."""
        result = DatasetValidationResult()
        result.status = ProcessingStatus.PARTIAL
        result.feature_count = 42
        result.error_messages.append("Test error")
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert result_dict["status"] == ProcessingStatus.PARTIAL.value
        assert result_dict["feature_count"] == 42
        assert "Test error" in result_dict["error_messages"]
