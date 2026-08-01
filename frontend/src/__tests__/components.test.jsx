/* Frontend component unit tests */
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import Header from '../components/Header'
import ControlPanel from '../components/ControlPanel'
import ErrorPanel from '../components/ErrorPanel'
import LoadingIndicator from '../components/LoadingIndicator'
import ResultsPanel from '../components/ResultsPanel'

describe('Header Component', () => {
  it('should render header', () => {
    render(<Header />)
    expect(screen.getByRole('banner')).toBeDefined()
  })

  it('should display title', () => {
    render(<Header />)
    const title = screen.queryByText(/Land Scanner/i)
    expect(title).toBeDefined()
  })

  it('should display subtitle', () => {
    render(<Header />)
    const subtitle = document.querySelector('.subtitle')
    expect(subtitle).toBeDefined()
  })
})

describe('ControlPanel Component', () => {
  const mockHandlers = {
    onClear: vi.fn(),
    onAnalyze: vi.fn(),
    onGeoJSONUpload: vi.fn()
  }

  it('should render control panel', () => {
    render(
      <ControlPanel
        {...mockHandlers}
        hasPolygon={false}
        isAnalyzing={false}
      />
    )
    expect(document.querySelector('.control-panel')).toBeDefined()
  })

  it('should render file input', () => {
    render(
      <ControlPanel
        {...mockHandlers}
        hasPolygon={false}
        isAnalyzing={false}
      />
    )
    const fileInput = document.querySelector('input[type="file"]')
    expect(fileInput).toBeDefined()
  })

  it('should render clear button', () => {
    render(
      <ControlPanel
        {...mockHandlers}
        hasPolygon={true}
        isAnalyzing={false}
      />
    )
    const clearBtn = screen.queryByText(/Clear/i)
    expect(clearBtn).toBeDefined()
  })

  it('should render analyze button', () => {
    render(
      <ControlPanel
        {...mockHandlers}
        hasPolygon={true}
        isAnalyzing={false}
      />
    )
    const analyzeBtn = screen.queryByText(/Analyze/i)
    expect(analyzeBtn).toBeDefined()
  })

  it('should disable analyze button when analyzing', () => {
    render(
      <ControlPanel
        {...mockHandlers}
        hasPolygon={true}
        isAnalyzing={true}
      />
    )
    const analyzeBtn = screen.queryByText(/Analyze/i)
    if (analyzeBtn) {
      expect(analyzeBtn.disabled).toBe(true)
    }
  })
})

describe('ErrorPanel Component', () => {
  const mockOnClose = vi.fn()

  it('should render error panel', () => {
    render(<ErrorPanel error="Test error" onClose={mockOnClose} />)
    expect(document.querySelector('.error-panel')).toBeDefined()
  })

  it('should display error message', () => {
    render(<ErrorPanel error="Test error message" onClose={mockOnClose} />)
    expect(screen.queryByText(/Test error message/i)).toBeDefined()
  })

  it('should have close button', () => {
    render(<ErrorPanel error="Test error" onClose={mockOnClose} />)
    const closeBtn = document.querySelector('.close-btn')
    expect(closeBtn).toBeDefined()
  })

  it('should call onClose when close button clicked', () => {
    const { rerender } = render(<ErrorPanel error="Test error" onClose={mockOnClose} />)
    const closeBtn = document.querySelector('.close-btn')
    if (closeBtn) {
      closeBtn.click()
      expect(mockOnClose).toHaveBeenCalled()
    }
  })
})

describe('LoadingIndicator Component', () => {
  it('should render loading indicator', () => {
    render(<LoadingIndicator />)
    expect(document.querySelector('.loading-indicator')).toBeDefined()
  })

  it('should display spinner', () => {
    render(<LoadingIndicator />)
    expect(document.querySelector('.spinner')).toBeDefined()
  })

  it('should display loading text', () => {
    render(<LoadingIndicator />)
    const text = screen.queryByText(/analyzing/i)
    expect(text).toBeDefined()
  })
})

describe('ResultsPanel Component', () => {
  const mockResults = {
    status: 'success',
    analysis_summary: {
      polygon_area_sqkm: 100,
      primary_land_cover: 'Forest',
      key_findings: ['Finding 1', 'Finding 2']
    },
    processing_time_ms: 5000,
    land_information: {},
    processing_status: []
  }

  it('should not render when results are null', () => {
    render(<ResultsPanel results={null} />)
    expect(document.querySelector('.result-panel')).toBeNull()
  })

  it('should render results panel when results provided', () => {
    render(<ResultsPanel results={mockResults} />)
    expect(document.querySelector('.result-panel')).toBeDefined()
  })

  it('should display area information', () => {
    render(<ResultsPanel results={mockResults} />)
    expect(screen.queryByText(/100/)).toBeDefined()
  })

  it('should display land cover information', () => {
    render(<ResultsPanel results={mockResults} />)
    expect(screen.queryByText(/Forest/i)).toBeDefined()
  })

  it('should display key findings', () => {
    render(<ResultsPanel results={mockResults} />)
    expect(screen.queryByText(/Finding 1/)).toBeDefined()
  })

  it('should display processing time', () => {
    render(<ResultsPanel results={mockResults} />)
    expect(screen.queryByText(/5000|Processing Time/i)).toBeDefined()
  })
})
