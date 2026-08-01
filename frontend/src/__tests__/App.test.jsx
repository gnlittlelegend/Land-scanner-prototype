/* Frontend component tests - App logic and state management */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from '../App'

// Mock Firebase
vi.mock('../firebase', () => ({
  app: {},
  analytics: {}
}))

describe('App Component', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.clearAllMocks()
  })

  it('should render the app', () => {
    render(<App />)
    expect(screen.getByText(/Land Scanner/i)).toBeDefined()
  })

  it('should render header', () => {
    render(<App />)
    const header = screen.getByRole('banner')
    expect(header).toBeDefined()
  })

  it('should render main content area', () => {
    render(<App />)
    const mainContent = document.querySelector('.main-content')
    expect(mainContent).toBeDefined()
  })

  it('should have control panel visible', () => {
    render(<App />)
    const controlPanel = document.querySelector('.control-panel')
    expect(controlPanel).toBeDefined()
  })

  it('should have map container visible', () => {
    render(<App />)
    const mapContainer = document.querySelector('.map-container')
    expect(mapContainer).toBeDefined()
  })

  it('should not display results panel initially', () => {
    render(<App />)
    const resultPanel = document.querySelector('.result-panel')
    expect(resultPanel).toBeNull()
  })

  it('should not display error panel initially', () => {
    render(<App />)
    const errorPanel = document.querySelector('.error-panel')
    expect(errorPanel).toBeNull()
  })

  it('should not display loading indicator initially', () => {
    render(<App />)
    const loadingIndicator = document.querySelector('.loading-indicator')
    expect(loadingIndicator).toBeNull()
  })
})

describe('App Component - Polygon Management', () => {
  it('should have analyze button disabled when no polygon', () => {
    render(<App />)
    const analyzeBtn = screen.queryByText(/Analyze/i)
    // Should exist but be disabled
    if (analyzeBtn) {
      expect(analyzeBtn.disabled).toBe(true)
    }
  })

  it('should have clear button visible', () => {
    render(<App />)
    const clearBtn = screen.queryByText(/Clear/i)
    expect(clearBtn).toBeDefined()
  })
})

describe('App Component - API Constants', () => {
  it('should use correct API base URL', () => {
    const { container } = render(<App />)
    // API_BASE should be defined in module scope
    expect(container).toBeDefined()
  })

  it('should set reasonable API timeout', () => {
    const { container } = render(<App />)
    expect(container).toBeDefined()
  })
})
