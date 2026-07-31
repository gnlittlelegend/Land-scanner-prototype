"""
Error Handling Utilities for Land Scanner

Provides centralized error handling, message sanitization, and consistent
error response formatting across the application.
"""

from typing import Dict, Any, Optional, List
from enum import Enum
import logging
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)


class ErrorCode(Enum):
    """Standardized error codes for consistent error handling."""
    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    POLYGON_VALIDATION_ERROR = "POLYGON_VALIDATION_ERROR"
    
    # Collection errors
    PROVIDER_ERROR = "PROVIDER_ERROR"
    COLLECTION_ERROR = "COLLECTION_ERROR"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    
    # Processing errors
    PROCESSING_ERROR = "PROCESSING_ERROR"
    STANDARDIZATION_ERROR = "STANDARDIZATION_ERROR"
    RULE_EXECUTION_ERROR = "RULE_EXECUTION_ERROR"
    
    # System errors
    SYSTEM_ERROR = "SYSTEM_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorSeverity(Enum):
    """Error severity levels."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SafeError:
    """
    Represents a safe error that can be exposed to users.
    
    Contains only user-facing information with no internal details,
    stack traces, or sensitive information.
    """
    
    def __init__(
        self,
        error_code: ErrorCode,
        user_message: str,
        module: str,
        stage: Optional[str] = None,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize a safe error.
        
        Args:
            error_code: Standardized error code
            user_message: User-facing error message (no implementation details)
            module: Module where error occurred
            stage: Processing stage if applicable
            severity: Error severity level
            details: Optional additional details safe for user
        """
        self.error_code = error_code
        self.user_message = user_message
        self.module = module
        self.stage = stage
        self.severity = severity
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        result = {
            "error_code": self.error_code.value,
            "error_message": self.user_message,
            "module": self.module,
            "severity": self.severity.value,
            "timestamp": self.timestamp
        }
        
        if self.stage:
            result["stage"] = self.stage
        
        if self.details:
            result["details"] = self.details
        
        return result


def sanitize_error_message(message: str) -> str:
    """
    Sanitize an error message for user display.
    
    Removes implementation details, file paths, and other sensitive
    information while keeping the message readable.
    
    Args:
        message: Raw error message
        
    Returns:
        Sanitized user-facing message
    """
    # Remove common internal paths and details
    sanitized = message
    
    # Remove full file paths, keep just filename
    import re
    sanitized = re.sub(r'/[a-zA-Z0-9_\-/]*\.py', '[file]', sanitized)
    sanitized = re.sub(r'[C-Z]:\\[a-zA-Z0-9_\-\\]*\.py', '[file]', sanitized)
    
    # Remove memory addresses
    sanitized = re.sub(r'0x[0-9a-fA-F]+', '[address]', sanitized)
    
    # Remove absolute paths
    sanitized = re.sub(r'/[a-zA-Z0-9_\-/]+/', '[path]/', sanitized)
    sanitized = re.sub(r'[C-Z]:\\[a-zA-Z0-9_\-\\]+\\', '[path]/', sanitized)
    
    # Truncate very long messages
    if len(sanitized) > 500:
        sanitized = sanitized[:500] + "..."
    
    return sanitized


def create_error_response(
    status_code: int,
    error: SafeError,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a standardized error response.
    
    Args:
        status_code: HTTP status code
        error: SafeError object
        request_id: Optional request ID for tracking
        
    Returns:
        Dictionary with standardized error response format
    """
    response = {
        "status": "error",
        "error": error.to_dict()
    }
    
    if request_id:
        response["request_id"] = request_id
    
    response["http_status"] = status_code
    
    return response


def http_status_for_error(error_code: ErrorCode) -> int:
    """
    Map error code to appropriate HTTP status code.
    
    Args:
        error_code: StandardizedErrorCode
        
    Returns:
        HTTP status code
    """
    mapping = {
        ErrorCode.VALIDATION_ERROR: 400,
        ErrorCode.POLYGON_VALIDATION_ERROR: 400,
        ErrorCode.PROVIDER_ERROR: 500,
        ErrorCode.COLLECTION_ERROR: 500,
        ErrorCode.PROVIDER_UNAVAILABLE: 500,
        ErrorCode.PROCESSING_ERROR: 500,
        ErrorCode.STANDARDIZATION_ERROR: 500,
        ErrorCode.RULE_EXECUTION_ERROR: 500,
        ErrorCode.SYSTEM_ERROR: 500,
        ErrorCode.INTERNAL_ERROR: 500,
    }
    return mapping.get(error_code, 500)


def log_error(
    error_code: ErrorCode,
    message: str,
    module_name: str,
    exception: Optional[Exception] = None,
    request_id: Optional[str] = None
) -> None:
    """
    Log an error with full details (not exposed to user).
    
    Args:
        error_code: Standardized error code
        message: Error message
        module_name: Module where error occurred (renamed to avoid logging conflict)
        exception: Optional exception object
        request_id: Optional request ID for tracking
    """
    log_message = f"[{error_code.value}] {message}"
    
    if request_id:
        log_message = f"[{request_id}] {log_message}"
    
    if exception:
        logger.error(
            log_message,
            exc_info=True,
            extra={
                "source_module": module_name,
                "exception_type": type(exception).__name__,
                "stack_trace": traceback.format_exc()
            }
        )
    else:
        logger.error(log_message, extra={"source_module": module_name})


class ErrorContext:
    """
    Context manager for structured error handling.
    
    Captures errors, logs them internally, and converts them to
    safe user-facing error responses.
    """
    
    def __init__(
        self,
        module: str,
        stage: Optional[str] = None,
        request_id: Optional[str] = None
    ):
        """
        Initialize error context.
        
        Args:
            module: Module name
            stage: Processing stage if applicable
            request_id: Optional request ID for tracking
        """
        self.module = module
        self.stage = stage
        self.request_id = request_id
        self.errors: List[SafeError] = []
    
    def add_error(self, error: SafeError) -> None:
        """Add an error to the context."""
        self.errors.append(error)
        log_error(
            error.error_code,
            error.user_message,
            error.module,
            request_id=self.request_id
        )
    
    def has_errors(self) -> bool:
        """Check if any errors have occurred."""
        return len(self.errors) > 0
    
    def has_critical_errors(self) -> bool:
        """Check if any critical errors have occurred."""
        return any(e.severity == ErrorSeverity.CRITICAL for e in self.errors)
    
    def get_errors(self) -> List[Dict[str, Any]]:
        """Get all errors as dictionaries."""
        return [e.to_dict() for e in self.errors]
    
    def get_error_summary(self) -> Optional[Dict[str, Any]]:
        """Get summary of errors if any exist."""
        if not self.errors:
            return None
        
        return {
            "error_count": len(self.errors),
            "critical_count": sum(1 for e in self.errors if e.severity == ErrorSeverity.CRITICAL),
            "errors": self.get_errors()
        }
