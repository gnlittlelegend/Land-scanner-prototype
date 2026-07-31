"""
OpenStreetMap Buildings Collector

Retrieves building data from OpenStreetMap using the Overpass API.
"""

from typing import Optional, Dict, Any
import logging
import requests
from urllib.parse import urlencode

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector, DataCollectionError

logger = logging.getLogger(__name__)


class OSMBuildingsCollector(DataCollector):
    """
    Collects building data from OpenStreetMap via Overpass API.
    
    Queries the Overpass API for buildings within the polygon bounds.
    Returns raw OSM features with minimal processing.
    """
    
    # Overpass API endpoint
    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
    
    # Timeout for API requests (seconds)
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT):
        """
        Initialize OSM Buildings Collector.
        
        Args:
            timeout_seconds: Request timeout in seconds
        """
        super().__init__(
            provider_name="osm_buildings",
            category=DataCategory.BUILDINGS,
            timeout_seconds=timeout_seconds
        )
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect building data from OpenStreetMap.
        
        Args:
            polygon: Validated polygon to analyze
            
        Returns:
            RawDataset with building features from OSM
            
        Raises:
            DataCollectionError: If collection fails
        """
        self._log_collection_start(polygon)
        
        try:
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
                    "query_type": "buildings"
                }
            )
            
            self._log_collection_complete(len(features), 0)
            
            return dataset
            
        except Exception as e:
            self._log_collection_error(e)
            raise DataCollectionError(
                f"Failed to collect OSM buildings data: {str(e)}"
            ) from e
    
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
        Execute query against Overpass API.
        
        Args:
            query: Overpass query string
            
        Returns:
            List of building features from OSM
            
        Raises:
            DataCollectionError: If API request fails
        """
        try:
            logger.debug(f"Querying Overpass API with query: {query[:100]}...")
            
            response = requests.post(
                self.OVERPASS_API_URL,
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
            
        except requests.RequestException as e:
            raise DataCollectionError(
                f"Overpass API request failed: {str(e)}"
            ) from e
        except ValueError as e:
            raise DataCollectionError(
                f"Failed to parse Overpass API response: {str(e)}"
            ) from e
    
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
