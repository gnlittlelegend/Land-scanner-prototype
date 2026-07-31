"""
Response Formatting for Land Scanner

Provides utilities to format consistent API responses for both
successful analyses and error conditions.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class ResponseStatus(Enum):
    """Standard response status values."""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some data/providers failed but results available
    ERROR = "error"


def format_error_response(
    error_code: str,
    error_message: str,
    module: str,
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Format a standardized error response.
    
    Args:
        error_code: Machine-readable error code
        error_message: User-facing error message
        module: Module where error occurred
        request_id: Optional request ID
        details: Optional additional details
        
    Returns:
        Formatted error response dictionary
    """
    response = {
        "status": ResponseStatus.ERROR.value,
        "error_code": error_code,
        "error_message": error_message,
        "module": module,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if request_id:
        response["request_id"] = request_id
    
    if details:
        response["details"] = details
    
    return response


def format_success_response(
    request_id: str,
    analysis_summary: Dict[str, Any],
    land_information: Dict[str, Any],
    processing_status: Dict[str, Any],
    provider_status: Dict[str, Any],
    processing_time_ms: float,
    errors: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Format a successful analysis response.
    
    Args:
        request_id: Unique request identifier
        analysis_summary: Summary of analysis results
        land_information: Processed land information
        processing_status: Status of each processing module
        provider_status: Status of data providers
        processing_time_ms: Total processing time in milliseconds
        errors: Optional list of non-critical errors
        
    Returns:
        Formatted response dictionary
    """
    response = {
        "status": ResponseStatus.SUCCESS.value,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "processing_time_ms": processing_time_ms,
        "analysis_summary": analysis_summary,
        "land_information": land_information,
        "processing_status": processing_status,
        "provider_status": provider_status
    }
    
    if errors:
        response["errors"] = errors
    
    return response


def format_partial_response(
    request_id: str,
    analysis_summary: Dict[str, Any],
    land_information: Dict[str, Any],
    processing_status: Dict[str, Any],
    provider_status: Dict[str, Any],
    processing_time_ms: float,
    errors: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Format a partial success response (some failures but results available).
    
    Args:
        request_id: Unique request identifier
        analysis_summary: Summary of analysis results
        land_information: Processed land information (may be incomplete)
        processing_status: Status of each processing module
        provider_status: Status of data providers
        processing_time_ms: Total processing time in milliseconds
        errors: List of errors that occurred
        
    Returns:
        Formatted response dictionary with partial status
    """
    response = {
        "status": ResponseStatus.PARTIAL.value,
        "request_id": request_id,
        "timestamp": datetime.utcnow().isoformat(),
        "processing_time_ms": processing_time_ms,
        "analysis_summary": analysis_summary,
        "land_information": land_information,
        "processing_status": processing_status,
        "provider_status": provider_status,
        "errors": errors
    }
    
    return response


def format_validation_error_response(
    polygon_error: str,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format a polygon validation error response.
    
    Args:
        polygon_error: Validation error message
        request_id: Optional request ID
        
    Returns:
        Formatted error response
    """
    response = {
        "status": ResponseStatus.ERROR.value,
        "error_code": "POLYGON_VALIDATION_ERROR",
        "error_message": polygon_error,
        "module": "polygon_validator",
        "stage": "validation",
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if request_id:
        response["request_id"] = request_id
    
    return response


def format_provider_status(
    provider_name: str,
    available: bool,
    data_retrieved: bool = False,
    error_message: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format provider status information.
    
    Args:
        provider_name: Name of the provider
        available: Whether provider is available
        data_retrieved: Whether data was successfully retrieved
        error_message: Optional error message if failed
        
    Returns:
        Formatted provider status dictionary
    """
    status_map = {
        True: "available",
        False: "unavailable"
    }
    
    result = {
        "provider_name": provider_name,
        "status": status_map.get(available, "unknown"),
        "data_retrieved": data_retrieved
    }
    
    if error_message:
        result["error_message"] = error_message
    
    return result


def format_processing_status(
    validation: str = "pending",
    data_collection: str = "pending",
    standardization: str = "pending",
    rule_engine: str = "pending",
    output_generation: str = "pending"
) -> Dict[str, str]:
    """
    Format processing status for all modules.
    
    Valid values: pending, success, partial, failed
    
    Args:
        validation: Status of polygon validation
        data_collection: Status of data collection
        standardization: Status of data standardization
        rule_engine: Status of rule engine
        output_generation: Status of output generation
        
    Returns:
        Formatted processing status dictionary
    """
    return {
        "validation": validation,
        "data_collection": data_collection,
        "standardization": standardization,
        "rule_engine": rule_engine,
        "output_generation": output_generation
    }


def format_error_info(
    module: str,
    message: str,
    severity: str = "error"
) -> Dict[str, str]:
    """
    Format error information for inclusion in response.
    
    Args:
        module: Module where error occurred
        message: Error message
        severity: Error severity (warning, error, critical)
        
    Returns:
        Formatted error information
    """
    return {
        "module": module,
        "message": message,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat()
    }
