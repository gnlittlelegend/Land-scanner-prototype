import React from 'react'
import '../styles/ErrorDisplay.css'

/**
 * ErrorDisplay Component
 * 
 * Displays error messages with severity levels, error codes, and provider-specific information.
 * Task 11.7: Implement error display component
 * 
 * Props:
 *   error - Error object or string from API response
 *   severity - Error severity level (warning, error, critical)
 *   onClose - Callback when error is dismissed
 */
export default function ErrorDisplay({ error, severity = 'error', onClose }) {
  if (!error) return null

  // Parse error information from various formats
  const getErrorInfo = () => {
    let errorCode = null
    let errorMessage = null
    let errorDetails = null
    let providers = []

    if (typeof error === 'string') {
      // Simple string error
      errorMessage = error
    } else if (typeof error === 'object') {
      // Complex error object from API
      errorCode = error.error_code || error.code
      errorMessage = error.error_message || error.message || error.detail || 'Unknown error'
      errorDetails = error.details || error.provider_failures || null
      
      // Extract provider-specific failures
      if (error.provider_status) {
        providers = Object.entries(error.provider_status)
          .filter(([_, status]) => !status.data_retrieved && status.error_message)
          .map(([name, status]) => ({
            name,
            message: status.error_message
          }))
      }
    }

    return { errorCode, errorMessage, errorDetails, providers }
  }

  const { errorCode, errorMessage, errorDetails, providers } = getErrorInfo()

  // Map severity levels to icons and colors
  const getSeverityIcon = () => {
    switch (severity) {
      case 'warning':
        return (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3.05h16.94a2 2 0 0 0 1.71-3.05l-8.47-14.14a2 2 0 0 0-3.42 0z" />
            <line x1="12" y1="9" x2="12" y2="13" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
        )
      case 'critical':
        return (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        )
      case 'error':
      default:
        return (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        )
    }
  }

  // Make error message more readable for users
  const formatErrorMessage = (message) => {
    // Remove technical jargon and make user-friendly
    if (!message) return 'An error occurred during analysis'
    
    // Clean up common API error messages
    const replacements = {
      'POLYGON_VALIDATION_ERROR': 'Invalid polygon',
      'DATA_COLLECTION_ERROR': 'Failed to collect data',
      'STANDARDIZATION_ERROR': 'Failed to process data',
      'RULE_ENGINE_ERROR': 'Failed to analyze data',
      'OUTPUT_GENERATION_ERROR': 'Failed to generate results',
      'timeout': 'request timed out - please try again',
      'ConnectionError': 'unable to connect to data providers',
      'HTTPError': 'data provider returned an error',
      'JSON': 'received invalid response format'
    }

    let cleaned = message
    for (const [technical, friendly] of Object.entries(replacements)) {
      const regex = new RegExp(technical, 'gi')
      cleaned = cleaned.replace(regex, friendly)
    }

    return cleaned
  }

  return (
    <div className={`error-display error-display--${severity} fade-in`}>
      <div className="error-display__header">
        <div className="error-display__icon">
          {getSeverityIcon()}
        </div>
        <div className="error-display__title">
          {severity === 'warning' && 'Warning'}
          {severity === 'error' && 'Error'}
          {severity === 'critical' && 'Critical Error'}
        </div>
        <button
          className="error-display__close"
          onClick={onClose}
          aria-label="Close error"
          type="button"
        >
          ×
        </button>
      </div>

      <div className="error-display__content">
        {/* Main error message */}
        <div className="error-display__message">
          {formatErrorMessage(errorMessage)}
        </div>

        {/* Error code if available */}
        {errorCode && (
          <div className="error-display__code">
            Error Code: <code>{errorCode}</code>
          </div>
        )}

        {/* Provider-specific errors */}
        {providers.length > 0 && (
          <div className="error-display__providers">
            <h4>Data Provider Issues:</h4>
            <ul>
              {providers.map((provider, idx) => (
                <li key={idx}>
                  <strong>{provider.name}:</strong> {formatErrorMessage(provider.message)}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Additional details if available */}
        {errorDetails && typeof errorDetails === 'object' && (
          <div className="error-display__details">
            <details>
              <summary>Additional Details</summary>
              <pre className="error-display__details-content">
                {JSON.stringify(errorDetails, null, 2)}
              </pre>
            </details>
          </div>
        )}

        {/* Action suggestions based on error type */}
        <div className="error-display__suggestions">
          {errorCode && errorCode.includes('POLYGON') && (
            <p><strong>Suggestion:</strong> Check that your polygon is between 10 m² and 100 km²</p>
          )}
          {errorMessage && errorMessage.toLowerCase().includes('timeout') && (
            <p><strong>Suggestion:</strong> Try again in a moment or draw a smaller area</p>
          )}
          {errorMessage && errorMessage.toLowerCase().includes('unavailable') && (
            <p><strong>Suggestion:</strong> Data providers may be temporarily offline. Please try again later</p>
          )}
          {!errorCode && !errorMessage.toLowerCase().includes('timeout') && !errorMessage.toLowerCase().includes('unavailable') && (
            <p><strong>Suggestion:</strong> Try refreshing the page and analyzing again</p>
          )}
        </div>
      </div>
    </div>
  )
}
