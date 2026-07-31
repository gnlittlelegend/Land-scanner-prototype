"""
Property-based tests for Data Collection Completeness.

Feature: land-scanner, Property 2: Data Collection Completeness
Validates: Requirements 2.1, 2.2, 2.7
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import Mock, patch, MagicMock
import logging

from backend.managers.data_source_manager import DataSourceManager
from backend.services import ConfigManager
from backend.models import Polygon, ProcessingStatus, RawDataset, DataCategory
from backend.validators.polygon_validator import PolygonValidator


@st.composite
def valid_polygons_for_collection(draw):
    """Generate valid test polygons for collection testing."""
    lon_min = draw(st.floats(min_value=-170, max_value=170))
    lat_min = draw(st.floats(min_value=-80, max_value=80))
    width = draw(st.floats(min_value=1, max_value=30))
    height = draw(st.floats(min_value=1, max_value=30))
    
    lon_max = min(lon_min + width, 180)
    lat_max = min(lat_min + height, 90)
    
    coordinates = [
        [
            [lon_min, lat_min],
            [lon_max, lat_min],
            [lon_max, lat_max],
            [lon_min, lat_max],
            [lon_min, lat_min]
        ]
    ]
    
    return PolygonValidator.validate({
        "type": "Polygon",
        "coordinates": coordinates
    })


class TestDataCollectionCompleteness:
    """
    Property-based tests for data collection completeness.
    
    Feature: land-scanner, Property 2: Data Collection Completeness
    Validates: Requirements 2.1, 2.2, 2.7
    
    These tests verify that:
    1. All enabled collectors are queried for any polygon
    2. System collects from all providers regardless of success/failure
    3. Partial success doesn't crash the system
    4. All collected datasets are included in results
    """
    
    @given(valid_polygons_for_collection())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_all_collectors_are_queried(self, polygon: Polygon):
        """
        Property 2: For any polygon with N enabled collectors, all N collectors are queried.
        
        Validates: Requirements 2.1, 2.2
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        enabled_provider_count = manager.get_enabled_provider_count()
        queried_providers = set()
        
        # Track which providers are called
        original_method = manager._collect_from_provider
        
        def tracking_collect(provider_name, collector_info, polygon):
            queried_providers.add(provider_name)
            # Return empty dataset to avoid failures
            return RawDataset(
                source_provider=provider_name,
                category=collector_info["category"],
                geometry_type="Polygon",
                features=[],
                metadata={"test": True}
            )
        
        with patch.object(manager, '_collect_from_provider', side_effect=tracking_collect):
            result = manager.collect(polygon)
            
            # Verify all providers were queried
            assert len(queried_providers) == enabled_provider_count, \
                f"Expected {enabled_provider_count} providers to be queried, " \
                f"but only {len(queried_providers)} were: {queried_providers}"
    
    @given(valid_polygons_for_collection())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_collection_returns_all_successful_datasets(self, polygon: Polygon):
        """
        Property 2: For any polygon, all successfully collected datasets are returned.
        
        Validates: Requirements 2.7
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        enabled_provider_count = manager.get_enabled_provider_count()
        successful_providers = 0
        
        def mock_collect(provider_name, collector_info, polygon):
            nonlocal successful_providers
            successful_providers += 1
            
            return RawDataset(
                source_provider=provider_name,
                category=collector_info["category"],
                geometry_type="Polygon",
                features=[
                    {
                        "id": f"{provider_name}_feature_1",
                        "geometry": {"type": "Point", "coordinates": [0, 0]},
                        "properties": {"source": provider_name}
                    }
                ],
                metadata={"provider": provider_name}
            )
        
        with patch.object(manager, '_collect_from_provider', side_effect=mock_collect):
            result = manager.collect(polygon)
            
            # All datasets should be in results
            assert len(result["datasets"]) == successful_providers
            
            # Each dataset should have the expected structure
            for dataset in result["datasets"]:
                assert isinstance(dataset, RawDataset)
                assert len(dataset.features) > 0
                assert dataset.source_provider is not None
    
    @given(valid_polygons_for_collection())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_partial_success_doesnt_crash_system(self, polygon: Polygon):
        """
        Property 2: For any polygon, partial collection success doesn't crash the system.
        
        Validates: Requirements 2.1
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        # Deterministically fail osm_buildings provider, succeed on others
        def mock_collect(provider_name, collector_info, polygon):
            from backend.collectors.base import DataCollectionError
            
            if provider_name == "osm_buildings":
                raise DataCollectionError(f"{provider_name} failed")
            
            return RawDataset(
                source_provider=provider_name,
                category=collector_info["category"],
                geometry_type="Polygon",
                features=[],
                metadata={}
            )
        
        with patch.object(manager, '_collect_from_provider', side_effect=mock_collect):
            # Should not raise an exception
            try:
                result = manager.collect(polygon)
            except Exception as e:
                pytest.fail(f"Collection raised exception: {str(e)}")
            
            # Result should be valid even with one provider failing
            assert "datasets" in result
            assert "provider_status" in result
            assert "status" in result
            
            # Should not be complete failure (at least one provider succeeded)
            assert result["status"] != ProcessingStatus.FAILED, \
                "Should have partial or success status, not complete failure"
    
    @given(valid_polygons_for_collection())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_provider_status_tracks_all_providers(self, polygon: Polygon):
        """
        Property 2: For any polygon, provider status includes all enabled providers.
        
        Validates: Requirements 2.1, 2.2
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        enabled_provider_names = [p["name"] for p in config.get_enabled_providers()]
        enabled_provider_count = manager.get_enabled_provider_count()
        
        def mock_collect(provider_name, collector_info, polygon):
            return RawDataset(
                source_provider=provider_name,
                category=collector_info["category"],
                geometry_type="Polygon",
                features=[],
                metadata={}
            )
        
        with patch.object(manager, '_collect_from_provider', side_effect=mock_collect):
            result = manager.collect(polygon)
            
            # Provider status should have entries for all providers
            assert len(result["provider_status"]) == enabled_provider_count
            
            # Each enabled provider should be in provider_status
            for provider_name in enabled_provider_names:
                assert provider_name in result["provider_status"]
                
                # Each provider status should have required fields
                provider_status = result["provider_status"][provider_name]
                assert "status" in provider_status
                assert "data_retrieved" in provider_status
                assert "error_message" in provider_status
    
    @given(valid_polygons_for_collection())
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_collection_result_structure_completeness(self, polygon: Polygon):
        """
        Property 2: For any polygon, collection result has all required fields.
        
        Validates: Requirements 2.7
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        def mock_collect(provider_name, collector_info, polygon):
            return RawDataset(
                source_provider=provider_name,
                category=collector_info["category"],
                geometry_type="Polygon",
                features=[],
                metadata={}
            )
        
        with patch.object(manager, '_collect_from_provider', side_effect=mock_collect):
            result = manager.collect(polygon)
            
            # Verify result has all required fields
            required_fields = ["datasets", "provider_status", "status", "processing_time_ms"]
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"
            
            # Verify field types
            assert isinstance(result["datasets"], list)
            assert isinstance(result["provider_status"], dict)
            assert result["status"] in [
                ProcessingStatus.SUCCESS,
                ProcessingStatus.PARTIAL,
                ProcessingStatus.FAILED
            ]
            assert isinstance(result["processing_time_ms"], float)
    
    @given(
        valid_polygons_for_collection(),
        st.lists(st.sampled_from([0, 1, 2, 3, 4, 5]), min_size=1, max_size=6, unique=True)
    )
    @settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
    def test_collection_with_subset_of_providers(self, polygon: Polygon, provider_indices: list):
        """
        Property 2: For any polygon and subset of providers that fail, 
        remaining providers still return data.
        
        Validates: Requirements 2.1, 2.2
        """
        config = ConfigManager()
        manager = DataSourceManager(config)
        
        enabled_providers = [p["name"] for p in config.get_enabled_providers()]
        providers_to_fail = set()
        
        # Convert indices to provider names
        for idx in provider_indices:
            if idx < len(enabled_providers):
                providers_to_fail.add(enabled_providers[idx])
        
        def mock_collect(provider_name, collector_info, polygon):
            from backend.collectors.base import DataCollectionError
            
            if provider_name in providers_to_fail:
                raise DataCollectionError(f"{provider_name} failed")
            
            return RawDataset(
                source_provider=provider_name,
                category=collector_info["category"],
                geometry_type="Polygon",
                features=[{"id": f"{provider_name}_feature"}],
                metadata={}
            )
        
        with patch.object(manager, '_collect_from_provider', side_effect=mock_collect):
            result = manager.collect(polygon)
            
            # Calculate expected successful providers
            expected_successful = len(enabled_providers) - len(providers_to_fail)
            
            # Count actual successful providers
            successful_providers = [
                name for name, status in result["provider_status"].items()
                if status["status"] == "success"
            ]
            
            # Should have expected number of successful providers
            assert len(successful_providers) == expected_successful
            
            # Should have corresponding datasets
            assert len(result["datasets"]) == expected_successful
