import { useState, useEffect, useRef } from 'react'

function K8sPanel({ isOpen, onToggle, apiBase }) {
  const [components, setComponents] = useState([])
  const [activity, setActivity] = useState([])
  const [namespace, setNamespace] = useState('default')
  const [inK8s, setInK8s] = useState(false)
  const activityEndRef = useRef(null)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!isOpen) return

    const poll = async () => {
      try {
        const resp = await fetch(`${apiBase}/api/k8s/status`)
        if (resp.ok) {
          const data = await resp.json()
          setComponents(data.components || [])
          setActivity(data.activity || [])
          setNamespace(data.namespace || 'default')
          setInK8s(data.in_k8s || false)
        }
      } catch (e) {
        // silent
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 2000)
    return () => clearInterval(intervalRef.current)
  }, [isOpen, apiBase])

  useEffect(() => {
    if (activityEndRef.current) {
      activityEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [activity])

  const kindIcon = (kind) => {
    switch (kind) {
      case 'Pod': return '🟢'
      case 'Process': return '⚙️'
      case 'Service': return '🔗'
      case 'Model': return '🧠'
      case 'PVC': return '💾'
      case 'Ingress': return '🌐'
      default: return '📦'
    }
  }

  const eventIcon = (type) => {
    switch (type) {
      case 'upload': return '📤'
      case 'pipeline': return '⚙️'
      case 'model': return '🧠'
      case 'analysis': return '📊'
      case 'complete': return '✅'
      case 'api': return '🔗'
      default: return '•'
    }
  }

  const formatTime = (elapsed) => {
    const m = Math.floor(elapsed / 60)
    const s = Math.floor(elapsed % 60)
    return m > 0 ? `${m}m${s}s` : `${s}s`
  }

  return (
    <>
      {/* Toggle button (always visible) */}
      <button
        className={`k8s-toggle ${isOpen ? 'open' : ''}`}
        onClick={onToggle}
        title={isOpen ? 'Hide K8s Panel' : 'Show K8s Panel'}
      >
        <span className="k8s-toggle-icon">☸</span>
        {!isOpen && <span className="k8s-toggle-label">K8s</span>}
        <span className="k8s-toggle-arrow">{isOpen ? '▶' : '◀'}</span>
      </button>

      {/* Panel */}
      <div className={`k8s-panel ${isOpen ? 'open' : ''}`}>
        <div className="k8s-panel-header">
          <div className="k8s-panel-title">
            <span style={{ fontSize: '1.1rem' }}>☸</span>
            <span>Kubernetes</span>
          </div>
          <div className="k8s-panel-ns">
            <span className={`k8s-env-badge ${inK8s ? 'k8s' : 'local'}`}>
              {inK8s ? 'AKS Edge' : 'Local'}
            </span>
            <span className="k8s-ns-label">ns/{namespace}</span>
          </div>
        </div>

        {/* Components */}
        <div className="k8s-section">
          <div className="k8s-section-title">Components</div>
          <div className="k8s-component-list">
            {components.map((c, i) => (
              <div key={i} className="k8s-component">
                <div className="k8s-comp-row">
                  <span className="k8s-comp-icon">{kindIcon(c.kind)}</span>
                  <span className="k8s-comp-name">{c.name}</span>
                  <span className={`k8s-comp-status ${c.ready ? 'ready' : 'not-ready'}`}>
                    {c.status}
                  </span>
                </div>
                <div className="k8s-comp-meta">
                  <span className="k8s-comp-kind">{c.kind}</span>
                  {c.info && <span className="k8s-comp-info">{c.info}</span>}
                  {c.uptime && <span className="k8s-comp-uptime">↑{c.uptime}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Activity Feed */}
        <div className="k8s-section k8s-activity-section">
          <div className="k8s-section-title">
            Live Activity
            {activity.length > 0 && (
              <span className="k8s-activity-count">{activity.length}</span>
            )}
          </div>
          <div className="k8s-activity-feed">
            {activity.length === 0 ? (
              <div className="k8s-activity-empty">
                No activity yet. Upload a video to see live processing events.
              </div>
            ) : (
              activity.map((a, i) => (
                <div key={i} className="k8s-activity-item">
                  <span className="k8s-act-icon">{eventIcon(a.type)}</span>
                  <div className="k8s-act-content">
                    <div className="k8s-act-msg">{a.message}</div>
                    {a.detail && <div className="k8s-act-detail">{a.detail}</div>}
                  </div>
                  <span className="k8s-act-time">{formatTime(a.elapsed)}</span>
                </div>
              ))
            )}
            <div ref={activityEndRef} />
          </div>
        </div>
      </div>
    </>
  )
}

export default K8sPanel
