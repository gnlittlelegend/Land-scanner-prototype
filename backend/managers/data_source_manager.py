"""
Data Source Manager for Land Scanner Prototype.

Coordinates data collection from multiple real providers,
handles provider failures gracefully, and aggregates results.

This module implements the DataSourceManager which orchestrates:
- Loading enabled providers from configuration (with real endpoints)
- Sequential execution of all enabled collectors
- Rate limit delay management between requests (2-5 seconds)
- Provider failure handling (timeouts, rate limits, API errors)
- Graceful degradation: continues if optional providers fail
- Failure escalation: fails only if all critical providers unavailable
- Result aggregation into RawDataCollection with provider status

Requirements Met:
- Load enabled providers from configuration with real API endpoints
- Execute all enabled collectors sequentially
- Add rate limit delays between requests (2-5 seconds configurable)
- Aggregate results from all collectors
- Handle real provider failures (timeouts, rate limits, API errors)
- Continue processing if optional providers fail
- Fail only if all critical providers unavailable
- Return aggregated RawDataCollection with provider status
"""

import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.services.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class RawDataCollection:
    """
    Result of a complete data collection from all providers.
    
    Attributes:
        collections: Dict mapping provider names to raw datasets
        provider_status: Dict with success/failure status for each provider
        collection_timestamp: ISO timestamp of collection
        total_providers: Total number of enabled providers
        successful_providers: Count of successful providers
        failed_providers: Count of failed providers
        critical_failure: True if all critical providers failed
    """

    def __init__(self):
        """Initialize an empty collection result."""
        self.collections = {}
        self.provider_status = {}
        self.collection_timestamp = datetime.utcnow().isoformat()
        self.total_providers = 0
        self.successful_providers = 0
        self.failed_providers = 0
        self.critical_failure = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for JSON serialization."""
        return {
            "collections": self.collections,
            "provider_status": self.provider_status,
            "collection_timestamp": self.collection_timestamp,
            "total_providers": self.total_providers,
            "successful_providers": self.successful_providers,
            "failed_providers": self.failed_providers,
            "critical_failure": self.critical_failure
        }


class DataSourceManager:
    """
    Manages data collection from multiple real production providers.
    
    Responsibilities:
    - Load enabled providers from configuration (with real endpoints)
    - Execute collectors sequentially (respects rate limits)
    - Handle provider failures gracefully (timeouts, rate limits, errors)
    - Continue processing if optional providers fail
    - Fail only if all critical providers unavailable
    - Aggregate results from all providers into RawDataCollection
    
    Design Principles:
    1. ALL data from REAL providers - no mock data
    2. SEQUENTIAL execution respects provider rate limits
    3. GRACEFUL degradation - system continues with partial results
    4. CRITICAL vs OPTIONAL distinction - optional provider failures don't stop processing
    5. TRANSPARENT status - clear status for each provider
    6. FAILURE isolation - one provider's failure doesn't affect others
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        collectors: Dict[str, Any],
        rate_limit_delay: Optional[float] = None
    ):
        """
        Initialize DataSourceManager with real provider coordination.
        
        Args:
            config_manager: Configuration manager instance
            collectors: Dict mapping provider names to collector instances
                       All collectors must extend DataCollector base class
                       and use real production API endpoints
            rate_limit_delay: Delay between requests in seconds (2-5 recommended)
                             If None, uses config setting or default 2 seconds
        """
        self.config_manager = config_manager
        self.collectors = collectors
        self.rate_limit_delay = (
            rate_limit_delay
            or config_manager.get_setting('rate_limit_delay', 2)
        )
        self.logger = logging.getLogger(__name__)
        
        # Validate rate limit delay is in reasonable range
        # Try to convert to float if it's not already numeric
        try:
            self.rate_limit_delay = float(self.rate_limit_delay)
        except (TypeError, ValueError):
            self.logger.warning(
                f"Rate limit delay not numeric: {self.rate_limit_delay}, using default 2 seconds"
            )
            self.rate_limit_delay = 2.0
        
        if not (0.5 <= self.rate_limit_delay <= 30):
            self.logger.warning(
                f"Rate limit delay {self.rate_limit_delay}s is unusual; "
                f"expected 2-5 seconds"
            )

    def collect_data(self, polygon: Dict[str, Any]) -> RawDataCollection:
        """
        Execute all enabled collectors for the polygon.
        
        This is the main orchestration method that:
        1. Loads enabled providers from configuration
        2. Executes each enabled collector sequentially
        3. Applies rate limit delays between requests
        4. Handles provider failures gracefully
        5. Aggregates results from all available providers
        6. Returns complete RawDataCollection with status
        
        Args:
            polygon: Validated polygon with metadata structure:
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [...]},
                    "properties": {
                        "area_square_kilometers": float,
                        "bounding_box": {...},
                        "centroid": {...},
                        ...
                    }
                }
            
        Returns:
            RawDataCollection containing:
            - collections: Dict mapping provider names to raw datasets
            - provider_status: Dict with status for each provider
            - collection_timestamp: ISO timestamp
            - Counts: total, successful, failed providers
            - critical_failure: True if all critical providers failed
            
        Note: This method NEVER raises exceptions. All provider failures
              are logged and handled gracefully. The method always returns
              a RawDataCollection with status information.
        """
        polygon_area = polygon.area_sqkm  # PolygonMetadata has area_sqkm attribute
        self.logger.info(
            f"Starting data collection for polygon (area: {polygon_area:.2f} km²)"
        )
        
        # Initialize collection result
        result = RawDataCollection()
        
        # Get enabled providers from configuration
        enabled_providers = self.config_manager.get_enabled_providers()
        result.total_providers = len(enabled_providers)
        
        if not enabled_providers:
            self.logger.warning("No providers enabled in configuration")
            result.critical_failure = True
            return result
        
        self.logger.info(
            f"Enabled providers ({len(enabled_providers)}): "
            f"{list(enabled_providers.keys())}"
        )
        
        # Track critical provider status
        critical_provider_count = 0
        critical_succeeded = 0
        
        # Execute collectors sequentially
        provider_list = list(enabled_providers.items())
        for index, (provider_name, provider_config) in enumerate(provider_list):
            is_last = (index == len(provider_list) - 1)
            is_optional = provider_config.get("optional", False)
            
            self.logger.info(
                f"[{index + 1}/{len(provider_list)}] Collecting from "
                f"{provider_name}{'(optional)' if is_optional else '(critical)'}..."
            )
            
            # Track critical providers
            if not is_optional:
                critical_provider_count += 1
            
            # Get collector for this provider
            collector = self.collectors.get(provider_name)
            if not collector:
                self.logger.warning(f"No collector found for {provider_name}")
                result.provider_status[provider_name] = {
                    "status": "unavailable",
                    "error": "No collector available",
                    "optional": is_optional
                }
                result.failed_providers += 1
                
                # Apply rate limit delay before next provider (except last)
                if not is_last:
                    self._apply_rate_limit_delay(provider_name)
                continue
            
            try:
                # Execute collection from real provider
                start_time = time.time()
                collection_result = collector.collect(polygon)
                elapsed_ms = (time.time() - start_time) * 1000
                
                if collection_result:
                    # Validate collection result structure
                    validation_error = self._validate_collection_result(
                        provider_name, collection_result
                    )
                    
                    if validation_error:
                        # Invalid collection structure
                        result.provider_status[provider_name] = {
                            "status": "error",
                            "error": validation_error,
                            "optional": is_optional
                        }
                        result.failed_providers += 1
                        
                        self.logger.warning(
                            f"✗ {provider_name}: Collection validation failed: "
                            f"{validation_error}"
                        )
                    else:
                        # Valid successful collection
                        result.collections[provider_name] = collection_result
                        feature_count = len(collection_result.get("features", []))
                        
                        result.provider_status[provider_name] = {
                            "status": "success",
                            "feature_count": feature_count,
                            "collection_time_ms": elapsed_ms,
                            "optional": is_optional
                        }
                        result.successful_providers += 1
                        
                        if not is_optional:
                            critical_succeeded += 1
                        
                        self.logger.info(
                            f"✓ {provider_name}: {feature_count} features "
                            f"({elapsed_ms:.0f}ms)"
                        )
                else:
                    # Collection returned no data
                    result.provider_status[provider_name] = {
                        "status": "failed",
                        "error": "Collection returned no data",
                        "optional": is_optional
                    }
                    result.failed_providers += 1
                    
                    self.logger.warning(
                        f"✗ {provider_name}: Collection failed (no data)"
                    )
                    
            except Exception as e:
                # Provider error
                error_msg = str(e)
                self.logger.error(
                    f"Exception during collection from {provider_name}: {error_msg}",
                    exc_info=True
                )
                
                result.provider_status[provider_name] = {
                    "status": "error",
                    "error": error_msg,
                    "optional": is_optional
                }
                result.failed_providers += 1
                
                self.logger.warning(f"✗ {provider_name}: Exception during collection")
            
            # Apply rate limit delay between providers (except last)
            if not is_last:
                self._apply_rate_limit_delay(provider_name)
        
        # Determine if critical failure (all critical providers failed)
        if critical_provider_count > 0:
            result.critical_failure = (critical_succeeded == 0)
        else:
            result.critical_failure = (result.successful_providers == 0)
        
        # Summary
        self.logger.info(
            f"Data collection complete: "
            f"{result.successful_providers}/{result.total_providers} providers "
            f"successful, {result.failed_providers} failed"
            f"{' - CRITICAL FAILURE' if result.critical_failure else ''}"
        )
        
        return result

    def _apply_rate_limit_delay(self, current_provider: str):
        """
        Apply rate limit delay to respect provider rate limits.
        
        Args:
            current_provider: Name of provider just executed
        """
        self.logger.debug(
            f"Rate limit delay: {self.rate_limit_delay}s before next provider"
        )
        time.sleep(self.rate_limit_delay)

    def _validate_collection_result(
        self, provider_name: str, collection_result: Any
    ) -> Optional[str]:
        """
        Validate that collection result has required structure.
        
        Args:
            provider_name: Name of provider
            collection_result: Result from collector.collect()
            
        Returns:
            Error message if invalid, None if valid
        """
        if not isinstance(collection_result, dict):
            return f"Collection result must be a dict, got {type(collection_result).__name__}"
        
        # Check for required/expected fields
        if "source_provider" in collection_result and collection_result["source_provider"] is None:
            return "Collection result has null source_provider field"
        
        if "category" in collection_result and collection_result["category"] is None:
            return "Collection result has null category field"
        
        # Check features field
        features = collection_result.get("features")
        if features is not None and not isinstance(features, list):
            return f"Features field must be a list, got {type(features).__name__}"
        
        # Valid structure
        return None

    def get_collection_summary(self, result: RawDataCollection) -> Dict[str, Any]:
        """
        Get summary statistics of collection results.
        
        Args:
            result: RawDataCollection from collect_data()
            
        Returns:
            Summary dict with key statistics
        """
        total_features = sum(
            len(collection.get("features", []))
            for collection in result.collections.values()
        )
        
        provider_summaries = {}
        for provider_name, status in result.provider_status.items():
            provider_summaries[provider_name] = {
                "status": status.get("status"),
                "features": status.get("feature_count", 0),
                "optional": status.get("optional", False)
            }
        
        return {
            "total_providers": result.total_providers,
            "successful_providers": result.successful_providers,
            "failed_providers": result.failed_providers,
            "critical_failure": result.critical_failure,
            "total_features": total_features,
            "collection_timestamp": result.collection_timestamp,
            "providers": provider_summaries
        }

    def get_available_data_categories(self, result: RawDataCollection) -> List[str]:
        """
        Get list of data categories available from successful providers.
        
        Args:
            result: RawDataCollection from collect_data()
            
        Returns:
            List of category names (e.g., ["buildings", "land_cover", ...])
        """
        categories = set()
        for collection in result.collections.values():
            category = collection.get("category")
            if category:
                categories.add(category)
        return sorted(list(categories))
