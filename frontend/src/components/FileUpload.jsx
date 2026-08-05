import React, { useRef, useState } from 'react'
import { validatePolygon } from '../utils/polygonValidator'
import '../styles/FileUpload.css'

export default function FileUpload({ onUpload, onError, isDisabled }) {
  const fileInputRef = useRef(null)
  const [isDragging, setIsDragging] = useState(false)
  const [fileName, setFileName] = useState('')
  const [uploadStatus, setUploadStatus] = useState('')

  const handleDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }

  const handleDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)

    const files = e.dataTransfer.files
    if (files.length > 0) {
      processFile(files[0])
    }
  }

  const handleFileSelect = (event) => {
    const file = event.target.files[0]
    if (file) {
      processFile(file)
    }
    event.target.value = ''
  }

  const processFile = (file) => {
    // Validate file type
    if (!file.name.endsWith('.geojson') && !file.name.endsWith('.json')) {
      const error = 'Please upload a .geojson or .json file'
      onError(error)
      setUploadStatus(error)
      setFileName('')
      return
    }

    setFileName(file.name)
    setUploadStatus('Processing...')

    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const geojson = JSON.parse(e.target.result)

        if (!geojson.type) {
          throw new Error('Invalid GeoJSON: missing type property')
        }

        let geometry = null

        // Handle different GeoJSON types
        if (geojson.type === 'FeatureCollection') {
          if (!geojson.features || geojson.features.length === 0) {
            throw new Error('No features found in GeoJSON file')
          }
          geometry = geojson.features[0].geometry
        } else if (geojson.type === 'Feature') {
          geometry = geojson.geometry
        } else if (geojson.type === 'Polygon' || geojson.type === 'MultiPolygon') {
          geometry = geojson
        } else {
          throw new Error(`Unsupported GeoJSON type: ${geojson.type}`)
        }

        if (!geometry) {
          throw new Error('No valid geometry found in GeoJSON file')
        }

        // Validate polygon size and vertex count
        const validation = validatePolygon(geometry)

        if (!validation.valid) {
          throw new Error(validation.error)
        }

        setUploadStatus('Uploaded successfully')
        onUpload(geometry)
      } catch (error) {
        const errorMsg = `Failed to parse GeoJSON: ${error.message}`
        onError(errorMsg)
        setUploadStatus(errorMsg)
        setFileName('')
      }
    }

    reader.onerror = () => {
      const errorMsg = 'Failed to read file'
      onError(errorMsg)
      setUploadStatus(errorMsg)
      setFileName('')
    }

    reader.readAsText(file)
  }

  const handleClickUpload = () => {
    if (!isDisabled) {
      fileInputRef.current?.click()
    }
  }

  return (
    <div className="file-upload-component">
      <div
        className={`file-upload-area ${isDragging ? 'dragging' : ''} ${isDisabled ? 'disabled' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClickUpload}
      >
        <input
          type="file"
          ref={fileInputRef}
          accept=".geojson,.json"
          onChange={handleFileSelect}
          disabled={isDisabled}
          style={{ display: 'none' }}
          title="Upload a GeoJSON file"
        />

        <div className="upload-content">
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="upload-icon"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>

          <p className="upload-text">
            <strong>Drag and drop GeoJSON file</strong> or click to upload
          </p>
          <p className="upload-subtext">Supports .geojson or .json files</p>

          {fileName && <p className="file-name">Selected: {fileName}</p>}
          {uploadStatus && <p className="upload-status">{uploadStatus}</p>}
        </div>
      </div>
    </div>
  )
}
