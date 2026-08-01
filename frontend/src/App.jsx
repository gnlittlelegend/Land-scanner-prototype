import React, { useState } from 'react'
import Header from './components/Header'
import MapContainer from './components/MapContainer'
import ControlPanel from './components/ControlPanel'
import ResultsPanel from './components/ResultsPanel'
import ErrorPanel from './components/ErrorPanel'
import LoadingIndicator from './components/LoadingIndicator'
import ErrorBoundary from './components/ErrorBoundary'
import './index.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'https://land-scanner-prototype-backend.onrender.com'
const API_TIMEOUT = 60000

export default function App() {
  const [currentPolygon, setCurrentPolygon] = useState(null)
  const [analysisResults, setAnalysisResults] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const [analysisInProgress, setAnalysisInProgress] = useState(false)

  const handlePolygonDraw = (polygon) => {
    setCurrentPolygon(polygon)
    setError(null)
  }

  const handleClearPolygon = () => {
    setCurrentPolygon(null)
    setAnalysisResults(null)
    setError(null)
  }

  const handleGeoJSONUpload = (geojson) => {
    setCurrentPolygon(geojson)
    setError(null)
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
      const response = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ polygon: currentPolygon })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.error_message || `Server error: ${response.status}`)
      }

      const results = await response.json()
      setAnalysisResults(results)
    } catch (err) {
      let errorMsg = 'Failed to analyze polygon'
      if (err.name === 'AbortError') {
        errorMsg = 'Analysis request timed out. Please try again.'
      } else if (err.message) {
        errorMsg = err.message
      }
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
            />
          </ErrorBoundary>
        </div>
        <ErrorBoundary>
          {analysisResults && <ResultsPanel results={analysisResults} />}
        </ErrorBoundary>
        <ErrorBoundary>
          {error && <ErrorPanel error={error} onClose={() => setError(null)} />}
        </ErrorBoundary>
        <ErrorBoundary>
          {loading && <LoadingIndicator />}
        </ErrorBoundary>
      </div>
    </ErrorBoundary>
  )
}
