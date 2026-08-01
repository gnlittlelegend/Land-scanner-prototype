"""
Data Source Manager orchestrates data collection from all configured providers.
Manages collector execution, aggregates results, and handles provider failures.
"""

import asyncio
import importlib
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime

from backend.models.schemas import Polygon, RawDataset, ProcessingStatus
from backend.services.config_manager import ConfigManager
from backend.collectors.base_collector import DataCollector, DataCollectorError


logger = logging.getLogger(__name__)


class DataSourceManagerError(Exception):
    """Raised when data collection fails critically."""
    pass


class DataSourceManager:
    """
    Orchestrates data collection from multiple enabled data providers.
    
    Responsibilities:
    - Load enabled collectors from configuration
    - Execute collectors for a given polygon
    - Aggregate results from all collectors
    - Handle collector failures gracefully
    - Continue processing if optional providers fail
    - Record execution status for each collector
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the Data Source Manager.
        
        Args:
            config_manager: ConfigManager instance for loading provider configuration
        """
        self.config_manager = config_manager
        self.collectors: Dict[str, DataCollector] = {}
        self.provider_status: Dict[str, Dict] = {}
        self._auto_register_collectors()

    def _auto_register_collectors(self) -> None:
        """
        Auto-register all available collectors based on configuration.
        
        Imports collector classes dynamically and registers instances
        for all enabled providers.
        """
        collector_module_map = {
            "osm_buildings": "backend.collectors.osm_buildings:OSMBuildingsCollector",
            "admin_boundaries": "backend.collectors.admin_boundaries:AdminBoundariesCollector",
            "land_cover": "backend.collectors.land_cover:LandCoverCollector",
            "osm_roads": "backend.collectors.roads:RoadNetworkCollector",
            "osm_water": "backend.collectors.water:WaterBodiesCollector",
            "elevation": "backend.collectors.elevation:ElevationCollector",
        }

        enabled_providers = self.config_manager.get_enabled_providers()
        for provider in enabled_providers:
            provider_name = provider.get("name")
            if not provider_name:
                continue

            class_path = collector_module_map.get(provider_name)
            if not class_path:
                logger.warning(f"No collector mapping found for provider: {provider_name}")
                continue

            try:
                module_name, class_name = class_path.rsplit(":", 1)
                module = importlib.import_module(module_name)
                collector_class = getattr(module, class_name)
                timeout = provider.get("timeout_seconds", 30)
                collector = collector_class(timeout_seconds=timeout)
                self.register_collector(collector)
            except Exception as e:
                logger.error(
                    f"Failed to register collector for {provider_name}: {str(e)}",
                    exc_info=True
                )

    def register_collector(self, collector: DataCollector) -> None:
        """
        Register a data collector with the manager.
        
        Args:
            collector: DataCollector instance to register
        """
        self.collectors[collector.provider_name] = collector
        logger.info(f"Registered collector: {collector.provider_name}")

    def get_enabled_collectors(self) -> List[DataCollector]:
        """
        Get list of enabled collectors based on configuration.
        
        Returns:
            List of DataCollector instances that are enabled
        """
        enabled_providers = self.config_manager.get_enabled_providers()
        enabled_collectors = [
            self.collectors[provider["name"]]
            for provider in enabled_providers
            if provider["name"] in self.collectors
        ]
        return enabled_collectors

    async def collect_async(self, polygon: Polygon) -> Tuple[Dict[str, RawDataset], Dict[str, Dict]]:
        """
        Asynchronously collect data from all enabled providers.
        
        Args:
            polygon: Validated polygon defining area of interest
            
        Returns:
            Tuple of (collected_datasets, provider_statuses)
            - collected_datasets: Dict mapping provider_name to RawDataset
            - provider_statuses: Dict mapping provider_name to status info
        """
        enabled_collectors = self.get_enabled_collectors()
        
        if not enabled_collectors:
            logger.warning("No enabled collectors configured")
            return {}, {}

        # Create async tasks for all collectors
        tasks = [
            self._collect_from_provider(collector, polygon)
            for collector in enabled_collectors
        ]

        # Execute all collectors concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        collected_datasets = {}
        provider_statuses = {}

        for collector, result in zip(enabled_collectors, results):
            provider_name = collector.provider_name
            
            if isinstance(result, Exception):
                provider_statuses[provider_name] = {
                    "status": "error",
                    "success": False,
                    "error": str(result),
                    "data_retrieved": False
                }
                logger.error(f"Collector {provider_name} failed: {str(result)}")
            else:
                collected_datasets[provider_name] = result
                provider_statuses[provider_name] = {
                    "status": "available",
                    "success": True,
                    "data_retrieved": True,
                    "feature_count": len(result.features) if result.features else 0
                }
                logger.info(f"Collector {provider_name} succeeded with {len(result.features) if result.features else 0} features")

        self.provider_status = provider_statuses
        return collected_datasets, provider_statuses

    def collect(self, polygon: Polygon) -> Tuple[Dict[str, RawDataset], Dict[str, Dict]]:
        """
        Synchronously collect data from all enabled providers.
        
        This is a wrapper around the async method for synchronous contexts.
        
        Args:
            polygon: Validated polygon defining area of interest
            
        Returns:
            Tuple of (collected_datasets, provider_statuses)
        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.collect_async(polygon))
        finally:
            loop.close()

    async def _collect_from_provider(
        self,
        collector: DataCollector,
        polygon: Polygon
    ) -> RawDataset:
        """
        Collect data from a single provider with error handling.
        
        Args:
            collector: DataCollector instance
            polygon: Validated polygon
            
        Returns:
            RawDataset from the collector
            
        Raises:
            DataCollectorError: If collection fails
        """
        try:
            logger.info(f"Starting collection from {collector.provider_name}")
            
            # Execute collection with timeout
            timeout = collector.timeout_seconds
            dataset = await asyncio.wait_for(
                asyncio.to_thread(collector.collect, polygon),
                timeout=timeout
            )
            
            logger.info(f"Successfully collected from {collector.provider_name}")
            return dataset
            
        except asyncio.TimeoutError:
            raise DataCollectorError(
                f"Collection from {collector.provider_name} timed out after {timeout} seconds"
            )
        except DataCollectorError as e:
            raise e
        except Exception as e:
            raise DataCollectorError(
                f"Collection from {collector.provider_name} failed: {str(e)}"
            )

    def get_collection_status(self) -> Dict[str, Dict]:
        """
        Get the status of all collection attempts.
        
        Returns:
            Dictionary mapping provider names to status information
        """
        return self.provider_status

    def get_collection_summary(self) -> Dict:
        """
        Get a summary of collection results.
        
        Returns:
            Summary including total providers, successful, failed, etc.
        """
        statuses = list(self.provider_status.values())
        
        return {
            "total_providers": len(statuses),
            "successful": sum(1 for s in statuses if s.get("success", False)),
            "failed": sum(1 for s in statuses if not s.get("success", False)),
            "timestamp": datetime.utcnow().isoformat(),
            "details": self.provider_status
        }
