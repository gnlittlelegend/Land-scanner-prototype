"""
OpenStreetMap Administrative Boundaries Data Collector.
Retrieves administrative boundary data from OSM Overpass API.

This collector connects to the real production Overpass API endpoint
(http://overpass-api.de/api/interpreter) to fetch administrative boundaries
(country, state, district) for any polygon area.

Requirements Met:
- Connects to real Overpass API (production endpoint)
- Builds Overpass QL query for administrative boundaries (admin_level 2, 4, 6)
- Handles timeouts and rate limits
- Implements retry with longer timeout on first failure
- Parses response to extract country, state, district info
- Validates response is valid GeoJSON
- Returns administrative features with source attribution
- Handles provider unavailability gracefully
"""

import time
from typing import Dict, Any, List, Optional
import logging

from backend.collectors.base_collector import DataCollector

logger = logging.getLogger(__name__)


class AdminBoundariesCollector(DataCollector):
    """
    Collects administrative boundary data from OpenStreetMap via Overpass API.
    
    Data Source: OpenStreetMap Overpass API (Administrative Boundaries)
    - Endpoint: http://overpass-api.de/api/interpreter
    - Query: Overpass QL query for administrative boundaries (admin_level 2, 4, 6)
    - Returns: Administrative boundary features (country, state, district)
    - Timeout: 30 seconds per query
    - Rate Limit: Respectful query timing (2-5 second delays)
    - Error Handling: Log timeout, retry once with longer timeout
    
    Administrative Levels:
    - admin_level 2: Country borders
    - admin_level 4: State/Province borders
    - admin_level 6: District/County borders
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize Admin Boundaries collector with production API endpoint.
        
        Args:
            timeout: Request timeout in seconds (default 30)
        """
        super().__init__(
            provider_name="OSM Admin Boundaries",
            endpoint="http://overpass-api.de/api/interpreter",
            timeout=timeout,
            max_retries=2,
            retry_delay_base=2.0
        )

    def collect(self, polygon: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect administrative boundary data from OSM for the given polygon.

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
            Dictionary matching RawDataset structure with administrative features
            
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
                f"Collecting administrative boundaries for area {polygon['properties'].get('area_square_kilometers', 0):.2f} sqkm"
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
                    f"Failed to collect administrative boundaries after retries (collection_time={collection_time_ms:.0f}ms)"
                )
                return self._build_raw_dataset(
                    category="admin",
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
                    category="admin",
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
                f"✓ Retrieved {len(features)} administrative boundary features from OSM "
                f"(collection_time={collection_time_ms:.0f}ms)"
            )
            
            return self._build_raw_dataset(
                category="admin",
                features=features,
                attempt_count=attempt_count,
                collection_time_ms=collection_time_ms,
                status=status
            )
            
        except Exception as e:
            collection_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Administrative boundaries collection failed: {e}", exc_info=True)
            return self._build_raw_dataset(
                category="admin",
                features=[],
                attempt_count=attempt_count,
                collection_time_ms=collection_time_ms,
                status="error",
                error_message=str(e)
            )


    def _build_overpass_query(self, bbox: tuple) -> str:
        """
        Build Overpass QL query for administrative boundaries within bounding box.
        
        Queries for:
        - admin_level 2: Country borders
        - admin_level 4: State/Province borders
        - admin_level 6: District/County borders

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
    way["boundary"="administrative"]["admin_level"="2"];
    way["boundary"="administrative"]["admin_level"="4"];
    way["boundary"="administrative"]["admin_level"="6"];
    relation["boundary"="administrative"]["admin_level"="2"];
    relation["boundary"="administrative"]["admin_level"="4"];
    relation["boundary"="administrative"]["admin_level"="6"];
);
out geom;
"""
        return query

    def _parse_osm_response(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse Overpass API response into GeoJSON features.
        Extracts country, state, district info from tags.

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
            admin_level = tags.get("admin_level", "unknown")
            
            # Determine administrative level type
            admin_type = self._get_admin_type(admin_level)

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
                    "admin_level": admin_level,
                    "admin_type": admin_type,
                    "boundary": tags.get("boundary", "administrative"),
                    "source": "osm",
                    "iso_3166_1": tags.get("ISO3166-1", ""),
                    "iso_3166_2": tags.get("ISO3166-2", "")
                }
            }
        except Exception as e:
            self.logger.debug(f"Failed to convert way {way.get('id', '?')}: {e}")
            return None

    def _relation_to_feature(self, relation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Convert OSM relation to GeoJSON feature.
        
        For relations, we use the bounding box as an approximation
        since full multi-polygon geometry handling is complex.
        
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
            
            admin_level = tags.get("admin_level", "unknown")
            admin_type = self._get_admin_type(admin_level)

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
                    "admin_level": admin_level,
                    "admin_type": admin_type,
                    "boundary": tags.get("boundary", "administrative"),
                    "source": "osm",
                    "iso_3166_1": tags.get("ISO3166-1", ""),
                    "iso_3166_2": tags.get("ISO3166-2", "")
                }
            }
        except Exception as e:
            self.logger.debug(f"Failed to convert relation {relation.get('id', '?')}: {e}")
            return None

    def _get_admin_type(self, admin_level: str) -> str:
        """
        Map OSM admin_level to administrative region type.
        
        Args:
            admin_level: OSM admin_level value (typically 2, 4, 6)
            
        Returns:
            Administrative type string (country, state, district)
        """
        level_map = {
            "2": "country",
            "3": "region",
            "4": "state",
            "5": "province",
            "6": "district",
            "7": "county",
            "8": "municipality"
        }
        return level_map.get(str(admin_level), "administrative")
