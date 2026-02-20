import { useState, useCallback } from 'react'
import UploadPanel from './components/UploadPanel'
import ProgressPanel from './components/ProgressPanel'
import ResultsPanel from './components/ResultsPanel'

const API_BASE = ''

function App() {
  const [view, setView] = useState('upload') // upload | progress | results
  const [videoUrl, setVideoUrl] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleUpload = useCallback(async (file) => {
    setError(null)
    setVideoUrl(URL.createObjectURL(file))

    const formData = new FormData()
    formData.append('file', file)

    try {
      const resp = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: formData })
      if (!resp.ok) {
        const errData = await resp.json().catch(() => ({}))
        throw new Error(errData.detail || `Upload failed (${resp.status})`)
      }
      const data = await resp.json()
      setJobId(data.job_id)
      setView('progress')
    } catch (err) {
      setError(err.message)
    }
  }, [])

  const handleAnalysisComplete = useCallback((resultData) => {
    setResult(resultData)
    setView('results')
  }, [])

  const handleReset = useCallback(() => {
    setView('upload')
    setVideoUrl(null)
    setJobId(null)
    setResult(null)
    setError(null)
  }, [])

  return (
    <div className="app">
      <header className="header">
        <img src="/golf-icon.svg" alt="" className="header-icon" />
        <h1>Golf Swing <span>AI Analyzer</span></h1>
      </header>

      <main className="main">
        {error && <div className="error-message">{error}</div>}

        {view === 'upload' && (
          <UploadPanel onUpload={handleUpload} videoUrl={videoUrl} />
        )}

        {view === 'progress' && jobId && (
          <ProgressPanel
            jobId={jobId}
            apiBase={API_BASE}
            onComplete={handleAnalysisComplete}
            onError={(msg) => { setError(msg); setView('upload') }}
          />
        )}

        {view === 'results' && result && (
          <ResultsPanel result={result} onReset={handleReset} />
        )}
      </main>
    </div>
  )
}

export default App
