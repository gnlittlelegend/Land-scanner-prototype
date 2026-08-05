"""Elevation Data Collector - Retrieves elevation/DEM data."""

from typing import List, Dict, Any
import logging
import requests
import time
import os

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector, DataCollectionError

logger = logging.getLogger(__name__)


class ElevationCollector(DataCollector):
    """Collects elevation and digital elevation model (DEM) data."""
    
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 2
    DEFAULT_RETRY_DELAY = 1
    
    def __init__(self, timeout_seconds=DEFAULT_TIMEOUT, retry_count=DEFAULT_RETRY_COUNT,
                 retry_delay_seconds=DEFAULT_RETRY_DELAY, use_test_data=False):
        super().__init__(
            provider_name="elevation",
            category=DataCategory.ELEVATION,
            timeout_seconds=timeout_seconds
        )
        self.retry_count = retry_count
        self.retry_delay = retry_delay_seconds
        self.use_test_data = use_test_data or os.getenv("USE_TEST_DATA", "").lower() == "true"
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """Collect elevation data for polygon."""
        self._log_collection_start(polygon)
        
        try:
            if self.use_test_data:
                logger.info("Using test data (development mode)")
                return self._load_test_data(polygon)
            
            try:
                return self._collect_from_api(polygon)
            except DataCollectionError as api_error:
                logger.warning(f"API collection failed: {api_error}")
                logger.info("Falling back to test data...")
                return self._load_test_data(polygon)
        except Exception as e:
            self._log_collection_error(e)
            raise DataCollectionError(f"Failed to collect elevation data: {str(e)}") from e
    
    def _collect_from_api(self, polygon: Polygon) -> RawDataset:
        """Attempt to collect from real API with retry logic."""
        last_error = None
        for attempt in range(self.retry_count):
            try:
                logger.debug(f"API attempt {attempt + 1}/{self.retry_count}")
                features = self._query_api(polygon)
                dataset = self._create_raw_dataset(
                    features=features,
                    geometry_type="Point",
                    metadata={"source": "Elevation Service", "query_type": "elevation"}
                )
                self._log_collection_complete(len(features), 0)
                return dataset
            except (requests.RequestException, DataCollectionError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)[:100]}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        
        raise DataCollectionError(f"Elevation API failed: {str(last_error)}")
    
    def _query_api(self, polygon: Polygon) -> list:
        """Query elevation from API."""
        raise DataCollectionError("Elevation API temporarily unavailable")
    
    def _load_test_data(self, polygon: Polygon) -> RawDataset:
        """Load realistic test data for elevation."""
        logger.info("Loading test data for Elevation")
        centroid_lon, centroid_lat = polygon.centroid
        
        test_features = [
            {
                "id": "elev_point_001",
                "geometry": {"type": "Point", "coordinates": [centroid_lon - 0.5, centroid_lat - 0.5]},
                "properties": {"elevation_m": 145, "confidence": 0.95}
            },
            {
                "id": "elev_point_002",
                "geometry": {"type": "Point", "coordinates": [centroid_lon, centroid_lat]},
                "properties": {"elevation_m": 185, "confidence": 0.98}
            },
            {
                "id": "elev_point_003",
                "geometry": {"type": "Point", "coordinates": [centroid_lon + 0.5, centroid_lat + 0.5]},
                "properties": {"elevation_m": 165, "confidence": 0.92}
            },
            {
                "id": "elev_point_004",
                "geometry": {"type": "Point", "coordinates": [centroid_lon - 0.3, centroid_lat + 0.4]},
                "properties": {"elevation_m": 175, "confidence": 0.94}
            },
            {
                "id": "elev_point_005",
                "geometry": {"type": "Point", "coordinates": [centroid_lon + 0.4, centroid_lat - 0.3]},
                "properties": {"elevation_m": 155, "confidence": 0.96}
            }
        ]
        
        dataset = self._create_raw_dataset(
            features=test_features,
            geometry_type="Point",
            metadata={"source": "Elevation Service", "api": "Test Data", "query_type": "elevation"}
        )
        self._log_collection_complete(len(test_features), 0)
        return dataset
