import React from 'react'

export default function ResultsPanel({ results }) {
  if (!results) return null

  const safeString = (val) => {
    if (val === null || val === undefined) return ''
    if (typeof val === 'object') return JSON.stringify(val)
    return String(val)
  }

  const ruleIdMap = {
    'ADM-001': 'Administrative',
    'LC-001': 'Land Cover',
    'BLD-001': 'Buildings',
    'RD-001': 'Roads',
    'WT-001': 'Water Bodies',
    'ELV-001': 'Elevation'
  }

  const getStatusLabel = (status) => {
    const map = {
      success: 'Success',
      failed: 'Failed',
      skipped: 'Skipped',
      insufficient_data: 'Insufficient Data',
      partial: 'Partial',
      unknown: 'Unknown'
    }
    return map[status] || safeString(status)
  }

  const renderRuleResult = (ruleId, ruleResult) => {
    const title = ruleIdMap[ruleId] || safeString(ruleId)
    if (!ruleResult || typeof ruleResult !== 'object') return null

    const resultData = ruleResult.result || ruleResult
    if (!resultData || typeof resultData !== 'object') return null

    const entries = Object.entries(resultData).filter(([, v]) => v !== null && v !== undefined)
    if (entries.length === 0) return null

    return (
      <div key={ruleId} className="rule-card">
        <h4>{title}</h4>
        {entries.map(([key, value]) => {
          const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
          if (typeof value === 'number') {
            return (
              <p key={key}>
                <span className="result-label">{label}:</span>{' '}
                <span className="result-value">
                  {Number.isInteger(value) ? value : value.toFixed(1)}
                </span>
              </p>
            )
          }
          if (typeof value === 'boolean') {
            return (
              <p key={key}>
                <span className="result-label">{label}:</span>{' '}
                <span className="result-value">{value ? 'Yes' : 'No'}</span>
              </p>
            )
          }
          return (
            <p key={key}>
              <span className="result-label">{label}:</span>{' '}
              <span className="result-value">{safeString(value)}</span>
            </p>
          )
        })}
      </div>
    )
  }

  const processingStatusEntries = React.useMemo(() => {
    if (!results.processing_status) return []
    if (Array.isArray(results.processing_status)) {
      return results.processing_status.map((item) => {
        const rawStatus = item.status || item.status?.status || 'unknown'
        const rawError = item.error_message || item.status?.error_message || ''
        return {
          module: safeString(item.module_name || 'Unknown'),
          status: typeof rawStatus === 'object' ? 'unknown' : safeString(rawStatus),
          errorMessage: typeof rawError === 'object' ? '' : safeString(rawError)
        }
      })
    }
    if (typeof results.processing_status === 'object') {
      return Object.entries(results.processing_status).map(([module, status]) => {
        const rawStatus = typeof status === 'object' ? status.status : status
        const rawError = typeof status === 'object' ? status.error_message : ''
        return {
          module: safeString(module),
          status: typeof rawStatus === 'object' ? 'unknown' : safeString(rawStatus),
          errorMessage: typeof rawError === 'object' ? '' : safeString(rawError)
        }
      })
    }
    return []
  }, [results.processing_status])

  const providerStatusList = React.useMemo(() => {
    if (!results.provider_status) return []
    if (Array.isArray(results.provider_status)) {
      return results.provider_status.map((p) => {
        const rawStatus = p.status
        const rawError = p.error_message
        return {
          provider_name: safeString(p.provider_name),
          status: typeof rawStatus === 'object' ? 'unknown' : safeString(rawStatus),
          error_message: typeof rawError === 'object' ? '' : safeString(rawError)
        }
      })
    }
    if (typeof results.provider_status === 'object') {
      return Object.entries(results.provider_status).map(([provider, status]) => {
        const rawStatus = typeof status === 'object' ? status.status : status
        const rawError = typeof status === 'object' ? status.error_message : ''
        return {
          provider_name: safeString(provider),
          status: typeof rawStatus === 'object' ? 'unknown' : safeString(rawStatus),
          error_message: typeof rawError === 'object' ? '' : safeString(rawError)
        }
      })
    }
    return []
  }, [results.provider_status])

  const area = results.analysis_summary?.polygon_area_sqkm
  const hasArea = area != null && Number(area) > 0
  const displayArea = hasArea ? Number(area).toFixed(2) : '0.00'

  return (
    <div className="result-panel fade-in">
      <h2>Analysis Results</h2>

      {results.status && (
        <div className={`status-badge status-${results.status}`}>
          {getStatusLabel(results.status)}
        </div>
      )}

      {results.processing_time_ms && (
        <p className="processing-time">
          <strong>Processing Time:</strong> {(results.processing_time_ms / 1000).toFixed(2)}s
        </p>
      )}

      {(hasArea || results.analysis_summary) && (
        <div className="summary-card">
          <div className="label">Analysis Summary</div>
          <div className="value">
            Area: {displayArea} km²
          </div>
        </div>
      )}

      {results.land_information && Object.keys(results.land_information).length > 0 && (
        <>
          <h3>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
              <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
              <line x1="12" y1="22.08" x2="12" y2="12" />
            </svg>
            Land Information
          </h3>
          <div className="rules-grid">
            {Object.entries(results.land_information).map(([ruleId, ruleResult]) => renderRuleResult(ruleId, ruleResult))}
          </div>
        </>
      )}

      {processingStatusEntries.length > 0 && (
        <>
          <h3>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
            </svg>
            Processing Status
          </h3>
          <div className="processing-grid">
            {processingStatusEntries.map((item, idx) => (
              <div key={idx} className="processing-item">
                <span className="module-name">{item.module}</span>
                <span className="module-status">
                  <span className={`status-dot ${item.status || 'unknown'}`} />
                  <span className={`status-${item.status || 'unknown'}`}>{item.status || 'unknown'}</span>
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {providerStatusList.length > 0 && (
        <>
          <h3>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            Provider Status
          </h3>
          <div className="processing-grid">
            {providerStatusList.map((provider, idx) => (
              <div key={idx} className="provider-item">
                <span className="provider-name">{provider.provider_name}</span>
                <span className={`provider-status status-${provider.status || 'unknown'}`}>
                  {provider.status || 'unknown'}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {results.errors && results.errors.length > 0 && (
        <>
          <h3>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            Errors/Warnings
          </h3>
          <div className="errors-list">
            {results.errors.map((error, idx) => (
              <div key={idx} className="error-list-item">
                <span className="error-module">{safeString(error.module)}:</span>
                <span className="error-message">{safeString(error.message)}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
