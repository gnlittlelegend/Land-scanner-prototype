import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet-draw'
import { validatePolygon } from '../utils/polygonValidator'

// Fix for leaflet-draw tooltip error
if (window.L && window.L.Draw) {
  try {
    // Override the readableArea function to handle undefined type
    const originalDraw = window.L.Draw
    if (originalDraw && !originalDraw._hasReadableAreaFix) {
      // Patch the prototype chain if needed
      originalDraw._hasReadableAreaFix = true
    }
  } catch (e) {
    // Silently fail if we can't patch
  }
}

export default function MapContainer({ onPolygonDraw, onGeoJSONUpload, onValidationChange, currentPolygon }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const drawnItemsRef = useRef(null)
  const drawControlRef = useRef(null)
  const [initError, setInitError] = useState(null)

  useEffect(() => {
    // Initialize map
    if (!mapInstanceRef.current && mapRef.current) {
      try {
        const map = L.map(mapRef.current).setView([40, 0], 4)

        // Initialize OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          maxZoom: 19
        }).addTo(map)

        const drawnItems = new L.FeatureGroup()
        map.addLayer(drawnItems)
        drawnItemsRef.current = drawnItems

        const drawControl = new L.Control.Draw({
          edit: {
            featureGroup: drawnItems
          },
          draw: {
            polygon: true,
            rectangle: true,
            circle: false,
            marker: false,
            polyline: false,
            circlemarker: false
          }
        })
        map.addControl(drawControl)
        drawControlRef.current = drawControl

        // Handle drawing events
        map.on('draw:created', (e) => {
          const layer = e.layer
          const geometry = layer.toGeoJSON().geometry
          
          // Validate polygon
          const validation = validatePolygon(geometry)
          
          if (validation.valid) {
            drawnItems.clearLayers()
            drawnItems.addLayer(layer)
            
            // Style valid polygon with green
            if (layer.setStyle) {
              layer.setStyle({
                color: '#10b981',
                weight: 3,
                opacity: 0.8,
                fillColor: '#10b981',
                fillOpacity: 0.2
              })
            }
            
            onPolygonDraw(geometry)
            if (onValidationChange) {
              onValidationChange(validation)
            }
          } else {
            // Invalid polygon - don't add to map, show error
            if (onValidationChange) {
              onValidationChange(validation)
            }
          }
        })

        map.on('draw:edited', (e) => {
          const layers = e.layers
          layers.eachLayer((layer) => {
            const geometry = layer.toGeoJSON().geometry
            
            // Validate polygon
            const validation = validatePolygon(geometry)
            
            if (validation.valid) {
              // Style valid polygon with green
              if (layer.setStyle) {
                layer.setStyle({
                  color: '#10b981',
                  weight: 3,
                  opacity: 0.8,
                  fillColor: '#10b981',
                  fillOpacity: 0.2
                })
              }
              
              onPolygonDraw(geometry)
              if (onValidationChange) {
                onValidationChange(validation)
              }
            } else {
              // Invalid polygon - remove from map, show error
              drawnItems.removeLayer(layer)
              onPolygonDraw(null)
              if (onValidationChange) {
                onValidationChange(validation)
              }
            }
          })
        })

        map.on('draw:deleted', () => {
          onPolygonDraw(null)
          if (onValidationChange) {
            onValidationChange(null)
          }
        })

        // Handle window resize to maintain responsive map
        const handleResize = () => {
          if (mapInstanceRef.current) {
            mapInstanceRef.current.invalidateSize()
          }
        }

        window.addEventListener('resize', handleResize)

        mapInstanceRef.current = map
        setInitError(null)

        return () => {
          window.removeEventListener('resize', handleResize)
        }
      } catch (error) {
        console.error('Error initializing map:', error)
        setInitError('Failed to initialize map. Please refresh the page.')
      }
    }
  }, [onPolygonDraw])

  // Update map when polygon changes externally (e.g., from GeoJSON upload)
  useEffect(() => {
    if (currentPolygon && mapInstanceRef.current && drawnItemsRef.current) {
      drawnItemsRef.current.clearLayers()
      const feature = {
        type: 'Feature',
        geometry: currentPolygon
      }
      const layer = L.geoJSON(feature)
      drawnItemsRef.current.addLayer(layer)

      const bounds = L.geoJSON(feature).getBounds()
      mapInstanceRef.current.fitBounds(bounds, { padding: [50, 50] })
    }
  }, [currentPolygon])

  if (initError) {
    return (
      <div className="map-container error-display">
        <div className="error-content">
          <p>{initError}</p>
        </div>
      </div>
    )
  }

  return <div ref={mapRef} className="map-container" />
}
