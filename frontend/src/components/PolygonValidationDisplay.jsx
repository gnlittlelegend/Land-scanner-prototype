import React from 'react'

/**
 * PolygonValidationDisplay Component
 * Displays polygon validation status and details when drawing/editing
 */
export default function PolygonValidationDisplay({ validationResult }) {
  if (!validationResult) {
    return null
  }

  const { valid, error, area_km2, vertex_count } = validationResult

  if (valid) {
    return (
      <div className="polygon-validation-display valid">
        <div className="validation-icon">✓</div>
        <div className="validation-content">
          <div className="validation-status">Polygon Valid</div>
          <div className="validation-details">
            {area_km2 !== null && (
              <span className="detail-item">
                Area: {area_km2.toFixed(4)} km²
              </span>
            )}
            {vertex_count !== null && (
              <span className="detail-item">
                Vertices: {vertex_count}
              </span>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="polygon-validation-display invalid">
      <div className="validation-icon">✕</div>
      <div className="validation-content">
        <div className="validation-status">Polygon Invalid</div>
        <div className="validation-message">{error}</div>
      </div>
    </div>
  )
}
