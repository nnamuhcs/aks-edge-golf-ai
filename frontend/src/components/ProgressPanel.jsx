import { useEffect, useState, useRef } from 'react'

function ProgressPanel({ jobId, apiBase, onComplete, onError }) {
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('Starting analysis...')
  const intervalRef = useRef(null)

  useEffect(() => {
    let active = true

    const poll = async () => {
      try {
        const resp = await fetch(`${apiBase}/api/status/${jobId}`)
        if (!resp.ok) throw new Error('Failed to get status')
        const data = await resp.json()

        if (!active) return

        setProgress(data.progress || 0)
        setMessage(data.message || 'Processing...')

        if (data.status === 'completed') {
          // Fetch full result
          const resultResp = await fetch(`${apiBase}/api/result/${jobId}`)
          if (resultResp.ok) {
            const resultData = await resultResp.json()
            onComplete(resultData)
          } else {
            onError('Failed to load results')
          }
          return
        }

        if (data.status === 'failed') {
          onError(data.message || 'Analysis failed')
          return
        }
      } catch (err) {
        if (active) {
          // Don't fail immediately, could be temporary
          console.error('Poll error:', err)
        }
      }

      if (active) {
        intervalRef.current = setTimeout(poll, 1500)
      }
    }

    poll()

    return () => {
      active = false
      if (intervalRef.current) clearTimeout(intervalRef.current)
    }
  }, [jobId, apiBase, onComplete, onError])

  return (
    <div className="progress-container">
      <div style={{ fontSize: '2.5rem', marginBottom: 16 }}>🏌️</div>
      <h2 style={{ fontSize: '1.1rem', fontWeight: 500, marginBottom: 4 }}>
        Analyzing Your Swing
      </h2>
      <div className="progress-bar-track">
        <div
          className="progress-bar-fill"
          style={{ width: `${progress}%` }}
        />
      </div>
      <p className="progress-message">{message}</p>
      <p style={{ fontSize: '0.8rem', color: '#9ca3af', marginTop: 8 }}>
        {progress}% complete
      </p>
    </div>
  )
}

export default ProgressPanel
