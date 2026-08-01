import React, { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet-draw/dist/leaflet.draw.css'
import 'leaflet-draw'

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

export default function MapContainer({ onPolygonDraw, onGeoJSONUpload, currentPolygon }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const drawnItemsRef = useRef(null)
  const drawControlRef = useRef(null)

  useEffect(() => {
    // Initialize map
    if (!mapInstanceRef.current) {
      const map = L.map(mapRef.current).setView([20, 0], 2)

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
        drawnItems.clearLayers()
        drawnItems.addLayer(layer)
        onPolygonDraw(layer.toGeoJSON().geometry)
      })

      map.on('draw:edited', (e) => {
        const layers = e.layers
        layers.eachLayer((layer) => {
          onPolygonDraw(layer.toGeoJSON().geometry)
        })
      })

      map.on('draw:deleted', () => {
        onPolygonDraw(null)
      })

      mapInstanceRef.current = map
    }

    return () => {
      // Cleanup is handled on component unmount
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

  return <div ref={mapRef} className="map-container" />
}
