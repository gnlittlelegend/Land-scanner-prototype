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

  const renderRuleResult = (ruleId, ruleResult) => {
    const title = ruleIdMap[ruleId] || safeString(ruleId)
    if (!ruleResult || typeof ruleResult !== 'object') return null

    const resultData = ruleResult.result || ruleResult
    if (!resultData || typeof resultData !== 'object') return null

    const entries = Object.entries(resultData).filter(([, v]) => v !== null && v !== undefined)
    if (entries.length === 0) return null

    return (
      <div key={ruleId}>
        <h4>{title}</h4>
        {entries.map(([key, value]) => {
          const label = key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
          if (typeof value === 'number') {
            return (
              <p key={key}>
                {label}: {Number.isInteger(value) ? value : value.toFixed(1)}
              </p>
            )
          }
          if (typeof value === 'boolean') {
            return (
              <p key={key}>
                {label}: {value ? 'Yes' : 'No'}
              </p>
            )
          }
          return (
            <p key={key}>
              {label}: {safeString(value)}
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

  return (
    <div className="result-panel">
      <h2>Analysis Results</h2>

      {results.status && (
        <div className={`status-badge status-${results.status}`}>
          {safeString(results.status).toUpperCase()}
        </div>
      )}

      {results.processing_time_ms && (
        <p>
          <strong>Processing Time:</strong> {(results.processing_time_ms / 1000).toFixed(2)}s
        </p>
      )}

      {results.analysis_summary && (
        <>
          <h3>Analysis Summary</h3>
          {results.analysis_summary.polygon_area_sqkm != null && (
            <p>
              <strong>Area:</strong> {Number(results.analysis_summary.polygon_area_sqkm).toFixed(2)} km²
            </p>
          )}
          {results.analysis_summary.primary_land_cover && (
            <p>
              <strong>Primary Land Cover:</strong> {safeString(results.analysis_summary.primary_land_cover)}
            </p>
          )}
          {results.analysis_summary.key_findings && results.analysis_summary.key_findings.length > 0 && (
            <div>
              <strong>Key Findings:</strong>
              <ul>
                {results.analysis_summary.key_findings.map((finding, idx) => (
                  <li key={idx}>{safeString(finding)}</li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {results.land_information && Object.keys(results.land_information).length > 0 && (
        <>
          <h3>Land Information</h3>
          {Object.entries(results.land_information).map(([ruleId, ruleResult]) => renderRuleResult(ruleId, ruleResult))}
        </>
      )}

      {processingStatusEntries.length > 0 && (
        <>
          <h3>Processing Status</h3>
          <ul>
            {processingStatusEntries.map((item, idx) => (
              <li key={idx}>
                {item.module}: <span className={`status-${item.status || 'unknown'}`}>{item.status || 'unknown'}</span>
                {item.errorMessage && ` - ${item.errorMessage}`}
              </li>
            ))}
          </ul>
        </>
      )}

      {providerStatusList.length > 0 && (
        <>
          <h3>Provider Status</h3>
          <ul>
            {providerStatusList.map((provider, idx) => (
              <li key={idx}>
                {provider.provider_name}: <span className={`status-${provider.status || 'unknown'}`}>{provider.status || 'unknown'}</span>
                {provider.error_message && ` - ${provider.error_message}`}
              </li>
            ))}
          </ul>
        </>
      )}

      {results.errors && results.errors.length > 0 && (
        <>
          <h3>Errors/Warnings</h3>
          <ul>
            {results.errors.map((error, idx) => (
              <li key={idx}>
                <strong>{safeString(error.module)}:</strong> {safeString(error.message)}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
