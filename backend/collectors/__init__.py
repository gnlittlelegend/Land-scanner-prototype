"""Data collectors module for provider integration."""

from backend.collectors.base import DataCollector, DataCollectionError
from backend.collectors.osm_buildings import OSMBuildingsCollector
from backend.collectors.admin_boundaries import AdminBoundariesCollector
from backend.collectors.land_cover import LandCoverCollector
from backend.collectors.roads import RoadNetworkCollector
from backend.collectors.water import WaterBodiesCollector
from backend.collectors.elevation import ElevationCollector

__all__ = [
    "DataCollector",
    "DataCollectionError",
    "OSMBuildingsCollector",
    "AdminBoundariesCollector",
    "LandCoverCollector",
    "RoadNetworkCollector",
    "WaterBodiesCollector",
    "ElevationCollector",
]
