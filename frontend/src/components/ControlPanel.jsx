import React, { useState } from 'react'
import FileUpload from './FileUpload'
import PolygonValidationDisplay from './PolygonValidationDisplay'

export default function ControlPanel({
  onClear,
  onAnalyze,
  onGeoJSONUpload,
  hasPolygon,
  isAnalyzing,
  polygonValidation
}) {
  const [uploadError, setUploadError] = useState(null)

  const handleFileUploadSuccess = (geometry) => {
    setUploadError(null)
    onGeoJSONUpload(geometry)
  }

  const handleFileUploadError = (error) => {
    setUploadError(error)
  }

  return (
    <div className="control-panel">
      <PolygonValidationDisplay validationResult={polygonValidation} />
      <div className="control-group">
        <label>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          Upload GeoJSON:
        </label>
        <FileUpload
          onUpload={handleFileUploadSuccess}
          onError={handleFileUploadError}
          isDisabled={isAnalyzing}
        />
        {uploadError && <p className="error-text">{uploadError}</p>}
      </div>
      <div className="control-group">
        <button
          id="clear-polygon"
          className="btn btn-danger"
          onClick={onClear}
          disabled={!hasPolygon || isAnalyzing}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M3 6h18" />
            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
          </svg>
          Clear Polygon
        </button>
        <button
          id="analyze-btn"
          className="btn btn-primary"
          onClick={onAnalyze}
          disabled={!hasPolygon || isAnalyzing || (polygonValidation && !polygonValidation.valid)}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          {isAnalyzing ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>
    </div>
  )
}
