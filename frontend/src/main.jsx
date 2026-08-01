import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'
import './index.css'
import { app, analytics } from './firebase'

const originalError = console.error
console.error = function(...args) {
  if (
    args[0]?.includes?.('type is not defined') ||
    args[0]?.includes?.('readableArea') ||
    (typeof args[0] === 'string' && args[0].includes('Minified React error #31'))
  ) {
    return
  }
  originalError.apply(console, args)
}

window.addEventListener('error', (event) => {
  if (
    event.message?.includes('type is not defined') ||
    event.filename?.includes('leaflet')
  ) {
    event.preventDefault()
  }
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
