"""
Road Network Collector

Retrieves road network data from OpenStreetMap.
"""

from typing import Optional, Dict, Any
import logging
import requests

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector, DataCollectionError

logger = logging.getLogger(__name__)


class RoadNetworkCollector(DataCollector):
    """
    Collects road network data from OpenStreetMap via Overpass API.
    
    Queries for roads that intersect the polygon.
    Returns road network features with classification.
    """
    
    # Overpass API endpoint
    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
    
    # Timeout for API requests (seconds)
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT):
        """
        Initialize Road Network Collector.
        
        Args:
            timeout_seconds: Request timeout in seconds
        """
        super().__init__(
            provider_name="roads",
            category=DataCategory.ROADS,
            timeout_seconds=timeout_seconds
        )
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect road network data.
        
        Args:
            polygon: Validated polygon to analyze
            
        Returns:
            RawDataset with road network features
            
        Raises:
            DataCollectionError: If collection fails
        """
        self._log_collection_start(polygon)
        
        try:
            # Build Overpass query for roads
            overpass_query = self._build_overpass_query(polygon)
            
            # Query Overpass API
            features = self._query_overpass_api(overpass_query)
            
            # Create and return raw dataset
            dataset = self._create_raw_dataset(
                features=features,
                geometry_type="LineString",
                metadata={
                    "source": "OpenStreetMap",
                    "api": "Overpass",
                    "query_type": "roads"
                }
            )
            
            self._log_collection_complete(len(features), 0)
            
            return dataset
            
        except Exception as e:
            self._log_collection_error(e)
            raise DataCollectionError(
                f"Failed to collect road network data: {str(e)}"
            ) from e
    
    def _build_overpass_query(self, polygon: Polygon) -> str:
        """
        Build an Overpass query for roads.
        
        Queries for ways with highway tag that intersect the polygon's bounding box.
        
        Args:
            polygon: Polygon with bounding box
            
        Returns:
            Overpass query string
        """
        minx, miny, maxx, maxy = polygon.bounding_box
        
        # Overpass uses (south, west, north, east) order
        bbox = f"{miny},{minx},{maxy},{maxx}"
        
        # Query for roads (ways with highway tag)
        query = f"""
        [bbox:{bbox}];
        (
            way["highway"];
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
            List of road features
            
        Raises:
            DataCollectionError: If API request fails
        """
        try:
            logger.debug(f"Querying Overpass API for roads...")
            
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
            
            logger.info(f"Overpass API returned {len(features)} road features")
            
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
            
            # Skip if we can't create a line from the geometry
            if not geometry or len(geometry) < 2:
                continue
            
            # Create GeoJSON geometry
            geojson_geometry = {
                "type": "LineString",
                "coordinates": [[pt["lon"], pt["lat"]] for pt in geometry]
            }
            
            # Map highway tags to road types
            highway_type = tags.get("highway", "")
            
            road_type_map = {
                "motorway": "motorway",
                "trunk": "trunk",
                "primary": "primary",
                "secondary": "secondary",
                "tertiary": "tertiary",
                "residential": "residential",
                "living_street": "living_street",
                "track": "track",
                "path": "path"
            }
            
            road_type = road_type_map.get(highway_type, "other")
            
            # Create feature
            feature = {
                "id": f"osm_road_{element_id}",
                "geometry": geojson_geometry,
                "properties": {
                    "osm_id": element_id,
                    "osm_type": element_type,
                    "name": tags.get("name", ""),
                    "highway_type": highway_type,
                    "road_type": road_type,
                    "maxspeed": tags.get("maxspeed", ""),
                    "lanes": tags.get("lanes", ""),
                    "surface": tags.get("surface", ""),
                    "source": "osm"
                }
            }
            
            features.append(feature)
        
        return features
