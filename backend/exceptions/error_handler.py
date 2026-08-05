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
    
    Requirements: 8.2, 8.5
    
    Args:
        message: Raw error message
        
    Returns:
        Sanitized user-facing message
    """
    import re
    
    sanitized = message
    
    # Remove Python file paths (various formats)
    sanitized = re.sub(r'/[a-zA-Z0-9_\-./]*\.py(?::[0-9]+)?', '[file]', sanitized)
    sanitized = re.sub(r'[C-Z]:\\[a-zA-Z0-9_\-\\]*\.py(?::[0-9]+)?', '[file]', sanitized)
    sanitized = re.sub(r'File\s+"[^"]+"', 'File [internal]', sanitized)
    
    # Remove line numbers (e.g., line 42, :42)
    sanitized = re.sub(r'(line\s+)?:[0-9]+', '', sanitized, flags=re.IGNORECASE)
    
    # Remove memory addresses and object IDs
    sanitized = re.sub(r'0x[0-9a-fA-F]{8,16}', '[memory]', sanitized)
    sanitized = re.sub(r'<[a-zA-Z0-9._]+ object at 0x[0-9a-fA-F]+>', '[object]', sanitized)
    
    # Remove absolute paths
    sanitized = re.sub(r'(/[a-zA-Z0-9_\-./]+)+\.py', '[path]', sanitized)
    sanitized = re.sub(r'([C-Z]:)?\\[a-zA-Z0-9_\-\\]+\\[a-zA-Z0-9_\-\\]+', '[path]', sanitized)
    
    # Remove Python-specific exception traceback indicators
    sanitized = re.sub(r'Traceback.*?:', 'Error:', sanitized, flags=re.IGNORECASE)
    
    # Remove Python exception class names and types
    python_exceptions = [
        'NoneType', 'TypeError', 'ValueError', 'AttributeError',
        'KeyError', 'IndexError', 'RuntimeError', 'Exception',
        'ImportError', 'ModuleNotFoundError', 'FileNotFoundError',
        'IOError', 'OSError', 'ConnectionError', 'TimeoutError'
    ]
    for exc in python_exceptions:
        sanitized = re.sub(rf'\b{exc}\b', '[error]', sanitized)
    
    # Remove function/method signatures
    sanitized = re.sub(r'in\s+[a-zA-Z_][a-zA-Z0-9_]*\(', 'in [function](', sanitized)
    
    # Remove module names from import statements/errors
    sanitized = re.sub(r"No module named '([^']+)'", 'Module not available', sanitized)
    
    # Remove credentials-like patterns (basic safeguard)
    sanitized = re.sub(r'password["\']?\s*[:=]\s*["\'][^"\']*["\']', 'password=[hidden]', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']*["\']', 'api_key=[hidden]', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'token["\']?\s*[:=]\s*["\'][^"\']*["\']', 'token=[hidden]', sanitized, flags=re.IGNORECASE)
    
    # Remove SQL/database connection strings
    sanitized = re.sub(r'(database|db|postgresql)://[^\s]+', '[database_url]', sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'Server=[^\s;]*', 'Server=[hidden]', sanitized)
    
    # Remove environment variables if leaked
    sanitized = re.sub(r'(\w+)=([^\s]+)', lambda m: m.group(1) + '=[hidden]' if any(
        keyword in m.group(1).upper() for keyword in ['KEY', 'SECRET', 'PASSWORD', 'TOKEN', 'URL']
    ) else m.group(0), sanitized)
    
    # Limit message length to prevent abuse
    max_length = 500
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    
    # Clean up multiple spaces
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    return sanitized


class ErrorMessageSanitizer:
    """
    Utility class for sanitizing error messages.
    
    Requirement: 8.2, 8.5
    
    Removes internal implementation details, file paths, and stack traces
    while preserving meaningful error information for users.
    """
    
    # Patterns that should never appear in user-facing errors
    FORBIDDEN_PATTERNS = [
        r'(?:\/[\w.-]+)*(\/[\w.-]+)*\.py(?::[0-9]+)?',  # File paths
        r'[C-Z]:\\(?:[\w.-]+\\)*[\w.-]+\.py(?::[0-9]+)?',  # Windows paths
        r'File\s+"[^"]+"',  # File references
        r'(?:line\s+)?:[0-9]+',  # Line numbers
        r'0x[0-9a-fA-F]{8,}',  # Memory addresses
        r'Traceback',  # Traceback headers
        r'\(most recent call last\)',  # Traceback indicators
    ]
    
    # Python exception types to mask
    EXCEPTION_TYPES = {
        'NoneType', 'TypeError', 'ValueError', 'AttributeError',
        'KeyError', 'IndexError', 'RuntimeError', 'Exception',
        'ImportError', 'ModuleNotFoundError', 'FileNotFoundError',
        'IOError', 'OSError', 'ConnectionError', 'TimeoutError',
        'asyncio.TimeoutError', 'socket.timeout', 'requests.ConnectionError'
    }
    
    @staticmethod
    def sanitize_validation_error(raw_error: str) -> str:
        """Sanitize validation error messages."""
        message = sanitize_error_message(raw_error)
        # Validation errors are usually safe, but still sanitize
        return message
    
    @staticmethod
    def sanitize_provider_error(provider_name: str, raw_error: str) -> str:
        """
        Sanitize provider-specific error messages.
        
        Maps internal provider errors to user-friendly messages without
        exposing provider implementation details.
        """
        message = sanitize_error_message(raw_error).lower()
        
        # Timeout errors
        if 'timeout' in message or 'timed out' in message:
            return f"The {provider_name} data service is temporarily slow. Please try again in a moment."
        
        # Rate limiting
        if '429' in message or 'rate limit' in message:
            return f"The {provider_name} data service is temporarily busy. Please try again later."
        
        # Not found
        if '404' in message or 'not found' in message:
            return f"The {provider_name} data service endpoint is not available."
        
        # Server error
        if '500' in message or 'server error' in message or 'internal error' in message:
            return f"The {provider_name} data service is experiencing technical difficulties."
        
        # Connection error
        if 'connection' in message or 'refused' in message or 'unreachable' in message:
            return f"Cannot connect to {provider_name} data service. Please check your internet connection."
        
        # Service unavailable
        if '503' in message or 'service unavailable' in message or 'maintenance' in message:
            return f"The {provider_name} data service is temporarily unavailable."
        
        # Malformed response
        if 'json' in message or 'parse' in message or 'decode' in message:
            return f"The {provider_name} data service returned invalid data. Please try again."
        
        # Generic fallback
        return f"Error retrieving data from {provider_name}. Please try again."
    
    @staticmethod
    def sanitize_system_error(raw_error: str) -> str:
        """
        Sanitize system/internal error messages.
        
        Converts internal errors to generic, safe messages that don't
        expose implementation details.
        """
        message = sanitize_error_message(raw_error)
        
        # For system errors, use generic message - don't expose details
        return "An unexpected error occurred. Please try again."
    
    @staticmethod
    def contains_sensitive_data(message: str) -> bool:
        """
        Check if a message contains sensitive data that should be blocked.
        
        Args:
            message: Message to check
            
        Returns:
            True if sensitive data detected, False otherwise
        """
        import re
        
        # Check for common sensitive patterns
        sensitive_patterns = [
            r'password\s*[:=]',
            r'api[_-]?key\s*[:=]',
            r'token\s*[:=]',
            r'secret\s*[:=]',
            r'credential',
            r'database://[^\s]+',
            r'postgresql://[^\s]+',
            r'mongodb://[^\s]+',
            r'redis://[^\s]+',
            r'(?:[0-9a-f]{32,})',  # Long hex strings (potential tokens)
        ]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        
        return False
    
    @staticmethod
    def make_message_user_friendly(error_code: str, message: str) -> str:
        """
        Convert sanitized technical message to user-friendly format.
        
        Args:
            error_code: Error code (e.g., VALIDATION_ERROR)
            message: Sanitized error message
            
        Returns:
            User-friendly error message
        """
        # Validation errors - explain the problem
        if 'VALIDATION' in error_code:
            if 'polygon' in message.lower() or 'area' in message.lower():
                if 'small' in message.lower():
                    return "Polygon area is too small. Please draw a larger area."
                elif 'large' in message.lower():
                    return "Polygon area is too large. Please select a smaller area."
                elif 'vertex' in message.lower() or 'vertices' in message.lower():
                    return "Polygon has too many vertices. Please use a simpler shape."
                elif 'geometry' in message.lower():
                    return "Polygon geometry is invalid. Please provide a valid polygon."
                elif 'geojson' in message.lower():
                    return "Polygon format is invalid. Please provide valid GeoJSON."
            return "Invalid polygon. Please check your input and try again."
        
        # Keep sanitized message for other error types
        return message


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
