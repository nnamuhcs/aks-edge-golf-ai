import { useState, useCallback } from 'react'
import UploadPanel from './components/UploadPanel'
import ProgressPanel from './components/ProgressPanel'
import ResultsPanel from './components/ResultsPanel'
import K8sPanel from './components/K8sPanel'
import ArchitecturePanel from './components/ArchitecturePanel'

const API_BASE = ''

function App() {
  const [view, setView] = useState('upload') // upload | progress | results | architecture
  const [videoUrl, setVideoUrl] = useState(null)
  const [jobId, setJobId] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [k8sOpen, setK8sOpen] = useState(false)

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
      // Auto-open K8s panel during analysis so user sees live activity
      setK8sOpen(true)
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
    <div className={`app ${k8sOpen ? 'k8s-open' : ''}`}>
      <header className="header">
        <img src="/golf-icon.svg" alt="" className="header-icon" />
        <div className="header-titles">
          <h1>Golf Swing <span>AI Coacher</span></h1>
          <p className="header-subtitle">Schumann's AKS Edge Demo</p>
        </div>
        <nav className="header-nav">
          <button
            className={`nav-btn ${view !== 'architecture' ? 'active' : ''}`}
            onClick={handleReset}
          >🏌️ Coacher</button>
          <button
            className={`nav-btn ${view === 'architecture' ? 'active' : ''}`}
            onClick={() => setView('architecture')}
          >🏗️ Architecture</button>
        </nav>
      </header>

      <div className="app-body">
        <main className="main">
          {error && <div className="error-message">{error}</div>}

          {view === 'architecture' && (
            <ArchitecturePanel onBack={handleReset} />
          )}

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

        <K8sPanel
          isOpen={k8sOpen}
          onToggle={() => setK8sOpen(!k8sOpen)}
          apiBase={API_BASE}
        />
      </div>
    </div>
  )
}

export default App
