"""
Base Data Collector Module

Defines the abstract base class for all data collectors.
Each collector is responsible for retrieving data from a single data provider.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import logging
import time

from backend.models import RawDataset, DataCategory, Polygon

logger = logging.getLogger(__name__)


class DataCollectionError(Exception):
    """Raised when data collection fails."""
    pass


class DataCollector(ABC):
    """
    Abstract base class for data collectors.
    
    Each collector is responsible for:
    - Connecting to a single data provider
    - Building provider-specific requests
    - Retrieving data
    - Validating responses
    - Returning raw datasets
    
    Collectors must NOT:
    - Communicate with other collectors
    - Process or standardize data
    - Know about business rules
    """
    
    def __init__(self, provider_name: str, category: DataCategory, timeout_seconds: int = 30):
        """
        Initialize a data collector.
        
        Args:
            provider_name: Name of the data provider
            category: Data category this collector handles
            timeout_seconds: Request timeout in seconds
        """
        self.provider_name = provider_name
        self.category = category
        self.timeout_seconds = timeout_seconds
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")
    
    @abstractmethod
    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect data from the provider for the given polygon.
        
        Args:
            polygon: Validated polygon to analyze
            
        Returns:
            RawDataset with collected data
            
        Raises:
            DataCollectionError: If collection fails
        """
        pass
    
    def _create_raw_dataset(
        self,
        features: list,
        geometry_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDataset:
        """
        Create a RawDataset from collection results.
        
        Args:
            features: List of features from provider
            geometry_type: Type of geometries (Point, LineString, Polygon)
            metadata: Optional metadata dictionary
            
        Returns:
            RawDataset object
        """
        if metadata is None:
            metadata = {}
        
        metadata.setdefault("timestamp", time.time())
        metadata.setdefault("provider_name", self.provider_name)
        
        return RawDataset(
            source_provider=self.provider_name,
            category=self.category,
            geometry_type=geometry_type,
            features=features,
            metadata=metadata
        )
    
    def _log_collection_start(self, polygon: Polygon) -> None:
        """Log the start of data collection."""
        self.logger.info(
            f"Starting data collection for {self.category.value}: "
            f"area={polygon.area_sqkm:.2f} sq km, "
            f"bounds={polygon.bounding_box}"
        )
    
    def _log_collection_complete(self, feature_count: int, execution_time_ms: float) -> None:
        """Log successful completion of data collection."""
        self.logger.info(
            f"Data collection complete: {feature_count} features in {execution_time_ms:.2f}ms"
        )
    
    def _log_collection_error(self, error: Exception) -> None:
        """Log data collection error."""
        self.logger.error(f"Data collection failed: {str(error)}", exc_info=True)
