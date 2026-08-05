import React, { useState } from 'react'
import Header from './components/Header'
import MapContainer from './components/MapContainer'
import ControlPanel from './components/ControlPanel'
import ResultsPanel from './components/ResultsPanel'
import ErrorDisplay from './components/ErrorDisplay'
import LoadingIndicator from './components/LoadingIndicator'
import ErrorBoundary from './components/ErrorBoundary'
import { analyzePolygon, logApiEvent } from './services/api'
import './index.css'

export default function App() {
  const [currentPolygon, setCurrentPolygon] = useState(null)
  const [analysisResults, setAnalysisResults] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [analysisInProgress, setAnalysisInProgress] = useState(false)
  const [currentRequestId, setCurrentRequestId] = useState(null)
  const [polygonValidation, setPolygonValidation] = useState(null)

  const handlePolygonDraw = (polygon) => {
    setCurrentPolygon(polygon)
    setError(null)
  }

  const handleValidationChange = (validation) => {
    setPolygonValidation(validation)
    if (validation && !validation.valid) {
      setError(validation.error)
    } else {
      setError(null)
    }
  }

  const handleClearPolygon = () => {
    setCurrentPolygon(null)
    setAnalysisResults(null)
    setError(null)
    setPolygonValidation(null)
  }

  const handleGeoJSONUpload = (geojson) => {
    // Validate uploaded GeoJSON
    const { validatePolygon } = require('./utils/polygonValidator')
    const validation = validatePolygon(geojson)
    
    if (validation.valid) {
      setCurrentPolygon(geojson)
      setPolygonValidation(validation)
      setError(null)
    } else {
      setCurrentPolygon(null)
      setPolygonValidation(validation)
      setError(validation.error)
    }
  }

  const handleAnalyze = async () => {
    if (!currentPolygon) {
      setError('Please draw or upload a polygon first')
      return
    }

    if (analysisInProgress) {
      setError('Analysis already in progress')
      return
    }

    setLoading(true)
    setAnalysisInProgress(true)
    setError(null)

    try {
      logApiEvent(null, 'polygon_analysis_started', { polygon: currentPolygon })
      
      const results = await analyzePolygon(currentPolygon)
      
      // Store request ID for tracking
      if (results.request_id) {
        setCurrentRequestId(results.request_id)
        logApiEvent(results.request_id, 'analysis_completed', { 
          processing_time_ms: results.processing_time_ms,
          status: results.status 
        })
      }
      
      setAnalysisResults(results)
    } catch (err) {
      let errorMsg = 'Failed to analyze polygon'
      if (err.message.includes('timeout')) {
        errorMsg = err.message
      } else if (err.message) {
        errorMsg = err.message
      }
      
      logApiEvent(currentRequestId, 'analysis_failed', { error: errorMsg })
      setError(errorMsg)
    } finally {
      setLoading(false)
      setAnalysisInProgress(false)
    }
  }

  return (
    <ErrorBoundary>
      <div className="container">
        <Header />
        <div className="main-content">
          <ErrorBoundary>
            <MapContainer
              onPolygonDraw={handlePolygonDraw}
              onGeoJSONUpload={handleGeoJSONUpload}
              onValidationChange={handleValidationChange}
              currentPolygon={currentPolygon}
            />
          </ErrorBoundary>
          <ErrorBoundary>
            <ControlPanel
              onClear={handleClearPolygon}
              onAnalyze={handleAnalyze}
              onGeoJSONUpload={handleGeoJSONUpload}
              hasPolygon={!!currentPolygon}
              isAnalyzing={analysisInProgress}
              polygonValidation={polygonValidation}
            />
          </ErrorBoundary>
        </div>
        <ErrorBoundary>
          {analysisResults && <ResultsPanel results={analysisResults} />}
        </ErrorBoundary>
        <ErrorBoundary>
          {error && (
            <ErrorDisplay 
              error={error} 
              severity={error?.severity || 'error'}
              onClose={() => setError(null)} 
            />
          )}
        </ErrorBoundary>
        <ErrorBoundary>
          {loading && <LoadingIndicator />}
        </ErrorBoundary>
      </div>
    </ErrorBoundary>
  )
}
