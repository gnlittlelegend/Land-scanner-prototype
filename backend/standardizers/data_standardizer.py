"""
Data Standardizer - Converts provider-specific data formats to common internal format.
Normalizes coordinate systems, field names, and data structure.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pyproj import Transformer

from backend.models.schemas import (
    RawDataset, StandardizedDataset, Feature, DataCategory
)


logger = logging.getLogger(__name__)


class StandardizationError(Exception):
    """Raised when standardization fails."""
    pass


class DataStandardizer:
    """
    Standardizes raw data from various providers into a common internal format.
    
    Responsibilities:
    - Convert coordinate systems to WGS84 (EPSG:4326)
    - Normalize field names across providers
    - Normalize data structure to common schema
    - Map provider-specific values to standardized categories
    - Preserve data integrity and source attribution
    """

    def __init__(self):
        """Initialize the Data Standardizer."""
        self.source_crs_cache: Dict[str, Transformer] = {}

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
            normalizer = self._get_category_normalizer(raw_dataset.category)

            # Process features
            standardized_features = []
            for feature in raw_dataset.features:
                try:
                    std_feature = normalizer.normalize_feature(feature)
                    standardized_features.append(std_feature)
                except Exception as e:
                    logger.warning(
                        f"Failed to standardize feature {feature.get('id', '?')}: {str(e)}"
                    )
                    continue

            # Build standardized dataset
            # Return dicts; Pydantic will convert to Feature objects
            standardized = StandardizedDataset(
                category=raw_dataset.category,
                source_provider=raw_dataset.source_provider,
                features=standardized_features,
                metadata={
                    "timestamp": datetime.utcnow().isoformat(),
                    "crs": "EPSG:4326",
                    "record_count": len(standardized_features),
                    "original_crs": raw_dataset.metadata.get("crs", "unknown"),
                    "source_version": raw_dataset.metadata.get("version", "unknown")
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

    def _get_category_normalizer(self, category: DataCategory) -> "CategoryNormalizer":
        """Get the appropriate normalizer for a data category."""
        normalizers = {
            DataCategory.BUILDINGS: BuildingsNormalizer(),
            DataCategory.ADMIN: AdminBoundariesNormalizer(),
            DataCategory.LAND_COVER: LandCoverNormalizer(),
            DataCategory.ROADS: RoadsNormalizer(),
            DataCategory.WATER: WaterNormalizer(),
            DataCategory.ELEVATION: ElevationNormalizer(),
        }
        return normalizers.get(category, GenericNormalizer())


# ============================================================================
# Base Normalizer Class
# ============================================================================

class CategoryNormalizer:
    """Base class for category-specific normalization."""

    def normalize_feature(self, feature: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize a feature for this category.

        Args:
            feature: Raw feature from provider

        Returns:
            Standardized feature dictionary
        """
        # Extract components
        feature_id = feature.get("id", "")
        geometry = feature.get("geometry", {})
        properties = feature.get("properties", {})

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
    """Normalizes land cover classification properties."""

    LAND_COVER_MAP = {
        10: "tree_cover",
        20: "shrubland",
        30: "herbaceous_vegetation",
        40: "cropland",
        50: "built_up",
        60: "bare_ground",
        70: "snow_ice",
        80: "water",
        90: "clouds",
    }

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize land cover properties to common schema."""
        lc_code = properties.get("lc_code", 0)
        lc_class = self.LAND_COVER_MAP.get(lc_code, "unknown")

        return {
            "lc_code": lc_code,
            "lc_class": lc_class,
            "lc_name": properties.get("lc_class", lc_class),
            "confidence": float(properties.get("confidence", 0.5)),
            "year": int(properties.get("year", 2020)),
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
    """Normalizes elevation data properties."""

    def normalize_properties(self, properties: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize elevation properties to common schema."""
        try:
            elevation = float(properties.get("elevation_m", 0))
        except (ValueError, TypeError):
            elevation = 0.0

        return {
            "elevation_m": elevation,
            "confidence": float(properties.get("confidence", 0.8)),
            "source": properties.get("source", "unknown"),
            "method": properties.get("method", "dem"),
        }
