"""
Data Validator Module

Validates collected raw datasets before standardization.
Ensures datasets meet structural requirements and records validation status.
"""

from typing import List, Dict, Any, Optional
import logging

from backend.models import RawDataset, ProcessingStatus, DataCategory

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DatasetValidationResult:
    """Result of dataset validation."""
    
    def __init__(self):
        self.status: ProcessingStatus = ProcessingStatus.SUCCESS
        self.is_empty: bool = False
        self.has_errors: bool = False
        self.error_messages: List[str] = []
        self.warning_messages: List[str] = []
        self.feature_count: int = 0
        self.missing_fields: List[str] = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "status": self.status.value,
            "is_empty": self.is_empty,
            "has_errors": self.has_errors,
            "error_messages": self.error_messages,
            "warning_messages": self.warning_messages,
            "feature_count": self.feature_count,
            "missing_fields": self.missing_fields
        }


class DataValidator:
    """
    Validates collected raw datasets.
    
    Responsibilities:
    - Validate dataset structure matches RawDataset model
    - Check for empty datasets
    - Detect missing required fields
    - Record validation status (success, partial, failed)
    - Never reject data that could be standardized (graceful degradation)
    """
    
    # Required fields in dataset
    REQUIRED_DATASET_FIELDS = [
        "source_provider",
        "category",
        "geometry_type",
        "features",
        "metadata"
    ]
    
    # Required fields in each feature
    REQUIRED_FEATURE_FIELDS = [
        "geometry",
        "properties"
    ]
    
    # Required fields in geometry
    REQUIRED_GEOMETRY_FIELDS = [
        "type",
        "coordinates"
    ]
    
    @staticmethod
    def validate(dataset: RawDataset) -> DatasetValidationResult:
        """
        Validate a raw dataset.
        
        Args:
            dataset: Raw dataset to validate
            
        Returns:
            DatasetValidationResult with validation status
        """
        result = DatasetValidationResult()
        
        try:
            # Validate basic structure
            DataValidator._validate_dataset_structure(dataset, result)
            
            # Check for empty dataset
            if len(dataset.features) == 0:
                result.is_empty = True
                result.warning_messages.append("Dataset contains no features")
                result.status = ProcessingStatus.INSUFFICIENT_DATA
                logger.warning(
                    f"Dataset from {dataset.source_provider} ({dataset.category.value}) is empty"
                )
                return result
            
            # Validate feature count and feature structure
            result.feature_count = len(dataset.features)
            DataValidator._validate_features(dataset, result)
            
            # Check for critical errors
            if result.has_errors:
                result.status = ProcessingStatus.PARTIAL
                logger.warning(
                    f"Dataset validation completed with errors: "
                    f"{result.feature_count} features, "
                    f"{len(result.error_messages)} error(s)"
                )
            else:
                result.status = ProcessingStatus.SUCCESS
                logger.info(
                    f"Dataset validation successful: "
                    f"{result.feature_count} features from {dataset.source_provider}"
                )
            
            return result
            
        except DataValidationError as e:
            result.has_errors = True
            result.error_messages.append(str(e))
            result.status = ProcessingStatus.FAILED
            logger.error(f"Dataset validation failed: {str(e)}")
            return result
        except Exception as e:
            result.has_errors = True
            result.error_messages.append(f"Unexpected validation error: {str(e)}")
            result.status = ProcessingStatus.FAILED
            logger.error(f"Unexpected error during validation: {str(e)}", exc_info=True)
            return result
    
    @staticmethod
    def _validate_dataset_structure(dataset: RawDataset, result: DatasetValidationResult) -> None:
        """
        Validate dataset structure.
        
        Args:
            dataset: Dataset to validate
            result: Result object to populate
            
        Raises:
            DataValidationError: If structure is invalid
        """
        # Verify dataset is a RawDataset instance
        if not isinstance(dataset, RawDataset):
            raise DataValidationError(
                f"Expected RawDataset instance, got {type(dataset).__name__}"
            )
        
        # Validate source provider
        if not dataset.source_provider or not isinstance(dataset.source_provider, str):
            raise DataValidationError("Dataset must have a valid source_provider string")
        
        # Validate category
        if not isinstance(dataset.category, (DataCategory, str)):
            raise DataValidationError("Dataset must have a valid category")
        
        # Validate geometry type
        if not dataset.geometry_type or not isinstance(dataset.geometry_type, str):
            raise DataValidationError("Dataset must have a valid geometry_type string")
        
        valid_geometry_types = ["Point", "LineString", "Polygon"]
        if dataset.geometry_type not in valid_geometry_types:
            raise DataValidationError(
                f"Invalid geometry_type: {dataset.geometry_type}. "
                f"Must be one of {valid_geometry_types}"
            )
        
        # Validate features is a list
        if not isinstance(dataset.features, list):
            raise DataValidationError(
                f"Dataset.features must be a list, got {type(dataset.features).__name__}"
            )
        
        # Validate metadata is a dictionary
        if not isinstance(dataset.metadata, dict):
            raise DataValidationError(
                f"Dataset.metadata must be a dictionary, got {type(dataset.metadata).__name__}"
            )
    
    @staticmethod
    def _validate_features(dataset: RawDataset, result: DatasetValidationResult) -> None:
        """
        Validate features in the dataset.
        
        Records errors for malformed features but doesn't reject the entire dataset.
        
        Args:
            dataset: Dataset containing features
            result: Result object to populate with validation results
        """
        for idx, feature in enumerate(dataset.features):
            if not isinstance(feature, dict):
                result.error_messages.append(
                    f"Feature {idx}: Expected dictionary, got {type(feature).__name__}"
                )
                result.has_errors = True
                continue
            
            # Check for geometry
            if "geometry" not in feature:
                result.error_messages.append(
                    f"Feature {idx}: Missing required field 'geometry'"
                )
                result.has_errors = True
                result.missing_fields.append(f"feature[{idx}].geometry")
                continue
            
            # Validate geometry
            geometry = feature.get("geometry")
            if not isinstance(geometry, dict):
                result.error_messages.append(
                    f"Feature {idx}: Geometry must be a dictionary"
                )
                result.has_errors = True
                continue
            
            # Check geometry structure
            if "type" not in geometry:
                result.error_messages.append(
                    f"Feature {idx}: Geometry missing 'type' field"
                )
                result.has_errors = True
            
            if "coordinates" not in geometry:
                result.error_messages.append(
                    f"Feature {idx}: Geometry missing 'coordinates' field"
                )
                result.has_errors = True
            
            # Check for properties
            if "properties" not in feature:
                result.error_messages.append(
                    f"Feature {idx}: Missing required field 'properties'"
                )
                result.has_errors = True
                result.missing_fields.append(f"feature[{idx}].properties")
                continue
            
            # Validate properties is a dictionary
            properties = feature.get("properties")
            if not isinstance(properties, (dict, type(None))):
                result.error_messages.append(
                    f"Feature {idx}: Properties must be a dictionary or null, "
                    f"got {type(properties).__name__}"
                )
                result.has_errors = True
    
    @staticmethod
    def validate_collection(
        datasets: List[RawDataset]
    ) -> Dict[str, DatasetValidationResult]:
        """
        Validate a collection of datasets.
        
        Args:
            datasets: List of raw datasets
            
        Returns:
            Dictionary mapping source_provider to validation result
        """
        results = {}
        
        for dataset in datasets:
            if dataset and hasattr(dataset, 'source_provider'):
                provider_key = dataset.source_provider
                results[provider_key] = DataValidator.validate(dataset)
            else:
                logger.warning("Invalid dataset in collection, skipping")
        
        return results
    
    @staticmethod
    def check_critical_data_available(
        validation_results: Dict[str, DatasetValidationResult],
        critical_providers: Optional[List[str]] = None
    ) -> bool:
        """
        Check if critical data is available from validation results.
        
        Args:
            validation_results: Dictionary of validation results
            critical_providers: List of critical provider names (optional)
            
        Returns:
            True if at least one critical provider succeeded, False otherwise
        """
        if not critical_providers:
            # If no critical providers specified, check for any successful validation
            return any(
                result.status in [ProcessingStatus.SUCCESS, ProcessingStatus.PARTIAL]
                for result in validation_results.values()
            )
        
        # Check if at least one critical provider succeeded
        for provider in critical_providers:
            if provider in validation_results:
                result = validation_results[provider]
                if result.status in [ProcessingStatus.SUCCESS, ProcessingStatus.PARTIAL]:
                    return True
        
        return False
    
    @staticmethod
    def get_validation_summary(
        validation_results: Dict[str, DatasetValidationResult]
    ) -> Dict[str, Any]:
        """
        Get a summary of validation results.
        
        Args:
            validation_results: Dictionary of validation results
            
        Returns:
            Summary dictionary with overall statistics
        """
        total_datasets = len(validation_results)
        successful = sum(
            1 for r in validation_results.values()
            if r.status == ProcessingStatus.SUCCESS
        )
        partial = sum(
            1 for r in validation_results.values()
            if r.status == ProcessingStatus.PARTIAL
        )
        failed = sum(
            1 for r in validation_results.values()
            if r.status == ProcessingStatus.FAILED
        )
        insufficient = sum(
            1 for r in validation_results.values()
            if r.status == ProcessingStatus.INSUFFICIENT_DATA
        )
        total_features = sum(
            r.feature_count for r in validation_results.values()
        )
        
        overall_status = ProcessingStatus.SUCCESS
        if failed > 0:
            overall_status = ProcessingStatus.PARTIAL if successful > 0 else ProcessingStatus.FAILED
        elif partial > 0 or insufficient > 0:
            overall_status = ProcessingStatus.PARTIAL
        
        return {
            "overall_status": overall_status.value,
            "total_datasets": total_datasets,
            "successful_datasets": successful,
            "partial_datasets": partial,
            "failed_datasets": failed,
            "insufficient_data_datasets": insufficient,
            "total_features": total_features,
            "provider_results": {
                provider: result.to_dict()
                for provider, result in validation_results.items()
            }
        }
