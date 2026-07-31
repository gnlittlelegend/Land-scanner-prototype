"""
Land Cover-specific field normalization.

Maps provider-specific land cover fields to common standardized schema.
Handles land cover data from Copernicus, ESA, and other providers.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class LandCoverStandardizer:
    """
    Standardizes land cover properties from various providers.
    
    Handles:
    - Copernicus Global Land Cover
    - ESA WorldCover
    - Land cover classification codes
    - Confidence and metadata
    """

    # Standardized land cover classes (based on LCCS standard)
    LAND_COVER_CLASSES = {
        "no_data": "no_data",
        "water": "water",
        "permanent_water": "water",
        "seasonal_water": "water",
        "aquatic_vegetation": "aquatic_vegetation",
        "tree_cover": "tree_cover",
        "herbaceous_cover": "herbaceous_cover",
        "bare": "bare",
        "bare_rock": "bare",
        "sand": "bare",
        "snow_ice": "snow_ice",
        "built_up": "built_up",
        "urban": "built_up",
        "settlement": "built_up",
        "crops": "crops",
        "agriculture": "crops",
        "grassland": "grassland",
        "grass": "grassland",
        "shrubland": "shrubland",
        "shrub": "shrubland",
        "moss_lichen": "moss_lichen",
        "cloud": "cloud",
        "shadow": "cloud",
    }

    # Mapping of provider-specific field names to standardized names
    FIELD_MAPPINGS = {
        # Land cover classification
        ("lc_class", "lc_classes", "classification", "class", "lc_type"): "lc_class",
        ("lc_code", "code", "classification_code"): "lc_code",
        ("lc_name", "class_name", "classification_name"): "lc_name",
        
        # Certainty and confidence
        ("confidence", "certainty", "qa", "quality"): "confidence",
        ("confidence_pct", "confidence_percent"): "confidence_percent",
        
        # Data source and version
        ("source", "data_source", "product"): "source",
        ("version", "product_version"): "version",
        ("epoch", "year", "observation_date"): "epoch",
        
        # Percentages of each class (for pixel mixtures)
        ("percent_water",): "percent_water",
        ("percent_tree",): "percent_tree",
        ("percent_grass",): "percent_grass",
        ("percent_crops",): "percent_crops",
        ("percent_built",): "percent_built",
        ("percent_bare",): "percent_bare",
        
        # Metadata
        ("metadata",): "metadata",
        ("pixel_size", "resolution"): "resolution_m",
        ("valid",): "valid",
    }

    # Provider code mappings
    # Copernicus Global Land Cover codes (v3)
    COPERNICUS_CODE_MAPPING = {
        "0": "no_data",
        "1": "tree_cover",
        "2": "herbaceous_cover",
        "3": "shrubland",
        "4": "crops",
        "5": "built_up",
        "6": "bare",
        "7": "snow_ice",
        "8": "water",
    }

    # ESA WorldCover codes
    ESA_CODE_MAPPING = {
        "0": "no_data",
        "10": "tree_cover",
        "20": "shrubland",
        "30": "grassland",
        "40": "crops",
        "50": "built_up",
        "60": "bare",
        "70": "snow_ice",
        "80": "water",
        "90": "herbaceous_cover",
        "95": "herbaceous_cover",
        "100": "moss_lichen",
    }

    @classmethod
    def standardize_properties(
        cls,
        raw_properties: Dict[str, Any],
        provider: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Standardize land cover properties.
        
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
                    raw_value,
                    provider
                )
                standardized[standardized_key] = standardized_value

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
    def _normalize_value(
        cls,
        field_name: str,
        value: Any,
        provider: str = "unknown"
    ) -> Any:
        """
        Normalize property values based on field type.
        
        Args:
            field_name: Standardized field name
            value: Raw value from provider
            provider: Provider name (for code mapping)
            
        Returns:
            Normalized value
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return None

        # Handle land cover code normalization
        if field_name == "lc_code":
            return cls._normalize_lc_code(value, provider)
        
        # Handle land cover class normalization
        if field_name == "lc_class":
            return cls._normalize_lc_class(value)
        
        # Handle confidence normalization
        if "confidence" in field_name:
            return cls._normalize_confidence(value)
        
        # Handle percentage fields
        if "percent" in field_name:
            return cls._normalize_percentage(value)
        
        # Handle resolution (numeric)
        if field_name == "resolution_m":
            return cls._normalize_numeric(value)
        
        # Handle epoch/year
        if field_name == "epoch":
            return cls._normalize_epoch(value)
        
        # Handle boolean fields
        if field_name == "valid":
            return cls._normalize_boolean(value)
        
        # Keep as string for other fields
        if isinstance(value, str):
            return value.strip()
        
        return value

    @classmethod
    def _normalize_lc_code(cls, value: Any, provider: str = "unknown") -> str:
        """
        Normalize land cover code using provider-specific mappings.
        
        Args:
            value: Raw land cover code
            provider: Provider name
            
        Returns:
            Normalized land cover code or class name
        """
        if not value:
            return None
        
        code_str = str(value).strip()
        
        # Try provider-specific mapping
        if "copernicus" in provider.lower():
            if code_str in cls.COPERNICUS_CODE_MAPPING:
                return cls.COPERNICUS_CODE_MAPPING[code_str]
        elif "esa" in provider.lower() or "worldcover" in provider.lower():
            if code_str in cls.ESA_CODE_MAPPING:
                return cls.ESA_CODE_MAPPING[code_str]
        
        # Return code as-is if no mapping found
        return code_str

    @classmethod
    def _normalize_lc_class(cls, value: Any) -> str:
        """
        Normalize land cover class name.
        
        Args:
            value: Raw land cover class
            
        Returns:
            Standardized land cover class
        """
        if not value:
            return None
        
        value_str = str(value).lower().replace("-", "_").replace(" ", "_")
        
        # Check if already standardized
        if value_str in cls.LAND_COVER_CLASSES.values():
            return value_str
        
        # Check mapping
        return cls.LAND_COVER_CLASSES.get(value_str, "no_data")

    @classmethod
    def _normalize_confidence(cls, value: Any) -> float:
        """
        Normalize confidence value (0-100).
        
        Args:
            value: Raw confidence value
            
        Returns:
            Confidence as percentage (0-100)
        """
        try:
            confidence = float(value)
            # Clamp to 0-100 range
            return max(0.0, min(100.0, confidence))
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
        return cls._normalize_confidence(value)

    @classmethod
    def _normalize_numeric(cls, value: Any) -> float:
        """
        Normalize numeric values.
        
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
    def _normalize_epoch(cls, value: Any) -> str:
        """
        Normalize epoch/year value.
        
        Args:
            value: Raw epoch value
            
        Returns:
            Epoch as string (YYYY or YYYY-MM-DD)
        """
        if not value:
            return None
        
        return str(value).strip()

    @classmethod
    def _normalize_boolean(cls, value: Any) -> bool:
        """
        Normalize boolean values.
        
        Args:
            value: Raw boolean value
            
        Returns:
            Boolean value
        """
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value_lower = value.lower()
            return value_lower in ("true", "yes", "1")
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return False
