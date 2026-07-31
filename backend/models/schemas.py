"""
Data models and schemas for the Land Scanner Prototype.
Defines the core data structures used throughout the system.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum


class ProcessingStatus(str, Enum):
    """Processing status values for modules and rules."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    INSUFFICIENT_DATA = "insufficient_data"
    PARTIAL = "partial"


class DataCategory(str, Enum):
    """Data categories for standardized datasets."""
    BUILDINGS = "buildings"
    LAND_COVER = "land_cover"
    ROADS = "roads"
    WATER = "water"
    ELEVATION = "elevation"
    ADMIN = "admin"


class Polygon(BaseModel):
    """Validated polygon with metadata."""
    geojson: Dict[str, Any] = Field(..., description="Valid GeoJSON structure")
    area_sqkm: float = Field(..., description="Calculated polygon area in square kilometers")
    bounding_box: tuple = Field(..., description="(minx, miny, maxx, maxy)")
    centroid: tuple = Field(..., description="(longitude, latitude)")
    crs: str = Field(default="EPSG:4326", description="Coordinate Reference System")
    is_valid: bool = Field(default=True, description="Validation status")


class RawDataset(BaseModel):
    """Raw dataset from a data provider."""
    source_provider: str = Field(..., description="Name of data provider")
    category: DataCategory = Field(..., description="Data category")
    geometry_type: str = Field(..., description="Point, LineString, or Polygon")
    features: List[Dict[str, Any]] = Field(default_factory=list, description="Raw features from provider")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider metadata")


class Feature(BaseModel):
    """Standardized feature in a dataset."""
    id: str = Field(..., description="Feature identifier")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry")
    properties: Dict[str, Any] = Field(..., description="Standardized properties")


class StandardizedDataset(BaseModel):
    """Standardized dataset with common format."""
    category: DataCategory = Field(..., description="Data category")
    source_provider: str = Field(..., description="Original provider name")
    features: List[Feature] = Field(default_factory=list, description="Standardized features")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dataset metadata (timestamp, CRS, count, etc.)"
    )


class RuleResult(BaseModel):
    """Result from a rule execution."""
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    status: ProcessingStatus = Field(..., description="Execution status")
    result: Dict[str, Any] = Field(default_factory=dict, description="Rule-specific results")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")


class ModuleStatus(BaseModel):
    """Status of a processing module."""
    module_name: str = Field(..., description="Name of the module")
    status: ProcessingStatus = Field(..., description="Execution status")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")


class ErrorInfo(BaseModel):
    """Error information in response."""
    module: str = Field(..., description="Module where error occurred")
    message: str = Field(..., description="Error message")
    severity: str = Field(default="error", description="warning or error")


class ProviderStatus(BaseModel):
    """Status of a data provider."""
    provider_name: str = Field(..., description="Provider name")
    status: str = Field(..., description="available, unavailable, or error")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    data_retrieved: bool = Field(default=False, description="Whether data was successfully retrieved")


class AnalysisResponse(BaseModel):
    """Complete analysis response to return to frontend."""
    request_id: str = Field(..., description="Unique request identifier")
    status: ProcessingStatus = Field(..., description="Overall processing status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    processing_time_ms: float = Field(..., description="Total processing time in milliseconds")
    
    analysis_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="High-level analysis summary"
    )
    
    land_information: Dict[str, RuleResult] = Field(
        default_factory=dict,
        description="All rule results organized by category"
    )
    
    processing_status: Dict[str, ModuleStatus] = Field(
        default_factory=dict,
        description="Status of each processing module"
    )
    
    provider_status: List[ProviderStatus] = Field(
        default_factory=list,
        description="Status of each data provider"
    )
    
    errors: List[ErrorInfo] = Field(
        default_factory=list,
        description="List of errors if any occurred"
    )


class ValidationError(BaseModel):
    """Validation error response."""
    status: str = Field(default="error", description="Error status")
    error_code: str = Field(..., description="Error code (VALIDATION_ERROR, etc.)")
    error_message: str = Field(..., description="User-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
