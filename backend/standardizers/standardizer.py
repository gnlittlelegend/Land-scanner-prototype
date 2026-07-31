"""
Core Data Standardizer for normalizing diverse provider formats.

Responsibilities:
- Convert raw datasets from any provider to common internal format
- Normalize field names to lowercase with underscores
- Normalize coordinate systems to WGS84 (EPSG:4326)
- Normalize data structures to StandardizedDataset schema
- Preserve data integrity and source attribution
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from pyproj import Transformer
from shapely.geometry import shape, Point, LineString, Polygon as ShapelyPolygon
from shapely.geometry.base import BaseGeometry

from backend.models.schemas import (
    RawDataset,
    StandardizedDataset,
    Feature,
    DataCategory,
    ProcessingStatus,
)

logger = logging.getLogger(__name__)


class StandardizationError(Exception):
    """Raised when standardization fails."""
    pass


class Standardizer:
    """
    Standardizes raw datasets from various providers into common format.
    
    All outputs use WGS84 (EPSG:4326) coordinates and follow StandardizedDataset schema.
    Provider-specific data is never exposed outside this component.
    """

    def __init__(self):
        """Initialize the Standardizer with CRS transformers for common coordinate systems."""
        # Create transformers for common CRS to WGS84
        # These will be cached and reused
        self.transformers: Dict[str, Transformer] = {}
        self._init_transformers()

    def _init_transformers(self) -> None:
        """Initialize CRS transformers for common coordinate systems."""
        common_crs = [
            "EPSG:3857",  # Web Mercator
            "EPSG:3395",  # World Mercator
            "EPSG:2154",  # French Lambert 93
            "EPSG:25832", # ETRS89 / UTM zone 32N
            "EPSG:25833", # ETRS89 / UTM zone 33N
            "EPSG:32632", # WGS 84 / UTM zone 32N
            "EPSG:32633", # WGS 84 / UTM zone 33N
        ]
        
        for crs in common_crs:
            try:
                self.transformers[crs] = Transformer.from_crs(
                    crs, "EPSG:4326", always_xy=True
                )
            except Exception as e:
                logger.warning(f"Failed to create transformer for {crs}: {e}")

    def standardize(self, raw_dataset: RawDataset) -> StandardizedDataset:
        """
        Standardize a raw dataset from any provider.
        
        Args:
            raw_dataset: Raw dataset from a data provider
            
        Returns:
            StandardizedDataset with normalized format
            
        Raises:
            StandardizationError: If standardization fails
        """
        try:
            # Standardize each feature
            standardized_features = []
            
            for raw_feature in raw_dataset.features:
                try:
                    standardized_feature = self._standardize_feature(
                        raw_feature,
                        raw_dataset.source_provider,
                        raw_dataset.category
                    )
                    standardized_features.append(standardized_feature)
                except Exception as e:
                    logger.warning(
                        f"Failed to standardize feature from {raw_dataset.source_provider}: {e}"
                    )
                    # Continue processing other features
                    continue

            # Build standardized metadata with actual count of standardized features
            standardized_metadata = self._standardize_metadata(
                raw_dataset.metadata,
                raw_dataset.source_provider,
                len(standardized_features)  # Use actual count
            )

            # Create StandardizedDataset
            standardized_dataset = StandardizedDataset(
                category=raw_dataset.category,
                source_provider=raw_dataset.source_provider,
                features=standardized_features,
                metadata=standardized_metadata
            )

            logger.info(
                f"Standardized dataset from {raw_dataset.source_provider} "
                f"({raw_dataset.category}): {len(standardized_features)} features"
            )

            return standardized_dataset

        except Exception as e:
            logger.error(f"Standardization failed for {raw_dataset.source_provider}: {e}")
            raise StandardizationError(
                f"Failed to standardize data from {raw_dataset.source_provider}: {str(e)}"
            )

    def _standardize_feature(
        self,
        raw_feature: Dict[str, Any],
        provider: str,
        category: DataCategory
    ) -> Feature:
        """
        Standardize a single raw feature.
        
        Args:
            raw_feature: Feature object from provider
            provider: Provider name (for logging)
            category: Data category
            
        Returns:
            Standardized Feature
            
        Raises:
            StandardizationError: If feature cannot be standardized
        """
        # Extract geometry and properties
        geometry_obj = raw_feature.get("geometry")
        properties_obj = raw_feature.get("properties", {})
        feature_id = raw_feature.get("id") or self._generate_feature_id(raw_feature)

        if geometry_obj is None:
            raise StandardizationError("Feature missing geometry")

        # Normalize geometry to WGS84
        normalized_geometry = self._normalize_geometry(geometry_obj)

        # Normalize properties
        normalized_properties = self._normalize_properties(
            properties_obj, provider, category
        )

        # Create standardized feature
        feature = Feature(
            id=str(feature_id),
            geometry=normalized_geometry,
            properties=normalized_properties
        )

        return feature
    
    def _count_valid_features(self, features: List[Dict[str, Any]]) -> int:
        """
        Count features that have valid geometry.
        
        Args:
            features: List of raw features
            
        Returns:
            Count of features with valid geometry
        """
        count = 0
        for feature in features:
            if feature.get("geometry") is not None:
                count += 1
        return count

    def _normalize_geometry(self, geometry_obj: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize geometry to WGS84 and standard GeoJSON format.
        
        Args:
            geometry_obj: Raw GeoJSON geometry object
            
        Returns:
            Normalized GeoJSON geometry object (WGS84)
        """
        try:
            # Parse geometry using Shapely
            geom = shape(geometry_obj)

            # Get CRS info if available in geometry
            crs = geometry_obj.get("crs", {})
            
            # Transform to WGS84 if needed
            transformed_geom = self._transform_geometry(geom, crs)

            # Convert back to GeoJSON
            normalized_geojson = {
                "type": transformed_geom.geom_type,
                "coordinates": self._get_coordinates(transformed_geom)
            }

            return normalized_geojson

        except Exception as e:
            logger.warning(f"Failed to normalize geometry: {e}")
            # Return geometry as-is if transformation fails
            # Assume it's already in WGS84
            return geometry_obj

    def _transform_geometry(
        self,
        geom: BaseGeometry,
        crs_info: Dict[str, Any]
    ) -> BaseGeometry:
        """
        Transform geometry to WGS84 if it's in a different CRS.
        
        Args:
            geom: Shapely geometry object
            crs_info: CRS information from GeoJSON
            
        Returns:
            Transformed geometry in WGS84
        """
        # Extract CRS code if available
        source_crs = None
        
        if isinstance(crs_info, dict):
            if "properties" in crs_info:
                source_crs = crs_info["properties"].get("name")
            else:
                source_crs = crs_info.get("name")

        if not source_crs or source_crs == "EPSG:4326":
            # Already in WGS84
            return geom

        # Check if we have a transformer for this CRS
        transformer = self.transformers.get(source_crs)
        
        if not transformer:
            logger.warning(f"No transformer for {source_crs}, assuming WGS84")
            return geom

        # Transform coordinates
        return self._apply_transform(geom, transformer)

    def _apply_transform(
        self,
        geom: BaseGeometry,
        transformer: Transformer
    ) -> BaseGeometry:
        """
        Apply coordinate transformation to a geometry.
        
        Args:
            geom: Shapely geometry
            transformer: Coordinate transformer
            
        Returns:
            Transformed geometry
        """
        def transform_coords(coords):
            if isinstance(coords[0], (list, tuple)):
                # Nested coordinates (rings, parts, etc.)
                return [transform_coords(c) for c in coords]
            else:
                # Single coordinate pair
                x, y = coords[0], coords[1]
                transformed_x, transformed_y = transformer.transform(x, y)
                return [transformed_x, transformed_y] + list(coords[2:])

        coords = list(geom.coords) if hasattr(geom, 'coords') else geom.exterior.coords
        
        if geom.geom_type == "Point":
            transformed = transform_coords(list(geom.coords[0]))
            return Point(transformed[0], transformed[1])
        elif geom.geom_type == "LineString":
            transformed = [transform_coords([c]) for c in geom.coords]
            return LineString([t[0] if isinstance(t[0], (list, tuple)) else t 
                             for t in transformed])
        elif geom.geom_type == "Polygon":
            exterior = [transform_coords([c]) for c in geom.exterior.coords]
            exterior_flat = [c[0] if isinstance(c[0], (list, tuple)) else c 
                            for c in exterior]
            interiors = []
            for interior in geom.interiors:
                interior_coords = [transform_coords([c]) for c in interior.coords]
                interior_flat = [c[0] if isinstance(c[0], (list, tuple)) else c 
                               for c in interior_coords]
                interiors.append(interior_flat)
            return ShapelyPolygon(exterior_flat, interiors)
        
        return geom

    def _get_coordinates(self, geom: BaseGeometry) -> Any:
        """
        Extract coordinates from a Shapely geometry in GeoJSON format.
        
        Args:
            geom: Shapely geometry
            
        Returns:
            Coordinates in GeoJSON format
        """
        if geom.geom_type == "Point":
            return list(geom.coords[0])
        elif geom.geom_type == "LineString":
            return [list(c) for c in geom.coords]
        elif geom.geom_type == "Polygon":
            coords = [list(geom.exterior.coords)]
            coords.extend([list(interior.coords) for interior in geom.interiors])
            return coords
        elif geom.geom_type == "MultiPoint":
            return [list(c) for c in geom.geoms]
        elif geom.geom_type == "MultiLineString":
            return [[list(c) for c in g.coords] for g in geom.geoms]
        elif geom.geom_type == "MultiPolygon":
            coords = []
            for poly in geom.geoms:
                polygon_coords = [list(poly.exterior.coords)]
                polygon_coords.extend([list(interior.coords) 
                                      for interior in poly.interiors])
                coords.append(polygon_coords)
            return coords
        
        return list(geom.coords) if hasattr(geom, 'coords') else []

    def _normalize_properties(
        self,
        properties_obj: Dict[str, Any],
        provider: str,
        category: DataCategory
    ) -> Dict[str, Any]:
        """
        Normalize property names and values.
        
        Field names are normalized to lowercase with underscores.
        Provider-specific naming conventions are converted to standard format.
        
        Args:
            properties_obj: Raw properties from provider
            provider: Provider name
            category: Data category
            
        Returns:
            Normalized properties dictionary
        """
        normalized = {}
        
        for key, value in properties_obj.items():
            # Normalize key: lowercase, replace spaces/hyphens with underscores
            normalized_key = self._normalize_key(key)
            
            # Skip empty or null values
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            
            # Normalize value based on type
            normalized_value = self._normalize_value(value, normalized_key)
            
            normalized[normalized_key] = normalized_value
        
        # Add provider attribution
        normalized["_source_provider"] = provider
        
        # Add category if not already present
        if "_category" not in normalized:
            normalized["_category"] = category.value
        
        return normalized

    def _normalize_key(self, key: str) -> str:
        """
        Normalize a property key to lowercase with underscores.
        
        Examples:
            "BuildingArea" -> "building_area"
            "building-type" -> "building_type"
            "building.type" -> "building_type"
            "BUILDING TYPE" -> "building_type"
        """
        # Replace common separators with underscores
        key = key.replace("-", "_").replace(".", "_").replace(" ", "_")
        
        # Convert CamelCase to snake_case
        import re
        key = re.sub("([a-z0-9])([A-Z])", r"\1_\2", key)
        
        # Convert to lowercase
        key = key.lower()
        
        # Remove duplicate underscores
        key = re.sub("_+", "_", key)
        
        # Remove leading/trailing underscores
        key = key.strip("_")
        
        return key

    def _normalize_value(self, value: Any, key: str) -> Any:
        """
        Normalize a property value based on its type and key.
        
        Args:
            value: Raw value from provider
            key: Normalized property key
            
        Returns:
            Normalized value
        """
        if value is None:
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            # Try to convert to appropriate numeric type
            try:
                if isinstance(value, float) and value.is_integer():
                    return int(value)
                return value
            except Exception:
                return value
        
        if isinstance(value, str):
            # Try to convert numeric strings
            try:
                if "." in value:
                    return float(value)
                return int(value)
            except ValueError:
                # Keep as string
                return value.strip()
        
        if isinstance(value, (list, dict)):
            # Keep complex types as-is but convert to JSON-serializable format
            return value
        
        return value

    def _standardize_metadata(
        self,
        raw_metadata: Dict[str, Any],
        provider: str,
        record_count: int = 0
    ) -> Dict[str, Any]:
        """
        Standardize dataset metadata.
        
        Args:
            raw_metadata: Raw metadata from provider
            provider: Provider name
            record_count: Number of standardized features
            
        Returns:
            Standardized metadata dictionary
        """
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "crs": "EPSG:4326",  # Always WGS84 after standardization
            "source_provider": provider,
            "record_count": record_count,
            "version": raw_metadata.get("version", "unknown"),
        }

    def _generate_feature_id(self, feature: Dict[str, Any]) -> str:
        """
        Generate a unique feature ID if one is not provided.
        
        Args:
            feature: Feature object
            
        Returns:
            Generated feature ID
        """
        import hashlib
        import json
        
        # Create a deterministic hash of the feature
        feature_str = json.dumps(feature, sort_keys=True, default=str)
        feature_hash = hashlib.md5(feature_str.encode()).hexdigest()[:8]
        return f"feature_{feature_hash}"
