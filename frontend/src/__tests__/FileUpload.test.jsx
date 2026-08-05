import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import FileUpload from '../components/FileUpload'

describe('FileUpload Component', () => {
  let mockOnUpload, mockOnError

  beforeEach(() => {
    mockOnUpload = vi.fn()
    mockOnError = vi.fn()
  })

  it('should render the file upload area', () => {
    render(<FileUpload onUpload={mockOnUpload} onError={mockOnError} isDisabled={false} />)
    const uploadArea = screen.getByText(/Drag and drop GeoJSON file/i)
    expect(uploadArea).toBeInTheDocument()
  })

  it('should accept file input via click', async () => {
    render(<FileUpload onUpload={mockOnUpload} onError={mockOnError} isDisabled={false} />)

    const file = new File(
      [JSON.stringify({ type: 'Polygon', coordinates: [[[-10, -10], [10, -10], [10, 10], [-10, 10], [-10, -10]]] })],
      'test.geojson',
      { type: 'application/json' }
    )

    const input = screen.getByRole('button', { hidden: true })
      .parentElement?.querySelector('input[type="file"]')

    if (input) {
      fireEvent.change(input, { target: { files: [file] } })

      await waitFor(() => {
        expect(mockOnUpload).toHaveBeenCalled()
      })
    }
  })

  it('should reject non-GeoJSON files', async () => {
    render(<FileUpload onUpload={mockOnUpload} onError={mockOnError} isDisabled={false} />)

    const file = new File(['test content'], 'test.txt', { type: 'text/plain' })

    const input = screen.getByRole('button', { hidden: true })
      .parentElement?.querySelector('input[type="file"]')

    if (input) {
      fireEvent.change(input, { target: { files: [file] } })

      await waitFor(() => {
        expect(mockOnError).toHaveBeenCalledWith(expect.stringContaining('.geojson or .json'))
      })
    }
  })

  it('should be disabled when isDisabled prop is true', () => {
    render(<FileUpload onUpload={mockOnUpload} onError={mockOnError} isDisabled={true} />)
    const input = document.querySelector('input[type="file"]')
    expect(input).toBeDisabled()
  })

  it('should support drag and drop', async () => {
    render(<FileUpload onUpload={mockOnUpload} onError={mockOnError} isDisabled={false} />)
    const uploadArea = screen.getByText(/Drag and drop GeoJSON file/i).closest('.file-upload-area')

    expect(uploadArea).toHaveClass('file-upload-area')
    expect(uploadArea).not.toHaveClass('dragging')
  })
})
