"""Custom exceptions for Land Scanner."""

class LandScannerException(Exception):
    """Base exception for Land Scanner."""
    pass


class ValidationError(LandScannerException):
    """Raised when validation fails."""
    pass


class CollectionError(LandScannerException):
    """Raised when data collection fails."""
    pass


class StandardizationError(LandScannerException):
    """Raised when standardization fails."""
    pass


class RuleEngineError(LandScannerException):
    """Raised when rule engine encounters errors."""
    pass
