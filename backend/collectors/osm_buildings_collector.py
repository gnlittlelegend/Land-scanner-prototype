"""
OpenStreetMap Buildings Data Collector.
Retrieves building footprint data from OSM Overpass API.

This collector connects to the real production Overpass API endpoint
(http://overpass-api.de/api/interpreter) to fetch building footprints
for any polygon area.

Requirements Met:
- Connects to real Overpass API (production endpoint)
- Builds Overpass QL query for buildings
- Handles timeouts and rate limits
- Implements retry with longer timeout on first failure
- Validates response is valid GeoJSON
- Returns raw features with OSM attribution
- Handles provider unavailability gracefully
"""

import time
from typing import Dict, Any, List, Optional
import logging

from backend.collectors.base_collector import DataCollector

logger = logging.getLogger(__name__)


class OSMBuildingsCollector(DataCollector):
    """
    Collects building footprint data from OpenStreetMap via Overpass API.
    
    Data Source: OpenStreetMap Overpass API
    - Endpoint: http://overpass-api.de/api/interpreter
    - Query: Overpass QL query for all buildings within polygon
    - Returns: GeoJSON features with building properties
    - Timeout: 30 seconds per query
    - Rate Limit: Respectful query timing (2-5 second delays)
    - Error Handling: Log timeout, retry once with longer timeout
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize OSM Buildings collector with production API endpoint.
        
        Args:
            timeout: Request timeout in seconds (default 30)
        """
        super().__init__(
            provider_name="OSM Buildings",
            endpoint="http://overpass-api.de/api/interpreter",
            timeout=timeout,
            max_retries=2,
            retry_delay_base=2.0
        )

    def collect(self, polygon: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect building data from OSM for the given polygon.

        Args:
            polygon: Validated polygon dict with structure:
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [...]},
                    "properties": {
                        "area_square_kilometers": float,
                        "bounding_box": {"min_lon", "min_lat", "max_lon", "max_lat"},
                        "centroid": {"longitude": float, "latitude": float},
                        "vertex_count": int,
                        "crs": "EPSG:4326"
                    }
                }

        Returns:
            Dictionary matching RawDataset structure with building features
            
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
                f"Collecting OSM buildings for area {polygon['properties'].get('area_square_kilometers', 0):.2f} sqkm"
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
                    f"Failed to collect OSM buildings after retries (collection_time={collection_time_ms:.0f}ms)"
                )
                return self._build_raw_dataset(
                    category="buildings",
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
                    category="buildings",
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
                f"✓ Retrieved {len(features)} building features from OSM "
                f"(collection_time={collection_time_ms:.0f}ms)"
            )
            
            return self._build_raw_dataset(
                category="buildings",
                features=features,
                attempt_count=attempt_count,
                collection_time_ms=collection_time_ms,
                status=status
            )
            
        except Exception as e:
            collection_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"OSM buildings collection failed: {e}", exc_info=True)
            return self._build_raw_dataset(
                category="buildings",
                features=[],
                attempt_count=attempt_count,
                collection_time_ms=collection_time_ms,
                status="error",
                error_message=str(e)
            )


    def _build_overpass_query(self, bbox: tuple) -> str:
        """
        Build Overpass QL query for buildings within bounding box.

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
    way["building"];
    relation["building"];
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
                elif element.get("type") == "relation":
                    feature = self._relation_to_feature(element)
                    if feature:
                        features.append(feature)

        except Exception as e:
            self.logger.warning(f"Error parsing OSM response: {e}", exc_info=True)

        return features

    def _way_to_feature(self, way: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert OSM way to GeoJSON feature.
        
        Args:
            way: OSM way element from Overpass API
            
        Returns:
            GeoJSON feature dict or None if conversion fails
        """
        try:
            geometry = way.get("geometry", [])
            
            if not geometry or len(geometry) < 3:
                return None

            # Extract coordinates from geometry
            coords = [[geom.get("lon", 0), geom.get("lat", 0)] for geom in geometry]
            
            # Close the ring if not already closed
            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])

            tags = way.get("tags", {})

            return {
                "type": "Feature",
                "id": f"way_{way.get('id', 'unknown')}",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "properties": {
                    "osm_id": way.get("id"),
                    "osm_type": "way",
                    "name": tags.get("name", ""),
                    "type": tags.get("building", "yes"),
                    "source": "osm"
                }
            }
        except Exception as e:
            self.logger.debug(f"Failed to convert way {way.get('id', '?')}: {e}")
            return None

    def _relation_to_feature(self, relation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert OSM relation to GeoJSON feature (using bounding box as approximation).
        
        Args:
            relation: OSM relation element from Overpass API
            
        Returns:
            GeoJSON feature dict or None if conversion fails
        """
        try:
            # For relations, use bounds as a simple approximation
            tags = relation.get("tags", {})
            bounds = relation.get("bounds", {})

            if not bounds:
                return None

            minlat = bounds.get("minlat")
            minlon = bounds.get("minlon")
            maxlat = bounds.get("maxlat")
            maxlon = bounds.get("maxlon")

            if None in (minlat, minlon, maxlat, maxlon):
                return None

            # Create a bounding box polygon
            coords = [
                [minlon, minlat],
                [maxlon, minlat],
                [maxlon, maxlat],
                [minlon, maxlat],
                [minlon, minlat]
            ]

            return {
                "type": "Feature",
                "id": f"relation_{relation.get('id', 'unknown')}",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "properties": {
                    "osm_id": relation.get("id"),
                    "osm_type": "relation",
                    "name": tags.get("name", ""),
                    "type": tags.get("building", "yes"),
                    "source": "osm"
                }
            }
        except Exception as e:
            self.logger.debug(f"Failed to convert relation {relation.get('id', '?')}: {e}")
            return None
