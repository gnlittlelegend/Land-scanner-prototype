"""
Test data sharing protocol for declarative data dependencies.

Allows tests to declare their data needs using decorators/markers,
and ensures data is loaded once and shared across all tests in a session.
"""

from typing import Set, List, Dict, Any
from functools import wraps
import pytest
import logging

logger = logging.getLogger(__name__)


class TestDataDependency:
    """Tracks data dependencies for a test."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.required_polygons: Set[str] = set()
        self.required_provider_data: List[tuple] = []  # [(provider, polygon_id), ...]
        self.required_api_calls: List[dict] = []  # [{provider, polygon_id}, ...]
    
    def add_polygon(self, polygon_id: str) -> None:
        """Declare need for a polygon fixture."""
        self.required_polygons.add(polygon_id)
        logger.debug(f"Test {self.test_name} requires polygon: {polygon_id}")
    
    def add_provider_data(self, provider: str, polygon_id: str) -> None:
        """Declare need for provider data."""
        self.required_provider_data.append((provider, polygon_id))
        logger.debug(f"Test {self.test_name} requires {provider} data for {polygon_id}")
    
    def add_api_call(self, provider: str, polygon_id: str) -> None:
        """Declare need for real API call data."""
        self.required_api_calls.append({"provider": provider, "polygon_id": polygon_id})
        logger.debug(f"Test {self.test_name} requires real API call: {provider}({polygon_id})")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of data dependencies."""
        return {
            "test_name": self.test_name,
            "polygon_count": len(self.required_polygons),
            "provider_data_count": len(self.required_provider_data),
            "api_call_count": len(self.required_api_calls),
            "polygons": list(self.required_polygons),
            "provider_data": self.required_provider_data,
            "api_calls": self.required_api_calls
        }


class TestDataDependencyRegistry:
    """Central registry for test data dependencies."""
    
    def __init__(self):
        self.dependencies: Dict[str, TestDataDependency] = {}
        self.all_required_polygons: Set[str] = set()
        self.all_required_provider_data: Set[tuple] = set()
        self.all_required_api_calls: Set[tuple] = set()
    
    def register_dependency(self, test_name: str, dependency: TestDataDependency) -> None:
        """Register a test's data dependencies."""
        self.dependencies[test_name] = dependency
        
        # Aggregate
        self.all_required_polygons.update(dependency.required_polygons)
        self.all_required_provider_data.update(dependency.required_provider_data)
        for call in dependency.required_api_calls:
            self.all_required_api_calls.add((call["provider"], call["polygon_id"]))
        
        logger.info(f"Registered dependencies for {test_name}: "
                   f"{len(dependency.required_polygons)} polygons, "
                   f"{len(dependency.required_provider_data)} provider data, "
                   f"{len(dependency.required_api_calls)} API calls")
    
    def get_test_dependencies(self, test_name: str) -> TestDataDependency:
        """Get dependencies for a specific test."""
        if test_name not in self.dependencies:
            self.dependencies[test_name] = TestDataDependency(test_name)
        return self.dependencies[test_name]
    
    def get_all_polygon_ids_needed(self) -> Set[str]:
        """Get all polygon IDs needed across all tests."""
        return self.all_required_polygons.copy()
    
    def get_all_provider_data_needed(self) -> List[tuple]:
        """Get all provider data needed across all tests."""
        return list(self.all_required_provider_data)
    
    def get_load_plan(self) -> Dict[str, Any]:
        """Get data load plan - what data to load before running tests."""
        return {
            "total_tests_registered": len(self.dependencies),
            "unique_polygons_needed": len(self.all_required_polygons),
            "unique_provider_data_needed": len(self.all_required_provider_data),
            "unique_api_calls_needed": len(self.all_required_api_calls),
            "polygons": list(self.all_required_polygons),
            "provider_data": list(self.all_required_provider_data),
            "api_calls": list(self.all_required_api_calls)
        }
    
    def generate_summary(self) -> str:
        """Generate human-readable summary."""
        plan = self.get_load_plan()
        return (
            f"Test Data Load Plan:\n"
            f"  - Tests: {plan['total_tests_registered']}\n"
            f"  - Unique polygons: {plan['unique_polygons_needed']}\n"
            f"  - Provider data requests: {plan['unique_provider_data_needed']}\n"
            f"  - Real API calls needed: {plan['unique_api_calls_needed']}\n"
        )


# Global registry
_registry = TestDataDependencyRegistry()


def needs_polygon(polygon_id: str):
    """Decorator to declare polygon dependency."""
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            test_name = test_func.__name__
            dependency = _registry.get_test_dependencies(test_name)
            dependency.add_polygon(polygon_id)
            return test_func(*args, **kwargs)
        return wrapper
    return decorator


def needs_provider_data(provider: str, polygon_id: str):
    """Decorator to declare provider data dependency."""
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            test_name = test_func.__name__
            dependency = _registry.get_test_dependencies(test_name)
            dependency.add_provider_data(provider, polygon_id)
            return test_func(*args, **kwargs)
        return wrapper
    return decorator


def needs_real_api_call(provider: str, polygon_id: str):
    """Decorator to declare real API call dependency."""
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            test_name = test_func.__name__
            dependency = _registry.get_test_dependencies(test_name)
            dependency.add_api_call(provider, polygon_id)
            return test_func(*args, **kwargs)
        return wrapper
    return decorator


def get_dependency_registry() -> TestDataDependencyRegistry:
    """Get the global dependency registry."""
    return _registry


class DataDependencyTracker:
    """Tracks actual data access during tests."""
    
    def __init__(self):
        self.polygon_accesses: Dict[str, int] = {}  # polygon_id -> access count
        self.provider_data_accesses: Dict[tuple, int] = {}  # (provider, polygon_id) -> access count
        self.api_calls_made: Dict[tuple, int] = {}  # (provider, polygon_id) -> call count
        self.cache_hits: int = 0
        self.cache_misses: int = 0
    
    def record_polygon_access(self, polygon_id: str) -> None:
        """Record access to polygon fixture."""
        self.polygon_accesses[polygon_id] = self.polygon_accesses.get(polygon_id, 0) + 1
    
    def record_provider_data_access(self, provider: str, polygon_id: str, is_cache_hit: bool) -> None:
        """Record access to provider data."""
        key = (provider, polygon_id)
        self.provider_data_accesses[key] = self.provider_data_accesses.get(key, 0) + 1
        
        if is_cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
    
    def record_api_call(self, provider: str, polygon_id: str) -> None:
        """Record real API call."""
        key = (provider, polygon_id)
        self.api_calls_made[key] = self.api_calls_made.get(key, 0) + 1
    
    def get_report(self) -> Dict[str, Any]:
        """Get access report."""
        total_provider_accesses = self.cache_hits + self.cache_misses
        cache_hit_rate = (self.cache_hits / total_provider_accesses * 100) if total_provider_accesses > 0 else 0
        
        return {
            "polygon_accesses": self.polygon_accesses,
            "provider_data_accesses": self.provider_data_accesses,
            "api_calls_made": self.api_calls_made,
            "total_cache_hits": self.cache_hits,
            "total_cache_misses": self.cache_misses,
            "cache_hit_rate_percent": cache_hit_rate,
            "total_api_calls": len(self.api_calls_made)
        }


# Global tracker
_tracker = DataDependencyTracker()


def get_dependency_tracker() -> DataDependencyTracker:
    """Get the global dependency tracker."""
    return _tracker


# Pytest hooks to integrate with test session

def pytest_sessionstart(session):
    """Called before test session starts."""
    logger.info("Test session starting - data dependencies will be tracked")


def pytest_sessionfinish(session, exitstatus):
    """Called after test session ends."""
    plan = _registry.get_load_plan()
    report = _tracker.get_report()
    
    logger.info("=" * 60)
    logger.info("Test Data Protocol Summary")
    logger.info("=" * 60)
    logger.info(f"Tests registered: {plan['total_tests_registered']}")
    logger.info(f"Unique polygons needed: {plan['unique_polygons_needed']}")
    logger.info(f"Unique provider data: {plan['unique_provider_data_needed']}")
    logger.info(f"Unique API calls needed: {plan['unique_api_calls_needed']}")
    logger.info("")
    logger.info("Actual Data Access:")
    logger.info(f"  Polygon accesses: {len(report['polygon_accesses'])}")
    logger.info(f"  Provider data accesses: {len(report['provider_data_accesses'])}")
    logger.info(f"  API calls made: {report['total_api_calls']}")
    logger.info(f"  Cache hit rate: {report['cache_hit_rate_percent']:.1f}%")
    logger.info("=" * 60)
