"""
Property-based tests for error handling and response formatting.

Uses hypothesis to verify error handling properties across many randomly
generated inputs and error conditions.
"""

import pytest
from hypothesis import given, strategies as st, assume
from datetime import datetime
import re

from backend.exceptions.error_handler import (
    ErrorCode,
    ErrorSeverity,
    SafeError,
    sanitize_error_message,
    http_status_for_error
)
from backend.exceptions.response_formatter import (
    format_error_response,
    format_success_response,
    format_validation_error_response,
    format_processing_status
)


# Strategies for generating test data

@st.composite
def error_codes(draw):
    """Generate random error codes."""
    return draw(st.sampled_from(list(ErrorCode)))


@st.composite
def error_messages(draw):
    """Generate readable error messages."""
    messages = [
        "Invalid input",
        "Resource not found",
        "Database connection failed",
        "Authentication required",
        "Permission denied",
        "Rate limit exceeded",
        "Service unavailable",
        "Invalid request format"
    ]
    return draw(st.sampled_from(messages))


@st.composite
def module_names(draw):
    """Generate module names."""
    modules = [
        "validator",
        "collector",
        "standardizer",
        "rule_engine",
        "output_generator",
        "data_manager"
    ]
    return draw(st.sampled_from(modules))


@st.composite
def processing_stages(draw):
    """Generate processing stages."""
    stages = ["validation", "collection", "standardization", "processing", "output"]
    return draw(st.one_of(st.just(None), st.sampled_from(stages)))


@st.composite
def safe_errors(draw):
    """Generate random SafeError objects."""
    return SafeError(
        error_code=draw(error_codes()),
        user_message=draw(error_messages()),
        module=draw(module_names()),
        stage=draw(processing_stages()),
        severity=draw(st.sampled_from(list(ErrorSeverity)))
    )


# Property-based tests

class TestHTTPStatusCodeConsistency:
    """
    Property 11: HTTP Status Code Consistency
    
    For any error code, the system should return consistent HTTP status codes:
    - Validation errors → 400
    - System errors → 500
    """
    
    @given(error_code=error_codes())
    def test_http_status_for_error_code_is_valid(self, error_code):
        """
        For any error code, http_status_for_error returns a valid HTTP status.
        **Property 11: HTTP Status Code Consistency**
        **Validates: Requirements 9.4, 9.5, 9.6, 9.7**
        """
        status = http_status_for_error(error_code)
        
        # All status codes should be valid HTTP status codes (100-599)
        assert isinstance(status, int)
        assert 100 <= status <= 599
    
    @given(error_code=error_codes())
    def test_http_status_for_validation_errors_is_4xx(self, error_code):
        """
        For validation error codes, http_status_for_error returns 4xx status.
        """
        if error_code in [ErrorCode.VALIDATION_ERROR, ErrorCode.POLYGON_VALIDATION_ERROR]:
            status = http_status_for_error(error_code)
            assert 400 <= status < 500
    
    @given(error_code=error_codes())
    def test_http_status_for_system_errors_is_5xx(self, error_code):
        """
        For system/provider error codes, http_status_for_error returns 5xx status.
        """
        if error_code in [ErrorCode.SYSTEM_ERROR, ErrorCode.INTERNAL_ERROR, 
                         ErrorCode.PROVIDER_ERROR, ErrorCode.PROCESSING_ERROR]:
            status = http_status_for_error(error_code)
            assert 500 <= status < 600


class TestErrorMessageSafety:
    """
    Property 12: Error Message Safety
    
    For any error condition, error messages should be readable but never expose:
    - Stack traces
    - File paths
    - Memory addresses
    - Internal implementation details
    """
    
    @given(message=st.text(min_size=1, max_size=500))
    def test_sanitized_message_has_no_stack_traces(self, message):
        """
        For any error message, sanitization should remove stack trace indicators.
        **Property 12: Error Message Safety**
        **Validates: Requirements 8.2, 8.5, 8.6**
        """
        sanitized = sanitize_error_message(message)
        
        # Should not contain common stack trace indicators
        assert "Traceback" not in sanitized
        assert "File" not in sanitized or "[file]" in sanitized
        assert "line" not in sanitized.lower() or "line" not in message.lower()
    
    @given(message=st.text(min_size=1, max_size=500))
    def test_sanitized_message_is_readable(self, message):
        """
        For any message, sanitization should preserve readability.
        """
        # Skip messages that are all non-ASCII to avoid rendering issues
        try:
            message.encode('utf-8').decode('utf-8')
        except:
            assume(False)
        
        sanitized = sanitize_error_message(message)
        
        # Should be a string
        assert isinstance(sanitized, str)
        
        # Should not be too long
        assert len(sanitized) <= 503  # 500 + "..."
        
        # Should be non-empty if original was non-empty
        if message.strip():
            assert len(sanitized) > 0
    
    def test_sanitized_message_removes_memory_addresses(self):
        """
        For messages containing memory addresses, sanitization should remove them.
        """
        message = "Object at 0x7f1234567890 failed with 0xdeadbeef"
        sanitized = sanitize_error_message(message)
        
        # Should remove memory addresses
        hex_pattern = r'0x[0-9a-fA-F]+'
        original_hex_count = len(re.findall(hex_pattern, message))
        sanitized_hex_count = len(re.findall(hex_pattern, sanitized))
        assert sanitized_hex_count < original_hex_count
    
    @given(error=safe_errors())
    def test_safe_error_dict_has_no_internal_details(self, error):
        """
        For any SafeError, the dict representation should be safe for users.
        """
        error_dict = error.to_dict()
        
        # Should not contain common internal details
        error_str = str(error_dict)
        assert "Traceback" not in error_str
        
        # Should have required fields
        assert "error_code" in error_dict
        assert "error_message" in error_dict
        assert "timestamp" in error_dict


class TestResponseFormatConsistency:
    """
    Property 9: Output Format Consistency
    
    For any analysis response, the format should be consistent with
    all required fields present and properly formatted.
    """
    
    @given(
        request_id=st.text(min_size=1, max_size=50),
        summary=st.dictionaries(st.text(), st.text(), min_size=0, max_size=10),
        info=st.dictionaries(st.text(), st.text(), min_size=0, max_size=10),
        status=st.dictionaries(st.text(), st.text(), min_size=0, max_size=10),
        providers=st.dictionaries(st.text(), st.text(), min_size=0, max_size=10),
        time_ms=st.floats(min_value=0, max_value=10000)
    )
    def test_success_response_format_consistency(
        self, request_id, summary, info, status, providers, time_ms
    ):
        """
        For any valid success response data, format_success_response
        returns properly formatted output.
        **Property 9: Output Format Consistency**
        **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8**
        """
        response = format_success_response(
            request_id=request_id,
            analysis_summary=summary,
            land_information=info,
            processing_status=status,
            provider_status=providers,
            processing_time_ms=time_ms
        )
        
        # Should have required fields
        assert "status" in response
        assert response["status"] == "success"
        assert "request_id" in response
        assert response["request_id"] == request_id
        assert "timestamp" in response
        assert "processing_time_ms" in response
        assert "analysis_summary" in response
        assert "land_information" in response
        assert "processing_status" in response
        assert "provider_status" in response
        
        # Timestamp should be ISO format
        assert isinstance(response["timestamp"], str)
        assert "T" in response["timestamp"]
        
        # Processing time should match input
        assert response["processing_time_ms"] == time_ms
    
    @given(
        error_code=st.text(min_size=1, max_size=50),
        error_msg=st.text(min_size=1, max_size=200),
        module=st.text(min_size=1, max_size=50)
    )
    def test_error_response_format_consistency(self, error_code, error_msg, module):
        """
        For any error response data, format_error_response returns
        properly formatted output with all required fields.
        """
        response = format_error_response(
            error_code=error_code,
            error_message=error_msg,
            module=module
        )
        
        # Should have required fields
        assert "status" in response
        assert response["status"] == "error"
        assert "error_code" in response
        assert response["error_code"] == error_code
        assert "error_message" in response
        assert response["error_message"] == error_msg
        assert "module" in response
        assert response["module"] == module
        assert "timestamp" in response
        
        # Timestamp should be ISO format
        assert "T" in response["timestamp"]
    
    @given(
        validation=st.sampled_from(["pending", "success", "partial", "failed"]),
        collection=st.sampled_from(["pending", "success", "partial", "failed"]),
        standardization=st.sampled_from(["pending", "success", "partial", "failed"]),
        rules=st.sampled_from(["pending", "success", "partial", "failed"]),
        output=st.sampled_from(["pending", "success", "partial", "failed"])
    )
    def test_processing_status_format(self, validation, collection, standardization, rules, output):
        """
        For any processing status values, format_processing_status
        returns all statuses correctly.
        """
        status = format_processing_status(
            validation=validation,
            data_collection=collection,
            standardization=standardization,
            rule_engine=rules,
            output_generation=output
        )
        
        # Should contain all status fields
        assert status["validation"] == validation
        assert status["data_collection"] == collection
        assert status["standardization"] == standardization
        assert status["rule_engine"] == rules
        assert status["output_generation"] == output
        
        # All values should be valid status strings
        valid_statuses = {"pending", "success", "partial", "failed"}
        for key, value in status.items():
            assert value in valid_statuses


class TestErrorMessageSanitizationComprehensive:
    """
    Comprehensive tests for error message sanitization across various
    potentially dangerous message types.
    """
    
    @given(st.text(min_size=0, max_size=1000))
    def test_sanitized_message_never_exceeds_max_length(self, message):
        """
        For any message, sanitization never produces output longer than 503 chars.
        """
        sanitized = sanitize_error_message(message)
        assert len(sanitized) <= 503
    
    @given(st.text(min_size=1, max_size=500))
    def test_sanitized_message_is_string(self, message):
        """
        For any message, sanitization always returns a string.
        """
        sanitized = sanitize_error_message(message)
        assert isinstance(sanitized, str)
    
    @given(message=st.just("User-friendly error: Invalid polygon at [file]"))
    def test_sanitization_preserves_readable_errors(self, message):
        """
        For user-friendly error messages, sanitization preserves content.
        """
        sanitized = sanitize_error_message(message)
        
        # Should preserve the core message
        assert "Invalid polygon" in sanitized or "error" in sanitized.lower()
