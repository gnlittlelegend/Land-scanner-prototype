/**
 * API Service Layer
 * Centralized API client for all backend communication
 * Handles: request/response formatting, error handling, timeouts, and request tracking
 */

const API_BASE = import.meta.env.VITE_API_BASE || 'https://land-scanner-prototype-backend.onrender.com'
const API_TIMEOUT = 60000 // 60 seconds

/**
 * @typedef {Object} ApiResponse
 * @property {string} request_id - Unique request identifier
 * @property {string} status - Processing status (success, partial, failed)
 * @property {number} processing_time_ms - Total processing time
 * @property {Object} analysis_summary - High-level summary
 * @property {Object} land_information - Rule results organized by category
 * @property {Object} processing_status - Status of each processing module
 * @property {Array} provider_status - Status of each data provider
 * @property {Array} errors - List of errors if any occurred
 */

/**
 * Format error response consistently
 * @param {Error|Object} error - The error to format
 * @param {string} context - Where the error occurred
 * @returns {Object} Formatted error object
 */
function formatError(error, context) {
  return {
    context,
    message: error?.message || String(error) || 'Unknown error',
    timestamp: new Date().toISOString(),
    type: error?.name || 'Error'
  }
}

/**
 * Validate GeoJSON polygon structure on client side
 * @param {Object} polygon - GeoJSON polygon object
 * @throws {Error} If polygon is invalid
 */
function validatePolygon(polygon) {
  if (!polygon) {
    throw new Error('Polygon is required')
  }

  if (!polygon.type || polygon.type !== 'Polygon') {
    throw new Error('Invalid GeoJSON: type must be "Polygon"')
  }

  if (!Array.isArray(polygon.coordinates)) {
    throw new Error('Invalid GeoJSON: coordinates must be an array')
  }

  if (polygon.coordinates.length === 0) {
    throw new Error('Invalid GeoJSON: coordinates cannot be empty')
  }

  // Each coordinate should be [lon, lat]
  const firstRing = polygon.coordinates[0]
  if (!Array.isArray(firstRing) || firstRing.length < 3) {
    throw new Error('Invalid GeoJSON: polygon must have at least 3 coordinate pairs')
  }

  firstRing.forEach((coord, idx) => {
    if (!Array.isArray(coord) || coord.length < 2) {
      throw new Error(`Invalid GeoJSON: coordinate at index ${idx} must be [longitude, latitude]`)
    }
    const [lon, lat] = coord
    if (typeof lon !== 'number' || typeof lat !== 'number') {
      throw new Error(`Invalid GeoJSON: coordinates must be numbers at index ${idx}`)
    }
    if (lon < -180 || lon > 180 || lat < -90 || lat > 90) {
      throw new Error(`Invalid GeoJSON: out of bounds at coordinate index ${idx}`)
    }
  })
}

/**
 * Execute API request with timeout and error handling
 * @param {string} endpoint - API endpoint path (e.g., '/analyze')
 * @param {Object} options - Fetch options
 * @returns {Promise<ApiResponse>} API response
 * @throws {Error} If request fails or times out
 */
async function executeRequest(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    })

    clearTimeout(timeoutId)

    // Handle HTTP errors
    if (!response.ok) {
      let errorData = {}
      try {
        errorData = await response.json()
      } catch {
        // Response body is not JSON, use status text
      }

      const errorMessage = errorData.detail?.message || 
                          errorData.error_message || 
                          errorData.detail ||
                          `HTTP ${response.status}: ${response.statusText}`

      const error = new Error(errorMessage)
      error.status = response.status
      error.response = errorData
      throw error
    }

    return await response.json()
  } catch (error) {
    clearTimeout(timeoutId)

    if (error.name === 'AbortError') {
      throw new Error(`Request timeout after ${API_TIMEOUT}ms. Please try again.`)
    }

    throw error
  }
}

/**
 * Analyze a polygon using the backend analysis engine
 * @param {Object} polygon - GeoJSON polygon to analyze
 * @returns {Promise<ApiResponse>} Analysis results
 * @throws {Error} If validation or request fails
 */
async function analyzePolygon(polygon) {
  // Validate on client side first
  validatePolygon(polygon)

  const response = await executeRequest('/analyze', {
    method: 'POST',
    body: JSON.stringify({ polygon })
  })

  // Request succeeded, validate response structure
  if (!response.request_id) {
    throw new Error('Invalid API response: missing request_id')
  }

  return response
}

/**
 * Check backend health status
 * @returns {Promise<Object>} Health check response
 */
async function checkHealth() {
  return executeRequest('/health', { method: 'GET' })
}

/**
 * Get service status and configuration
 * @returns {Promise<Object>} Service status response
 */
async function getStatus() {
  return executeRequest('/status', { method: 'GET' })
}

/**
 * Log API event for debugging/monitoring
 * @param {string} requestId - Request ID from API response
 * @param {string} eventType - Type of event (e.g., 'request_sent', 'response_received')
 * @param {Object} details - Additional event details
 */
function logApiEvent(requestId, eventType, details = {}) {
  if (import.meta.env.DEV) {
    console.log(`[API ${eventType}] Request: ${requestId}`, details)
  }
}

export {
  API_BASE,
  API_TIMEOUT,
  analyzePolygon,
  checkHealth,
  getStatus,
  executeRequest,
  validatePolygon,
  formatError,
  logApiEvent
}
