"""
Tests for error handling and response formatting.

Tests that errors are properly caught, sanitized, and returned to users
without exposing implementation details or stack traces.
"""

import pytest
from datetime import datetime

from backend.exceptions.error_handler import (
    SafeError,
    ErrorCode,
    ErrorSeverity,
    sanitize_error_message,
    create_error_response,
    http_status_for_error,
    ErrorContext
)
from backend.exceptions.response_formatter import (
    ResponseStatus,
    format_error_response,
    format_success_response,
    format_validation_error_response,
    format_processing_status,
    format_provider_status,
    format_error_info
)


class TestErrorSanitization:
    """Test error message sanitization."""
    
    def test_sanitize_removes_file_paths(self):
        """Verify file paths are removed from error messages."""
        message = "Error in /home/user/project/backend/file.py at line 42"
        sanitized = sanitize_error_message(message)
        assert "/home/user/project/backend/file.py" not in sanitized
        assert "[file]" in sanitized
    
    def test_sanitize_removes_windows_paths(self):
        """Verify Windows paths are removed."""
        message = "Error in C:\\Users\\Dev\\code\\app.py"
        sanitized = sanitize_error_message(message)
        assert "C:\\" not in sanitized or "[file]" in sanitized
    
    def test_sanitize_removes_memory_addresses(self):
        """Verify memory addresses are removed."""
        message = "Object at 0x7f1234567890 failed"
        sanitized = sanitize_error_message(message)
        assert "0x7f1234567890" not in sanitized
    
    def test_sanitize_truncates_long_messages(self):
        """Verify overly long messages are truncated."""
        message = "x" * 1000
        sanitized = sanitize_error_message(message)
        assert len(sanitized) <= 503  # 500 + "..."
    
    def test_sanitize_preserves_readable_content(self):
        """Verify readable error content is preserved."""
        message = "Invalid polygon: coordinates out of range"
        sanitized = sanitize_error_message(message)
        assert "Invalid polygon" in sanitized
        assert "coordinates" in sanitized


class TestSafeError:
    """Test SafeError class."""
    
    def test_safe_error_creation(self):
        """Verify SafeError can be created."""
        error = SafeError(
            error_code=ErrorCode.VALIDATION_ERROR,
            user_message="Input is invalid",
            module="validator"
        )
        assert error.error_code == ErrorCode.VALIDATION_ERROR
        assert error.user_message == "Input is invalid"
        assert error.module == "validator"
    
    def test_safe_error_to_dict(self):
        """Verify SafeError converts to dictionary."""
        error = SafeError(
            error_code=ErrorCode.VALIDATION_ERROR,
            user_message="Invalid input",
            module="validator",
            stage="validation",
            severity=ErrorSeverity.ERROR
        )
        error_dict = error.to_dict()
        
        assert error_dict["error_code"] == "VALIDATION_ERROR"
        assert error_dict["error_message"] == "Invalid input"
        assert error_dict["module"] == "validator"
        assert error_dict["stage"] == "validation"
        assert error_dict["severity"] == "error"
        assert "timestamp" in error_dict
    
    def test_safe_error_with_details(self):
        """Verify SafeError includes optional details."""
        details = {"field": "email", "reason": "invalid format"}
        error = SafeError(
            error_code=ErrorCode.VALIDATION_ERROR,
            user_message="Invalid email",
            module="validator",
            details=details
        )
        error_dict = error.to_dict()
        
        assert error_dict["details"] == details


class TestErrorResponseCreation:
    """Test error response creation."""
    
    def test_http_status_for_validation_error(self):
        """Verify validation errors map to 400."""
        status = http_status_for_error(ErrorCode.VALIDATION_ERROR)
        assert status == 400
    
    def test_http_status_for_polygon_validation_error(self):
        """Verify polygon validation errors map to 400."""
        status = http_status_for_error(ErrorCode.POLYGON_VALIDATION_ERROR)
        assert status == 400
    
    def test_http_status_for_system_error(self):
        """Verify system errors map to 500."""
        status = http_status_for_error(ErrorCode.SYSTEM_ERROR)
        assert status == 500
    
    def test_create_error_response(self):
        """Verify error response is properly formatted."""
        error = SafeError(
            error_code=ErrorCode.VALIDATION_ERROR,
            user_message="Invalid input",
            module="validator"
        )
        response = create_error_response(
            status_code=400,
            error=error,
            request_id="req_123"
        )
        
        assert response["status"] == "error"
        assert response["request_id"] == "req_123"
        assert response["http_status"] == 400
        assert response["error"]["error_code"] == "VALIDATION_ERROR"


class TestResponseFormatters:
    """Test response formatting functions."""
    
    def test_format_error_response(self):
        """Verify error response formatting."""
        response = format_error_response(
            error_code="VALIDATION_ERROR",
            error_message="Invalid input",
            module="validator",
            request_id="req_123"
        )
        
        assert response["status"] == "error"
        assert response["error_code"] == "VALIDATION_ERROR"
        assert response["error_message"] == "Invalid input"
        assert response["module"] == "validator"
        assert response["request_id"] == "req_123"
        assert "timestamp" in response
    
    def test_format_success_response(self):
        """Verify success response formatting."""
        response = format_success_response(
            request_id="req_123",
            analysis_summary={"key": "value"},
            land_information={"land_cover": "grass"},
            processing_status={"validation": "success"},
            provider_status={"osm": "available"},
            processing_time_ms=150.5
        )
        
        assert response["status"] == "success"
        assert response["request_id"] == "req_123"
        assert response["analysis_summary"]["key"] == "value"
        assert response["land_information"]["land_cover"] == "grass"
        assert response["processing_status"]["validation"] == "success"
        assert response["provider_status"]["osm"] == "available"
        assert response["processing_time_ms"] == 150.5
    
    def test_format_validation_error_response(self):
        """Verify validation error response formatting."""
        response = format_validation_error_response(
            polygon_error="Invalid polygon geometry",
            request_id="req_123"
        )
        
        assert response["status"] == "error"
        assert response["error_code"] == "POLYGON_VALIDATION_ERROR"
        assert response["error_message"] == "Invalid polygon geometry"
        assert response["module"] == "polygon_validator"
        assert response["stage"] == "validation"
        assert response["request_id"] == "req_123"
    
    def test_format_processing_status(self):
        """Verify processing status formatting."""
        status = format_processing_status(
            validation="success",
            data_collection="partial",
            standardization="success",
            rule_engine="success",
            output_generation="failed"
        )
        
        assert status["validation"] == "success"
        assert status["data_collection"] == "partial"
        assert status["standardization"] == "success"
        assert status["rule_engine"] == "success"
        assert status["output_generation"] == "failed"
    
    def test_format_provider_status_available(self):
        """Verify provider status formatting for available provider."""
        status = format_provider_status(
            provider_name="openstreetmap",
            available=True,
            data_retrieved=True
        )
        
        assert status["provider_name"] == "openstreetmap"
        assert status["status"] == "available"
        assert status["data_retrieved"] is True
    
    def test_format_provider_status_unavailable(self):
        """Verify provider status formatting for unavailable provider."""
        status = format_provider_status(
            provider_name="copernicus",
            available=False,
            data_retrieved=False,
            error_message="Connection timeout"
        )
        
        assert status["provider_name"] == "copernicus"
        assert status["status"] == "unavailable"
        assert status["data_retrieved"] is False
        assert status["error_message"] == "Connection timeout"
    
    def test_format_error_info(self):
        """Verify error information formatting."""
        error_info = format_error_info(
            module="data_collector",
            message="Provider timeout",
            severity="error"
        )
        
        assert error_info["module"] == "data_collector"
        assert error_info["message"] == "Provider timeout"
        assert error_info["severity"] == "error"
        assert "timestamp" in error_info


class TestErrorContext:
    """Test ErrorContext for structured error tracking."""
    
    def test_error_context_creation(self):
        """Verify ErrorContext can be created."""
        ctx = ErrorContext(
            module="test_module",
            stage="testing",
            request_id="req_123"
        )
        
        assert ctx.module == "test_module"
        assert ctx.stage == "testing"
        assert ctx.request_id == "req_123"
        assert not ctx.has_errors()
    
    def test_error_context_add_error(self):
        """Verify errors can be added to context."""
        ctx = ErrorContext(module="test_module")
        
        error = SafeError(
            error_code=ErrorCode.VALIDATION_ERROR,
            user_message="Test error",
            module="test_module"
        )
        
        ctx.add_error(error)
        
        assert ctx.has_errors()
        assert len(ctx.errors) == 1
    
    def test_error_context_critical_detection(self):
        """Verify context detects critical errors."""
        ctx = ErrorContext(module="test_module")
        
        critical_error = SafeError(
            error_code=ErrorCode.SYSTEM_ERROR,
            user_message="System failure",
            module="test_module",
            severity=ErrorSeverity.CRITICAL
        )
        
        ctx.add_error(critical_error)
        
        assert ctx.has_critical_errors()
    
    def test_error_context_summary(self):
        """Verify error summary generation."""
        ctx = ErrorContext(module="test_module")
        
        error1 = SafeError(
            error_code=ErrorCode.VALIDATION_ERROR,
            user_message="Error 1",
            module="test_module"
        )
        error2 = SafeError(
            error_code=ErrorCode.PROCESSING_ERROR,
            user_message="Error 2",
            module="test_module",
            severity=ErrorSeverity.CRITICAL
        )
        
        ctx.add_error(error1)
        ctx.add_error(error2)
        
        summary = ctx.get_error_summary()
        
        assert summary is not None
        assert summary["error_count"] == 2
        assert summary["critical_count"] == 1
        assert len(summary["errors"]) == 2


class TestResponseStatusEnum:
    """Test ResponseStatus enum."""
    
    def test_response_status_values(self):
        """Verify response status enum values."""
        assert ResponseStatus.SUCCESS.value == "success"
        assert ResponseStatus.PARTIAL.value == "partial"
        assert ResponseStatus.ERROR.value == "error"
