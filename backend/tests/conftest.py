"""
Pytest configuration and shared fixtures for Land Scanner tests.

Provides:
- Centralized test data management
- Shared polygon fixtures
- Shared provider response cache
- Test dependency tracking
- Audit logging
"""

import pytest
import logging
from pathlib import Path
from typing import Dict, Any

from .test_data_manager import (
    TestDataManager,
    TestPolygonGenerator,
    ResponseCache,
    TestDataValidator
)

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# Session-level fixtures (shared across all tests in a session)

@pytest.fixture(scope="session")
def test_data_manager():
    """
    Centralized test data manager shared by all tests.
    
    Ensures:
    - All tests use same polygon fixtures
    - Provider responses are cached and reused
    - Test data is consistent and deterministic
    - No duplicate API calls
    """
    fixtures_dir = Path(__file__).parent / "fixtures"
    manager = TestDataManager(str(fixtures_dir))
    
    yield manager
    
    # Generate audit report after all tests
    audit_report = manager.get_audit_report()
    logging.info(f"Test session audit report: {audit_report}")


@pytest.fixture(scope="session")
def polygon_generator():
    """Test polygon generator with deterministic generation."""
    return TestPolygonGenerator(seed=42)


@pytest.fixture(scope="session")
def response_cache(test_data_manager):
    """Response cache for avoiding duplicate API calls."""
    cache_dir = test_data_manager.fixtures_dir / "provider_responses"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return ResponseCache(cache_dir, ttl_days=30)


@pytest.fixture(scope="session")
def test_data_validator():
    """Test data validator for consistency checks."""
    return TestDataValidator()


# Module-level fixtures

@pytest.fixture
def all_polygons(test_data_manager):
    """Get all available test polygon fixtures."""
    return test_data_manager.get_all_polygons()


@pytest.fixture
def valid_polygons(test_data_manager):
    """Get valid test polygon fixtures."""
    polygons = test_data_manager.get_all_polygons()
    valid = {
        k: v for k, v in polygons.items()
        if not k.startswith("invalid_")
    }
    return valid


@pytest.fixture
def invalid_polygons(test_data_manager):
    """Get invalid test polygon fixtures."""
    polygons = test_data_manager.get_all_polygons()
    invalid = {
        k: v for k, v in polygons.items()
        if k.startswith("invalid_")
    }
    return invalid


# Function-level fixtures (created fresh for each test)

@pytest.fixture
def polygon_small(test_data_manager):
    """Get small valid polygon fixture."""
    return test_data_manager.get_polygon("valid_small")


@pytest.fixture
def polygon_medium(test_data_manager):
    """Get medium valid polygon fixture."""
    return test_data_manager.get_polygon("valid_medium")


@pytest.fixture
def polygon_boundary_min(test_data_manager):
    """Get boundary minimum polygon fixture."""
    return test_data_manager.get_polygon("boundary_minimum")


@pytest.fixture
def polygon_boundary_max(test_data_manager):
    """Get boundary maximum polygon fixture."""
    return test_data_manager.get_polygon("boundary_maximum")


@pytest.fixture
def polygon_urban(test_data_manager):
    """Get urban area polygon fixture."""
    return test_data_manager.get_polygon("urban_dense")


@pytest.fixture
def polygon_rural(test_data_manager):
    """Get rural area polygon fixture."""
    return test_data_manager.get_polygon("rural_sparse")


@pytest.fixture
def polygon_ocean(test_data_manager):
    """Get ocean area polygon fixture."""
    return test_data_manager.get_polygon("ocean_area")


@pytest.fixture
def polygon_admin(test_data_manager):
    """Get administrative boundary polygon fixture."""
    return test_data_manager.get_polygon("admin_boundary")


@pytest.fixture
def polygon_equator(test_data_manager):
    """Get equator-crossing polygon fixture."""
    return test_data_manager.get_polygon("equator_crossing")


@pytest.fixture
def polygon_pole(test_data_manager):
    """Get pole region polygon fixture."""
    return test_data_manager.get_polygon("pole_region")


@pytest.fixture
def polygon_antimeridian(test_data_manager):
    """Get antimeridian-crossing polygon fixture."""
    return test_data_manager.get_polygon("antimeridian")


# Pytest hooks for logging and tracking

def pytest_runtest_setup(item):
    """Track test data dependencies before each test."""
    # Check for test marker indicating required data
    markers = [marker.name for marker in item.iter_markers()]
    # This can be extended to track specific data needs


def pytest_runtest_teardown(item, nextitem):
    """Log test data usage after each test."""
    # This could be extended to record detailed audit information per test


# Hypothesis strategies for property-based testing

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers",
        "needs_polygon(polygon_id): marks test as needing a specific polygon fixture"
    )
    config.addinivalue_line(
        "markers",
        "needs_provider_data(provider, polygon_id): marks test as needing provider data"
    )
    config.addinivalue_line(
        "markers",
        "property_test: marks test as a property-based test"
    )
