"""
Data Standardizer - Converts provider-specific data formats to common internal format.
Normalizes coordinate systems, field names, and data structure.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from backend.data_models import RawDataset, StandardizedDataset, Feature
from backend.standardizers.landcover_standardizer import LandCoverStandardizer
from backend.standardizers.elevation_standardizer import ElevationStandardizer


logger = logging.getLogger(__name__)


class StandardizationError(Exception):
    """Raised when standardization fails."""
    pass


class DataStandardizer:
    """
    Standardizes raw data from various providers into a common internal format.
    
    Responsibilities:
    - Normalize field names across providers
    - Normalize data structure to common schema
    - Map provider-specific values to standardized categories
    - Preserve data integrity and source attribution
    - Assumes all input data is in WGS84 (EPSG:4326)
    """

    def __init__(self):
        """Initialize the Data Standardizer."""
        pass

    def standardize(self, raw_dataset: RawDataset) -> StandardizedDataset:
        """
        Convert raw dataset to standardized format.

        Args:
            raw_dataset: Raw data from a provider

        Returns:
            StandardizedDataset with normalized format

        Raises:
            StandardizationError: If standardization fails
        """
        try:
            logger.info(
                f"Standardizing dataset from {raw_dataset.source_provider} "
                f"(category: {raw_dataset.category})"
            )

            # Get standardization rules for this category
            normalizer = self._get_category_normalizer(
                raw_dataset.category, 
                provider=raw_dataset.source_provider
            )

            # Process features
            standardized_features = []
            for feature in raw_dataset.features:
                try:
                    # Convert feature dict if needed
                    if hasattr(feature, 'model_dump'):
                        feature_dict = feature.model_dump()
                    elif hasattr(feature, 'dict'):
                        feature_dict = feature.dict()
                    else:
                        feature_dict = feature

                    std_feature = normalizer.normalize_feature(feature_dict)
                    standardized_features.append(std_feature)
                except Exception as e:
                    logger.warning(
                        f"Failed to standardize feature: {str(e)}"
                    )
                    continue

            # Build standardized dataset
            standardized = StandardizedDataset(
                category=raw_dataset.category,
                source_provider=raw_dataset.source_provider,
                features=standardized_features,
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "crs": "EPSG:4326",
                    "record_count": len(standardized_features),
                    "source_provider": raw_dataset.source_provider,
                    "original_crs": raw_dataset.metadata.get("crs", "unknown"),
                    "source_version": raw_dataset.metadata.get("version", "unknown"),
                    "version": raw_dataset.metadata.get("version", "unknown")
                }
            )

            logger.info(
                f"Standardized {len(standardized_features)} features "
                f"from {raw_dataset.source_provider}"
            )

            return standardized

        except Exception as e:
            raise StandardizationError(
                f"Standardization failed for {raw_dataset.source_provider}: {str(e)}"
            )

    def _get_category_normalizer(self, category: str, provider: str = "unknown") -> "CategoryNormalizer":
        """Get the appropriate normalizer for a data category."""
        category_lower = category.lower().replace("-", "_")
        
        normalizers = {
            "buildings": BuildingsNormalizer(),
            "admin": AdminBoundariesNormalizer(),
            "admin_boundaries": AdminBoundariesNormalizer(),
            "land_cover": LandCoverNormalizer(provider=provider),
            "landcover": LandCoverNormalizer(provider=provider),
            "roads": RoadsNormalizer(),
            "water": WaterNormalizer(),
            "elevation": ElevationNormalizer(),
        }
        return normalizers.get(category_lower, GenericNormalizer())


# ============================================================================
# Base Normalizer Class
# ============================================================================

class CategoryNormalizer:
    """Base class for category-specific normalization."""

    def normalize_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a feature for this category.

        Args:
            feature: Raw feature from provider (dict or Pydantic model)

        Returns:
            Standardized feature dictionary
        """
        # Handle both dict and Pydantic model
        if hasattr(feature, 'model_dump'):
            # Pydantic v2 model
            feature_dict = feature.model_dump()
        elif hasattr(feature, 'dict'):
            # Pydantic v1 model
            feature_dict = feature.dict()
        else:
            # Already a dict
            feature_dict = feature

        # Extract components
        feature_id = feature_dict.get("id", "")
        geometry = feature_dict.get("geometry", {})
        properties = feature_dict.get("properties", {})

        # Normalize properties
        normalized_props = self.normalize_properties(properties)

        # Build standardized feature
        return {
            "id": feature_id,
            "geometry": geometry,
            "properties": normalized_props
        }

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize properties for this category. Override in subclasses.

        Args:
            properties: Raw properties from provider

        Returns:
            Normalized properties dictionary
        """
        return properties


class GenericNormalizer(CategoryNormalizer):
    """Generic normalizer for unknown categories."""

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Keep properties as-is for unknown categories."""
        return {
            "type": properties.get("type", "unknown"),
            "name": properties.get("name", ""),
        }


# ============================================================================
# Category-Specific Normalizers
# ============================================================================

class BuildingsNormalizer(CategoryNormalizer):
    """Normalizes building feature properties."""

    BUILDING_TYPE_MAP = {
        "yes": "building",
        "residential": "residential",
        "commercial": "commercial",
        "office": "office",
        "industrial": "industrial",
        "warehouse": "warehouse",
        "garage": "garage",
        "apartments": "apartments",
        "house": "house",
    }

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize building properties to common schema."""
        building_type = properties.get("type", "yes")
        normalized_type = self.BUILDING_TYPE_MAP.get(
            building_type.lower(), "building"
        )

        return {
            "name": properties.get("name", ""),
            "type": normalized_type,
            "levels": self._extract_levels(properties),
            "material": properties.get("material", "unknown"),
            "source_type": properties.get("type", "unknown"),
        }

    def _extract_levels(self, properties: Dict[str, Any]) -> int:
        """Extract building levels/stories if available."""
        levels = properties.get("levels")
        if levels:
            try:
                return int(levels)
            except (ValueError, TypeError):
                pass
        return 1


class AdminBoundariesNormalizer(CategoryNormalizer):
    """Normalizes administrative boundary properties."""

    ADMIN_TYPE_MAP = {
        "2": "country",
        "3": "macro_region",
        "4": "state",
        "5": "province",
        "6": "district",
    }

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize admin boundary properties to common schema."""
        admin_level = str(properties.get("admin_level", ""))
        admin_type = self.ADMIN_TYPE_MAP.get(admin_level, "administrative")

        return {
            "name": properties.get("name", ""),
            "type": admin_type,
            "admin_level": admin_level,
            "country_code": properties.get("country_code", ""),
            "country": properties.get("country", ""),
        }


class LandCoverNormalizer(CategoryNormalizer):
    """
    Normalizes land cover classification properties.
    
    Uses LandCoverStandardizer to handle provider-specific land cover formats.
    Supports Copernicus GLC, ESA WorldCover, and other land cover providers.
    """
    
    def __init__(self, provider: str = "copernicus"):
        """Initialize with optional provider info."""
        self.provider = provider

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize land cover properties to common schema.
        
        Uses LandCoverStandardizer for comprehensive field mapping,
        code translation, and value normalization.
        """
        # Use LandCoverStandardizer for comprehensive field normalization
        standardized = LandCoverStandardizer.standardize_properties(
            properties, provider=self.provider
        )
        
        # Ensure required fields are present with defaults
        return {
            "lc_code": standardized.get("lc_code", ""),
            "lc_class": standardized.get("lc_class", "unknown"),
            "lc_name": standardized.get("lc_name", ""),
            "confidence": standardized.get("confidence", 0.5),
            "confidence_percent": standardized.get("confidence_percent"),
            "source": standardized.get("source", "unknown"),
            "version": standardized.get("version"),
            "epoch": standardized.get("epoch"),
            "percent_water": standardized.get("percent_water"),
            "percent_tree": standardized.get("percent_tree"),
            "percent_grass": standardized.get("percent_grass"),
            "percent_crops": standardized.get("percent_crops"),
            "percent_built": standardized.get("percent_built"),
            "percent_bare": standardized.get("percent_bare"),
            "resolution_m": standardized.get("resolution_m"),
            "valid": standardized.get("valid"),
        }


class RoadsNormalizer(CategoryNormalizer):
    """Normalizes road network properties."""

    ROAD_TYPE_MAP = {
        "motorway": "motorway",
        "trunk": "trunk",
        "primary": "primary",
        "secondary": "secondary",
        "tertiary": "tertiary",
        "unclassified": "unclassified",
        "residential": "residential",
        "service": "service",
        "pedestrian": "pedestrian",
        "track": "track",
        "path": "path",
    }

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize road properties to common schema."""
        road_type = properties.get("type", "unclassified")
        normalized_type = self.ROAD_TYPE_MAP.get(
            road_type.lower(), "unclassified"
        )

        return {
            "name": properties.get("name", ""),
            "type": normalized_type,
            "surface": properties.get("surface", "unknown"),
            "lanes": int(properties.get("lanes", 1)) if properties.get("lanes") else 1,
            "source_type": properties.get("type", "unknown"),
        }


class WaterNormalizer(CategoryNormalizer):
    """Normalizes water bodies properties."""

    WATER_TYPE_MAP = {
        "river": "river",
        "canal": "canal",
        "stream": "stream",
        "pond": "pond",
        "lake": "lake",
        "reservoir": "reservoir",
        "water": "water_area",
    }

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize water feature properties to common schema."""
        water_type = properties.get("type", "water")
        normalized_type = self.WATER_TYPE_MAP.get(
            water_type.lower(), "water_area"
        )

        return {
            "name": properties.get("name", ""),
            "type": normalized_type,
            "water_type": water_type,
            "flow_direction": properties.get("flow_direction", "unknown"),
        }


class ElevationNormalizer(CategoryNormalizer):
    """
    Normalizes elevation data properties.
    
    Uses ElevationStandardizer to handle provider-specific elevation formats.
    Supports USGS DEM, GEBCO ocean bathymetry, and other elevation data providers.
    """

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize elevation properties to common schema.
        
        Uses ElevationStandardizer for comprehensive field mapping,
        category assignment, and value normalization.
        """
        # Use ElevationStandardizer for comprehensive field normalization
        standardized = ElevationStandardizer.standardize_properties(
            properties, provider="usgs"
        )
        
        # Ensure required fields are present with defaults
        return {
            "elevation_m": standardized.get("elevation_m"),
            "elevation_ft": standardized.get("elevation_ft"),
            "min_elevation_m": standardized.get("min_elevation_m"),
            "max_elevation_m": standardized.get("max_elevation_m"),
            "mean_elevation_m": standardized.get("mean_elevation_m"),
            "elevation_std_m": standardized.get("elevation_std_m"),
            "elevation_category": standardized.get("elevation_category"),
            "elevation_range_m": standardized.get("elevation_range_m"),
            "slope_degrees": standardized.get("slope_degrees"),
            "slope_percent": standardized.get("slope_percent"),
            "slope_category": standardized.get("slope_category"),
            "aspect_degrees": standardized.get("aspect_degrees"),
            "terrain_type": standardized.get("terrain_type"),
            "roughness": standardized.get("roughness"),
            "ruggedness": standardized.get("ruggedness"),
            "source": standardized.get("source", "unknown"),
            "resolution_m": standardized.get("resolution_m"),
            "accuracy_m": standardized.get("accuracy_m"),
            "coverage_percent": standardized.get("coverage_percent"),
            "nodata_percent": standardized.get("nodata_percent"),
            "depth_m": standardized.get("depth_m"),
            "min_depth_m": standardized.get("min_depth_m"),
            "max_depth_m": standardized.get("max_depth_m"),
            "mean_depth_m": standardized.get("mean_depth_m"),
            "version": standardized.get("version"),
            "timestamp": standardized.get("timestamp"),
            "datum": standardized.get("datum"),
            "vertical_datum": standardized.get("vertical_datum"),
            "suggested_vertical_exaggeration": standardized.get("suggested_vertical_exaggeration"),
        }
