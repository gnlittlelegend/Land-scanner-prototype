"""
Elevation Data-specific field normalization.

Maps provider-specific elevation fields to common standardized schema.
Handles elevation/DEM data from USGS, GEBCO, and other providers.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ElevationStandardizer:
    """
    Standardizes elevation data properties from various providers.
    
    Handles:
    - USGS elevation data
    - GEBCO ocean bathymetry data
    - DEM (Digital Elevation Model) data
    - Slope and aspect calculations
    """

    # Slope categories (degrees)
    SLOPE_CATEGORIES = {
        "flat": (0, 2),
        "gentle": (2, 5),
        "moderate": (5, 15),
        "steep": (15, 35),
        "very_steep": (35, 90),
    }

    # Elevation categories (meters)
    ELEVATION_CATEGORIES = {
        "below_sea_level": (-1000, 0),
        "sea_level": (0, 100),
        "low": (100, 500),
        "medium": (500, 1500),
        "high": (1500, 3000),
        "very_high": (3000, 9000),
    }

    # Mapping of provider-specific field names to standardized names
    FIELD_MAPPINGS = {
        # Elevation values
        ("elevation", "elev", "dem", "height"): "elevation_m",
        ("elevation_m", "elev_m"): "elevation_m",
        ("elevation_ft", "elev_ft"): "elevation_ft",
        ("elevation_min", "min_elevation"): "min_elevation_m",
        ("elevation_max", "max_elevation"): "max_elevation_m",
        ("elevation_mean", "mean_elevation", "avg_elevation"): "mean_elevation_m",
        ("elevation_std", "stdev_elevation"): "elevation_std_m",
        
        # Slope
        ("slope", "slope_degrees", "gradient"): "slope_degrees",
        ("slope_percent", "gradient_percent"): "slope_percent",
        ("slope_category", "terrain_slope"): "slope_category",
        
        # Aspect (directional slope)
        ("aspect", "aspect_degrees", "exposure", "slope_direction"): "aspect_degrees",
        
        # Terrain characteristics
        ("terrain_type", "terrain_class", "landform"): "terrain_type",
        ("roughness", "terrain_roughness"): "roughness",
        ("ruggedness", "terrain_ruggedness"): "ruggedness",
        
        # Data source and quality
        ("source", "dem_source", "data_source"): "source",
        ("resolution", "dem_resolution", "pixel_size"): "resolution_m",
        ("accuracy", "vertical_accuracy", "rmse"): "accuracy_m",
        ("coverage", "data_coverage", "percent_coverage"): "coverage_percent",
        ("nodata_percent",): "nodata_percent",
        
        # Bathymetry (underwater elevation)
        ("depth", "water_depth", "bathymetry"): "depth_m",
        ("depth_min", "min_depth"): "min_depth_m",
        ("depth_max", "max_depth"): "max_depth_m",
        ("depth_mean", "mean_depth"): "mean_depth_m",
        
        # Metadata
        ("version", "dem_version"): "version",
        ("timestamp", "creation_date"): "timestamp",
        ("datum", "reference_datum"): "datum",
        ("vertical_datum", "geoid_model"): "vertical_datum",
    }

    @classmethod
    def standardize_properties(
        cls,
        raw_properties: Dict[str, Any],
        provider: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Standardize elevation data properties.
        
        Args:
            raw_properties: Raw properties from provider
            provider: Provider name (for logging)
            
        Returns:
            Standardized properties dictionary
        """
        standardized = {}

        # Map provider-specific fields to standardized names
        for raw_key, raw_value in raw_properties.items():
            standardized_key = cls._get_standardized_key(raw_key)
            
            if standardized_key:
                # Apply value normalization based on field type
                standardized_value = cls._normalize_value(
                    standardized_key,
                    raw_value
                )
                standardized[standardized_key] = standardized_value

        # Add derived fields if source data available
        cls._add_derived_fields(standardized)

        return standardized

    @classmethod
    def _get_standardized_key(cls, raw_key: str) -> str:
        """
        Map a raw property key to standardized name.
        
        Args:
            raw_key: Raw property key from provider
            
        Returns:
            Standardized key name, or empty string if not recognized
        """
        raw_key_lower = raw_key.lower().replace("-", "_").replace(".", "_").replace(" ", "_")
        
        # Check direct mapping
        for provider_keys, standardized_key in cls.FIELD_MAPPINGS.items():
            if raw_key_lower in provider_keys:
                return standardized_key
        
        # No mapping found
        return ""

    @classmethod
    def _normalize_value(cls, field_name: str, value: Any) -> Any:
        """
        Normalize property values based on field type.
        
        Args:
            field_name: Standardized field name
            value: Raw value from provider
            
        Returns:
            Normalized value
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        # Handle elevation values (numeric)
        if "elevation" in field_name or "depth" in field_name:
            return cls._normalize_numeric(value)
        
        # Handle slope values
        if "slope" in field_name:
            if field_name == "slope_category":
                return cls._normalize_slope_category(value)
            return cls._normalize_numeric(value)
        
        # Handle aspect (0-360 degrees)
        if field_name == "aspect_degrees":
            return cls._normalize_aspect(value)
        
        # Handle terrain type
        if field_name == "terrain_type":
            return cls._normalize_terrain_type(value)
        
        # Handle numeric fields (accuracy, resolution, etc.)
        if field_name in [
            "roughness",
            "ruggedness",
            "resolution_m",
            "accuracy_m",
            "coverage_percent",
            "nodata_percent"
        ]:
            return cls._normalize_numeric(value)
        
        # Handle percentage fields
        if "percent" in field_name:
            return cls._normalize_percentage(value)
        
        # Keep as string for other fields
        if isinstance(value, str):
            return value.strip()
        
        return value

    @classmethod
    def _normalize_numeric(cls, value: Any) -> float:
        """
        Normalize numeric values (elevation, depth, etc.).
        
        Args:
            value: Raw numeric value
            
        Returns:
            Normalized numeric value, or None if cannot convert
        """
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @classmethod
    def _normalize_percentage(cls, value: Any) -> float:
        """
        Normalize percentage value (0-100).
        
        Args:
            value: Raw percentage value
            
        Returns:
            Percentage as float (0-100)
        """
        try:
            percentage = float(value)
            # Clamp to 0-100 range
            return max(0.0, min(100.0, percentage))
        except (ValueError, TypeError):
            return None

    @classmethod
    def _normalize_aspect(cls, value: Any) -> float:
        """
        Normalize aspect value to 0-360 degrees.
        
        Args:
            value: Raw aspect value
            
        Returns:
            Aspect in degrees (0-360)
        """
        try:
            aspect = float(value)
            # Normalize to 0-360 range
            aspect = aspect % 360
            return aspect if aspect >= 0 else aspect + 360
        except (ValueError, TypeError):
            return None

    @classmethod
    def _normalize_slope_category(cls, value: Any) -> str:
        """
        Normalize slope category value.
        
        Args:
            value: Raw slope category
            
        Returns:
            Standardized slope category
        """
        if not value:
            return None
        
        value_str = str(value).lower().replace("-", "_").strip()
        
        categories = {
            "flat": "flat",
            "gentle": "gentle",
            "moderate": "moderate",
            "steep": "steep",
            "very_steep": "very_steep",
        }
        
        return categories.get(value_str, value_str)

    @classmethod
    def _normalize_terrain_type(cls, value: Any) -> str:
        """
        Normalize terrain type classification.
        
        Args:
            value: Raw terrain type
            
        Returns:
            Standardized terrain type
        """
        if not value:
            return None
        
        value_str = str(value).lower().replace("-", "_").replace(" ", "_").strip()
        
        terrain_types = {
            "plain": "plain",
            "plateau": "plateau",
            "mountain": "mountain",
            "hill": "hill",
            "valley": "valley",
            "basin": "basin",
            "escarpment": "escarpment",
            "canyon": "canyon",
            "ridge": "ridge",
            "peak": "peak",
            "lowland": "lowland",
            "highland": "highland",
            "coastal": "coastal",
            "flat": "flat",
        }
        
        return terrain_types.get(value_str, value_str)

    @classmethod
    def _add_derived_fields(cls, properties: Dict[str, Any]) -> None:
        """
        Add derived fields based on available elevation data.
        
        Args:
            properties: Properties dictionary (modified in place)
        """
        # Add elevation category if elevation value is available
        if "elevation_m" in properties and properties["elevation_m"] is not None:
            elevation = properties["elevation_m"]
            for category, (min_elev, max_elev) in cls.ELEVATION_CATEGORIES.items():
                if min_elev <= elevation < max_elev:
                    properties["elevation_category"] = category
                    break
        
        # Add slope category if slope value is available
        if "slope_degrees" in properties and properties["slope_degrees"] is not None:
            slope = properties["slope_degrees"]
            for category, (min_slope, max_slope) in cls.SLOPE_CATEGORIES.items():
                if min_slope <= slope < max_slope:
                    properties["slope_category"] = category
                    break
        
        # Add elevation range if min/max available
        if "min_elevation_m" in properties and "max_elevation_m" in properties:
            min_elev = properties.get("min_elevation_m")
            max_elev = properties.get("max_elevation_m")
            if min_elev is not None and max_elev is not None:
                properties["elevation_range_m"] = max_elev - min_elev
        
        # Add vertical exaggeration suggestion if slope available
        if "slope_degrees" in properties:
            slope = properties.get("slope_degrees")
            if slope is not None and slope > 0:
                # Suggest exaggeration factor based on slope
                if slope < 2:
                    properties["suggested_vertical_exaggeration"] = 20
                elif slope < 5:
                    properties["suggested_vertical_exaggeration"] = 10
                elif slope < 15:
                    properties["suggested_vertical_exaggeration"] = 5
                else:
                    properties["suggested_vertical_exaggeration"] = 2
