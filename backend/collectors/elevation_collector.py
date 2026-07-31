"""
Elevation Data Collector.
Retrieves elevation and DEM data from open sources.
"""

import logging
from typing import Dict, Any, List

from backend.models.schemas import Polygon, RawDataset, DataCategory
from backend.collectors.base_collector import DataCollector, DataCollectorError


logger = logging.getLogger(__name__)


class ElevationCollector(DataCollector):
    """
    Collects elevation data from open DEM sources.
    
    Note: This is a demonstration implementation that generates synthetic
    elevation data based on the polygon area. In production, this would
    query actual raster DEM data from sources like GEBCO, SRTM, or USGS.
    """

    def __init__(self, timeout_seconds: int = 30):
        """Initialize Elevation collector."""
        super().__init__(
            provider_name="elevation",
            category=DataCategory.ELEVATION,
            timeout_seconds=timeout_seconds
        )

    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect elevation data for the given polygon.

        Args:
            polygon: Validated polygon defining area of interest

        Returns:
            RawDataset with elevation features

        Raises:
            DataCollectorError: If collection fails
        """
        try:
            logger.info(f"Collecting elevation data for polygon area {polygon.area_sqkm:.2f} sqkm")

            # Generate synthetic elevation data
            features = self._generate_elevation_features(polygon)

            logger.info(f"Generated {len(features)} elevation data points")

            return self._build_raw_dataset(
                features=features,
                geometry_type="Point",
                metadata={"version": "1.0", "source": "dem_synthetic"}
            )

        except Exception as e:
            raise DataCollectorError(f"Elevation collection failed: {str(e)}")

    def _generate_elevation_features(self, polygon: Polygon) -> List[Dict[str, Any]]:
        """
        Generate synthetic elevation data points within the polygon.

        In a real implementation, this would query raster DEM data and
        return sampled elevation values at regular intervals. For demonstration,
        we create synthetic elevation points.

        Args:
            polygon: Polygon defining area of interest

        Returns:
            List of elevation feature dictionaries
        """
        features = []

        try:
            minx, miny, maxx, maxy = polygon.bounding_box
            centroid_lon, centroid_lat = polygon.centroid
            
            # Create a 5x5 grid of elevation points
            lon_step = (maxx - minx) / 5
            lat_step = (maxy - miny) / 5

            feature_id = 0
            for i in range(5):
                for j in range(5):
                    lon = minx + (i * lon_step) + (lon_step / 2)
                    lat = miny + (j * lat_step) + (lat_step / 2)

                    # Generate synthetic elevation based on distance from centroid
                    # This creates a simple hill-like elevation pattern
                    dist_lon = (lon - centroid_lon) * 111  # approximate km per degree
                    dist_lat = (lat - centroid_lat) * 111
                    distance = (dist_lon**2 + dist_lat**2) ** 0.5

                    # Base elevation with distance-based variation
                    base_elevation = 500
                    elevation = max(0, base_elevation - (distance * 50))  # 50m drop per km
                    
                    # Add some random-like variation
                    variation = ((i * 7 + j * 11) % 100) * 5
                    elevation = elevation + variation

                    feature = {
                        "id": f"dem_{feature_id}",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        },
                        "properties": {
                            "elevation_m": round(elevation, 1),
                            "source": "dem_synthetic",
                            "confidence": 0.85
                        }
                    }
                    features.append(feature)
                    feature_id += 1

        except Exception as e:
            logger.warning(f"Error generating elevation features: {str(e)}")

        return features
