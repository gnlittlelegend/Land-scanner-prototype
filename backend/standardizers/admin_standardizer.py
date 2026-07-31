"""
Administrative Boundaries-specific field normalization.

Maps provider-specific administrative fields to common standardized schema.
Handles administrative boundaries from OpenStreetMap and other providers.
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class AdminStandardizer:
    """
    Standardizes administrative boundary properties from various providers.
    
    Handles:
    - OpenStreetMap administrative boundaries
    - Administrative hierarchy (country, state, district, municipality)
    - Administrative codes and references
    - Jurisdictional information
    """

    # Mapping of provider-specific field names to standardized names
    FIELD_MAPPINGS = {
        # Administrative level and type
        ("admin_level", "level", "administrative_level"): "admin_level",
        ("boundary", "boundary_type"): "boundary_type",
        ("type",): "boundary_type",
        
        # Country information
        ("country", "country_name", "iso3166_1"): "country",
        ("country_code", "iso3166_1_alpha2", "iso_code"): "country_code",
        ("iso3166_1_alpha2",): "country_code",
        ("iso3166_1_alpha3",): "country_code_alpha3",
        
        # State/Province information
        ("state", "province", "region", "state_name", "province_name"): "state",
        ("state_code", "province_code", "state_short"): "state_code",
        
        # District/County information
        ("district", "county", "district_name", "county_name"): "district",
        ("district_code", "county_code"): "district_code",
        
        # Municipality/City information
        ("municipality", "city", "municipality_name", "city_name"): "municipality",
        ("municipality_code", "city_code"): "municipality_code",
        
        # Locality/Ward information
        ("locality", "ward", "suburb", "neighborhood"): "locality",
        ("locality_code", "ward_code"): "locality_code",
        
        # Area and population
        ("area_sqkm", "area", "area_km2"): "area_sqkm",
        ("area_sqmi", "area_square_miles"): "area_sqmi",
        ("population", "pop", "num_residents"): "population",
        ("population_density", "pop_density"): "population_density",
        
        # Official names and references
        ("name", "official_name", "en_name"): "name",
        ("name:en", "english_name"): "name_en",
        ("name:fr", "french_name"): "name_fr",
        ("name:de", "german_name"): "name_de",
        ("name:es", "spanish_name"): "name_es",
        
        # Administrative references
        ("ref", "reference", "admin_ref"): "reference_id",
        ("ref:wikidata", "wikidata_id", "wikidata"): "wikidata_id",
        ("ref:wikipedia", "wikipedia"): "wikipedia",
        ("ref:fips", "fips_code"): "fips_code",
        ("ref:hasc", "hasc_code"): "hasc_code",
        
        # Status and attributes
        ("status", "admin_status", "type"): "admin_status",
        ("official_status",): "official_status",
        ("capital", "capital_city"): "capital",
        ("historic",): "historic",
        
        # Temporal information
        ("start_date", "established_date"): "established_date",
        ("end_date", "dissolved_date"): "dissolved_date",
    }

    # Administrative level hierarchy
    ADMIN_LEVEL_NAMES = {
        "2": "country",
        "3": "region",
        "4": "state",
        "5": "county",
        "6": "district",
        "7": "county_subdivision",
        "8": "municipality",
        "9": "city",
        "10": "suburb",
        "11": "neighborhood",
        "12": "locality",
    }

    @classmethod
    def standardize_properties(
        cls,
        raw_properties: Dict[str, Any],
        provider: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Standardize administrative boundary properties.
        
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

        # Ensure key administrative fields are present
        cls._fill_defaults(standardized)

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

        # Handle admin level normalization
        if field_name == "admin_level":
            return cls._normalize_admin_level(value)
        
        # Handle country code normalization
        if field_name in ["country_code", "country_code_alpha3"]:
            return cls._normalize_country_code(value, field_name)
        
        # Handle numeric fields
        if field_name in [
            "area_sqkm",
            "area_sqmi",
            "population",
            "population_density"
        ]:
            return cls._normalize_numeric(value)
        
        # Handle boolean fields
        if field_name in ["capital", "historic"]:
            return cls._normalize_boolean(value)
        
        # Handle date fields
        if "date" in field_name:
            return cls._normalize_date(value)
        
        # Handle code fields (should be uppercase)
        if "code" in field_name:
            if isinstance(value, str):
                return value.upper().strip()
            return value
        
        # Keep as string for other fields
        if isinstance(value, str):
            return value.strip()
        
        return value

    @classmethod
    def _normalize_admin_level(cls, value: Any) -> int:
        """
        Normalize admin level to integer.
        
        Args:
            value: Raw admin level value
            
        Returns:
            Admin level as integer
        """
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @classmethod
    def _normalize_country_code(cls, value: Any, field_name: str) -> str:
        """
        Normalize country code.
        
        Args:
            value: Raw country code
            field_name: Field name (to determine format)
            
        Returns:
            Normalized country code
        """
        if not value:
            return None
        
        code_str = str(value).upper().strip()
        
        # Validate format based on field type
        if field_name == "country_code_alpha3":
            # Alpha-3 codes should be 3 letters
            if len(code_str) == 3 and code_str.isalpha():
                return code_str
        else:
            # Alpha-2 codes should be 2 letters
            if len(code_str) == 2 and code_str.isalpha():
                return code_str
        
        return code_str

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

    @classmethod
    def _normalize_date(cls, value: Any) -> str:
        """
        Normalize date values to ISO format string.
        
        Args:
            value: Raw date value
            
        Returns:
            ISO format date string
        """
        if not value:
            return None
        
        return str(value).strip()

    @classmethod
    def _fill_defaults(cls, properties: Dict[str, Any]) -> None:
        """
        Ensure required administrative fields have values.
        
        Args:
            properties: Properties dictionary to fill (modified in place)
        """
        # If we have an admin_level but no type name, add it
        if "admin_level" in properties and "admin_level_name" not in properties:
            level_str = str(properties["admin_level"])
            if level_str in cls.ADMIN_LEVEL_NAMES:
                properties["admin_level_name"] = cls.ADMIN_LEVEL_NAMES[level_str]
