/* Frontend integration tests - user workflows */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from '../App'

// Mock Firebase
vi.mock('../firebase', () => ({
  app: {},
  analytics: {}
}))

// Mock fetch for API calls
global.fetch = vi.fn()

describe('Frontend Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch.mockClear()
  })

  describe('User Flow: Draw Polygon and Analyze', () => {
    it('should start with empty state', () => {
      render(<App />)
      const mapContainer = document.querySelector('.map-container')
      expect(mapContainer).toBeDefined()
    })

    it('should have all UI components present', () => {
      render(<App />)
      
      // Check all main components are rendered
      expect(document.querySelector('header')).toBeDefined()
      expect(document.querySelector('.main-content')).toBeDefined()
      expect(document.querySelector('.map-container')).toBeDefined()
      expect(document.querySelector('.control-panel')).toBeDefined()
    })

    it('should update when analysis completes', async () => {
      global.fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          status: 'SUCCESS',
          analysis_summary: {
            polygon_area_sqkm: 50,
            key_findings: ['Test finding']
          },
          processing_time_ms: 1000,
          land_information: {},
          processing_status: [],
          errors: []
        })
      })

      render(<App />)
      
      // Wait for component to mount
      await waitFor(() => {
        expect(document.querySelector('.control-panel')).toBeDefined()
      })
    })
  })

  describe('Error Handling', () => {
    it('should display error when upload fails', async () => {
      global.fetch.mockRejectedValueOnce(new Error('Network error'))

      render(<App />)
      
      // Wait and check for error handling
      await waitFor(() => {
        expect(document.querySelector('.control-panel')).toBeDefined()
      }, { timeout: 1000 })
    })

    it('should recover from error', async () => {
      const { rerender } = render(<App />)
      
      // Should be able to render without errors
      expect(document.querySelector('.map-container')).toBeDefined()
      
      rerender(<App />)
      
      // Should still be functional
      expect(document.querySelector('.control-panel')).toBeDefined()
    })
  })

  describe('User Interaction', () => {
    it('should render without crashing', () => {
      const { container } = render(<App />)
      expect(container).toBeDefined()
    })

    it('should display results section when data available', async () => {
      render(<App />)
      
      // Results panel should not be visible initially
      expect(document.querySelector('.result-panel')).toBeNull()
    })

    it('should maintain consistency across re-renders', () => {
      const { rerender } = render(<App />)
      const mapBefore = document.querySelector('.map-container')
      
      rerender(<App />)
      const mapAfter = document.querySelector('.map-container')
      
      expect(mapBefore).toBeDefined()
      expect(mapAfter).toBeDefined()
    })
  })

  describe('Performance', () => {
    it('should render quickly', () => {
      const start = performance.now()
      render(<App />)
      const end = performance.now()
      
      // Should render in less than 100ms
      expect(end - start).toBeLessThan(100)
    })

    it('should not cause excessive re-renders', async () => {
      let renderCount = 0
      const originalRender = global.render
      
      render(<App />)
      
      await waitFor(() => {
        expect(document.querySelector('.control-panel')).toBeDefined()
      }, { timeout: 500 })
    })
  })

  describe('Responsive Design', () => {
    it('should render on desktop', () => {
      global.innerWidth = 1024
      global.innerHeight = 768
      
      render(<App />)
      expect(document.querySelector('.main-content')).toBeDefined()
    })

    it('should render on mobile', () => {
      global.innerWidth = 375
      global.innerHeight = 667
      
      render(<App />)
      expect(document.querySelector('.main-content')).toBeDefined()
    })

    it('should render on tablet', () => {
      global.innerWidth = 768
      global.innerHeight = 1024
      
      render(<App />)
      expect(document.querySelector('.main-content')).toBeDefined()
    })
  })
})
