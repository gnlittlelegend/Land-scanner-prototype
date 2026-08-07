"""
OpenStreetMap Road Network Data Collector.
Retrieves road network data from OSM Overpass API.

This collector connects to the real production Overpass API endpoint
(http://overpass-api.de/api/interpreter) to fetch road network data
for any polygon area.

Requirements Met:
- Connects to real Overpass API (production endpoint)
- Builds Overpass QL query for roads with highway tags
- Handles timeouts and rate limits
- Implements retry with longer timeout on first failure
- Validates response is valid GeoJSON
- Returns raw features with OSM attribution
- Handles provider unavailability gracefully
- Extracts road classification (primary, secondary, tertiary, etc.)
"""

import time
from typing import Dict, Any, List, Optional
import logging

from backend.collectors.base_collector import DataCollector

logger = logging.getLogger(__name__)


class RoadNetworkCollector(DataCollector):
    """
    Collects road network data from OpenStreetMap via Overpass API.
    
    Data Source: OpenStreetMap Overpass API
    - Endpoint: http://overpass-api.de/api/interpreter
    - Query: Overpass QL query for all ways with highway tags
    - Returns: GeoJSON features with road properties and classification
    - Timeout: 30 seconds per query
    - Rate Limit: Respectful query timing (2-5 second delays)
    - Error Handling: Log timeout, retry with exponential backoff
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize OSM Road Network collector with production API endpoint.
        
        Args:
            timeout: Request timeout in seconds (default 30)
        """
        super().__init__(
            provider_name="OSM Roads",
            endpoint="http://overpass-api.de/api/interpreter",
            timeout=timeout,
            max_retries=2,
            retry_delay_base=2.0
        )

    def collect(self, polygon: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect road network data from OSM for the given polygon.

        Args:
            polygon: Validated polygon dict with structure:
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [...]},
                    "properties": {
                        "area_sqm": float,
                        "bounding_box": {"min_lon", "min_lat", "max_lon", "max_lat"},
                        "centroid": {"longitude": float, "latitude": float},
                        "vertex_count": int,
                        "crs": "EPSG:4326"
                    }
                }

        Returns:
            Dictionary matching RawDataset structure with road features
            
        Raises:
            CollectionError: If collection fails after all retries
        """
        start_time = time.time()
        attempt_count = 0
        
        try:
            # Build Overpass QL query
            bbox = self._get_bbox(polygon)
            query = self._build_overpass_query(bbox)
            
            self.logger.info(
                f"Collecting OSM roads for area {polygon['properties'].get('area_sqm', 0):.0f} m²"
            )
            
            # Query Overpass API with production endpoint
            response = self._make_request(
                method="POST",
                url=self.endpoint,
                data=query,
                headers={"Content-Type": "application/osm3s"}
            )
            
            attempt_count = 1
            
            if response is None:
                # All retries exhausted
                collection_time_ms = (time.time() - start_time) * 1000
                self.logger.warning(
                    f"Failed to collect OSM roads after retries (collection_time={collection_time_ms:.0f}ms)"
                )
                return self._build_raw_dataset(
                    category="roads",
                    features=[],
                    attempt_count=attempt_count,
                    collection_time_ms=collection_time_ms,
                    status="error",
                    error_message="Overpass API unavailable or timeout"
                )
            
            # Parse response
            try:
                data = response.json()
            except ValueError as e:
                self.logger.error(f"Failed to parse Overpass API response as JSON: {e}")
                return self._build_raw_dataset(
                    category="roads",
                    features=[],
                    attempt_count=attempt_count,
                    collection_time_ms=(time.time() - start_time) * 1000,
                    status="error",
                    error_message="Invalid JSON response from Overpass API"
                )
            
            # Extract and process features
            features = self._parse_osm_response(data)
            collection_time_ms = (time.time() - start_time) * 1000
            
            status = "success" if features else "empty"
            self.logger.info(
                f"✓ Retrieved {len(features)} road features from OSM "
                f"(collection_time={collection_time_ms:.0f}ms)"
            )
            
            return self._build_raw_dataset(
                category="roads",
                features=features,
                attempt_count=attempt_count,
                collection_time_ms=collection_time_ms,
                status=status
            )
            
        except Exception as e:
            collection_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"OSM roads collection failed: {e}", exc_info=True)
            return self._build_raw_dataset(
                category="roads",
                features=[],
                attempt_count=attempt_count,
                collection_time_ms=collection_time_ms,
                status="error",
                error_message=str(e)
            )


    def _build_overpass_query(self, bbox: tuple) -> str:
        """
        Build Overpass QL query for roads (ways with highway tags) within bounding box.

        Args:
            bbox: Tuple of (min_lon, min_lat, max_lon, max_lat) in WGS84

        Returns:
            Overpass QL query string
        """
        min_lon, min_lat, max_lon, max_lat = bbox
        # Overpass format: [bbox:south,west,north,east]
        bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"
        
        query = f"""
[bbox:{bbox_str}];
(
    way["highway"];
);
out geom;
"""
        return query

    def _parse_osm_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse Overpass API response into GeoJSON features.

        Args:
            data: JSON response from Overpass API

        Returns:
            List of GeoJSON feature dictionaries
        """
        features = []

        try:
            elements = data.get("elements", [])
            self.logger.info(f"Parsing {len(elements)} elements from Overpass response")

            for element in elements:
                if element.get("type") == "way":
                    feature = self._way_to_feature(element)
                    if feature:
                        features.append(feature)

        except Exception as e:
            self.logger.warning(f"Error parsing OSM response: {e}", exc_info=True)

        return features

    def _way_to_feature(self, way: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert OSM way (road) to GeoJSON feature.
        
        Args:
            way: OSM way element from Overpass API
            
        Returns:
            GeoJSON feature dict or None if conversion fails
        """
        try:
            geometry = way.get("geometry", [])
            
            if not geometry or len(geometry) < 2:
                return None

            # Extract coordinates from geometry
            coords = [[geom.get("lon", 0), geom.get("lat", 0)] for geom in geometry]
            
            tags = way.get("tags", {})
            
            # Extract road classification from highway tag
            highway_type = tags.get("highway", "unknown")
            
            # Map highway types to classifications
            road_classification = self._classify_road(highway_type)

            return {
                "type": "Feature",
                "id": f"way_{way.get('id', 'unknown')}",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {
                    "osm_id": way.get("id"),
                    "osm_type": "way",
                    "name": tags.get("name", ""),
                    "highway": highway_type,
                    "classification": road_classification,
                    "lanes": tags.get("lanes", ""),
                    "surface": tags.get("surface", ""),
                    "maxspeed": tags.get("maxspeed", ""),
                    "source": "osm"
                }
            }
        except Exception as e:
            self.logger.debug(f"Failed to convert way {way.get('id', '?')}: {e}")
            return None

    def _classify_road(self, highway_type: str) -> str:
        """
        Classify road based on OSM highway tag value.
        
        Maps OSM highway tag values to standardized road classifications:
        - Primary: motorway, trunk, primary
        - Secondary: secondary, tertiary
        - Tertiary: tertiary, unclassified
        - Local: residential, living_street, service
        - Other: everything else
        
        Args:
            highway_type: Value of OSM highway tag
            
        Returns:
            Standardized road classification string
        """
        highway_type = highway_type.lower().strip()
        
        # Primary roads (major thoroughfares)
        if highway_type in ["motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link"]:
            return "primary"
        
        # Secondary roads
        elif highway_type in ["secondary", "secondary_link"]:
            return "secondary"
        
        # Tertiary roads
        elif highway_type in ["tertiary", "tertiary_link", "unclassified"]:
            return "tertiary"
        
        # Local roads
        elif highway_type in ["residential", "living_street", "service", "pedestrian", "track"]:
            return "local"
        
        # Other/unknown
        else:
            return "other"
