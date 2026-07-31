"""
Administrative Boundaries Collector

Retrieves administrative boundary data from OpenStreetMap.
"""

from typing import Optional, Dict, Any
import logging
import requests

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector, DataCollectionError

logger = logging.getLogger(__name__)


class AdminBoundariesCollector(DataCollector):
    """
    Collects administrative boundary data from OpenStreetMap via Overpass API.
    
    Queries for administrative boundaries that intersect the polygon.
    Returns administrative regions (countries, states, districts, etc.).
    """
    
    # Overpass API endpoint
    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
    
    # Timeout for API requests (seconds)
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT):
        """
        Initialize Admin Boundaries Collector.
        
        Args:
            timeout_seconds: Request timeout in seconds
        """
        super().__init__(
            provider_name="admin_boundaries",
            category=DataCategory.ADMIN,
            timeout_seconds=timeout_seconds
        )
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect administrative boundary data.
        
        Args:
            polygon: Validated polygon to analyze
            
        Returns:
            RawDataset with administrative boundary features
            
        Raises:
            DataCollectionError: If collection fails
        """
        self._log_collection_start(polygon)
        
        try:
            # Build Overpass query for admin boundaries
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
                    "query_type": "administrative_boundaries"
                }
            )
            
            self._log_collection_complete(len(features), 0)
            
            return dataset
            
        except Exception as e:
            self._log_collection_error(e)
            raise DataCollectionError(
                f"Failed to collect administrative boundary data: {str(e)}"
            ) from e
    
    def _build_overpass_query(self, polygon: Polygon) -> str:
        """
        Build an Overpass query for administrative boundaries.
        
        Queries for relations with boundary=administrative tag
        that intersect the polygon's bounding box.
        
        Args:
            polygon: Polygon with bounding box
            
        Returns:
            Overpass query string
        """
        minx, miny, maxx, maxy = polygon.bounding_box
        
        # Overpass uses (south, west, north, east) order
        bbox = f"{miny},{minx},{maxy},{maxx}"
        
        # Query for administrative boundaries
        query = f"""
        [bbox:{bbox}];
        (
            relation["boundary"="administrative"]["admin_level"];
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
            List of administrative boundary features
            
        Raises:
            DataCollectionError: If API request fails
        """
        try:
            logger.debug(f"Querying Overpass API for admin boundaries...")
            
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
            
            logger.info(f"Overpass API returned {len(features)} administrative boundaries")
            
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
            
            # Extract administrative level and name
            admin_level = tags.get("admin_level", "")
            
            # Map admin_level to region type
            admin_type_map = {
                "2": "country",
                "4": "state",
                "6": "county",
                "8": "municipality",
                "10": "locality"
            }
            admin_type = admin_type_map.get(admin_level, "region")
            
            # Create feature
            feature = {
                "id": f"osm_admin_{element_id}",
                "geometry": geojson_geometry,
                "properties": {
                    "osm_id": element_id,
                    "osm_type": element_type,
                    "name": tags.get("name", ""),
                    "admin_level": admin_level,
                    "admin_type": admin_type,
                    "iso_3166_1_alpha2": tags.get("ISO3166-1:alpha2", ""),
                    "iso_3166_2": tags.get("ISO3166-2", ""),
                    "source": "osm"
                }
            }
            
            features.append(feature)
        
        return features
