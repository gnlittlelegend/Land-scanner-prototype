export default function ErrorPanel({ error, onClose }) {
  if (!error) return null

  return (
    <div className="error-panel fade-in">
      <div className="error-header">
        <h3>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          Error
        </h3>
        <button className="close-btn" onClick={onClose} aria-label="Close">
          ×
        </button>
      </div>
      <div className="error-content">{error}</div>
    </div>
  )
}
