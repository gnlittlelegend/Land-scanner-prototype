"""
Mock Data Collector for Development and Testing

Generates realistic test data without requiring external APIs.
Useful for:
- Testing pipeline when APIs are unavailable/slow
- Development and debugging
- UI/UX iteration
- Performance testing

Each mock collector generates synthetic data that matches the expected format
of real collectors, allowing testing the entire pipeline end-to-end.
"""

from typing import Dict, Any, List
from datetime import datetime
import logging
import random

from backend.models import Polygon, RawDataset, DataCategory
from backend.collectors.base import DataCollector

logger = logging.getLogger(__name__)


class MockCollector(DataCollector):
    """Base mock collector that generates test data."""
    
    def __init__(self, provider_name: str, category: DataCategory, timeout_seconds: int = 1):
        """
        Initialize mock collector.
        
        Args:
            provider_name: Name of this mock provider
            category: Data category
            timeout_seconds: Fake timeout (always fast)
        """
        super().__init__(provider_name, category, timeout_seconds)
    
    def collect(self, polygon: Polygon) -> RawDataset:
        """Generate mock data for the polygon."""
        self._log_collection_start(polygon)
        
        features = self._generate_mock_features(polygon)
        
        dataset = self._create_raw_dataset(
            features=features,
            geometry_type=self._get_geometry_type(),
            metadata={
                "note": f"Mock data generated for testing ({self.provider_name})",
                "polygon_area_sqkm": polygon.area_sqkm,
                "generated_at": datetime.utcnow().isoformat()
            }
        )
        
        self._log_collection_complete(len(features), 0)
        return dataset
    
    def _generate_mock_features(self, polygon: Polygon) -> List[Dict[str, Any]]:
        """Generate mock features within polygon bounds. Override in subclasses."""
        raise NotImplementedError()
    
    def _get_geometry_type(self) -> str:
        """Return the geometry type for this category."""
        return "Polygon"


class MockBuildingsCollector(MockCollector):
    """Mock buildings collector - generates synthetic building data."""
    
    def __init__(self, timeout_seconds: int = 1):
        super().__init__("mock_buildings", DataCategory.BUILDINGS, timeout_seconds)
    
    def _generate_mock_features(self, polygon: Polygon) -> List[Dict[str, Any]]:
        """Generate mock building features."""
        minx, miny, maxx, maxy = polygon.bounding_box
        features = []
        
        # Generate 8-15 random buildings in the polygon area
        num_buildings = random.randint(8, 15)
        
        for i in range(num_buildings):
            lon = minx + random.random() * (maxx - minx)
            lat = miny + random.random() * (maxy - miny)
            
            # Random building properties
            building_types = ["residential", "commercial", "office", "industrial", "apartment", "house"]
            materials = ["brick", "concrete", "steel", "wood", "glass"]
            
            features.append({
                "id": f"mock_building_{i}",
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon, lat],
                        [lon + 0.0005, lat],
                        [lon + 0.0005, lat + 0.0005],
                        [lon, lat + 0.0005],
                        [lon, lat]
                    ]]
                },
                "properties": {
                    "name": f"Building {i+1}",
                    "building_type": random.choice(building_types),
                    "levels": random.randint(1, 20),
                    "material": random.choice(materials),
                    "year_built": random.randint(1950, 2024),
                    "source": "mock_data"
                }
            })
        
        return features


class MockRoadsCollector(MockCollector):
    """Mock roads collector - generates synthetic road data."""
    
    def __init__(self, timeout_seconds: int = 1):
        super().__init__("mock_roads", DataCategory.ROADS, timeout_seconds)
    
    def _get_geometry_type(self) -> str:
        return "LineString"
    
    def _generate_mock_features(self, polygon: Polygon) -> List[Dict[str, Any]]:
        """Generate mock road features."""
        minx, miny, maxx, maxy = polygon.bounding_box
        features = []
        
        # Generate 5-10 random roads
        num_roads = random.randint(5, 10)
        road_types = ["motorway", "primary", "secondary", "residential", "service"]
        
        for i in range(num_roads):
            # Random start and end points
            start_lon = minx + random.random() * (maxx - minx)
            start_lat = miny + random.random() * (maxy - miny)
            end_lon = minx + random.random() * (maxx - minx)
            end_lat = miny + random.random() * (maxy - miny)
            
            features.append({
                "id": f"mock_road_{i}",
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [start_lon, start_lat],
                        [end_lon, end_lat]
                    ]
                },
                "properties": {
                    "name": f"Road {i+1}",
                    "road_type": random.choice(road_types),
                    "lanes": random.randint(1, 6),
                    "surface": random.choice(["asphalt", "concrete", "gravel"]),
                    "source": "mock_data"
                }
            })
        
        return features


class MockLandCoverCollector(MockCollector):
    """Mock land cover collector - generates synthetic land cover data."""
    
    def __init__(self, timeout_seconds: int = 1):
        super().__init__("mock_land_cover", DataCategory.LAND_COVER, timeout_seconds)
    
    def _generate_mock_features(self, polygon: Polygon) -> List[Dict[str, Any]]:
        """Generate mock land cover features."""
        minx, miny, maxx, maxy = polygon.bounding_box
        features = []
        
        # Generate grid of land cover points
        step = (maxx - minx) / 5
        lc_classes = [
            ("tree_cover", 10),
            ("herbaceous_vegetation", 30),
            ("cropland", 40),
            ("built_up", 50),
            ("bare_ground", 60),
            ("water", 80)
        ]
        
        point_id = 0
        for lon in [minx + i * step for i in range(6)]:
            for lat in [miny + i * step for i in range(6)]:
                lc_class, code = random.choice(lc_classes)
                
                features.append({
                    "id": f"mock_lc_{point_id}",
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": {
                        "lc_code": code,
                        "lc_class": lc_class,
                        "confidence": random.uniform(0.7, 1.0),
                        "year": 2023,
                        "source": "mock_data"
                    }
                })
                point_id += 1
        
        return features


class MockWaterCollector(MockCollector):
    """Mock water bodies collector - generates synthetic water feature data."""
    
    def __init__(self, timeout_seconds: int = 1):
        super().__init__("mock_water", DataCategory.WATER, timeout_seconds)
    
    def _generate_mock_features(self, polygon: Polygon) -> List[Dict[str, Any]]:
        """Generate mock water features."""
        minx, miny, maxx, maxy = polygon.bounding_box
        features = []
        
        # Generate 2-5 random water bodies
        num_water = random.randint(2, 5)
        water_types = ["river", "lake", "pond", "canal", "stream"]
        
        for i in range(num_water):
            lon = minx + random.random() * (maxx - minx)
            lat = miny + random.random() * (maxy - miny)
            
            features.append({
                "id": f"mock_water_{i}",
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [lon - 0.0003, lat - 0.0003],
                        [lon + 0.0003, lat - 0.0003],
                        [lon + 0.0003, lat + 0.0003],
                        [lon - 0.0003, lat + 0.0003],
                        [lon - 0.0003, lat - 0.0003]
                    ]]
                },
                "properties": {
                    "name": f"Water {i+1}",
                    "water_type": random.choice(water_types),
                    "flow_direction": random.choice(["north", "south", "east", "west", "unknown"]),
                    "source": "mock_data"
                }
            })
        
        return features


class MockAdminCollector(MockCollector):
    """Mock administrative boundaries collector - generates synthetic admin data."""
    
    def __init__(self, timeout_seconds: int = 1):
        super().__init__("mock_admin", DataCategory.ADMIN, timeout_seconds)
    
    def _generate_mock_features(self, polygon: Polygon) -> List[Dict[str, Any]]:
        """Generate mock administrative boundary features."""
        features = []
        
        # Generate 1-3 administrative regions
        num_admin = random.randint(1, 3)
        admin_types = ["country", "state", "province", "district"]
        
        for i in range(num_admin):
            features.append({
                "id": f"mock_admin_{i}",
                "type": "Feature",
                "geometry": polygon.geojson,  # Use the input polygon as admin boundary
                "properties": {
                    "name": f"Admin Region {i+1}",
                    "admin_level": random.randint(2, 6),
                    "admin_type": random.choice(admin_types),
                    "country": "USA",
                    "population": random.randint(10000, 1000000),
                    "source": "mock_data"
                }
            })
        
        return features


class MockElevationCollector(MockCollector):
    """Mock elevation collector - generates synthetic DEM data."""
    
    def __init__(self, timeout_seconds: int = 1):
        super().__init__("mock_elevation", DataCategory.ELEVATION, timeout_seconds)
    
    def _get_geometry_type(self) -> str:
        return "Point"
    
    def _generate_mock_features(self, polygon: Polygon) -> List[Dict[str, Any]]:
        """Generate mock elevation data points."""
        minx, miny, maxx, maxy = polygon.bounding_box
        features = []
        
        # Generate elevation grid
        step = (maxx - minx) / 8
        point_id = 0
        
        for lon in [minx + i * step for i in range(10)]:
            for lat in [miny + i * step for i in range(10)]:
                # Generate elevation based on "location" (deterministic but variable)
                base_elevation = 100 + (hash((lon, lat)) % 900)  # 100-1000m
                
                features.append({
                    "id": f"mock_elevation_{point_id}",
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "properties": {
                        "elevation_m": float(base_elevation),
                        "confidence": random.uniform(0.8, 0.99),
                        "source": "mock_data",
                        "method": "dem"
                    }
                })
                point_id += 1
        
        return features
