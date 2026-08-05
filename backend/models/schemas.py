"""
Core data models for Land Scanner Prototype.

This module defines Pydantic models for:
- Polygon (GeoJSON wrapper)
- StandardizedDataset
- Feature (geometry and properties)
- RuleResult
- AnalysisResponse

All models include validation to ensure data integrity.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Any, Dict, List, Optional
from enum import Enum


class DataCategory(str, Enum):
    """Enumeration of data categories."""
    BUILDINGS = "buildings"
    ADMIN = "admin"
    LAND_COVER = "land_cover"
    ROADS = "roads"
    WATER = "water"
    ELEVATION = "elevation"


class ProcessingStatus(str, Enum):
    """Enumeration of processing statuses."""
    SUCCESS = "success"
    FAILED = "failed"
    INSUFFICIENT_DATA = "insufficient_data"
    PARTIAL = "partial"


class Coordinates(BaseModel):
    """Represents geographic coordinates [longitude, latitude]."""
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")


class Geometry(BaseModel):
    """Represents GeoJSON geometry object."""
    type: str = Field(..., description="Geometry type (e.g., 'Polygon', 'MultiPolygon')")
    coordinates: List = Field(..., description="Coordinates array")
    
    @field_validator('type')
    @classmethod
    def validate_geometry_type(cls, v):
        """Validate that geometry type is supported."""
        allowed_types = ['Polygon', 'MultiPolygon', 'Point', 'LineString', 'MultiLineString']
        if v not in allowed_types:
            raise ValueError(f"Geometry type must be one of {allowed_types}, got {v}")
        return v


class Feature(BaseModel):
    """Represents a GeoJSON feature with geometry and properties."""
    type: str = Field(default="Feature", description="Feature type")
    geometry: Geometry = Field(..., description="Feature geometry")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Feature properties")


class Polygon(BaseModel):
    """
    Represents a GeoJSON polygon for analysis.
    Validates structure, geometry, and size constraints.
    """
    type: str = Field(default="FeatureCollection", description="Type must be FeatureCollection")
    features: List[Feature] = Field(..., description="Array of features")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]
                        },
                        "properties": {}
                    }
                ]
            }
        }


class StandardizedFeature(BaseModel):
    """Represents a standardized feature with normalized structure."""
    type: str = Field(default="Feature")
    geometry: Geometry
    properties: Dict[str, Any]
    source_provider: str = Field(..., description="Source data provider")
    source_category: str = Field(..., description="Data category (buildings, roads, etc.)")


class StandardizedDataset(BaseModel):
    """Represents a standardized dataset with consistent structure across all providers."""
    features: List[StandardizedFeature] = Field(default_factory=list)
    source_provider: str = Field(..., description="Primary data provider")
    category: DataCategory = Field(..., description="Data category")
    feature_count: int = Field(default=0, description="Number of features")
    crs: str = Field(default="EPSG:4326", description="Coordinate Reference System")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Provider-specific metadata")


class RuleResult(BaseModel):
    """Represents the result of a rule execution."""
    rule_id: str = Field(..., description="Unique rule identifier")
    rule_name: str = Field(..., description="Human-readable rule name")
    status: ProcessingStatus = Field(..., description="Execution status")
    result: Dict[str, Any] = Field(default_factory=dict, description="Rule output data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")


class ProviderStatus(BaseModel):
    """Represents the status of a data provider."""
    provider_name: str = Field(..., description="Provider name")
    status: str = Field(..., description="Status (available, unavailable, timeout, rate_limited)")
    error_message: Optional[str] = Field(None, description="Error message if applicable")
    feature_count: int = Field(default=0, description="Number of features collected")


class AnalysisResponse(BaseModel):
    """
    Complete analysis response with all required sections.
    Sent to frontend after analysis completion.
    """
    status: str = Field(..., description="Overall analysis status (success, partial, failed)")
    polygon_info: Dict[str, Any] = Field(default_factory=dict, description="Input polygon information")
    analysis_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of analysis")
    land_information: Dict[str, Any] = Field(default_factory=dict, description="Processed land information")
    processing_status: Dict[str, str] = Field(default_factory=dict, description="Status of each processing module")
    provider_status: List[ProviderStatus] = Field(default_factory=list, description="Status of each data provider")
    error_summary: Optional[Dict[str, Any]] = Field(None, description="Error summary if any failures occurred")
    timestamp: str = Field(..., description="ISO 8601 timestamp of analysis")
