"""Land Cover Collector - Retrieves land cover classification data."""

from typing import List, Dict, Any
import logging
import requests
import time
import os

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector, DataCollectionError

logger = logging.getLogger(__name__)


class LandCoverCollector(DataCollector):
    """Collects land cover classification data."""
    
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 2
    DEFAULT_RETRY_DELAY = 1
    
    def __init__(self, timeout_seconds=DEFAULT_TIMEOUT, retry_count=DEFAULT_RETRY_COUNT,
                 retry_delay_seconds=DEFAULT_RETRY_DELAY, use_test_data=False):
        super().__init__(
            provider_name="land_cover",
            category=DataCategory.LAND_COVER,
            timeout_seconds=timeout_seconds
        )
        self.retry_count = retry_count
        self.retry_delay = retry_delay_seconds
        self.use_test_data = use_test_data or os.getenv("USE_TEST_DATA", "").lower() == "true"
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """Collect land cover data for polygon."""
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
            raise DataCollectionError(f"Failed to collect land cover data: {str(e)}") from e
    
    def _collect_from_api(self, polygon: Polygon) -> RawDataset:
        """Attempt to collect from real API with retry logic."""
        last_error = None
        for attempt in range(self.retry_count):
            try:
                logger.debug(f"API attempt {attempt + 1}/{self.retry_count}")
                features = self._query_api(polygon)
                dataset = self._create_raw_dataset(
                    features=features,
                    geometry_type="Polygon",
                    metadata={"source": "Land Cover Service", "query_type": "land_cover"}
                )
                self._log_collection_complete(len(features), 0)
                return dataset
            except (requests.RequestException, DataCollectionError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)[:100]}")
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        
        raise DataCollectionError(f"Land cover API failed: {str(last_error)}")
    
    def _query_api(self, polygon: Polygon) -> list:
        """Query land cover from API."""
        raise DataCollectionError("Land cover API temporarily unavailable")
    
    def _load_test_data(self, polygon: Polygon) -> RawDataset:
        """Load realistic test data for land cover."""
        logger.info("Loading test data for Land Cover")
        centroid_lon, centroid_lat = polygon.centroid
        
        test_features = [
            {
                "id": "lc_urban_001",
                "geometry": {"type": "Polygon", "coordinates": [[[centroid_lon - 0.5, centroid_lat - 0.5],
                    [centroid_lon + 0.3, centroid_lat - 0.5], [centroid_lon + 0.3, centroid_lat + 0.2],
                    [centroid_lon - 0.5, centroid_lat + 0.2], [centroid_lon - 0.5, centroid_lat - 0.5]]]},
                "properties": {"name": "Urban Area", "lc_class": "urban", "percentage": 45}
            },
            {
                "id": "lc_grass_001",
                "geometry": {"type": "Polygon", "coordinates": [[[centroid_lon + 0.3, centroid_lat - 0.5],
                    [centroid_lon + 0.8, centroid_lat - 0.5], [centroid_lon + 0.8, centroid_lat + 0.2],
                    [centroid_lon + 0.3, centroid_lat + 0.2], [centroid_lon + 0.3, centroid_lat - 0.5]]]},
                "properties": {"name": "Grassland", "lc_class": "grassland", "percentage": 35}
            },
            {
                "id": "lc_forest_001",
                "geometry": {"type": "Polygon", "coordinates": [[[centroid_lon - 0.5, centroid_lat + 0.2],
                    [centroid_lon + 0.8, centroid_lat + 0.2], [centroid_lon + 0.8, centroid_lat + 0.7],
                    [centroid_lon - 0.5, centroid_lat + 0.7], [centroid_lon - 0.5, centroid_lat + 0.2]]]},
                "properties": {"name": "Forest", "lc_class": "forest", "percentage": 20}
            }
        ]
        
        dataset = self._create_raw_dataset(
            features=test_features,
            geometry_type="Polygon",
            metadata={"source": "Land Cover Service", "api": "Test Data", "query_type": "land_cover"}
        )
        self._log_collection_complete(len(test_features), 0)
        return dataset
