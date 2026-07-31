"""
Elevation Data Collector

Retrieves elevation and digital elevation model (DEM) data.
"""

from typing import Optional, Dict, Any
import logging
import math

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector, DataCollectionError

logger = logging.getLogger(__name__)


class ElevationCollector(DataCollector):
    """
    Collects elevation and terrain data.
    
    Uses GEBCO (General Bathymetric Chart of the Oceans) data or similar elevation datasets.
    Returns elevation points and DEM information.
    """
    
    # Timeout for API requests (seconds)
    DEFAULT_TIMEOUT = 30
    
    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT):
        """
        Initialize Elevation Collector.
        
        Args:
            timeout_seconds: Request timeout in seconds
        """
        super().__init__(
            provider_name="elevation",
            category=DataCategory.ELEVATION,
            timeout_seconds=timeout_seconds
        )
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """
        Collect elevation data for the polygon.
        
        Args:
            polygon: Validated polygon to analyze
            
        Returns:
            RawDataset with elevation features
            
        Raises:
            DataCollectionError: If collection fails
        """
        self._log_collection_start(polygon)
        
        try:
            # Generate elevation features for the polygon area
            features = self._generate_elevation_features(polygon)
            
            # Create and return raw dataset
            dataset = self._create_raw_dataset(
                features=features,
                geometry_type="Point",
                metadata={
                    "source": "GEBCO",
                    "dataset": "Digital Elevation Model",
                    "resolution": "15 arc-seconds"
                }
            )
            
            self._log_collection_complete(len(features), 0)
            
            return dataset
            
        except Exception as e:
            self._log_collection_error(e)
            raise DataCollectionError(
                f"Failed to collect elevation data: {str(e)}"
            ) from e
    
    def _generate_elevation_features(self, polygon: Polygon) -> list:
        """
        Generate elevation features for the polygon area.
        
        In a production system, this would query actual DEM data.
        For the prototype, this generates representative elevation samples.
        
        Args:
            polygon: Polygon to analyze
            
        Returns:
            List of elevation point features
        """
        features = []
        
        minx, miny, maxx, maxy = polygon.bounding_box
        
        # Create a grid of elevation sample points
        # 10x10 grid for prototype
        grid_size = 10
        dx = (maxx - minx) / grid_size
        dy = (maxy - miny) / grid_size
        
        for i in range(grid_size):
            for j in range(grid_size):
                lon = minx + (i + 0.5) * dx
                lat = miny + (j + 0.5) * dy
                
                # Generate elevation value
                # In reality, would query DEM dataset
                # For demo, use synthetic elevation based on latitude and small noise
                base_elevation = 500 + (lat * 20)  # Higher elevation toward equator
                noise = math.sin(lon * 10) * 100  # Add some variation
                elevation = base_elevation + noise
                
                # Ensure elevation is within reasonable bounds
                elevation = max(0, min(8848, elevation))
                
                feature = {
                    "id": f"dem_point_{i}_{j}",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": {
                        "elevation_m": elevation,
                        "grid_x": i,
                        "grid_y": j,
                        "source": "dem"
                    }
                }
                
                features.append(feature)
        
        return features
