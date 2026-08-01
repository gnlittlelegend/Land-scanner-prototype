export default function ErrorPanel({ error, onClose }) {
  if (!error) return null

  return (
    <div className="error-panel">
      <div className="error-header">
        <h3>Error</h3>
        <button className="close-btn" onClick={onClose}>
          ×
        </button>
      </div>
      <div className="error-content">{error}</div>
    </div>
  )
}
