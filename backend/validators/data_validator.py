"""Data validation module for collected datasets from providers"""

from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging
from backend.data_models import RawDataset, Feature


logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Validation status enumeration"""
    SUCCESS = "success"
    EMPTY = "empty"
    INVALID = "invalid"
    PARTIAL = "partial"


class ValidationResult:
    """Result of dataset validation"""
    
    def __init__(
        self,
        status: ValidationStatus,
        is_valid: bool,
        message: str = "",
        issues: Optional[List[str]] = None,
        record_count: int = 0,
    ):
        """
        Initialize validation result
        
        Args:
            status: ValidationStatus enum value
            is_valid: Whether dataset is valid
            message: Human-readable message
            issues: List of validation issues found
            record_count: Number of valid records
        """
        self.status = status
        self.is_valid = is_valid
        self.message = message
        self.issues = issues or []
        self.record_count = record_count
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "status": self.status.value,
            "is_valid": self.is_valid,
            "message": self.message,
            "issues": self.issues,
            "record_count": self.record_count,
            "timestamp": self.timestamp.isoformat(),
        }


class DataValidator:
    """Validates collected datasets from providers"""
    
    # Required fields in RawDataset
    REQUIRED_DATASET_FIELDS = {"source_provider", "category", "features", "metadata"}
    
    # Required fields in each Feature
    REQUIRED_FEATURE_FIELDS = {"type", "geometry", "properties"}
    
    # Valid geometry types
    VALID_GEOMETRY_TYPES = {"Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"}
    
    # Valid data categories
    VALID_CATEGORIES = {"buildings", "land_cover", "roads", "water", "elevation", "admin"}
    
    # Valid data source providers
    VALID_PROVIDERS = {"OSM", "Copernicus", "USGS", "GEBCO"}
    
    def __init__(self):
        """Initialize DataValidator"""
        self.logger = logger
    
    def validate(self, dataset: RawDataset) -> ValidationResult:
        """
        Validate a dataset from a provider
        
        Args:
            dataset: RawDataset to validate
            
        Returns:
            ValidationResult with status and details
        """
        issues = []
        
        # Validate dataset structure
        structure_issues = self._validate_structure(dataset)
        issues.extend(structure_issues)
        
        if issues:
            self.logger.warning(f"Dataset structure validation failed: {issues}")
            return ValidationResult(
                status=ValidationStatus.INVALID,
                is_valid=False,
                message=f"Dataset structure invalid: {'; '.join(issues)}",
                issues=issues,
                record_count=0,
            )
        
        # Check if dataset is empty
        if not dataset.features:
            self.logger.info(f"Dataset from {dataset.source_provider} is empty")
            return ValidationResult(
                status=ValidationStatus.EMPTY,
                is_valid=False,
                message="Dataset contains no features",
                issues=["No features in dataset"],
                record_count=0,
            )
        
        # Validate features
        feature_issues, valid_count = self._validate_features(dataset.features)
        
        # Determine overall status
        if feature_issues:
            if valid_count > 0:
                # Some features are valid, some invalid
                status = ValidationStatus.PARTIAL
                is_valid = False
                message = f"Dataset partially valid: {valid_count} valid records, {len(dataset.features) - valid_count} invalid"
                issues.extend(feature_issues)
            else:
                # No valid features
                status = ValidationStatus.INVALID
                is_valid = False
                message = "All features in dataset are invalid"
                issues.extend(feature_issues)
        else:
            # All features valid
            status = ValidationStatus.SUCCESS
            is_valid = True
            message = f"Dataset validation successful: {valid_count} records"
            valid_count = len(dataset.features)
        
        self.logger.info(f"Dataset validation complete: {message}")
        
        return ValidationResult(
            status=status,
            is_valid=is_valid,
            message=message,
            issues=issues,
            record_count=valid_count,
        )
    
    def _validate_structure(self, dataset: RawDataset) -> List[str]:
        """
        Validate dataset top-level structure
        
        Args:
            dataset: RawDataset to validate
            
        Returns:
            List of validation issues (empty if no issues)
        """
        issues = []
        
        # Check required fields
        for field in self.REQUIRED_DATASET_FIELDS:
            if not hasattr(dataset, field):
                issues.append(f"Missing required field: {field}")
        
        # Validate source_provider
        if dataset.source_provider not in self.VALID_PROVIDERS:
            issues.append(f"Invalid source_provider '{dataset.source_provider}'. Must be one of: {self.VALID_PROVIDERS}")
        
        # Validate category
        if dataset.category not in self.VALID_CATEGORIES:
            issues.append(f"Invalid category '{dataset.category}'. Must be one of: {self.VALID_CATEGORIES}")
        
        # Validate features is a list
        if not isinstance(dataset.features, list):
            issues.append(f"Features must be a list, got {type(dataset.features)}")
        
        # Validate metadata is a dict
        if not isinstance(dataset.metadata, dict):
            issues.append(f"Metadata must be a dict, got {type(dataset.metadata)}")
        
        return issues
    
    def _validate_features(self, features: List[Feature]) -> Tuple[List[str], int]:
        """
        Validate individual features in dataset
        
        Args:
            features: List of Feature objects to validate
            
        Returns:
            Tuple of (validation_issues, valid_feature_count)
        """
        issues = []
        valid_count = 0
        
        for idx, feature in enumerate(features):
            feature_issues = self._validate_feature(feature, idx)
            if not feature_issues:
                valid_count += 1
            else:
                issues.extend(feature_issues)
        
        return issues, valid_count
    
    def _validate_feature(self, feature: Feature, index: int) -> List[str]:
        """
        Validate a single feature
        
        Args:
            feature: Feature to validate
            index: Index of feature in list
            
        Returns:
            List of validation issues for this feature
        """
        issues = []
        
        # Check required fields
        for field in self.REQUIRED_FEATURE_FIELDS:
            if not hasattr(feature, field):
                issues.append(f"Feature {index}: Missing required field '{field}'")
        
        # Validate type field
        if hasattr(feature, 'type') and feature.type != "Feature":
            issues.append(f"Feature {index}: Type must be 'Feature', got '{feature.type}'")
        
        # Validate geometry
        if hasattr(feature, 'geometry'):
            geometry_issues = self._validate_geometry(feature.geometry, index)
            issues.extend(geometry_issues)
        
        # Validate properties
        if hasattr(feature, 'properties'):
            if not isinstance(feature.properties, dict):
                issues.append(f"Feature {index}: Properties must be a dict, got {type(feature.properties)}")
        
        return issues
    
    def _validate_geometry(self, geometry: Dict[str, Any], feature_index: int) -> List[str]:
        """
        Validate GeoJSON geometry
        
        Args:
            geometry: Geometry dict to validate
            feature_index: Index of feature (for error messages)
            
        Returns:
            List of validation issues
        """
        issues = []
        
        if not isinstance(geometry, dict):
            issues.append(f"Feature {feature_index}: Geometry must be a dict, got {type(geometry)}")
            return issues
        
        # Check for type field
        if "type" not in geometry:
            issues.append(f"Feature {feature_index}: Geometry missing 'type' field")
            return issues
        
        geom_type = geometry.get("type")
        
        # Validate geometry type
        if geom_type not in self.VALID_GEOMETRY_TYPES:
            issues.append(f"Feature {feature_index}: Invalid geometry type '{geom_type}'. Must be one of: {self.VALID_GEOMETRY_TYPES}")
            return issues
        
        # Check for coordinates field
        if "coordinates" not in geometry:
            issues.append(f"Feature {feature_index}: Geometry missing 'coordinates' field")
            return issues
        
        coordinates = geometry.get("coordinates")
        
        # Validate coordinates structure by type
        if geom_type == "Point":
            coord_issues = self._validate_point_coordinates(coordinates, feature_index)
        elif geom_type == "LineString":
            coord_issues = self._validate_linestring_coordinates(coordinates, feature_index)
        elif geom_type == "Polygon":
            coord_issues = self._validate_polygon_coordinates(coordinates, feature_index)
        elif geom_type == "MultiPoint":
            coord_issues = self._validate_multipoint_coordinates(coordinates, feature_index)
        elif geom_type == "MultiLineString":
            coord_issues = self._validate_multilinestring_coordinates(coordinates, feature_index)
        elif geom_type == "MultiPolygon":
            coord_issues = self._validate_multipolygon_coordinates(coordinates, feature_index)
        else:
            coord_issues = [f"Feature {feature_index}: Unsupported geometry type '{geom_type}'"]
        
        issues.extend(coord_issues)
        return issues
    
    def _validate_point_coordinates(self, coordinates: Any, feature_index: int) -> List[str]:
        """Validate Point coordinates"""
        issues = []
        if not isinstance(coordinates, list):
            issues.append(f"Feature {feature_index}: Point coordinates must be a list")
            return issues
        if len(coordinates) < 2:
            issues.append(f"Feature {feature_index}: Point must have at least 2 coordinates [lon, lat]")
            return issues
        if not isinstance(coordinates[0], (int, float)) or not isinstance(coordinates[1], (int, float)):
            issues.append(f"Feature {feature_index}: Point coordinates must be numbers")
            return issues
        return issues
    
    def _validate_linestring_coordinates(self, coordinates: Any, feature_index: int) -> List[str]:
        """Validate LineString coordinates"""
        issues = []
        if not isinstance(coordinates, list):
            issues.append(f"Feature {feature_index}: LineString coordinates must be a list")
            return issues
        if len(coordinates) < 2:
            issues.append(f"Feature {feature_index}: LineString must have at least 2 positions")
            return issues
        for idx, coord in enumerate(coordinates):
            if not isinstance(coord, list) or len(coord) < 2:
                issues.append(f"Feature {feature_index}: LineString position {idx} invalid")
                break
        return issues
    
    def _validate_polygon_coordinates(self, coordinates: Any, feature_index: int) -> List[str]:
        """Validate Polygon coordinates"""
        issues = []
        if not isinstance(coordinates, list):
            issues.append(f"Feature {feature_index}: Polygon coordinates must be a list")
            return issues
        if len(coordinates) == 0:
            issues.append(f"Feature {feature_index}: Polygon must have at least one ring")
            return issues
        
        # Check each ring
        for ring_idx, ring in enumerate(coordinates):
            if not isinstance(ring, list):
                issues.append(f"Feature {feature_index}: Polygon ring {ring_idx} must be a list")
                continue
            if len(ring) < 4:
                issues.append(f"Feature {feature_index}: Polygon ring {ring_idx} must have at least 4 positions")
                continue
            # Check if ring is closed (first and last coordinates should match)
            if ring[0] != ring[-1]:
                issues.append(f"Feature {feature_index}: Polygon ring {ring_idx} is not closed")
        
        return issues
    
    def _validate_multipoint_coordinates(self, coordinates: Any, feature_index: int) -> List[str]:
        """Validate MultiPoint coordinates"""
        issues = []
        if not isinstance(coordinates, list):
            issues.append(f"Feature {feature_index}: MultiPoint coordinates must be a list")
            return issues
        for idx, point in enumerate(coordinates):
            if not isinstance(point, list) or len(point) < 2:
                issues.append(f"Feature {feature_index}: MultiPoint position {idx} invalid")
                break
        return issues
    
    def _validate_multilinestring_coordinates(self, coordinates: Any, feature_index: int) -> List[str]:
        """Validate MultiLineString coordinates"""
        issues = []
        if not isinstance(coordinates, list):
            issues.append(f"Feature {feature_index}: MultiLineString coordinates must be a list")
            return issues
        for idx, linestring in enumerate(coordinates):
            if not isinstance(linestring, list) or len(linestring) < 2:
                issues.append(f"Feature {feature_index}: MultiLineString {idx} invalid")
                break
        return issues
    
    def _validate_multipolygon_coordinates(self, coordinates: Any, feature_index: int) -> List[str]:
        """Validate MultiPolygon coordinates"""
        issues = []
        if not isinstance(coordinates, list):
            issues.append(f"Feature {feature_index}: MultiPolygon coordinates must be a list")
            return issues
        for idx, polygon in enumerate(coordinates):
            if not isinstance(polygon, list) or len(polygon) == 0:
                issues.append(f"Feature {feature_index}: MultiPolygon {idx} invalid")
                break
        return issues
