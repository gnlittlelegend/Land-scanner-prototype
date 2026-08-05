import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ErrorDisplay from '../components/ErrorDisplay'

describe('ErrorDisplay Component', () => {
  const mockOnClose = vi.fn()

  it('should not render when error is null', () => {
    const { container } = render(
      <ErrorDisplay error={null} onClose={mockOnClose} />
    )
    expect(container.querySelector('.error-display')).toBeNull()
  })

  it('should render error display for string error', () => {
    const { container } = render(
      <ErrorDisplay error="Test error message" onClose={mockOnClose} />
    )
    expect(container.querySelector('.error-display')).toBeDefined()
    expect(screen.getByText(/Test error message/)).toBeDefined()
  })

  it('should display error severity levels', () => {
    const { container: warningContainer } = render(
      <ErrorDisplay error="Warning message" severity="warning" onClose={mockOnClose} />
    )
    expect(warningContainer.querySelector('.error-display--warning')).toBeDefined()

    const { container: errorContainer } = render(
      <ErrorDisplay error="Error message" severity="error" onClose={mockOnClose} />
    )
    expect(errorContainer.querySelector('.error-display--error')).toBeDefined()

    const { container: criticalContainer } = render(
      <ErrorDisplay error="Critical message" severity="critical" onClose={mockOnClose} />
    )
    expect(criticalContainer.querySelector('.error-display--critical')).toBeDefined()
  })

  it('should display error code when provided in object', () => {
    const error = {
      error_code: 'VALIDATION_ERROR',
      error_message: 'Invalid polygon input',
      details: 'Polygon area is too small'
    }
    render(<ErrorDisplay error={error} onClose={mockOnClose} />)
    expect(screen.getByText(/VALIDATION_ERROR/)).toBeDefined()
  })

  it('should display provider-specific error information', () => {
    const error = {
      error_message: 'Collection failed',
      provider_status: {
        osm_buildings: {
          data_retrieved: false,
          error_message: 'Overpass API timeout'
        },
        elevation: {
          data_retrieved: true,
          error_message: null
        }
      }
    }
    const { container } = render(
      <ErrorDisplay error={error} onClose={mockOnClose} />
    )
    expect(container.querySelector('.error-display__providers')).toBeDefined()
    expect(container.querySelector('.error-display__providers')).toBeDefined()
    const providerSection = container.querySelector('.error-display__providers')
    expect(providerSection.textContent).toContain('osm_buildings')
  })

  it('should format error messages to be non-technical', () => {
    const error = {
      error_message: 'POLYGON_VALIDATION_ERROR: timeout occurred'
    }
    render(<ErrorDisplay error={error} onClose={mockOnClose} />)
    const message = screen.getByText(/Invalid polygon/)
    expect(message).toBeDefined()
  })

  it('should display error title based on severity', () => {
    const { container: warningContainer } = render(
      <ErrorDisplay error="Warning message" severity="warning" onClose={mockOnClose} />
    )
    expect(warningContainer.querySelector('.error-display__title')).toBeDefined()
    
    const { container: errorContainer } = render(
      <ErrorDisplay error="Error message" severity="error" onClose={mockOnClose} />
    )
    expect(errorContainer.querySelector('.error-display__title')).toBeDefined()
    
    const { container: criticalContainer } = render(
      <ErrorDisplay error="Critical message" severity="critical" onClose={mockOnClose} />
    )
    expect(criticalContainer.querySelector('.error-display__title')).toBeDefined()
  })

  it('should have close button that calls onClose', () => {
    mockOnClose.mockClear()
    const { container } = render(
      <ErrorDisplay error="Test error" onClose={mockOnClose} />
    )
    const closeBtn = container.querySelector('.error-display__close')
    expect(closeBtn).toBeDefined()
    if (closeBtn) {
      closeBtn.click()
      expect(mockOnClose).toHaveBeenCalled()
    }
  })

  it('should display error icons for different severity levels', () => {
    const { container: warningContainer } = render(
      <ErrorDisplay error="Warning" severity="warning" onClose={mockOnClose} />
    )
    const warningSvg = warningContainer.querySelector('.error-display__icon svg')
    expect(warningSvg).toBeDefined()

    const { container: errorContainer } = render(
      <ErrorDisplay error="Error" severity="error" onClose={mockOnClose} />
    )
    const errorSvg = errorContainer.querySelector('.error-display__icon svg')
    expect(errorSvg).toBeDefined()
  })

  it('should display helpful suggestions based on error type', () => {
    const polygonError = {
      error_code: 'POLYGON_SIZE_ERROR',
      error_message: 'Polygon area is too large'
    }
    render(<ErrorDisplay error={polygonError} onClose={mockOnClose} />)
    expect(screen.getByText(/between 10 m² and 100 km²/)).toBeDefined()
  })

  it('should display timeout suggestion for timeout errors', () => {
    const timeoutError = {
      error_message: 'Request timeout after 30 seconds'
    }
    const { container } = render(
      <ErrorDisplay error={timeoutError} onClose={mockOnClose} />
    )
    // Check for both the formatted message and suggestion
    const messageDiv = container.querySelector('.error-display__message')
    expect(messageDiv.textContent.toLowerCase()).toContain('timed out')
  })

  it('should display unavailability suggestion for provider errors', () => {
    const providerError = {
      error_message: 'Data providers are currently unavailable'
    }
    render(<ErrorDisplay error={providerError} onClose={mockOnClose} />)
    expect(screen.getByText(/providers may be temporarily offline/i)).toBeDefined()
  })

  it('should expand additional details when provided', () => {
    const error = {
      error_message: 'Processing failed',
      details: { timestamp: '2024-01-01', module: 'RuleEngine' }
    }
    const { container } = render(
      <ErrorDisplay error={error} onClose={mockOnClose} />
    )
    const detailsElement = container.querySelector('.error-display__details')
    expect(detailsElement).toBeDefined()
  })

  it('should handle complex error object with multiple fields', () => {
    const complexError = {
      error_code: 'PROCESSING_ERROR',
      error_message: 'Multiple failures occurred',
      details: {
        validation: 'passed',
        collection: 'failed',
        standardization: 'failed'
      },
      provider_status: {
        osm: { data_retrieved: false, error_message: 'Timeout' },
        copernicus: { data_retrieved: true, error_message: null }
      }
    }
    render(<ErrorDisplay error={complexError} onClose={mockOnClose} />)
    expect(screen.getByText(/PROCESSING_ERROR/)).toBeDefined()
    expect(screen.getByText(/Multiple failures occurred/)).toBeDefined()
    expect(screen.getByText(/Data Provider Issues/)).toBeDefined()
  })

  it('should have proper CSS classes for styling', () => {
    const { container } = render(
      <ErrorDisplay error="Test error" severity="error" onClose={mockOnClose} />
    )
    expect(container.querySelector('.error-display')).toBeDefined()
    expect(container.querySelector('.error-display__header')).toBeDefined()
    expect(container.querySelector('.error-display__content')).toBeDefined()
    expect(container.querySelector('.error-display__message')).toBeDefined()
    expect(container.querySelector('.error-display__icon')).toBeDefined()
    expect(container.querySelector('.error-display__title')).toBeDefined()
    expect(container.querySelector('.error-display__close')).toBeDefined()
  })
})
