import { useState, useEffect } from 'react'

const ARCHITECTURE = {
  title: 'System Architecture',
  layers: [
    {
      name: 'Frontend',
      icon: '🖥️',
      color: '#3b82f6',
      components: [
        { name: 'Upload Panel', desc: 'Drag-and-drop video upload with preview', status: 'done' },
        { name: 'Progress Panel', desc: 'Real-time job status polling with progress bar', status: 'done' },
        { name: 'Results Panel', desc: 'Stage timeline, side-by-side comparison, lightbox', status: 'done' },
        { name: 'Dashboard Panel', desc: 'Architecture, design, and task tracking', status: 'done' },
      ]
    },
    {
      name: 'REST API',
      icon: '🔌',
      color: '#8b5cf6',
      components: [
        { name: 'POST /api/upload', desc: 'Video upload → job creation → background processing', status: 'done' },
        { name: 'GET /api/status/:id', desc: 'Job status polling (queued → processing → completed)', status: 'done' },
        { name: 'GET /api/result/:id', desc: 'Full analysis JSON with image paths', status: 'done' },
        { name: 'GET /assets/...', desc: 'Serve annotated stage screenshots', status: 'done' },
      ]
    },
    {
      name: 'ML Pipeline',
      icon: '🧠',
      color: '#10b981',
      components: [
        { name: 'Video Decoder', desc: 'FFmpeg-based frame extraction (max 150 frames)', status: 'done' },
        { name: 'Pose Estimator', desc: 'MediaPipe PoseLandmarker (33 body landmarks)', status: 'done' },
        { name: 'Stage Segmentation', desc: 'Motion signal + proportional timing → 8 swing stages', status: 'done' },
        { name: 'Orientation Fixer', desc: 'Landmark-based rotation correction (ground-is-down)', status: 'done' },
        { name: 'Scoring Engine', desc: 'Per-metric ideal ranges → weighted stage & overall scores', status: 'done' },
        { name: 'Feedback Generator', desc: 'Template-driven good/bad/why/tips per stage', status: 'done' },
        { name: 'Reference Matcher', desc: 'CLIP embedding similarity (fallback: direct load)', status: 'done' },
        { name: 'Annotator', desc: 'Skeleton overlay, callouts, colored borders, score badges', status: 'done' },
      ]
    },
    {
      name: 'Infrastructure',
      icon: '☸️',
      color: '#f59e0b',
      components: [
        { name: 'Docker (Backend)', desc: 'Python 3.11-slim + ffmpeg + MediaPipe + CLIP', status: 'done' },
        { name: 'Docker (Frontend)', desc: 'Node build → Nginx static serve', status: 'done' },
        { name: 'K8s Manifests', desc: 'Namespace, Deployments, Services, PVCs, ConfigMap', status: 'done' },
        { name: 'Kustomize Overlays', desc: 'Base + demo overlay for one-command deploy', status: 'done' },
      ]
    }
  ]
}

const PIPELINE_STAGES = [
  { step: 1, name: 'Upload', icon: '📤', desc: 'Video received, saved to disk, job ID assigned' },
  { step: 2, name: 'Decode', icon: '🎬', desc: 'FFmpeg extracts up to 150 frames from video' },
  { step: 3, name: 'Pose Detection', icon: '🦴', desc: 'MediaPipe detects 33 body landmarks per frame' },
  { step: 4, name: 'Stage Segmentation', icon: '📊', desc: 'Motion analysis splits swing into 8 stages' },
  { step: 5, name: 'Orientation Fix', icon: '🔄', desc: 'Ensures ground-is-down using landmark positions' },
  { step: 6, name: 'Scoring', icon: '📐', desc: 'Measures angles, distances → scores per metric' },
  { step: 7, name: 'Reference Match', icon: '🔍', desc: 'CLIP embeddings find best matching reference frame' },
  { step: 8, name: 'Annotation', icon: '✏️', desc: 'Draws skeleton, callouts, borders on both images' },
  { step: 9, name: 'Feedback', icon: '💬', desc: 'Generates natural language tips per stage' },
  { step: 10, name: 'Deliver', icon: '✅', desc: 'JSON result + annotated images ready' },
]

const TASKS = [
  { id: 'repo', title: 'Repository structure', category: 'Setup', status: 'done' },
  { id: 'backend-api', title: 'FastAPI REST endpoints', category: 'Backend', status: 'done' },
  { id: 'video-decoder', title: 'Video frame extraction', category: 'Backend', status: 'done' },
  { id: 'pose-estimator', title: 'MediaPipe pose detection', category: 'Backend', status: 'done' },
  { id: 'stage-segment', title: 'Swing stage segmentation', category: 'Backend', status: 'done' },
  { id: 'orientation', title: 'Frame orientation correction', category: 'Backend', status: 'done' },
  { id: 'scoring', title: 'Metric scoring engine', category: 'Backend', status: 'done' },
  { id: 'feedback', title: 'Feedback text generation', category: 'Backend', status: 'done' },
  { id: 'reference', title: 'Reference frame matching', category: 'Backend', status: 'done' },
  { id: 'annotator', title: 'Image annotation engine', category: 'Backend', status: 'done' },
  { id: 'upload-ui', title: 'Upload panel with drag/drop', category: 'Frontend', status: 'done' },
  { id: 'progress-ui', title: 'Progress polling panel', category: 'Frontend', status: 'done' },
  { id: 'results-ui', title: 'Results with comparison view', category: 'Frontend', status: 'done' },
  { id: 'dashboard-ui', title: 'Project dashboard', category: 'Frontend', status: 'done' },
  { id: 'lightbox', title: 'Image lightbox/enlarge', category: 'Frontend', status: 'done' },
  { id: 'demo-content', title: 'Synthetic demo videos', category: 'Content', status: 'done' },
  { id: 'ref-frames', title: 'Reference stage frames', category: 'Content', status: 'done' },
  { id: 'docker-be', title: 'Backend Dockerfile', category: 'Infra', status: 'done' },
  { id: 'docker-fe', title: 'Frontend Dockerfile', category: 'Infra', status: 'done' },
  { id: 'k8s-manifests', title: 'K8s deployment manifests', category: 'Infra', status: 'done' },
  { id: 'compose', title: 'Docker Compose for local', category: 'Infra', status: 'done' },
  { id: 'tests-seg', title: 'Segmentation unit tests', category: 'Testing', status: 'done' },
  { id: 'tests-orient', title: 'Orientation unit tests', category: 'Testing', status: 'done' },
  { id: 'tests-score', title: 'Scoring unit tests', category: 'Testing', status: 'done' },
  { id: 'tests-api', title: 'API integration tests', category: 'Testing', status: 'done' },
  { id: 'verify-script', title: 'verify_and_fix.sh', category: 'Testing', status: 'done' },
  { id: 'e2e-test', title: 'End-to-end pipeline test', category: 'Testing', status: 'done' },
  { id: 'stage-distinct', title: 'Stage image distinctness', category: 'Testing', status: 'done' },
  { id: 'docs-readme', title: 'README quickstart', category: 'Docs', status: 'done' },
  { id: 'docs-arch', title: 'Architecture docs', category: 'Docs', status: 'done' },
  { id: 'docs-license', title: 'License documentation', category: 'Docs', status: 'done' },
]

const DESIGN_DECISIONS = [
  { topic: 'Pose Estimation', choice: 'MediaPipe PoseLandmarker', why: 'Fast CPU inference, 33 landmarks, production-quality accuracy. Works offline after model download.' },
  { topic: 'Reference Matching', choice: 'OpenAI CLIP (ViT-B/32)', why: 'HuggingFace vision model for semantic similarity between user frames and reference library.' },
  { topic: 'Stage Detection', choice: 'Motion signal + proportional timing', why: 'Deterministic, explainable. Uses frame differencing when pose data unavailable.' },
  { topic: 'Backend Framework', choice: 'FastAPI + threading', why: 'Async API with sync ML pipeline in background threads. Simple, no Redis/Celery needed for demo.' },
  { topic: 'Frontend', choice: 'Vite + React', why: 'Fast dev experience, tiny bundle (~149KB). No heavy framework needed for SPA.' },
  { topic: 'Scoring Model', choice: 'Ideal-range linear decay', why: 'Each metric has ideal/min/max. Score = 100 at ideal, linear decay to 0 at bounds. Interpretable.' },
  { topic: 'Container Strategy', choice: 'Build-time model download', why: 'Models cached in Docker image layer. No runtime internet needed. Optional PVC for K8s.' },
]

function DashboardPanel() {
  const [activeTab, setActiveTab] = useState('overview')
  const [healthStatus, setHealthStatus] = useState(null)

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(d => setHealthStatus(d))
      .catch(() => setHealthStatus({ status: 'unreachable' }))
  }, [])

  const tasksByCategory = TASKS.reduce((acc, t) => {
    if (!acc[t.category]) acc[t.category] = []
    acc[t.category].push(t)
    return acc
  }, {})

  const doneCount = TASKS.filter(t => t.status === 'done').length
  const totalCount = TASKS.length
  const progressPct = Math.round((doneCount / totalCount) * 100)

  return (
    <div className="dashboard">
      {/* Navigation Tabs */}
      <div className="dash-tabs">
        {[
          ['overview', '📋 Overview'],
          ['architecture', '🏗️ Architecture'],
          ['pipeline', '⚙️ Pipeline'],
          ['tasks', '✅ Tasks'],
          ['design', '🎯 Design'],
        ].map(([key, label]) => (
          <button
            key={key}
            className={`dash-tab ${activeTab === key ? 'active' : ''}`}
            onClick={() => setActiveTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="dash-content">
          <div className="dash-hero">
            <h2>Golf Swing AI Analyzer</h2>
            <p>Production-grade demo: upload a golf swing video → AI-powered analysis with stage-by-stage feedback and annotated side-by-side comparisons.</p>
          </div>

          <div className="dash-stats">
            <div className="stat-card">
              <div className="stat-value">{totalCount}</div>
              <div className="stat-label">Total Tasks</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: 'var(--color-success)' }}>{doneCount}</div>
              <div className="stat-label">Completed</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{progressPct}%</div>
              <div className="stat-label">Progress</div>
            </div>
            <div className="stat-card">
              <div className="stat-value" style={{ color: healthStatus?.status === 'ok' ? 'var(--color-success)' : 'var(--color-error)' }}>
                {healthStatus?.status === 'ok' ? '●' : '○'}
              </div>
              <div className="stat-label">API Status</div>
            </div>
          </div>

          <div className="dash-progress-bar">
            <div className="dash-progress-fill" style={{ width: `${progressPct}%` }}></div>
          </div>

          <div className="dash-grid-2">
            <div className="dash-card">
              <h3>🛠️ Tech Stack</h3>
              <ul className="dash-list">
                <li><strong>Backend:</strong> Python 3.11 · FastAPI · MediaPipe · CLIP · OpenCV</li>
                <li><strong>Frontend:</strong> React 18 · Vite · CSS3</li>
                <li><strong>ML Models:</strong> MediaPipe PoseLandmarker · OpenAI CLIP ViT-B/32</li>
                <li><strong>Infra:</strong> Docker · Kubernetes · Kustomize · Nginx</li>
              </ul>
            </div>
            <div className="dash-card">
              <h3>📊 Swing Stages</h3>
              <ul className="dash-list">
                {['Address', 'Takeaway', 'Backswing', 'Top', 'Downswing', 'Impact', 'Follow-through', 'Finish'].map(s => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Architecture Tab */}
      {activeTab === 'architecture' && (
        <div className="dash-content">
          <h2>System Architecture</h2>
          <div className="arch-flow">
            <div className="arch-flow-item">📱 Browser</div>
            <div className="arch-flow-arrow">→</div>
            <div className="arch-flow-item">🔌 REST API</div>
            <div className="arch-flow-arrow">→</div>
            <div className="arch-flow-item">🧠 ML Pipeline</div>
            <div className="arch-flow-arrow">→</div>
            <div className="arch-flow-item">📁 Assets</div>
          </div>

          {ARCHITECTURE.layers.map(layer => (
            <div key={layer.name} className="arch-layer" style={{ borderLeftColor: layer.color }}>
              <h3>{layer.icon} {layer.name}</h3>
              <div className="arch-components">
                {layer.components.map(c => (
                  <div key={c.name} className="arch-component">
                    <div className="arch-comp-header">
                      <span className="arch-comp-name">{c.name}</span>
                      <span className={`arch-status status-${c.status}`}>
                        {c.status === 'done' ? '✓' : '○'}
                      </span>
                    </div>
                    <p>{c.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pipeline Tab */}
      {activeTab === 'pipeline' && (
        <div className="dash-content">
          <h2>Analysis Pipeline</h2>
          <p style={{ opacity: 0.7, marginBottom: 24 }}>Each uploaded video flows through these 10 processing steps:</p>
          <div className="pipeline-steps">
            {PIPELINE_STAGES.map((s, i) => (
              <div key={s.step} className="pipeline-step">
                <div className="pipeline-step-num">{s.step}</div>
                <div className="pipeline-step-body">
                  <div className="pipeline-step-header">
                    <span className="pipeline-icon">{s.icon}</span>
                    <strong>{s.name}</strong>
                  </div>
                  <p>{s.desc}</p>
                </div>
                {i < PIPELINE_STAGES.length - 1 && <div className="pipeline-connector">│</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks Tab */}
      {activeTab === 'tasks' && (
        <div className="dash-content">
          <h2>Task Tracking</h2>
          <div className="dash-progress-bar" style={{ marginBottom: 24 }}>
            <div className="dash-progress-fill" style={{ width: `${progressPct}%` }}></div>
            <span className="dash-progress-label">{doneCount}/{totalCount} completed</span>
          </div>

          {Object.entries(tasksByCategory).map(([category, tasks]) => (
            <div key={category} className="task-category">
              <h3>{category} <span className="task-count">{tasks.filter(t => t.status === 'done').length}/{tasks.length}</span></h3>
              <div className="task-list">
                {tasks.map(t => (
                  <div key={t.id} className={`task-item status-${t.status}`}>
                    <span className="task-check">
                      {t.status === 'done' ? '✅' : t.status === 'in_progress' ? '🔄' : '⬜'}
                    </span>
                    <span className="task-title">{t.title}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Design Decisions Tab */}
      {activeTab === 'design' && (
        <div className="dash-content">
          <h2>Design Decisions</h2>
          <div className="design-cards">
            {DESIGN_DECISIONS.map(d => (
              <div key={d.topic} className="design-card">
                <h3>{d.topic}</h3>
                <div className="design-choice">{d.choice}</div>
                <p>{d.why}</p>
              </div>
            ))}
          </div>

          <div className="dash-card" style={{ marginTop: 24 }}>
            <h3>📂 Repository Structure</h3>
            <pre className="repo-tree">{`aks-edge-golf-ai/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI endpoints
│   │   ├── pipeline.py        # Orchestrator
│   │   ├── pose_estimator.py  # MediaPipe Tasks API
│   │   ├── stage_segmentation.py
│   │   ├── scoring.py         # Metric scoring
│   │   ├── annotator.py       # Image annotations
│   │   ├── reference_matcher.py  # CLIP matching
│   │   ├── orientation.py     # Frame rotation
│   │   └── video_decoder.py   # FFmpeg extraction
│   ├── tests/                 # 26 pytest tests
│   ├── reference_data/stages/ # 8 reference frames
│   └── Dockerfile
├── frontend/
│   ├── src/components/
│   │   ├── UploadPanel.jsx
│   │   ├── ProgressPanel.jsx
│   │   ├── ResultsPanel.jsx
│   │   └── DashboardPanel.jsx
│   └── Dockerfile
├── deploy/                    # K8s manifests
├── scripts/                   # verify_and_fix.sh
├── sample_videos/             # Demo videos
└── docs/                      # Architecture, licenses`}</pre>
          </div>
        </div>
      )}
    </div>
  )
}

export default DashboardPanel
