"""
Base Collector class for Land Scanner Prototype.

Defines the interface for all data collectors and provides
common HTTP request handling, retry logic, and error handling.

This module implements the DataCollector abstract base class that all
real data collectors must inherit from. It ensures consistent HTTP handling,
timeout management, and graceful failure handling across all providers.

Requirements Met:
- Abstract collector interface: collect(polygon) -> RawDataset
- RawDataset model with required fields
- HTTP request handling with timeout management
- Exponential backoff retry logic
- Generic error handling for provider failures
- All collectors use real HTTP requests (no mock adapters)
"""

import logging
import time
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CollectionError(Exception):
    """Raised when data collection fails."""
    pass


class TimeoutError(CollectionError):
    """Raised when request times out."""
    pass


class RateLimitError(CollectionError):
    """Raised when rate limited by provider."""
    pass


class DataCollector(ABC):
    """
    Abstract base class for all data collectors.
    
    Every concrete collector must:
    1. Inherit from DataCollector
    2. Implement the collect(polygon) method
    3. Return a dict matching RawDataset structure
    4. Use _make_request() for all HTTP requests
    
    Provides common functionality for:
    - HTTP request handling with timeout management (configurable per collector)
    - Exponential backoff retry logic for transient failures
    - Error handling for provider failures (timeout, 429, 5xx, connection errors)
    - Request/response logging for debugging
    - Metadata tracking (timestamp, provider info, attempt count)
    """

    def __init__(
        self,
        provider_name: str,
        endpoint: str,
        timeout: int = 30,
        max_retries: int = 2,
        retry_delay_base: float = 2.0
    ):
        """
        Initialize collector with production API endpoint.
        
        Args:
            provider_name: Human-readable name of the data provider (e.g., "OSM Buildings")
            endpoint: Real production API endpoint URL (not mock URL)
            timeout: Request timeout in seconds (default 30, actual may be longer for raster data)
            max_retries: Maximum number of retry attempts for transient failures (default 2)
            retry_delay_base: Base delay in seconds for exponential backoff (default 2.0)
            
        Note: All endpoints MUST be real production URLs, not test/mock endpoints.
        """
        self.provider_name = provider_name
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay_base = retry_delay_base
        self.session = requests.Session()
        self.logger = logging.getLogger(f"{__name__}.{provider_name}")
        
    @abstractmethod
    def collect(self, polygon: Dict[str, Any]) -> Dict[str, Any]:
        """
        Collect data from the provider for the given polygon.
        
        This method MUST be implemented by all subclasses.
        
        Args:
            polygon: Validated polygon dict with structure:
                {
                    "type": "Feature",
                    "geometry": {"type": "Polygon", "coordinates": [...]},
                    "properties": {
                        "area_sqm": float,
                        "bounding_box": {"min_lon", "min_lat", "max_lon", "max_lat"},
                        "centroid": {"longitude": float, "latitude": float},
                        "vertex_count": int,
                        "crs": "EPSG:4326"
                    }
                }
            
        Returns:
            Dictionary matching RawDataset structure:
            {
                "source_provider": str (provider name),
                "category": str (buildings|land_cover|roads|water|elevation|admin),
                "features": [  # List of GeoJSON features
                    {
                        "id": str,
                        "type": "Feature",
                        "geometry": {...},
                        "properties": {...}
                    }
                ],
                "metadata": {
                    "timestamp": datetime.isoformat(),
                    "feature_count": int,
                    "collection_time_ms": float,
                    "attempt_count": int,
                    "status": "success|empty|timeout|error"
                }
            }
            
        Raises:
            CollectionError: If collection fails (timeout, provider error, network error)
        """
        pass

    def _make_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Optional[requests.Response]:
        """
        Make an HTTP request with production API endpoint and exponential backoff retry.
        
        This is the ONLY way to make HTTP requests in collectors. It handles:
        - Timeout management (configurable per collector, default 30s)
        - Exponential backoff retry for transient failures
        - Rate limit handling (HTTP 429)
        - Connection errors (timeout, refused, DNS)
        - Server errors (5xx)
        
        Exponential backoff formula:
            delay = retry_delay_base * (2 ^ attempt_number)
            
        Examples:
            - First retry: 2 * (2^0) = 2 seconds
            - Second retry: 2 * (2^1) = 4 seconds
            - Third retry: 2 * (2^2) = 8 seconds
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Real production API endpoint URL
            **kwargs: Additional arguments for requests (headers, data, params, etc.)
            
        Returns:
            Response object if successful (status 200-299)
            None if all retries exhausted or unrecoverable error
        """
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.info(
                    f"HTTP request: {method} {url} "
                    f"(attempt {attempt + 1}/{self.max_retries + 1}, "
                    f"timeout={self.timeout}s)"
                )
                
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs
                )
                
                # Success (2xx status code)
                if 200 <= response.status_code < 300:
                    self.logger.info(
                        f"✓ Success: {response.status_code} "
                        f"({len(response.content)} bytes)"
                    )
                    return response
                
                # Rate limit (429) - retry with backoff
                elif response.status_code == 429:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay_base * (2 ** attempt)
                        self.logger.warning(
                            f"⚠ Rate limited (429). Waiting {wait_time:.1f}s before retry..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(
                            f"✗ Rate limited (429) - max retries exhausted"
                        )
                        return None
                
                # Server error (5xx) - retry with backoff
                elif response.status_code >= 500:
                    if attempt < self.max_retries:
                        wait_time = self.retry_delay_base * (2 ** attempt)
                        self.logger.warning(
                            f"⚠ Server error ({response.status_code}). "
                            f"Waiting {wait_time:.1f}s before retry..."
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        self.logger.error(
                            f"✗ Server error ({response.status_code}) - "
                            f"max retries exhausted"
                        )
                        return None
                
                # Client error (4xx) - don't retry
                else:
                    self.logger.error(
                        f"✗ HTTP {response.status_code}: {response.text[:200]}"
                    )
                    return None
                    
            except requests.Timeout:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay_base * (2 ** attempt)
                    self.logger.warning(
                        f"⚠ Timeout (>{self.timeout}s). "
                        f"Waiting {wait_time:.1f}s before retry..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(
                        f"✗ Timeout - max retries ({self.max_retries}) exhausted"
                    )
                    return None
                
            except requests.ConnectionError as e:
                if attempt < self.max_retries:
                    wait_time = self.retry_delay_base * (2 ** attempt)
                    self.logger.warning(
                        f"⚠ Connection error: {e}. "
                        f"Waiting {wait_time:.1f}s before retry..."
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    self.logger.error(
                        f"✗ Connection error - max retries exhausted: {e}"
                    )
                    return None
                
            except requests.RequestException as e:
                self.logger.error(f"✗ Request error: {e}")
                return None
            
            except Exception as e:
                self.logger.error(f"✗ Unexpected error: {e}", exc_info=True)
                return None
        
        self.logger.error(f"✗ All {self.max_retries + 1} attempts failed")
        return None

    def _get_bbox(self, polygon: Dict[str, Any]) -> tuple:
        """
        Extract bounding box from validated polygon.
        
        Args:
            polygon: Polygon dict with properties from PolygonValidator
            
        Returns:
            Tuple of (min_lon, min_lat, max_lon, max_lat) in WGS84
        """
        bbox = polygon.get('properties', {}).get('bounding_box')
        
        # Handle both dict and tuple formats
        if isinstance(bbox, dict):
            return (
                bbox.get('min_lon', 0),
                bbox.get('min_lat', 0),
                bbox.get('max_lon', 1),
                bbox.get('max_lat', 1)
            )
        elif isinstance(bbox, (tuple, list)) and len(bbox) == 4:
            # Shapely format: (minx, miny, maxx, maxy)
            return tuple(bbox)
        else:
            # Fallback - return default bbox
            return (0, 0, 1, 1)

    def _build_raw_dataset(
        self,
        category: str,
        features: List[Dict[str, Any]],
        attempt_count: int = 1,
        collection_time_ms: float = 0,
        status: str = "success",
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build RawDataset dict from collection results.
        
        Args:
            category: Data category (buildings|land_cover|roads|water|elevation|admin)
            features: List of GeoJSON features collected
            attempt_count: Number of HTTP attempts made
            collection_time_ms: Time taken for collection in milliseconds
            status: Collection status (success|empty|timeout|error)
            error_message: Optional error message if status is error
            
        Returns:
            Dict matching RawDataset structure with all required fields
        """
        return {
            "source_provider": self.provider_name,
            "category": category,
            "features": features,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "feature_count": len(features),
                "collection_time_ms": collection_time_ms,
                "attempt_count": attempt_count,
                "status": status,
                "error_message": error_message,
                "provider_endpoint": self.endpoint,
                "timeout_seconds": self.timeout
            }
        }

    def close(self):
        """Close HTTP session and cleanup resources."""
        self.session.close()
        self.logger.info(f"Collector session closed: {self.provider_name}")

    def __repr__(self) -> str:
        """String representation of collector."""
        return (
            f"{self.__class__.__name__}("
            f"provider={self.provider_name}, "
            f"endpoint={self.endpoint}, "
            f"timeout={self.timeout}s)"
        )
