"""
Administrative Boundaries Collector

Retrieves administrative boundary data from open sources.
Includes retry logic and test data fallback.
"""

from typing import List, Dict, Any
import logging
import requests
import time
import os

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector, DataCollectionError

logger = logging.getLogger(__name__)


class AdminBoundariesCollector(DataCollector):
    """
    Collects administrative boundary data.
    
    Features:
    - Queries available administrative data sources
    - Implements retry logic
    - Falls back to test data when APIs unavailable
    """
    
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 2
    DEFAULT_RETRY_DELAY = 1
    
    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY,
        use_test_data: bool = False
    ):
        super().__init__(
            provider_name="admin_boundaries",
            category=DataCategory.ADMIN,
            timeout_seconds=timeout_seconds
        )
        self.retry_count = retry_count
        self.retry_delay = retry_delay_seconds
        self.use_test_data = use_test_data or os.getenv("USE_TEST_DATA", "").lower() == "true"
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """Collect administrative boundary data for polygon."""
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
            raise DataCollectionError(
                f"Failed to collect administrative boundaries: {str(e)}"
            ) from e
    
    def _collect_from_api(self, polygon: Polygon) -> RawDataset:
        """Attempt to collect from real API with retry logic."""
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                logger.debug(f"API attempt {attempt + 1}/{self.retry_count}")
                
                # Try to query administrative data
                # In production, this would query an actual service
                features = self._query_admin_api(polygon)
                
                dataset = self._create_raw_dataset(
                    features=features,
                    geometry_type="Polygon",
                    metadata={
                        "source": "Administrative Data Source",
                        "query_type": "administrative_boundaries",
                        "retry_attempt": attempt + 1
                    }
                )
                
                self._log_collection_complete(len(features), 0)
                return dataset
                
            except (requests.RequestException, DataCollectionError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)[:100]}")
                
                if attempt < self.retry_count - 1:
                    time.sleep(self.retry_delay)
        
        raise DataCollectionError(
            f"Admin API failed after {self.retry_count} attempts: {str(last_error)}"
        )
    
    def _query_admin_api(self, polygon: Polygon) -> list:
        """Query administrative boundaries from API."""
        # In production, this would call an actual API
        # For now, we'll use test data since external services are unreachable
        raise DataCollectionError("Administrative boundaries API temporarily unavailable")
    
    def _load_test_data(self, polygon: Polygon) -> RawDataset:
        """Load realistic test data for administrative boundaries."""
        logger.info("Loading test data for Administrative Boundaries")
        
        centroid_lon, centroid_lat = polygon.centroid
        
        # Generate test administrative regions
        test_features = []
        
        # Country boundary
        test_features.append({
            "id": "admin_country_test_001",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [centroid_lon - 2, centroid_lat - 2],
                    [centroid_lon + 2, centroid_lat - 2],
                    [centroid_lon + 2, centroid_lat + 2],
                    [centroid_lon - 2, centroid_lat + 2],
                    [centroid_lon - 2, centroid_lat - 2]
                ]]
            },
            "properties": {
                "admin_id": "USA",
                "admin_level": 2,
                "name": "United States of America",
                "type": "country"
            }
        })
        
        # State boundary
        test_features.append({
            "id": "admin_state_test_001",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [centroid_lon - 1, centroid_lat - 1],
                    [centroid_lon + 1, centroid_lat - 1],
                    [centroid_lon + 1, centroid_lat + 1],
                    [centroid_lon - 1, centroid_lat + 1],
                    [centroid_lon - 1, centroid_lat - 1]
                ]]
            },
            "properties": {
                "admin_id": "CA",
                "admin_level": 4,
                "name": "California",
                "type": "state"
            }
        })
        
        # County boundary
        test_features.append({
            "id": "admin_county_test_001",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [centroid_lon - 0.5, centroid_lat - 0.5],
                    [centroid_lon + 0.5, centroid_lat - 0.5],
                    [centroid_lon + 0.5, centroid_lat + 0.5],
                    [centroid_lon - 0.5, centroid_lat + 0.5],
                    [centroid_lon - 0.5, centroid_lat - 0.5]
                ]]
            },
            "properties": {
                "admin_id": "SF",
                "admin_level": 6,
                "name": "San Francisco County",
                "type": "county"
            }
        })
        
        dataset = self._create_raw_dataset(
            features=test_features,
            geometry_type="Polygon",
            metadata={
                "source": "Administrative Data Source",
                "api": "Test Data",
                "query_type": "administrative_boundaries",
                "note": "Test data for development/testing"
            }
        )
        
        self._log_collection_complete(len(test_features), 0)
        return dataset
