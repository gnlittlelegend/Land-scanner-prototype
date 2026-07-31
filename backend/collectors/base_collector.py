"""
Base collector class that defines the interface for all data collectors.
Each collector retrieves data from a specific geospatial data provider.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from datetime import datetime
from backend.models.schemas import Polygon, RawDataset, DataCategory


class DataCollectorError(Exception):
    """Raised when a data collector encounters an error."""
    pass


class DataCollector(ABC):
    """
    Abstract base class for all data collectors.
    
    Each collector is responsible for:
    - Building provider-specific API requests
    - Querying a single geospatial data provider
    - Validating response structure
    - Returning raw data with source attribution
    - Handling provider-specific errors gracefully
    """

    def __init__(self, provider_name: str, category: DataCategory, timeout_seconds: int = 30):
        """
        Initialize the data collector.
        
        Args:
            provider_name: Name of the data provider (e.g., "osm_buildings")
            category: Category of data being collected (buildings, land_cover, etc.)
            timeout_seconds: Timeout for API requests in seconds
        """
        self.provider_name = provider_name
        self.category = category
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect data from the provider for the given polygon.
        
        Args:
            polygon: Validated polygon defining the area of interest
            
        Returns:
            RawDataset containing the collected features
            
        Raises:
            DataCollectorError: If data collection fails
        """
        pass

    def _build_raw_dataset(
        self,
        features: list,
        geometry_type: str = "Polygon",
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDataset:
        """
        Helper method to construct a RawDataset from collected features.
        
        Args:
            features: List of features from the provider
            geometry_type: Type of geometry (Point, LineString, Polygon)
            metadata: Optional metadata dictionary
            
        Returns:
            RawDataset object with standardized structure
        """
        if metadata is None:
            metadata = {}

        return RawDataset(
            source_provider=self.provider_name,
            category=self.category,
            geometry_type=geometry_type,
            features=features,
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "version": metadata.get("version", "1.0"),
                "crs": metadata.get("crs", "EPSG:4326"),
                **metadata
            }
        )

    def _validate_response_structure(self, response: Dict[str, Any]) -> bool:
        """
        Validate that a provider response has the expected structure.
        
        Args:
            response: Response dictionary from the provider
            
        Returns:
            True if valid, raises DataCollectorError if invalid
        """
        if not isinstance(response, dict):
            raise DataCollectorError(
                f"{self.provider_name}: Invalid response structure (expected dict)"
            )
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} provider={self.provider_name} category={self.category}>"
