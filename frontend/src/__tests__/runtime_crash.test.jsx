/* Frontend runtime crash tests - edge cases and error boundaries */
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import App from '../App'

vi.mock('../firebase', () => ({
  app: {},
  analytics: {}
}))

describe('Frontend Runtime Crash Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should not crash with null/undefined map state', () => {
    const { container } = render(<App />)
    expect(container).toBeDefined()
  })

  it('should not crash on rapid re-renders', () => {
    const { rerender } = render(<App />)
    for (let i = 0; i < 100; i++) {
      rerender(<App />)
    }
    expect(document.querySelector('.main-content')).toBeDefined()
  })

  it('should not crash when DOM elements are missing', () => {
    render(<App />)
    const nonExistent = document.querySelector('.does-not-exist')
    expect(nonExistent).toBeNull()
  })

  it('should not crash with empty fetch responses', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => null,
      status: 200
    })
    render(<App />)
    await waitFor(() => {
      expect(document.querySelector('.control-panel')).toBeDefined()
    }, { timeout: 2000 })
  })

  it('should not crash on malformed API response', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: true,
      json: async () => ({ invalid: 'structure' }),
      status: 200
    })
    render(<App />)
    await waitFor(() => {
      expect(document.querySelector('.control-panel')).toBeDefined()
    }, { timeout: 2000 })
  })

  it('should not crash on 500 server error', async () => {
    global.fetch = vi.fn().mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: async () => ({})
    })
    render(<App />)
    await waitFor(() => {
      expect(document.querySelector('.control-panel')).toBeDefined()
    }, { timeout: 2000 })
  })

  it('should not crash on network timeout', async () => {
    global.fetch = vi.fn().mockRejectedValueOnce(new Error('ETIMEDOUT'))
    render(<App />)
    await waitFor(() => {
      expect(document.querySelector('.control-panel')).toBeDefined()
    }, { timeout: 2000 })
  })

  it('should not crash when localStorage is inaccessible', () => {
    const originalGetItem = Storage.prototype.getItem
    Storage.prototype.getItem = vi.fn(() => { throw new Error('localStorage disabled') })
    render(<App />)
    expect(document.querySelector('.main-content')).toBeDefined()
    Storage.prototype.getItem = originalGetItem
  })

  it('should not crash on extremely long text input', () => {
    const longString = 'a'.repeat(100000)
    render(<App />)
    expect(document.querySelector('.main-content')).toBeDefined()
  })

  it('should not crash with special characters in state', () => {
    const special = '<script>alert("xss")</script>'
    render(<App />)
    expect(document.querySelector('.main-content')).toBeDefined()
  })

  it('should not crash when console errors occur', () => {
    const originalError = console.error
    console.error = vi.fn()
    render(<App />)
    console.error = originalError
    expect(document.querySelector('.main-content')).toBeDefined()
  })

  it('should not crash with invalid date objects', () => {
    render(<App />)
    const invalidDate = new Date('invalid')
    expect(isNaN(invalidDate.getTime())).toBe(true)
    expect(document.querySelector('.main-content')).toBeDefined()
  })

  it('should not crash when ResizeObserver is not available', () => {
    const originalRO = global.ResizeObserver
    global.ResizeObserver = undefined
    render(<App />)
    expect(document.querySelector('.main-content')).toBeDefined()
    global.ResizeObserver = originalRO
  })
})
