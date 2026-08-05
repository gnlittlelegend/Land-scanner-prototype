/**
 * Polygon Validation Utility
 * Validates polygon size (10 m² to 100 km²) and vertex count (max 10,000)
 */

import * as turf from '@turf/turf'

const MIN_AREA_M2 = 10 // 10 square meters
const MAX_AREA_M2 = 100 * 1_000_000 // 100 square kilometers = 100M square meters
const MAX_VERTICES = 10_000

/**
 * Convert square meters to square kilometers
 * @param {number} areaM2 - Area in square meters
 * @returns {number} Area in square kilometers
 */
function m2ToKm2(areaM2) {
  return areaM2 / 1_000_000
}

/**
 * Convert square kilometers to square meters
 * @param {number} areaKm2 - Area in square kilometers
 * @returns {number} Area in square meters
 */
function km2ToM2(areaKm2) {
  return areaKm2 * 1_000_000
}

/**
 * Count the total number of vertices in a polygon
 * @param {Object} polygon - GeoJSON polygon object
 * @returns {number} Total vertex count
 */
function countVertices(polygon) {
  if (!polygon || !polygon.coordinates) {
    return 0
  }

  let count = 0
  
  // For Polygon: coordinates is an array of rings
  if (polygon.type === 'Polygon') {
    for (const ring of polygon.coordinates) {
      count += ring.length - 1 // Exclude closing vertex (duplicate of first)
    }
  }
  // For MultiPolygon: coordinates is an array of polygons
  else if (polygon.type === 'MultiPolygon') {
    for (const polygonCoords of polygon.coordinates) {
      for (const ring of polygonCoords) {
        count += ring.length - 1 // Exclude closing vertex (duplicate of first)
      }
    }
  }

  return count
}

/**
 * Validate a polygon's area
 * @param {Object} polygon - GeoJSON polygon object
 * @returns {Object} Validation result { valid: boolean, area_m2: number, area_km2: number, error: string|null }
 */
function validateArea(polygon) {
  try {
    // Use turf.js to calculate area
    const feature = {
      type: 'Feature',
      geometry: polygon,
      properties: {}
    }
    
    const areaKm2 = turf.area(feature) / 1_000_000 // turf.area returns square meters
    const areaM2 = areaKm2 * 1_000_000

    if (areaM2 < MIN_AREA_M2) {
      return {
        valid: false,
        area_m2: areaM2,
        area_km2: areaKm2,
        error: `Polygon area is too small (${areaM2.toFixed(2)} m²). Minimum area is ${MIN_AREA_M2} m².`
      }
    }

    if (areaM2 > MAX_AREA_M2) {
      return {
        valid: false,
        area_m2: areaM2,
        area_km2: areaKm2,
        error: `Polygon area is too large (${areaKm2.toFixed(2)} km²). Maximum area is ${m2ToKm2(MAX_AREA_M2).toFixed(0)} km².`
      }
    }

    return {
      valid: true,
      area_m2: areaM2,
      area_km2: areaKm2,
      error: null
    }
  } catch (error) {
    return {
      valid: false,
      area_m2: null,
      area_km2: null,
      error: `Unable to calculate area: ${error.message}`
    }
  }
}

/**
 * Validate a polygon's vertex count
 * @param {Object} polygon - GeoJSON polygon object
 * @returns {Object} Validation result { valid: boolean, vertex_count: number, error: string|null }
 */
function validateVertexCount(polygon) {
  const vertexCount = countVertices(polygon)

  if (vertexCount > MAX_VERTICES) {
    return {
      valid: false,
      vertex_count: vertexCount,
      error: `Polygon has too many vertices (${vertexCount}). Maximum is ${MAX_VERTICES} vertices.`
    }
  }

  return {
    valid: true,
    vertex_count: vertexCount,
    error: null
  }
}

/**
 * Validate a complete polygon (area and vertex count)
 * @param {Object} polygon - GeoJSON polygon object
 * @returns {Object} Complete validation result
 */
function validatePolygon(polygon) {
  if (!polygon) {
    return {
      valid: false,
      error: 'Polygon is required'
    }
  }

  if (!polygon.type || (polygon.type !== 'Polygon' && polygon.type !== 'MultiPolygon')) {
    return {
      valid: false,
      error: `Invalid polygon type: ${polygon.type}. Only Polygon and MultiPolygon types are supported.`
    }
  }

  if (!polygon.coordinates || polygon.coordinates.length === 0) {
    return {
      valid: false,
      error: 'Polygon coordinates are missing or empty'
    }
  }

  // Validate vertex count first (faster)
  const vertexValidation = validateVertexCount(polygon)
  if (!vertexValidation.valid) {
    return {
      valid: false,
      error: vertexValidation.error,
      vertex_count: vertexValidation.vertex_count
    }
  }

  // Validate area
  const areaValidation = validateArea(polygon)
  if (!areaValidation.valid) {
    return {
      valid: false,
      error: areaValidation.error,
      area_m2: areaValidation.area_m2,
      area_km2: areaValidation.area_km2,
      vertex_count: vertexValidation.vertex_count
    }
  }

  // All validations passed
  return {
    valid: true,
    error: null,
    area_m2: areaValidation.area_m2,
    area_km2: areaValidation.area_km2,
    vertex_count: vertexValidation.vertex_count
  }
}

export {
  validatePolygon,
  validateArea,
  validateVertexCount,
  countVertices,
  m2ToKm2,
  km2ToM2,
  MIN_AREA_M2,
  MAX_AREA_M2,
  MAX_VERTICES
}
