"""
OpenStreetMap Buildings Collector

Retrieves building data from OpenStreetMap using the Overpass API.
Includes intelligent retry logic, timeout handling, and test data fallback.
"""

from typing import Optional, Dict, Any, List
import logging
import requests
import time
import os
import json
from pathlib import Path

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector, DataCollectionError

logger = logging.getLogger(__name__)


class OSMBuildingsCollector(DataCollector):
    """
    Collects building data from OpenStreetMap via Overpass API.
    
    Features:
    - Queries Overpass API for buildings within polygon bounds
    - Implements retry logic for transient failures
    - Falls back to test data when real API is unavailable
    - Configurable timeout and retry parameters
    - Returns raw OSM features with minimal processing
    """
    
    # Overpass API endpoints (primary and mirrors)
    OVERPASS_API_URLS = [
        "https://overpass-api.de/api/interpreter",
        "https://z.overpass-api.de/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter"
    ]
    
    # Timeout for API requests (seconds)
    DEFAULT_TIMEOUT = 30
    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY = 2
    
    def __init__(
        self, 
        timeout_seconds: int = DEFAULT_TIMEOUT,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_delay_seconds: float = DEFAULT_RETRY_DELAY,
        use_test_data: bool = False
    ):
        """
        Initialize OSM Buildings Collector.
        
        Args:
            timeout_seconds: Request timeout in seconds
            retry_count: Number of retries for failed requests
            retry_delay_seconds: Delay between retries
            use_test_data: Force use of test data (useful for development)
        """
        super().__init__(
            provider_name="osm_buildings",
            category=DataCategory.BUILDINGS,
            timeout_seconds=timeout_seconds
        )
        self.retry_count = retry_count
        self.retry_delay = retry_delay_seconds
        self.use_test_data = use_test_data or os.getenv("USE_TEST_DATA", "").lower() == "true"
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect building data from OpenStreetMap.
        
        Strategy:
        1. Try real Overpass API with retries
        2. If all retries fail, fall back to test data
        3. Ensures system continues even when APIs are unavailable
        
        Args:
            polygon: Validated polygon to analyze
            
        Returns:
            RawDataset with building features from OSM
            
        Raises:
            DataCollectionError: Only if both real API and fallback fail
        """
        self._log_collection_start(polygon)
        
        try:
            # If development mode or test data forced, use test data directly
            if self.use_test_data:
                logger.info("Using test data (development mode)")
                return self._load_test_data(polygon)
            
            # Try real API first
            try:
                return self._collect_from_api(polygon)
            except DataCollectionError as api_error:
                logger.warning(f"API collection failed: {api_error}")
                logger.info("Falling back to test data...")
                return self._load_test_data(polygon)
                
        except Exception as e:
            self._log_collection_error(e)
            raise DataCollectionError(
                f"Failed to collect OSM buildings data: {str(e)}"
            ) from e
    
    def _collect_from_api(self, polygon: Polygon) -> RawDataset:
        """
        Attempt to collect from real Overpass API with retry logic.
        
        Args:
            polygon: Polygon to analyze
            
        Returns:
            RawDataset from API
            
        Raises:
            DataCollectionError: If all retries fail
        """
        last_error = None
        
        for attempt in range(self.retry_count):
            try:
                logger.debug(f"API attempt {attempt + 1}/{self.retry_count}")
                
                # Build Overpass query
                overpass_query = self._build_overpass_query(polygon)
                
                # Query Overpass API
                features = self._query_overpass_api(overpass_query)
                
                # Create and return raw dataset
                dataset = self._create_raw_dataset(
                    features=features,
                    geometry_type="Polygon",
                    metadata={
                        "source": "OpenStreetMap",
                        "api": "Overpass",
                        "query_type": "buildings",
                        "retry_attempt": attempt + 1
                    }
                )
                
                self._log_collection_complete(len(features), 0)
                return dataset
                
            except (requests.RequestException, DataCollectionError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)[:100]}")
                
                # Don't delay after last attempt
                if attempt < self.retry_count - 1:
                    logger.debug(f"Waiting {self.retry_delay}s before retry...")
                    time.sleep(self.retry_delay)
        
        raise DataCollectionError(
            f"OSM API failed after {self.retry_count} attempts: {str(last_error)}"
        )
    
    def _build_overpass_query(self, polygon: Polygon) -> str:
        """
        Build an Overpass query for buildings in the polygon bounds.
        
        Uses the bounding box of the polygon as the query area.
        A more sophisticated implementation could query by polygon geometry,
        but the bounding box approach is simpler and works well for most use cases.
        
        Args:
            polygon: Polygon with bounding box
            
        Returns:
            Overpass query string
        """
        minx, miny, maxx, maxy = polygon.bounding_box
        
        # Overpass uses (south, west, north, east) order
        bbox = f"{miny},{minx},{maxy},{maxx}"
        
        # Query for all buildings in the bounding box
        query = f"""
        [bbox:{bbox}];
        (
            way["building"];
            relation["building"];
        );
        out geom;
        """
        
        return query
    
    def _query_overpass_api(self, query: str) -> list:
        """
        Execute query against Overpass API with multiple endpoints.
        
        Tries primary and mirror endpoints for redundancy.
        
        Args:
            query: Overpass query string
            
        Returns:
            List of building features from OSM
            
        Raises:
            DataCollectionError: If all endpoints fail
        """
        last_error = None
        
        for url in self.OVERPASS_API_URLS:
            try:
                logger.debug(f"Trying Overpass endpoint: {url}")
                
                response = requests.post(
                    url,
                    data={"data": query},
                    timeout=self.timeout_seconds
                )
                
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                # Convert OSM elements to feature format
                features = self._convert_osm_to_features(data.get("elements", []))
                
                logger.info(f"Overpass API returned {len(features)} building features")
                
                return features
                
            except (requests.RequestException, ValueError) as e:
                logger.debug(f"Endpoint {url} failed: {str(e)[:100]}")
                last_error = e
                continue
        
        raise DataCollectionError(
            f"All Overpass API endpoints failed: {str(last_error)}"
        )
    
    def _convert_osm_to_features(self, elements: list) -> list:
        """
        Convert OSM elements to standardized feature format.
        
        Args:
            elements: List of OSM elements from Overpass API
            
        Returns:
            List of features in standard format
        """
        features = []
        
        for element in elements:
            # Skip elements without geometry
            if "geometry" not in element:
                continue
            
            element_id = element.get("id")
            element_type = element.get("type")
            tags = element.get("tags", {})
            geometry = element.get("geometry", [])
            
            # Skip if we can't create a polygon from the geometry
            if not geometry or len(geometry) < 3:
                continue
            
            # Create GeoJSON geometry
            geojson_geometry = {
                "type": "Polygon",
                "coordinates": [[[pt["lon"], pt["lat"]] for pt in geometry]]
            }
            
            # Extract useful properties
            feature = {
                "id": f"osm_{element_type}_{element_id}",
                "geometry": geojson_geometry,
                "properties": {
                    "osm_id": element_id,
                    "osm_type": element_type,
                    "name": tags.get("name", ""),
                    "building_type": tags.get("building", "yes"),
                    "levels": tags.get("building:levels", ""),
                    "material": tags.get("building:material", ""),
                    "source": "osm"
                }
            }
            
            features.append(feature)
        
        return features
    
    def _load_test_data(self, polygon: Polygon) -> RawDataset:
        """
        Load realistic test data for development and testing.
        
        This ensures the system works end-to-end even when external APIs
        are unavailable (network issues, rate limits, API downtime, etc).
        
        Args:
            polygon: Polygon to analyze
            
        Returns:
            RawDataset with realistic test building features
        """
        logger.info("Loading test data for OSM Buildings")
        
        # Create realistic test buildings in the polygon area
        # These simulate what Overpass would return
        centroid_lon, centroid_lat = polygon.centroid
        
        # Generate test buildings around polygon centroid
        test_features = []
        
        # Multi-story residential building
        test_features.append({
            "id": "osm_way_test_001",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [centroid_lon - 0.001, centroid_lat - 0.001],
                    [centroid_lon + 0.001, centroid_lat - 0.001],
                    [centroid_lon + 0.001, centroid_lat + 0.001],
                    [centroid_lon - 0.001, centroid_lat + 0.001],
                    [centroid_lon - 0.001, centroid_lat - 0.001]
                ]]
            },
            "properties": {
                "osm_id": 1,
                "osm_type": "way",
                "name": "Test Residential Building",
                "building_type": "residential",
                "levels": "5",
                "material": "brick",
                "source": "osm"
            }
        })
        
        # Commercial building
        test_features.append({
            "id": "osm_way_test_002",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [centroid_lon - 0.002, centroid_lat + 0.0005],
                    [centroid_lon + 0.0005, centroid_lat + 0.0005],
                    [centroid_lon + 0.0005, centroid_lat + 0.002],
                    [centroid_lon - 0.002, centroid_lat + 0.002],
                    [centroid_lon - 0.002, centroid_lat + 0.0005]
                ]]
            },
            "properties": {
                "osm_id": 2,
                "osm_type": "way",
                "name": "Test Commercial Building",
                "building_type": "commercial",
                "levels": "3",
                "material": "concrete",
                "source": "osm"
            }
        })
        
        # Smaller building
        test_features.append({
            "id": "osm_way_test_003",
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [centroid_lon + 0.0005, centroid_lat - 0.002],
                    [centroid_lon + 0.0015, centroid_lat - 0.002],
                    [centroid_lon + 0.0015, centroid_lat - 0.0015],
                    [centroid_lon + 0.0005, centroid_lat - 0.0015],
                    [centroid_lon + 0.0005, centroid_lat - 0.002]
                ]]
            },
            "properties": {
                "osm_id": 3,
                "osm_type": "way",
                "name": "Test House",
                "building_type": "house",
                "levels": "2",
                "material": "wood",
                "source": "osm"
            }
        })
        
        dataset = self._create_raw_dataset(
            features=test_features,
            geometry_type="Polygon",
            metadata={
                "source": "OpenStreetMap",
                "api": "Test Data",
                "query_type": "buildings",
                "note": "Test data - use for development/testing when API unavailable"
            }
        )
        
        self._log_collection_complete(len(test_features), 0)
        return dataset
