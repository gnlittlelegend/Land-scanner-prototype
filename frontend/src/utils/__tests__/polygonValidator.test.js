import { describe, it, expect } from 'vitest'
import {
  validatePolygon,
  validateArea,
  validateVertexCount,
  countVertices,
  m2ToKm2,
  km2ToM2,
  MIN_AREA_M2,
  MAX_AREA_M2,
  MAX_VERTICES
} from '../polygonValidator'

describe('polygonValidator', () => {
  describe('Unit conversions', () => {
    it('should convert square meters to square kilometers', () => {
      expect(m2ToKm2(1_000_000)).toBe(1)
      expect(m2ToKm2(100_000_000)).toBe(100)
    })

    it('should convert square kilometers to square meters', () => {
      expect(km2ToM2(1)).toBe(1_000_000)
      expect(km2ToM2(100)).toBe(100_000_000)
    })
  })

  describe('Vertex counting', () => {
    it('should count vertices in a simple polygon (triangle)', () => {
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 0]  // closing vertex
        ]]
      }
      expect(countVertices(polygon)).toBe(3)
    })

    it('should count vertices in a square polygon', () => {
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [0, 0],
          [1, 0],
          [1, 1],
          [0, 1],
          [0, 0]  // closing vertex
        ]]
      }
      expect(countVertices(polygon)).toBe(4)
    })

    it('should count vertices in a polygon with holes', () => {
      const polygon = {
        type: 'Polygon',
        coordinates: [
          [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]],  // outer ring (4 vertices)
          [[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]]       // hole (4 vertices)
        ]
      }
      expect(countVertices(polygon)).toBe(8)
    })

    it('should count vertices in a MultiPolygon', () => {
      const polygon = {
        type: 'MultiPolygon',
        coordinates: [
          [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],    // polygon 1 (4 vertices)
          [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]]     // polygon 2 (4 vertices)
        ]
      }
      expect(countVertices(polygon)).toBe(8)
    })

    it('should return 0 for polygon with no coordinates', () => {
      const polygon = {
        type: 'Polygon',
        coordinates: []
      }
      expect(countVertices(polygon)).toBe(0)
    })
  })

  describe('Vertex validation', () => {
    it('should accept polygon with valid vertex count', () => {
      const polygon = {
        type: 'Polygon',
        coordinates: [[[0, 0], [1, 0], [1, 1], [0, 0]]]
      }
      const result = validateVertexCount(polygon)
      expect(result.valid).toBe(true)
      expect(result.error).toBeNull()
      expect(result.vertex_count).toBe(3)
    })

    it('should reject polygon with too many vertices', () => {
      // Create a polygon with MAX_VERTICES + 1 vertices
      const coords = []
      for (let i = 0; i < MAX_VERTICES + 1; i++) {
        const angle = (i / (MAX_VERTICES + 1)) * Math.PI * 2
        coords.push([Math.cos(angle), Math.sin(angle)])
      }
      coords.push(coords[0]) // close the polygon
      
      const polygon = {
        type: 'Polygon',
        coordinates: [coords]
      }
      
      const result = validateVertexCount(polygon)
      expect(result.valid).toBe(false)
      expect(result.error).toContain('too many vertices')
      expect(result.vertex_count).toBeGreaterThan(MAX_VERTICES)
    })
  })

  describe('Area validation', () => {
    it('should accept polygon with valid area (10 m²)', () => {
      // A 10m x 1m rectangle = 10 m²
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [0, 0],
          [0.00009, 0],         // ~10 meters at equator
          [0.00009, 0.00009],
          [0, 0.00009],
          [0, 0]
        ]]
      }
      const result = validateArea(polygon)
      expect(result.valid).toBe(true)
      expect(result.error).toBeNull()
      expect(result.area_m2).toBeGreaterThan(0)
    })

    it('should reject polygon that is too small', () => {
      // A 1m x 1m square = 1 m² (below 10 m² minimum)
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [0, 0],
          [0.00001, 0],
          [0.00001, 0.00001],
          [0, 0.00001],
          [0, 0]
        ]]
      }
      const result = validateArea(polygon)
      expect(result.valid).toBe(false)
      expect(result.error).toContain('too small')
    })

    it('should reject polygon that is too large', () => {
      // A very large polygon (more than 100 km²)
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [0, 0],
          [2, 0],        // ~200+ km at equator
          [2, 2],
          [0, 2],
          [0, 0]
        ]]
      }
      const result = validateArea(polygon)
      expect(result.valid).toBe(false)
      expect(result.error).toContain('too large')
    })

    it('should handle invalid polygon gracefully', () => {
      const polygon = {
        type: 'Polygon',
        coordinates: [[[null, null]]]
      }
      const result = validateArea(polygon)
      expect(result.valid).toBe(false)
      expect(result.error).toContain('Unable to calculate')
    })
  })

  describe('Complete polygon validation', () => {
    it('should reject null polygon', () => {
      const result = validatePolygon(null)
      expect(result.valid).toBe(false)
      expect(result.error).toContain('required')
    })

    it('should reject polygon with wrong type', () => {
      const polygon = {
        type: 'Point',
        coordinates: [0, 0]
      }
      const result = validatePolygon(polygon)
      expect(result.valid).toBe(false)
      expect(result.error).toContain('Invalid polygon type')
    })

    it('should reject polygon with missing coordinates', () => {
      const polygon = {
        type: 'Polygon'
      }
      const result = validatePolygon(polygon)
      expect(result.valid).toBe(false)
      expect(result.error).toContain('missing or empty')
    })

    it('should validate Polygon type', () => {
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [0, 0],
          [0.00009, 0],
          [0.00009, 0.00009],
          [0, 0.00009],
          [0, 0]
        ]]
      }
      const result = validatePolygon(polygon)
      expect(result.valid).toBe(true)
      expect(result.area_km2).toBeGreaterThan(0)
      expect(result.vertex_count).toBeGreaterThan(0)
    })

    it('should validate MultiPolygon type', () => {
      const polygon = {
        type: 'MultiPolygon',
        coordinates: [
          [[[0, 0], [0.00009, 0], [0.00009, 0.00009], [0, 0.00009], [0, 0]]]
        ]
      }
      const result = validatePolygon(polygon)
      expect(result.valid).toBe(true)
    })

    it('should return validation details on success', () => {
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [0, 0],
          [0.00009, 0],
          [0.00009, 0.00009],
          [0, 0.00009],
          [0, 0]
        ]]
      }
      const result = validatePolygon(polygon)
      expect(result.valid).toBe(true)
      expect(result.error).toBeNull()
      expect(result.area_m2).toBeDefined()
      expect(result.area_km2).toBeDefined()
      expect(result.vertex_count).toBeDefined()
    })

    it('should check vertex count before area (faster validation)', () => {
      // Create polygon with too many vertices but invalid area
      const coords = []
      for (let i = 0; i < MAX_VERTICES + 1; i++) {
        const angle = (i / (MAX_VERTICES + 1)) * Math.PI * 2
        coords.push([Math.cos(angle), Math.sin(angle)])
      }
      coords.push(coords[0])
      
      const polygon = {
        type: 'Polygon',
        coordinates: [coords]
      }
      
      const result = validatePolygon(polygon)
      expect(result.valid).toBe(false)
      expect(result.error).toContain('too many vertices')
    })
  })

  describe('Real-world polygon examples', () => {
    it('should validate a small city area (~1 km²)', () => {
      // Approximately 1 km x 1 km at equator
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [-0.0045, -0.0045],
          [0.0045, -0.0045],
          [0.0045, 0.0045],
          [-0.0045, 0.0045],
          [-0.0045, -0.0045]
        ]]
      }
      const result = validatePolygon(polygon)
      expect(result.valid).toBe(true)
      expect(result.area_km2).toBeGreaterThan(0.5)
      expect(result.area_km2).toBeLessThan(2)
    })

    it('should validate a medium area (~10 km²)', () => {
      // Approximately 3.2 km x 3.2 km at equator
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [-0.0144, -0.0144],
          [0.0144, -0.0144],
          [0.0144, 0.0144],
          [-0.0144, 0.0144],
          [-0.0144, -0.0144]
        ]]
      }
      const result = validatePolygon(polygon)
      expect(result.valid).toBe(true)
      expect(result.area_km2).toBeGreaterThan(8)
      expect(result.area_km2).toBeLessThan(12)
    })

    it('should validate a large area (~50 km²)', () => {
      // Approximately 7 km x 7 km at equator
      const polygon = {
        type: 'Polygon',
        coordinates: [[
          [-0.0315, -0.0315],
          [0.0315, -0.0315],
          [0.0315, 0.0315],
          [-0.0315, 0.0315],
          [-0.0315, -0.0315]
        ]]
      }
      const result = validatePolygon(polygon)
      expect(result.valid).toBe(true)
      expect(result.area_km2).toBeGreaterThan(40)
      expect(result.area_km2).toBeLessThan(60)
    })
  })
})
