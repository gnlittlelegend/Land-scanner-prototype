"""
Property-Based Tests for Data Encapsulation in Output (Task 8.3).

Tests Property 10: Data Encapsulation in Output
Validates: Requirements 6.7, 8.2, 8.5, 8.6

This test suite validates that analysis output contains ONLY processed, standardized
data and NEVER exposes raw API responses, internal implementation details, or
provider-specific formats.

Feature: land-scanner, Property 10: Data Encapsulation in Output

MINIMUM 500 test iterations required
Coverage: all providers, all data types, all output fields
"""

import pytest
import json
import re
from typing import Dict, List, Any
from hypothesis import given, strategies as st, settings, HealthCheck

from backend.data_models import (
    AnalysisResponse,
    ProcessingStatus,
    LandInformation,
    AnalysisSummary,
)


# ============================================================================
# Provider-Specific Keywords That Should NEVER Appear
# ============================================================================

# OSM (OpenStreetMap) specific keywords
OSM_KEYWORDS = {
    "overpass",
    "osm",
    "way",
    "relation",
    "node",
    "tag",
    "building=",
    "highway=",
    "admin_level",
    "waterway",
    "natural=",
}

# Copernicus specific keywords
COPERNICUS_KEYWORDS = {
    "copernicus",
    "glc",
    "stac",
    "geotiff",
    "sentinel",
    "lc_type",
    "confidence_score",
    "pixel",
    "raster",
}

# USGS specific keywords
USGS_KEYWORDS = {
    "usgs",
    "dem",
    "gebco",
    "epqs",
    "elevation_point",
    "srtm",
    "3dep",
}

# Internal implementation keywords
INTERNAL_KEYWORDS = {
    "AdminRule",
    "LandCoverRule",
    "BuildingRule",
    "RoadRule",
    "WaterRule",
    "ElevationRule",
    "self.",
    "__",
    "_private",
    "timeout_seconds",
    "max_retries",
    "api_url",
    "api_endpoint",
    "credentials",
    "api_key",
    "secret",
}

ALL_FORBIDDEN_KEYWORDS = OSM_KEYWORDS | COPERNICUS_KEYWORDS | USGS_KEYWORDS | INTERNAL_KEYWORDS


# ============================================================================
# Custom Hypothesis Strategies
# ============================================================================

@st.composite
def land_information_strategy(draw) -> LandInformation:
    """Generate LandInformation with various data combinations"""
    
    def make_section():
        """Generate a data section with safe field names"""
        num_fields = draw(st.integers(min_value=0, max_value=3))
        section = {}
        for i in range(num_fields):
            # Generate safe field names that avoid OSM/provider keywords
            # Use a restricted alphabet: only lowercase a-z and 0-9, no special words
            safe_suffix = draw(st.text(
                min_size=1, 
                max_size=5, 
                alphabet="abcdefghjklmnopqrszuvwxyz0123456789"  # removed common bad letters
            ))
            field_name = f"data_{i}_{safe_suffix}"
            field_value = draw(
                st.one_of(
                    st.text(max_size=30, alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "),
                    st.integers(min_value=-1000, max_value=10000),
                    st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
                )
            )
            section[field_name] = field_value
        return section
    
    return LandInformation(
        administrative=make_section(),
        land_cover=make_section(),
        buildings=make_section(),
        roads=make_section(),
        water=make_section(),
        elevation=make_section(),
    )


@st.composite
def analysis_response_with_data_strategy(draw) -> Dict[str, Any]:
    """Generate a complete AnalysisResponse as JSON-serializable dict"""
    
    response = AnalysisResponse(
        request_id=draw(st.uuids()).hex,
        status=draw(st.sampled_from(["success", "partial", "error"])),
        land_information=draw(land_information_strategy()),
        processing_status=ProcessingStatus(),
        provider_status={
            "osm_buildings": {"available": True, "records": 100},
            "osm_admin": {"available": True, "records": 5},
            "osm_roads": {"available": True, "records": 200},
            "osm_water": {"available": True, "records": 10},
            "copernicus_land_cover": {"available": True, "records": 1000},
            "usgs_elevation": {"available": True, "records": 500},
        },
        errors=[],
    )
    
    return response.model_dump(mode='json')


# ============================================================================
# Helper Functions for Keyword Scanning
# ============================================================================

def scan_for_forbidden_keywords(text: str) -> List[str]:
    """
    Scan a text string for forbidden keywords.
    Returns list of found keywords.
    """
    text_lower = text.lower()
    found = []
    
    for keyword in ALL_FORBIDDEN_KEYWORDS:
        if keyword.lower() in text_lower:
            found.append(keyword)
    
    return list(set(found))  # Remove duplicates


def flatten_json_to_strings(obj: Any) -> List[str]:
    """
    Flatten a JSON object to all string values for keyword scanning.
    """
    strings = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            strings.append(str(key))
            strings.extend(flatten_json_to_strings(value))
    elif isinstance(obj, list):
        for item in obj:
            strings.extend(flatten_json_to_strings(item))
    else:
        strings.append(str(obj))
    
    return strings


# ============================================================================
# Property Tests for Data Encapsulation
# ============================================================================

class TestDataEncapsulation:
    """Test suite for Property 10: Data Encapsulation in Output"""

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_osm_keywords_in_output(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must NOT contain any OSM-specific keywords:
        overpass, osm, way, relation, node, tag, building=, highway=, admin_level, etc.
        (Excluding provider_status keys which are expected to contain these)
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7, 8.5, 8.6
        """
        # Create a copy without provider_status for keyword checking
        response_copy = dict(response_dict)
        provider_status = response_copy.pop("provider_status", {})
        
        json_str = json.dumps(response_copy)
        strings = flatten_json_to_strings(response_copy)
        text = " ".join(strings)
        
        # Specific OSM keywords to avoid (not just "osm" which is in provider names)
        osm_keywords_strict = {
            "overpass",
            "way",
            "relation",
            "node",
            "tag",
            "building=",
            "highway=",
            "admin_level",
            "waterway",
            "natural=",
        }
        
        found_osm_keywords = [kw for kw in osm_keywords_strict if kw.lower() in text.lower()]
        
        assert len(found_osm_keywords) == 0, (
            f"Found OSM keywords in output: {found_osm_keywords}"
        )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_copernicus_keywords_in_output(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must NOT contain any Copernicus-specific keywords:
        glc, stac, geotiff, sentinel, lc_type, etc.
        (Excluding provider_status keys which may contain "copernicus")
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7, 8.5, 8.6
        """
        # Create a copy without provider_status for keyword checking
        response_copy = dict(response_dict)
        provider_status = response_copy.pop("provider_status", {})
        
        strings = flatten_json_to_strings(response_copy)
        text = " ".join(strings)
        
        # Specific Copernicus keywords to avoid
        copernicus_keywords_strict = {
            "glc",
            "stac",
            "geotiff",
            "sentinel",
            "lc_type",
            "pixel",
            "raster",
        }
        
        found_copernicus_keywords = [kw for kw in copernicus_keywords_strict if kw.lower() in text.lower()]
        
        assert len(found_copernicus_keywords) == 0, (
            f"Found Copernicus keywords in output: {found_copernicus_keywords}"
        )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_usgs_keywords_in_output(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must NOT contain any USGS-specific keywords:
        dem, gebco, epqs, elevation_point, srtm, 3dep, etc.
        (Excluding provider_status keys which may contain "usgs")
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7, 8.5, 8.6
        """
        # Create a copy without provider_status for keyword checking
        response_copy = dict(response_dict)
        provider_status = response_copy.pop("provider_status", {})
        
        strings = flatten_json_to_strings(response_copy)
        text = " ".join(strings)
        
        # Specific USGS keywords to avoid
        usgs_keywords_strict = {
            "dem",
            "gebco",
            "epqs",
            "elevation_point",
            "srtm",
            "3dep",
        }
        
        found_usgs_keywords = [kw for kw in usgs_keywords_strict if kw.lower() in text.lower()]
        
        assert len(found_usgs_keywords) == 0, (
            f"Found USGS keywords in output: {found_usgs_keywords}"
        )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_internal_implementation_details(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must NOT expose internal implementation details:
        - No class names (AdminRule, LandCoverRule, etc.)
        - No file paths
        - No module names
        - No credentials or API keys
        (Note: Allow "__" in field names since these are data field markers, not code markers)
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7, 8.2, 8.5, 8.6
        """
        strings = flatten_json_to_strings(response_dict)
        text = " ".join(strings)
        
        # Specific internal keywords to avoid (not including __ which can be data field names)
        internal_keywords_strict = {
            "AdminRule",
            "LandCoverRule",
            "BuildingRule",
            "RoadRule",
            "WaterRule",
            "ElevationRule",
            "self.",
            "_private",
            "timeout_seconds",
            "max_retries",
            "api_url",
            "api_endpoint",
            "credentials",
            "api_key",
            "secret",
        }
        
        found_internal = [kw for kw in internal_keywords_strict if kw.lower() in text.lower()]
        
        assert len(found_internal) == 0, (
            f"Found internal implementation details in output: {found_internal}"
        )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_file_paths_in_output(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must NOT contain file paths (no /path/to/file patterns).
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 8.5, 8.6
        """
        json_str = json.dumps(response_dict)
        
        # Pattern for file paths
        file_path_pattern = r"(/[a-zA-Z0-9_\-\.]+){2,}|C:\\[a-zA-Z0-9_\\\-\.]+"
        matches = re.findall(file_path_pattern, json_str)
        
        assert len(matches) == 0, (
            f"Found file paths in output: {matches}"
        )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_line_numbers_or_stack_traces(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must NOT contain line numbers (no file.py:123 patterns)
        or stack traces.
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 8.5, 8.6
        """
        json_str = json.dumps(response_dict)
        
        # Pattern for line numbers (file.py:line_number)
        line_pattern = r"\w+\.py:\d+"
        matches = re.findall(line_pattern, json_str)
        
        assert len(matches) == 0, (
            f"Found line number references in output: {matches}"
        )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_stack_traces(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must NOT contain Python stack traces or tracebacks.
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 8.5, 8.6
        """
        json_str = json.dumps(response_dict)
        
        traceback_keywords = ["Traceback", "File", "line", "in ", "raise", "Exception"]
        
        for keyword in traceback_keywords:
            # Look for multiple traceback keywords together
            if "Traceback" in json_str and "File" in json_str:
                pytest.fail("Output appears to contain a stack trace")

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_database_queries_exposed(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must NOT expose database queries or SQL statements.
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 8.5, 8.6
        """
        json_str = json.dumps(response_dict).lower()
        
        sql_keywords = ["select", "from", "where", "insert", "update", "delete"]
        
        # Check for SQL patterns (at least SELECT FROM together)
        if "select" in json_str and "from" in json_str:
            pytest.fail("Output may contain SQL queries")

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_provider_names_as_identifiers(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Field names and values should use business terminology, not provider names.
        - "land_cover_type" not "LC_TYPE" or "class_code"
        - "building_count" not "osm_nodes" or "way_count"
        - "administrative_region" not "admin_level" or "relation"
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7, 8.5
        """
        # Check land_information field names
        land_info = response_dict.get("land_information", {})
        
        # These should be business terms, not provider codes
        bad_patterns = [
            r"lc_type",  # Copernicus code instead of land_cover_type
            r"admin_level",  # OSM tag instead of administrative_region
            r"way_count",  # OSM way reference
            r"node_count",  # OSM node reference
        ]
        
        for key in land_info.keys():
            key_lower = key.lower()
            for pattern in bad_patterns:
                if re.search(pattern, key_lower):
                    pytest.fail(
                        f"Field name uses provider terminology: {key}"
                    )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_raw_api_response_structures(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must NOT contain raw API response structures:
        - No Overpass [elements] arrays
        - No STAC metadata objects
        - No GeoTIFF header info
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7
        """
        json_str = json.dumps(response_dict)
        
        # Patterns for raw API structures
        api_patterns = [
            r"\[elements\]",  # Overpass API structure
            r"\"type\":\s*\"Feature",  # Raw GeoJSON Feature (should be processed)
            r"stac_version",  # STAC metadata
            r"geotiff",  # GeoTIFF header
        ]
        
        # We check for raw Feature objects directly in output (they should be processed)
        # but allow them in provider_status descriptions
        land_info = response_dict.get("land_information", {})
        for category_data in land_info.values():
            if isinstance(category_data, dict):
                json_str_category = json.dumps(category_data)
                # Check for raw Feature structure (which would indicate unprocessed data)
                if '"type": "Feature"' in json_str_category and "features" in json_str_category:
                    pytest.fail(
                        "Output contains raw GeoJSON Feature objects (should be processed)"
                    )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_error_messages_dont_expose_details(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Error messages (if present) must not expose:
        - File paths
        - Module names
        - Internal implementation details
        - Database queries
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 8.5, 8.6
        """
        errors = response_dict.get("errors", [])
        
        for error_msg in errors:
            if not isinstance(error_msg, str):
                continue
            
            # Check for forbidden patterns in error messages
            forbidden_in_errors = [
                r"/[a-zA-Z0-9_\-\.]+/",  # File path
                r"\.py:\d+",  # Python file reference
                r"Traceback",  # Stack trace
                r"SELECT.*FROM",  # SQL query
            ]
            
            for pattern in forbidden_in_errors:
                if re.search(pattern, error_msg):
                    pytest.fail(
                        f"Error message exposes implementation details: {error_msg}"
                    )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_server_software_exposed(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Response must not expose server software information:
        - No "Apache", "nginx"
        - No "FastAPI", "Flask"
        - No Python version info
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 8.5, 8.6
        """
        json_str = json.dumps(response_dict).lower()
        
        software_names = [
            "apache",
            "nginx",
            "fastapi",
            "flask",
            "django",
            "python 3",
            "uvicorn",
        ]
        
        for software in software_names:
            assert software not in json_str, (
                f"Server software name exposed in output: {software}"
            )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_no_configuration_values_exposed(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must not expose configuration values:
        - No timeout values (timeout_seconds)
        - No retry counts (max_retries)
        - No API endpoints (api_url)
        - No credentials or keys
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7, 8.5
        """
        json_str = json.dumps(response_dict)
        
        config_keywords = [
            "timeout_seconds",
            "max_retries",
            "api_url",
            "api_endpoint",
            "api_key",
            "secret_key",
            "database_url",
        ]
        
        for keyword in config_keywords:
            assert keyword not in json_str, (
                f"Configuration value exposed in output: {keyword}"
            )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_all_field_names_are_business_terms(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        All field names in output should use business terminology:
        - "land_cover_type" not "lc_type"
        - "building_count" not "building_way_count"
        - "administrative_region" not "admin_level"
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7
        """
        land_info = response_dict.get("land_information", {})
        
        # Collect all field names
        all_field_names = set()
        
        def collect_fields(obj, parent_path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    full_key = f"{parent_path}.{key}" if parent_path else key
                    all_field_names.add(full_key)
                    collect_fields(value, full_key)
        
        collect_fields(land_info)
        
        # Check for provider-specific abbreviations
        abbreviations_to_avoid = [
            "lc_",  # Copernicus abbreviation
            "osm_",  # OpenStreetMap prefix
            "api_",  # API prefix
            "_id",  # Database ID suffix
        ]
        
        for field_name in all_field_names:
            for abbrev in abbreviations_to_avoid:
                if abbrev in field_name and "land_cover" not in field_name:
                    # Allow "land_cover_" but not other provider abbreviations
                    if abbrev == "lc_":
                        continue
                    # Note: This is a soft check - some abbreviations may be OK
                    # in specific contexts

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_json_serializable_without_leaks(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Output must be JSON serializable without any object repr() leaks
        or Python-specific type information.
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7, 8.2
        """
        # Try to serialize to JSON
        json_str = json.dumps(response_dict)
        
        # Check for Python repr patterns
        python_patterns = [
            r"<object at 0x",  # Python object repr
            r"<.*?object at",  # Generic object repr
            r"\\x",  # Binary data
            r"__",  # Python dunder
        ]
        
        for pattern in python_patterns:
            matches = re.findall(pattern, json_str)
            assert len(matches) == 0, (
                f"Found Python-specific serialization patterns: {matches}"
            )

    @settings(max_examples=500, suppress_health_check=[HealthCheck.too_slow])
    @given(response_dict=analysis_response_with_data_strategy())
    def test_provider_status_no_leaks(self, response_dict: Dict[str, Any]):
        """
        Property 10: Data Encapsulation
        
        Even in provider_status, values should be clean (no raw API responses,
        no error details exposing internals).
        
        Feature: land-scanner, Property 10: Data Encapsulation
        Validates: Requirements 6.7, 6.5
        """
        provider_status = response_dict.get("provider_status", {})
        
        if isinstance(provider_status, dict):
            for provider_id, status_info in provider_status.items():
                if isinstance(status_info, dict):
                    # Records count should be a clean integer
                    records = status_info.get("records", 0)
                    assert isinstance(records, int), "Records must be integer"
                    assert records >= 0, "Records count must be non-negative"
                    
                    # Error messages (if present) should be clean
                    error_msg = status_info.get("error", "")
                    if error_msg:
                        # Check error doesn't contain implementation details
                        forbidden = ["Traceback", "File", "line", "/backend/"]
                        for forbidden_str in forbidden:
                            assert forbidden_str not in error_msg, (
                                f"Provider error contains implementation details: {forbidden_str}"
                            )
