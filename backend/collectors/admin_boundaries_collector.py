"""
Administrative Boundaries Data Collector.
Retrieves administrative region data from OpenStreetMap.
"""

import requests
from typing import Dict, Any, List
import logging

from backend.models.schemas import Polygon, RawDataset, DataCategory
from backend.collectors.base_collector import DataCollector, DataCollectorError


logger = logging.getLogger(__name__)


class AdminBoundariesCollector(DataCollector):
    """Collects administrative boundary data from OpenStreetMap."""

    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self, timeout_seconds: int = 30):
        """Initialize Admin Boundaries collector."""
        super().__init__(
            provider_name="admin_boundaries",
            category=DataCategory.ADMIN,
            timeout_seconds=timeout_seconds
        )

    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect administrative boundary data for the given polygon.

        Args:
            polygon: Validated polygon defining area of interest

        Returns:
            RawDataset with administrative boundary features

        Raises:
            DataCollectorError: If collection fails
        """
        try:
            logger.info(f"Collecting admin boundaries for polygon at {polygon.centroid}")

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
                    f"Overpass API returned status {response.status_code}: {response.text[:200]}"
                )

            # Parse response
            data = response.json()
            features = self._parse_osm_response(data)

            logger.info(f"Retrieved {len(features)} administrative boundaries")

            return self._build_raw_dataset(
                features=features,
                geometry_type="Polygon",
                metadata={"version": "1.0", "api": "overpass"}
            )

        except requests.Timeout:
            raise DataCollectorError(f"Overpass API timeout after {self.timeout_seconds}s")
        except requests.RequestException as e:
            raise DataCollectorError(f"Overpass API request failed: {str(e)}")
        except Exception as e:
            raise DataCollectorError(f"Admin boundaries collection failed: {str(e)}")

    def _get_bbox_string(self, polygon: Polygon) -> str:
        """
        Convert polygon bounding box to Overpass bbox format (south, west, north, east).

        Args:
            polygon: Polygon with bounding box

        Returns:
            Bbox string in format "south,west,north,east"
        """
        minx, miny, maxx, maxy = polygon.bounding_box
        return f"{miny},{minx},{maxy},{maxx}"

    def _build_overpass_query(self, bbox: str) -> str:
        """
        Build Overpass QL query for administrative boundaries.

        Args:
            bbox: Bounding box in format "south,west,north,east"

        Returns:
            Overpass QL query string
        """
        query = f"""
        [bbox:{bbox}];
        (
            relation["boundary"="administrative"]["admin_level"<=6];
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
                if element["type"] == "relation":
                    feature = self._relation_to_feature(element)
                    if feature:
                        features.append(feature)

        except Exception as e:
            logger.warning(f"Error parsing admin boundary response: {str(e)}")

        return features

    def _relation_to_feature(self, relation: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OSM relation to GeoJSON feature."""
        try:
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

            admin_level = tags.get("admin_level", "")
            admin_type_map = {
                "2": "country",
                "3": "macro_region",
                "4": "state",
                "5": "province",
                "6": "district"
            }
            admin_type = admin_type_map.get(admin_level, "administrative")

            return {
                "id": f"admin_{relation['id']}",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                },
                "properties": {
                    "name": tags.get("name", ""),
                    "type": admin_type,
                    "admin_level": admin_level,
                    "country_code": tags.get("ISO3166-1:alpha2", ""),
                    "osm_id": relation["id"]
                }
            }
        except Exception as e:
            logger.debug(f"Failed to convert admin boundary {relation.get('id', '?')}: {str(e)}")
            return None
