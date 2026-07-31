"""
Road Network Data Collector.
Retrieves road network data from OpenStreetMap.
"""

import requests
from typing import Dict, Any, List
import logging

from backend.models.schemas import Polygon, RawDataset, DataCategory
from backend.collectors.base_collector import DataCollector, DataCollectorError


logger = logging.getLogger(__name__)


class RoadNetworkCollector(DataCollector):
    """Collects road network data from OpenStreetMap."""

    OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"

    def __init__(self, timeout_seconds: int = 30):
        """Initialize Road Network collector."""
        super().__init__(
            provider_name="road_network",
            category=DataCategory.ROADS,
            timeout_seconds=timeout_seconds
        )

    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect road network data for the given polygon.

        Args:
            polygon: Validated polygon defining area of interest

        Returns:
            RawDataset with road features

        Raises:
            DataCollectorError: If collection fails
        """
        try:
            logger.info(f"Collecting road network for polygon area {polygon.area_sqkm:.2f} sqkm")

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

            logger.info(f"Retrieved {len(features)} road features from OSM")

            return self._build_raw_dataset(
                features=features,
                geometry_type="LineString",
                metadata={"version": "1.0", "api": "overpass"}
            )

        except requests.Timeout:
            raise DataCollectorError(f"Overpass API timeout after {self.timeout_seconds}s")
        except requests.RequestException as e:
            raise DataCollectorError(f"Overpass API request failed: {str(e)}")
        except Exception as e:
            raise DataCollectorError(f"Road network collection failed: {str(e)}")

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
        Build Overpass QL query for roads.

        Args:
            bbox: Bounding box in format "south,west,north,east"

        Returns:
            Overpass QL query string
        """
        query = f"""
        [bbox:{bbox}];
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

            for element in elements:
                if element["type"] == "way":
                    feature = self._way_to_feature(element)
                    if feature:
                        features.append(feature)

        except Exception as e:
            logger.warning(f"Error parsing road network response: {str(e)}")

        return features

    def _way_to_feature(self, way: Dict[str, Any]) -> Dict[str, Any]:
        """Convert OSM way to GeoJSON LineString feature."""
        try:
            if "geometry" not in way or len(way["geometry"]) < 2:
                return None

            coords = [[geom["lon"], geom["lat"]] for geom in way["geometry"]]

            tags = way.get("tags", {})
            highway_type = tags.get("highway", "road")

            return {
                "id": f"road_{way['id']}",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                },
                "properties": {
                    "name": tags.get("name", ""),
                    "type": highway_type,
                    "surface": tags.get("surface", "unknown"),
                    "lanes": tags.get("lanes", 1),
                    "osm_id": way["id"]
                }
            }
        except Exception as e:
            logger.debug(f"Failed to convert road way {way.get('id', '?')}: {str(e)}")
            return None
