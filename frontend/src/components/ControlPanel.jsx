import React, { useRef } from 'react'

export default function ControlPanel({
  onClear,
  onAnalyze,
  onGeoJSONUpload,
  hasPolygon,
  isAnalyzing
}) {
  const fileInputRef = useRef(null)

  const handleFileUpload = (event) => {
    const file = event.target.files[0]

    if (!file) {
      return
    }

    if (!file.name.endsWith('.geojson') && !file.name.endsWith('.json')) {
      alert('Please upload a .geojson or .json file')
      event.target.value = ''
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const geojson = JSON.parse(e.target.result)

        if (!geojson.type) {
          throw new Error('Invalid GeoJSON: missing type property')
        }

        let features = []
        if (geojson.type === 'FeatureCollection') {
          features = geojson.features
        } else if (geojson.type === 'Feature') {
          features = [geojson]
        } else if (geojson.type === 'Polygon' || geojson.type === 'MultiPolygon') {
          features = [{ type: 'Feature', geometry: geojson, properties: {} }]
        } else {
          throw new Error('Unsupported GeoJSON type: ' + geojson.type)
        }

        if (features.length === 0) {
          throw new Error('No features found in GeoJSON file')
        }

        const feature = features[0]
        onGeoJSONUpload(feature.geometry || feature)
      } catch (error) {
        alert('Failed to parse GeoJSON: ' + error.message)
      }

      event.target.value = ''
    }

    reader.onerror = () => {
      alert('Failed to read file')
      event.target.value = ''
    }

    reader.readAsText(file)
  }

  return (
    <div className="control-panel">
      <div className="control-group">
        <label htmlFor="geojson-input">Upload GeoJSON:</label>
        <input
          type="file"
          id="geojson-input"
          ref={fileInputRef}
          accept=".geojson,.json"
          onChange={handleFileUpload}
          title="Upload a GeoJSON file"
        />
      </div>
      <div className="control-group">
        <button
          id="clear-polygon"
          className="btn btn-danger"
          onClick={onClear}
          disabled={!hasPolygon || isAnalyzing}
        >
          Clear Polygon
        </button>
        <button
          id="analyze-btn"
          className="btn btn-primary"
          onClick={onAnalyze}
          disabled={!hasPolygon || isAnalyzing}
        >
          {isAnalyzing ? 'Analyzing...' : 'Analyze'}
        </button>
      </div>
    </div>
  )
}
