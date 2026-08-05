"""
Centralized Test Data Management for Land Scanner

Manages all test fixtures and provider responses to:
- Avoid duplicate real API calls
- Ensure test consistency and reproducibility
- Cache real provider data efficiently
- Track cache hits/misses and API call efficiency
- Support reproducible property-based testing
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Callable, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class DataConsistency(Enum):
    """Enum for data consistency checks."""
    IDENTICAL = "identical"
    EQUIVALENT = "equivalent"
    INCONSISTENT = "inconsistent"


class TestDataManager:
    """
    Centralized manager for all test data.
    
    Handles:
    - Loading and sharing test polygon fixtures
    - Caching real provider API responses
    - Avoiding duplicate API calls
    - Tracking cache efficiency
    - Managing test data lifecycle
    - Validating data consistency
    - Auditing test data usage
    """

    def __init__(self, fixtures_dir: str = "backend/tests/fixtures"):
        """Initialize test data manager."""
        self.fixtures_dir = Path(fixtures_dir)
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (self.fixtures_dir / "provider_responses").mkdir(exist_ok=True)
        
        # Load fixtures
        self.polygons = self._load_polygons()
        self.provider_cache = {}
        self.test_dependencies = {}  # Track which tests need which data
        self.audit_log = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": 0,
            "api_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "provider_calls": {},
            "test_data_usage": {},  # Track which tests used which data
            "data_consistency_checks": []
        }
        
        logger.info(f"TestDataManager initialized with {len(self.polygons)} polygon fixtures")

    def _load_polygons(self) -> Dict[str, Dict[str, Any]]:
        """Load polygon fixtures from fixtures/test_polygons.json"""
        polygons_file = self.fixtures_dir / "test_polygons.json"
        
        if polygons_file.exists():
            with open(polygons_file, 'r') as f:
                data = json.load(f)
                return data.get('polygons', {})
        
        # Return default polygons if file doesn't exist
        return self._get_default_polygons()

    def _get_default_polygons(self) -> Dict[str, Dict[str, Any]]:
        """Return default test polygon fixtures."""
        return {
            "valid_small": {
                "id": "valid_small",
                "area_sqkm": 0.025,
                "location": "Central Park, NYC",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-73.9822, 40.7684],
                        [-73.9549, 40.7684],
                        [-73.9549, 40.8011],
                        [-73.9822, 40.8011],
                        [-73.9822, 40.7684]
                    ]]
                }
            },
            "valid_medium": {
                "id": "valid_medium",
                "area_sqkm": 10.0,
                "location": "Austin, Texas",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-97.7, 30.2],
                        [-97.5, 30.2],
                        [-97.5, 30.4],
                        [-97.7, 30.4],
                        [-97.7, 30.2]
                    ]]
                }
            },
            "boundary_minimum": {
                "id": "boundary_minimum",
                "area_sqkm": 0.00001,
                "location": "Minimum valid area",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [0.001, 0],
                        [0.001, 0.001],
                        [0, 0.001],
                        [0, 0]
                    ]]
                }
            },
            "boundary_maximum": {
                "id": "boundary_maximum",
                "area_sqkm": 100.0,
                "location": "Maximum valid area",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [10, 0],
                        [10, 10],
                        [0, 10],
                        [0, 0]
                    ]]
                }
            },
            "invalid_small": {
                "id": "invalid_small",
                "area_sqkm": 0.000005,
                "location": "Below minimum area",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 0],
                        [0.0001, 0],
                        [0.0001, 0.0001],
                        [0, 0.0001],
                        [0, 0]
                    ]]
                }
            },
            "equator_crossing": {
                "id": "equator_crossing",
                "area_sqkm": 5.0,
                "location": "Crossing equator",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, -0.05],
                        [0.05, -0.05],
                        [0.05, 0.05],
                        [0, 0.05],
                        [0, -0.05]
                    ]]
                }
            },
            "pole_region": {
                "id": "pole_region",
                "area_sqkm": 5.0,
                "location": "Near North Pole",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [0, 80],
                        [5, 80],
                        [5, 85],
                        [0, 85],
                        [0, 80]
                    ]]
                }
            },
            "antimeridian": {
                "id": "antimeridian",
                "area_sqkm": 5.0,
                "location": "Crossing antimeridian",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [179.5, 0],
                        [180, 0],
                        [180, 5],
                        [179.5, 5],
                        [179.5, 0]
                    ]]
                }
            },
            "urban_dense": {
                "id": "urban_dense",
                "area_sqkm": 2.0,
                "location": "Manhattan, NYC",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-74.01, 40.71],
                        [-73.93, 40.71],
                        [-73.93, 40.75],
                        [-74.01, 40.75],
                        [-74.01, 40.71]
                    ]]
                }
            },
            "rural_sparse": {
                "id": "rural_sparse",
                "area_sqkm": 5.0,
                "location": "Rural Montana",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-109, 47],
                        [-108.5, 47],
                        [-108.5, 47.5],
                        [-109, 47.5],
                        [-109, 47]
                    ]]
                }
            },
            "ocean_area": {
                "id": "ocean_area",
                "area_sqkm": 10.0,
                "location": "Atlantic Ocean",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-50, 30],
                        [-49, 30],
                        [-49, 31],
                        [-50, 31],
                        [-50, 30]
                    ]]
                }
            },
            "admin_boundary": {
                "id": "admin_boundary",
                "area_sqkm": 50.0,
                "location": "State of Texas (subset)",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-99, 31],
                        [-97, 31],
                        [-97, 33],
                        [-99, 33],
                        [-99, 31]
                    ]]
                }
            },
            "mixed_terrain": {
                "id": "mixed_terrain",
                "area_sqkm": 8.0,
                "location": "Mixed urban/rural",
                "geojson": {
                    "type": "Polygon",
                    "coordinates": [[
                        [-87.6, 41.8],
                        [-87.5, 41.8],
                        [-87.5, 41.9],
                        [-87.6, 41.9],
                        [-87.6, 41.8]
                    ]]
                }
            }
        }

    def get_polygon(self, polygon_id: str) -> Optional[Dict[str, Any]]:
        """Get a test polygon fixture by ID."""
        polygon = self.polygons.get(polygon_id)
        if polygon:
            logger.debug(f"Retrieved polygon fixture: {polygon_id}")
        else:
            logger.warning(f"Polygon fixture not found: {polygon_id}")
        return polygon

    def get_all_polygons(self) -> Dict[str, Dict[str, Any]]:
        """Get all polygon fixtures."""
        return self.polygons.copy()

    def get_cached_response(self, provider: str, polygon_id: str) -> Optional[Dict[str, Any]]:
        """Get cached provider response."""
        cache_key = f"{provider}_{polygon_id}"
        
        if cache_key in self.provider_cache:
            self.audit_log["cache_hits"] += 1
            logger.debug(f"Cache hit: {cache_key}")
            return self.provider_cache[cache_key]
        
        # Try to load from disk
        cache_file = self.fixtures_dir / "provider_responses" / provider / f"{polygon_id}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                self.provider_cache[cache_key] = data
                self.audit_log["cache_hits"] += 1
                logger.debug(f"Loaded from disk: {cache_key}")
                return data
            except Exception as e:
                logger.error(f"Error loading cache file {cache_file}: {e}")
        
        self.audit_log["cache_misses"] += 1
        logger.debug(f"Cache miss: {cache_key}")
        return None

    def cache_response(self, provider: str, polygon_id: str, response: Dict[str, Any]) -> bool:
        """Cache a provider response."""
        cache_key = f"{provider}_{polygon_id}"
        
        # Store in memory
        self.provider_cache[cache_key] = response
        
        # Store on disk
        provider_dir = self.fixtures_dir / "provider_responses" / provider
        provider_dir.mkdir(parents=True, exist_ok=True)
        
        cache_file = provider_dir / f"{polygon_id}.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(response, f, indent=2, default=str)
            logger.info(f"Cached response: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Error saving cache file {cache_file}: {e}")
            return False

    def get_cache_age(self, provider: str, polygon_id: str) -> Optional[float]:
        """Get age of cached response in days."""
        cache_file = self.fixtures_dir / "provider_responses" / provider / f"{polygon_id}.json"
        
        if cache_file.exists():
            mtime = cache_file.stat().st_mtime
            age_seconds = (datetime.now().timestamp() - mtime)
            age_days = age_seconds / (24 * 3600)
            return age_days
        
        return None

    def get_audit_report(self) -> Dict[str, Any]:
        """Get comprehensive audit report of test data usage."""
        total_calls = self.audit_log["cache_hits"] + self.audit_log["cache_misses"]
        hit_rate = (self.audit_log["cache_hits"] / total_calls * 100) if total_calls > 0 else 0
        
        # Calculate efficiency metrics
        if self.audit_log["api_calls"] > 0:
            api_efficiency = (total_calls - self.audit_log["cache_misses"]) / self.audit_log["api_calls"]
        else:
            api_efficiency = 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_cache_requests": total_calls,
            "cache_hits": self.audit_log["cache_hits"],
            "cache_misses": self.audit_log["cache_misses"],
            "cache_hit_rate_percent": hit_rate,
            "real_api_calls_made": self.audit_log["api_calls"],
            "api_calls_avoided_by_cache": total_calls - self.audit_log["cache_misses"],
            "efficiency_multiplier": api_efficiency,
            "provider_calls_breakdown": self.audit_log["provider_calls"],
            "polygons_tested": list(self.audit_log["test_data_usage"].keys()),
            "data_consistency_checks": self.audit_log["data_consistency_checks"]
        }
    
    def record_test_polygon_usage(self, test_name: str, polygon_id: str) -> None:
        """Record which test used which polygon fixture."""
        if test_name not in self.audit_log["test_data_usage"]:
            self.audit_log["test_data_usage"][test_name] = []
        self.audit_log["test_data_usage"][test_name].append(polygon_id)
        logger.debug(f"Test {test_name} used polygon: {polygon_id}")
    
    def record_data_consistency_check(self, check_name: str, result: str, details: str = "") -> None:
        """Record result of data consistency check."""
        self.audit_log["data_consistency_checks"].append({
            "timestamp": datetime.now().isoformat(),
            "check_name": check_name,
            "result": result,
            "details": details
        })
        logger.info(f"Consistency check '{check_name}': {result} - {details}")
    
    def export_audit_report(self, filepath: str) -> bool:
        """Export audit report to JSON file."""
        try:
            report = self.get_audit_report()
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Audit report exported to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting audit report: {e}")
            return False

    def record_api_call(self, provider: str) -> None:
        """Record a real API call."""
        self.audit_log["api_calls"] += 1
        if provider not in self.audit_log["provider_calls"]:
            self.audit_log["provider_calls"][provider] = 0
        self.audit_log["provider_calls"][provider] += 1
        logger.info(f"API call recorded: {provider}")

    def save_fixtures(self) -> bool:
        """Save polygon fixtures to file."""
        fixtures_file = self.fixtures_dir / "test_polygons.json"
        
        try:
            with open(fixtures_file, 'w') as f:
                json.dump({"polygons": self.polygons}, f, indent=2)
            logger.info(f"Saved fixtures to {fixtures_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving fixtures: {e}")
            return False


class TestPolygonGenerator:
    """
    Deterministic test polygon generator.
    
    Generates polygon variations reproducibly using seed-based generation.
    Supports:
    - Size variations
    - Location variations
    - Shape variations
    - Coordinate precision variations
    - Vertex count variations
    """
    
    def __init__(self, seed: int = 42):
        """Initialize generator with seed for reproducibility."""
        self.seed = seed
    
    def generate_by_size(self, area_sqkm: float, seed: int = 42) -> Dict[str, Any]:
        """
        Generate a polygon of specified area (deterministically).
        
        Args:
            area_sqkm: Target area in square kilometers
            seed: Seed for reproducibility
            
        Returns:
            Dict with id, area_sqkm, geojson
        """
        import random as random_module
        random_module.seed(seed)
        
        # Convert area to degrees (approximate at equator)
        # 1 degree ≈ 111 km
        degrees_squared = area_sqkm / (111 * 111)
        side_degrees = degrees_squared ** 0.5
        
        # Generate at deterministic location
        base_lon = 0 + (seed % 36) * 10  # Distribute across longitudes
        base_lat = 0 + (seed % 18) * 5   # Distribute across latitudes
        
        # Clamp to valid ranges
        base_lon = max(-180, min(180, base_lon))
        base_lat = max(-90, min(90, base_lat))
        
        # Create rectangle
        coords = [
            [base_lon, base_lat],
            [base_lon + side_degrees, base_lat],
            [base_lon + side_degrees, base_lat + side_degrees],
            [base_lon, base_lat + side_degrees],
            [base_lon, base_lat]
        ]
        
        polygon_id = f"generated_size_{area_sqkm:.6f}_seed_{seed}"
        
        return {
            "id": polygon_id,
            "area_sqkm": area_sqkm,
            "location": f"Generated: {area_sqkm} sqkm",
            "geojson": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
    
    def generate_by_location(self, latitude: float, longitude: float, area_sqkm: float, seed: int = 42) -> Dict[str, Any]:
        """
        Generate a polygon at specific location.
        
        Args:
            latitude: Center latitude
            longitude: Center longitude
            area_sqkm: Target area
            seed: Seed for reproducibility
            
        Returns:
            Dict with id, area_sqkm, geojson
        """
        # Convert area to degrees
        degrees_squared = area_sqkm / (111 * 111)
        side_degrees = degrees_squared ** 0.5
        
        half_side = side_degrees / 2
        
        coords = [
            [longitude - half_side, latitude - half_side],
            [longitude + half_side, latitude - half_side],
            [longitude + half_side, latitude + half_side],
            [longitude - half_side, latitude + half_side],
            [longitude - half_side, latitude - half_side]
        ]
        
        polygon_id = f"location_{latitude:.2f}_{longitude:.2f}_seed_{seed}"
        
        return {
            "id": polygon_id,
            "area_sqkm": area_sqkm,
            "location": f"lat={latitude}, lon={longitude}",
            "geojson": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }
    
    def generate_by_vertex_count(self, num_vertices: int, area_sqkm: float, seed: int = 42) -> Dict[str, Any]:
        """
        Generate a polygon with specific vertex count (deterministically).
        
        Args:
            num_vertices: Number of vertices (including closing vertex)
            area_sqkm: Target area
            seed: Seed for reproducibility
            
        Returns:
            Dict with id, area_sqkm, geojson
        """
        import random as random_module
        import math
        
        random_module.seed(seed)
        
        # Start with a circle and discretize to vertices
        base_lon = 0
        base_lat = 0
        
        # Radius in degrees for target area
        # Area = pi * r^2, so r = sqrt(area / pi) in degrees
        degrees_squared = area_sqkm / (111 * 111)
        radius_degrees = (degrees_squared / math.pi) ** 0.5
        
        coords = []
        for i in range(num_vertices - 1):  # -1 because we close the ring
            angle = (i / (num_vertices - 1)) * 2 * math.pi
            lon = base_lon + radius_degrees * math.cos(angle)
            lat = base_lat + radius_degrees * math.sin(angle)
            coords.append([lon, lat])
        
        # Close the ring
        coords.append(coords[0])
        
        polygon_id = f"vertices_{num_vertices}_seed_{seed}"
        
        return {
            "id": polygon_id,
            "area_sqkm": area_sqkm,
            "location": f"Generated: {num_vertices} vertices",
            "geojson": {
                "type": "Polygon",
                "coordinates": [coords]
            }
        }


class TestDataValidator:
    """
    Validates test data consistency and completeness.
    
    Checks:
    - Data structure compliance
    - Provider response format compliance
    - Data completeness
    - Timestamp validity
    """
    
    @staticmethod
    def validate_provider_response(response: Dict[str, Any], provider: str) -> Tuple[bool, List[str]]:
        """
        Validate provider response structure.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        if not isinstance(response, dict):
            errors.append("Response must be a dictionary")
            return False, errors
        
        required_fields = ["type", "features"]
        for field in required_fields:
            if field not in response:
                errors.append(f"Missing required field: {field}")
        
        # Validate GeoJSON structure
        if response.get("type") != "FeatureCollection":
            errors.append(f"Invalid type: {response.get('type')}, expected FeatureCollection")
        
        features = response.get("features", [])
        if not isinstance(features, list):
            errors.append("Features must be a list")
            return False, errors
        
        # Validate each feature
        for i, feature in enumerate(features):
            if not isinstance(feature, dict):
                errors.append(f"Feature {i} must be a dictionary")
                continue
            
            if "geometry" not in feature:
                errors.append(f"Feature {i} missing geometry")
            
            if "properties" not in feature:
                errors.append(f"Feature {i} missing properties")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @staticmethod
    def compare_datasets(data1: Dict[str, Any], data2: Dict[str, Any]) -> Tuple[DataConsistency, str]:
        """
        Compare two datasets for consistency.
        
        Returns:
            (consistency_level, description)
        """
        # Exact match
        if data1 == data2:
            return DataConsistency.IDENTICAL, "Datasets are identical"
        
        # Check structure equivalence
        data1_keys = set(data1.keys())
        data2_keys = set(data2.keys())
        
        if data1_keys != data2_keys:
            missing = data1_keys - data2_keys
            extra = data2_keys - data1_keys
            return DataConsistency.INCONSISTENT, f"Key differences - missing: {missing}, extra: {extra}"
        
        # Check feature count equivalence
        features1 = data1.get("features", [])
        features2 = data2.get("features", [])
        
        if len(features1) != len(features2):
            return DataConsistency.INCONSISTENT, f"Feature count mismatch: {len(features1)} vs {len(features2)}"
        
        return DataConsistency.EQUIVALENT, "Datasets are structurally equivalent"
    
    @staticmethod
    def assert_no_duplicate_data(test_data_sets: List[Dict[str, Any]]) -> bool:
        """
        Assert that no duplicate data exists in test sets.
        
        Returns:
            True if all data sets are unique, False otherwise
        """
        hashes = set()
        
        for i, data_set in enumerate(test_data_sets):
            # Create hash of data
            data_str = json.dumps(data_set, sort_keys=True, default=str)
            data_hash = hashlib.sha256(data_str.encode()).hexdigest()
            
            if data_hash in hashes:
                logger.warning(f"Duplicate data detected in data set {i}")
                return False
            
            hashes.add(data_hash)
        
        return True


class ResponseCache:
    """
    Manages caching of provider responses to avoid duplicate API calls.
    
    Supports:
    - Get/cache responses by provider and polygon ID
    - Cache age tracking
    - Automatic refresh capability
    - TTL-based expiration
    """
    
    def __init__(self, cache_dir: Path, ttl_days: int = 30):
        """Initialize response cache."""
        self.cache_dir = cache_dir
        self.ttl_days = ttl_days
        self.in_memory_cache = {}
    
    def get_cached_response(self, provider: str, polygon_id: str) -> Optional[Dict[str, Any]]:
        """Get cached response or None if not found or expired."""
        cache_key = f"{provider}_{polygon_id}"
        
        # Check in-memory cache first
        if cache_key in self.in_memory_cache:
            logger.debug(f"Cache hit (memory): {cache_key}")
            return self.in_memory_cache[cache_key]
        
        # Check disk cache
        cache_file = self.cache_dir / provider / f"{polygon_id}.json"
        
        if not cache_file.exists():
            return None
        
        # Check if expired
        age_days = self._get_cache_age_days(cache_file)
        if age_days > self.ttl_days:
            logger.warning(f"Cache expired: {cache_key} ({age_days:.1f} days old, TTL: {self.ttl_days} days)")
            return None
        
        # Load from disk
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            self.in_memory_cache[cache_key] = data
            logger.debug(f"Cache hit (disk): {cache_key}")
            return data
        except Exception as e:
            logger.error(f"Error loading cache: {cache_file}: {e}")
            return None
    
    def cache_response(self, provider: str, polygon_id: str, response: Dict[str, Any]) -> bool:
        """Cache a provider response."""
        cache_key = f"{provider}_{polygon_id}"
        
        # Store in memory
        self.in_memory_cache[cache_key] = response
        
        # Store on disk
        provider_dir = self.cache_dir / provider
        provider_dir.mkdir(parents=True, exist_ok=True)
        
        cache_file = provider_dir / f"{polygon_id}.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(response, f, indent=2, default=str)
            logger.info(f"Response cached: {cache_key}")
            return True
        except Exception as e:
            logger.error(f"Error caching response: {e}")
            return False
    
    def get_cache_age(self, provider: str, polygon_id: str) -> Optional[float]:
        """Get cache age in days."""
        cache_file = self.cache_dir / provider / f"{polygon_id}.json"
        if cache_file.exists():
            return self._get_cache_age_days(cache_file)
        return None
    
    @staticmethod
    def _get_cache_age_days(file_path: Path) -> float:
        """Calculate file age in days."""
        mtime = file_path.stat().st_mtime
        age_seconds = datetime.now().timestamp() - mtime
        return age_seconds / (24 * 3600)
    
    def refresh_cache(self, provider: str, polygon_id: str) -> bool:
        """Mark cache entry for refresh (delete it)."""
        cache_key = f"{provider}_{polygon_id}"
        
        # Remove from memory cache
        if cache_key in self.in_memory_cache:
            del self.in_memory_cache[cache_key]
        
        # Remove from disk cache
        cache_file = self.cache_dir / provider / f"{polygon_id}.json"
        if cache_file.exists():
            try:
                cache_file.unlink()
                logger.info(f"Cache cleared: {cache_key}")
                return True
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
                return False
        
        return True
