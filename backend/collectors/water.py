"""
Water Bodies Collector

Retrieves water feature data from OpenStreetMap.
"""

from typing import Optional, Dict, Any
import logging
import requests

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector, DataCollectionError

logger = logging.getLogger(__name__)


class WaterBodiesCollector(DataCollector):
    """
    Collects water body and water feature data from OpenStreetMap via Overpass API.
    
    Queries for water features (rivers, lakes, canals, ponds) that intersect the polygon.
    Returns water features with classification.
    """
    
    # Overpass API endpoint
    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
    
    # Timeout for API requests (seconds)
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT):
        """
        Initialize Water Bodies Collector.
        
        Args:
            timeout_seconds: Request timeout in seconds
        """
        super().__init__(
            provider_name="water",
            category=DataCategory.WATER,
            timeout_seconds=timeout_seconds
        )
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect water body data.
        
        Args:
            polygon: Validated polygon to analyze
            
        Returns:
            RawDataset with water body features
            
        Raises:
            DataCollectionError: If collection fails
        """
        self._log_collection_start(polygon)
        
        try:
            # Build Overpass query for water features
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
                    "query_type": "water_bodies"
                }
            )
            
            self._log_collection_complete(len(features), 0)
            
            return dataset
            
        except Exception as e:
            self._log_collection_error(e)
            raise DataCollectionError(
                f"Failed to collect water body data: {str(e)}"
            ) from e
    
    def _build_overpass_query(self, polygon: Polygon) -> str:
        """
        Build an Overpass query for water features.
        
        Queries for water-related features in the polygon's bounding box.
        
        Args:
            polygon: Polygon with bounding box
            
        Returns:
            Overpass query string
        """
        minx, miny, maxx, maxy = polygon.bounding_box
        
        # Overpass uses (south, west, north, east) order
        bbox = f"{miny},{minx},{maxy},{maxx}"
        
        # Query for water features
        query = f"""
        [bbox:{bbox}];
        (
            way["water"];
            way["waterway"];
            relation["water"];
            relation["waterway"];
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
            List of water body features
            
        Raises:
            DataCollectionError: If API request fails
        """
        try:
            logger.debug(f"Querying Overpass API for water features...")
            
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
            
            logger.info(f"Overpass API returned {len(features)} water features")
            
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
            
            # Determine if this is a polygon or linestring
            if not geometry:
                continue
            
            # Determine geometry type
            if len(geometry) >= 3 and geometry[0] == geometry[-1]:
                # Closed ring - polygon
                geometry_type = "Polygon"
                coordinates = [[[pt["lon"], pt["lat"]] for pt in geometry]]
            else:
                # Open line - linestring
                geometry_type = "LineString"
                coordinates = [[pt["lon"], pt["lat"]] for pt in geometry]
            
            geojson_geometry = {
                "type": geometry_type,
                "coordinates": coordinates
            }
            
            # Determine water type
            water_tag = tags.get("water", tags.get("waterway", ""))
            
            water_type_map = {
                "river": "river",
                "stream": "stream",
                "canal": "canal",
                "lake": "lake",
                "pond": "pond",
                "reservoir": "reservoir",
                "lagoon": "lagoon",
                "bay": "bay"
            }
            
            water_type = water_type_map.get(water_tag, "water_body")
            
            # Create feature
            feature = {
                "id": f"osm_water_{element_id}",
                "geometry": geojson_geometry,
                "properties": {
                    "osm_id": element_id,
                    "osm_type": element_type,
                    "name": tags.get("name", ""),
                    "water_tag": water_tag,
                    "water_type": water_type,
                    "salt": tags.get("salt", "no"),
                    "intermittent": tags.get("intermittent", "no"),
                    "source": "osm"
                }
            }
            
            features.append(feature)
        
        return features
