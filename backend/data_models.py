"""Core data models for Land Scanner using Pydantic validation"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
import uuid
from enum import Enum


class ProcessingStatusEnum(str, Enum):
    """Enumeration for processing status values."""
    SUCCESS = "success"
    FAILED = "failed"
    INSUFFICIENT_DATA = "insufficient_data"
    PARTIAL = "partial"


class DataCategoryEnum(str, Enum):
    """Enumeration for data categories."""
    BUILDINGS = "buildings"
    ADMIN = "admin"
    LAND_COVER = "land_cover"
    ROADS = "roads"
    WATER = "water"
    ELEVATION = "elevation"


class Coordinate(BaseModel):
    """Represent a [longitude, latitude] coordinate pair"""
    longitude: float
    latitude: float

    @field_validator("longitude")
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v

    @field_validator("latitude")
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v


class Point(BaseModel):
    """GeoJSON Point geometry"""
    type: str = "Point"
    coordinates: List[float]

    @field_validator("coordinates")
    def validate_coordinates(cls, v):
        if len(v) != 2:
            raise ValueError("Point coordinates must be [longitude, latitude]")
        return v


class LineString(BaseModel):
    """GeoJSON LineString geometry"""
    type: str = "LineString"
    coordinates: List[List[float]]

    @field_validator("coordinates")
    def validate_coordinates(cls, v):
        if len(v) < 2:
            raise ValueError("LineString must have at least 2 coordinates")
        return v


class Polygon(BaseModel):
    """GeoJSON Polygon geometry"""
    type: str = "Polygon"
    coordinates: List[List[List[float]]]

    @field_validator("coordinates")
    def validate_coordinates(cls, v):
        if len(v) == 0:
            raise ValueError("Polygon must have at least one ring")
        if len(v[0]) < 4:
            raise ValueError("Polygon ring must have at least 4 coordinates")
        return v


class Feature(BaseModel):
    """GeoJSON Feature with geometry and properties"""
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any] = Field(default_factory=dict)


class RawDataset(BaseModel):
    """Raw dataset collected from a provider"""
    source_provider: str
    category: str
    features: List[Feature] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StandardizedFeature(BaseModel):
    """Feature in standardized format"""
    id: str
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class StandardizedDataset(BaseModel):
    """Standardized dataset with normalized format"""
    category: str  # buildings, land_cover, roads, water, elevation, admin
    source_provider: str  # OSM, Copernicus, USGS, GEBCO
    features: List[StandardizedFeature] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuleResult(BaseModel):
    """Result from a single rule execution"""
    rule_id: str
    rule_name: str
    status: str  # success, insufficient_data, failed
    output: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class ProcessingStatus(BaseModel):
    """Status of each processing module"""
    validation: str = "pending"  # pending, success, error
    data_collection: str = "pending"
    standardization: str = "pending"
    rule_engine: str = "pending"
    output_generation: str = "pending"


class ProviderStatus(BaseModel):
    """Status of each data provider"""
    provider_id: str
    provider_name: str
    available: bool
    records: int = 0
    error_message: Optional[str] = None


class AnalysisSummary(BaseModel):
    """Summary of analysis results"""
    polygon_area_sqm: float
    analysis_date: datetime
    primary_land_cover: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)


class LandInformation(BaseModel):
    """Processed land information output"""
    administrative: Dict[str, Any] = Field(default_factory=dict)
    land_cover: Dict[str, Any] = Field(default_factory=dict)
    buildings: Dict[str, Any] = Field(default_factory=dict)
    roads: Dict[str, Any] = Field(default_factory=dict)
    water: Dict[str, Any] = Field(default_factory=dict)
    elevation: Dict[str, Any] = Field(default_factory=dict)


class AnalysisResponse(BaseModel):
    """Complete response from analysis"""
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: str  # success, partial, error
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: int = 0
    analysis_summary: Optional[AnalysisSummary] = None
    land_information: LandInformation = Field(default_factory=LandInformation)
    processing_status: ProcessingStatus = Field(default_factory=ProcessingStatus)
    provider_status: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
