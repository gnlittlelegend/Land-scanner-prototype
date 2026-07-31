"""
OpenStreetMap Buildings Data Collector.
Retrieves building footprint data from OSM Overpass API.
"""

import requests
from typing import Dict, Any, List
import logging

from backend.models.schemas import Polygon, RawDataset, DataCategory
from backend.collectors.base_collector import DataCollector, DataCollectorError


logger = logging.getLogger(__name__)


class OSMBuildingsCollector(DataCollector):
    """Collects building footprint data from OpenStreetMap."""

    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self, timeout_seconds: int = 30):
        """Initialize OSM Buildings collector."""
        super().__init__(
            provider_name="osm_buildings",
            category=DataCategory.BUILDINGS,
            timeout_seconds=timeout_seconds
        )

    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect building data from OSM for the given polygon.

        Args:
            polygon: Validated polygon defining area of interest

        Returns:
            RawDataset with building features

        Raises:
            DataCollectorError: If collection fails
        """
        try:
            logger.info(f"Collecting OSM buildings for polygon area {polygon.area_sqkm:.2f} sqkm")

            # Build Overpass QL query
            bbox = self._get_bbox_string(polygon)
            query = self._build_overpass_query(bbox)

            # Query Overpass API
            response = requests.post(
                self.OVERPASS_API_URL,
                data=query,
                timeout=self.timeout_seconds
            )

            if response.status_code != 200:
                raise DataCollectorError(
                    f"OSM Overpass API returned status {response.status_code}: {response.text[:200]}"
                )

            # Parse response
            data = response.json()
            features = self._parse_osm_response(data)

            logger.info(f"Retrieved {len(features)} building features from OSM")

            return self._build_raw_dataset(
                features=features,
                geometry_type="Polygon",
                metadata={"version": "1.0", "api": "overpass"}
            )

        except requests.Timeout:
            raise DataCollectorError(f"OSM API timeout after {self.timeout_seconds}s")
        except requests.RequestException as e:
            raise DataCollectorError(f"OSM API request failed: {str(e)}")
        except Exception as e:
            raise DataCollectorError(f"OSM buildings collection failed: {str(e)}")

    def _get_bbox_string(self, polygon: Polygon) -> str:
        """
        Convert polygon bounding box to Overpass bbox format (south, west, north, east).

        Args:
            polygon: Polygon with bounding box

        Returns:
            Bbox string in format "south,west,north,east"
        """
        minx, miny, maxx, maxy = polygon.bounding_box
        # Overpass uses (south, west, north, east) = (miny, minx, maxy, maxx)
        return f"{miny},{minx},{maxy},{maxx}"

    def _build_overpass_query(self, bbox: str) -> str:
        """
        Build Overpass QL query for buildings.

        Args:
            bbox: Bounding box in format "south,west,north,east"

        Returns:
            Overpass QL query string
        """
        query = f"""
        [bbox:{bbox}];
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

            for element in elements:
                if element["type"] == "way":
                    feature = self._way_to_feature(element)
                    if feature:
                        features.append(feature)
                elif element["type"] == "relation":
                    feature = self._relation_to_feature(element)
                    if feature:
                        features.append(feature)

        except Exception as e:
            logger.warning(f"Error parsing OSM response: {str(e)}")

        return features

    def _way_to_feature(self, way: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OSM way to GeoJSON feature."""
        try:
            if "geometry" not in way or len(way["geometry"]) < 3:
                return None

            coords = [[geom["lon"], geom["lat"]] for geom in way["geometry"]]
            # Close the ring if not already closed
            if coords[0] != coords[-1]:
                coords.append(coords[0])

            tags = way.get("tags", {})

            return {
                "id": f"way_{way['id']}",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "properties": {
                    "name": tags.get("name", ""),
                    "type": tags.get("building", "yes"),
                    "osm_id": way["id"],
                    "osm_type": "way"
                }
            }
        except Exception as e:
            logger.debug(f"Failed to convert way {way.get('id', '?')}: {str(e)}")
            return None

    def _relation_to_feature(self, relation: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OSM relation to GeoJSON feature (simplified)."""
        try:
            # For relations, we'll use bounds as a simple approximation
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
                "id": f"relation_{relation['id']}",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "properties": {
                    "name": tags.get("name", ""),
                    "type": tags.get("building", "yes"),
                    "osm_id": relation["id"],
                    "osm_type": "relation"
                }
            }
        except Exception as e:
            logger.debug(f"Failed to convert relation {relation.get('id', '?')}: {str(e)}")
            return None
