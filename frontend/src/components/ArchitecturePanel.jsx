import { useState } from 'react'

const NODES = [
  // Row 0: User
  { id: 'user', label: '📹 Video Upload', desc: 'Drag & drop golf swing video', group: 'frontend', x: 50, y: 8, w: 160, h: 56 },
  // Row 1: API + Frontend
  { id: 'api', label: '⚡ FastAPI Gateway', desc: 'REST API • POST /upload • GET /status • GET /result', group: 'backend', x: 50, y: 22, w: 200, h: 56 },
  // Row 2: Pipeline
  { id: 'decoder', label: '🎬 Video Decoder', desc: 'ffmpeg • Two-pass swing extraction • Motion-based region detection', group: 'pipeline', x: 8, y: 38, w: 180, h: 56 },
  { id: 'pose', label: '🦴 Pose Estimation', desc: 'MediaPipe Heavy • 33 landmarks • 0.2 confidence threshold', group: 'ml', x: 42, y: 38, w: 180, h: 56 },
  { id: 'segment', label: '📐 Stage Segmentation', desc: 'Anchor-based: Impact→Top→Address→Finish • 8 stages', group: 'pipeline', x: 75, y: 38, w: 180, h: 56 },
  // Row 3: Analysis
  { id: 'scoring', label: '🎯 Scoring Engine', desc: 'Gaussian curves • Stage-weighted • Body metrics → 0-100', group: 'pipeline', x: 8, y: 55, w: 175, h: 56 },
  { id: 'reference', label: '🏆 Reference Matcher', desc: 'CLIP ViT-B/32 embeddings • Pro golfer frame similarity', group: 'ml', x: 42, y: 55, w: 190, h: 56 },
  { id: 'annotator', label: '🖊️ Frame Annotator', desc: 'Skeleton overlay • Arrows • Callouts • Side-by-side', group: 'pipeline', x: 75, y: 55, w: 180, h: 56 },
  // Row 4: Output
  { id: 'results', label: '📊 Results & Coaching', desc: 'Per-stage scores • Actionable tips • Comparison images', group: 'frontend', x: 50, y: 72, w: 200, h: 56 },
]

const EDGES = [
  { from: 'user', to: 'api', label: 'Upload' },
  { from: 'api', to: 'decoder', label: 'Video file' },
  { from: 'decoder', to: 'pose', label: 'Frames' },
  { from: 'pose', to: 'segment', label: 'Landmarks' },
  { from: 'segment', to: 'scoring', label: 'Stage indices' },
  { from: 'pose', to: 'reference', label: 'Frame features' },
  { from: 'reference', to: 'annotator', label: 'Best match' },
  { from: 'scoring', to: 'annotator', label: 'Metrics' },
  { from: 'annotator', to: 'results', label: 'Annotated' },
  { from: 'scoring', to: 'results', label: 'Scores + tips' },
]

const K8S_COMPONENTS = [
  { icon: '☸', name: 'AKS Edge Essentials', kind: 'Cluster', desc: 'Lightweight K8s on edge hardware' },
  { icon: '📦', name: 'golf-ai-backend', kind: 'Deployment', desc: 'FastAPI + ML pipeline container' },
  { icon: '🔗', name: 'golf-ai-api', kind: 'Service', desc: 'ClusterIP → port 8000' },
  { icon: '🌐', name: 'golf-ai-ingress', kind: 'Ingress', desc: 'External access routing' },
  { icon: '💾', name: 'model-cache-pvc', kind: 'PersistentVolumeClaim', desc: 'MediaPipe + CLIP model weights' },
  { icon: '⚙️', name: 'golf-ai-config', kind: 'ConfigMap', desc: 'Runtime settings & thresholds' },
  { icon: '📁', name: 'results-pvc', kind: 'PersistentVolumeClaim', desc: 'Generated analysis assets' },
]

const TECH_STACK = [
  { category: 'Frontend', items: ['React 18', 'Vite', 'CSS3 Custom Properties'] },
  { category: 'Backend', items: ['Python 3.11', 'FastAPI', 'uvicorn', 'OpenCV', 'ffmpeg'] },
  { category: 'ML Models', items: ['MediaPipe Pose (Heavy)', 'CLIP ViT-B/32 (HuggingFace)'] },
  { category: 'Infrastructure', items: ['Docker multi-stage', 'Kubernetes', 'AKS Edge Essentials'] },
]

const GROUP_COLORS = {
  frontend: { bg: '#1e3a5f', border: '#3b82f6', glow: 'rgba(59,130,246,0.3)' },
  backend: { bg: '#2d1b4e', border: '#8b5cf6', glow: 'rgba(139,92,246,0.3)' },
  pipeline: { bg: '#1a3c34', border: '#10b981', glow: 'rgba(16,185,129,0.3)' },
  ml: { bg: '#3b2313', border: '#f59e0b', glow: 'rgba(245,158,11,0.3)' },
}

const GROUP_LABELS = {
  frontend: '🖥️ Frontend',
  backend: '🔌 REST API',
  pipeline: '⚙️ Processing Pipeline',
  ml: '🧠 ML Models',
}

function ArchitecturePanel({ onBack }) {
  const [hoveredNode, setHoveredNode] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)

  const getNodeCenter = (node) => ({
    x: node.x + node.w / 2,
    y: node.y + node.h / 2,
  })

  return (
    <div className="arch-page">
      <div className="arch-header">
        <button className="arch-back-btn" onClick={onBack}>← Back</button>
        <div>
          <h2 className="arch-title">System Architecture</h2>
          <p className="arch-desc">Golf Swing AI Coacher — End-to-end pipeline on AKS Edge</p>
        </div>
      </div>

      {/* Legend */}
      <div className="arch-legend">
        {Object.entries(GROUP_LABELS).map(([key, label]) => (
          <div key={key} className="arch-legend-item">
            <span className="arch-legend-dot" style={{ background: GROUP_COLORS[key].border }} />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {/* Flowchart Canvas */}
      <div className="arch-canvas">
        <svg className="arch-edges" viewBox="0 0 100 85" preserveAspectRatio="none">
          <defs>
            <marker id="arrow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <path d="M0,0 L8,3 L0,6" fill="#475569" />
            </marker>
            <marker id="arrow-glow" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
              <path d="M0,0 L8,3 L0,6" fill="#10b981" />
            </marker>
          </defs>
          {EDGES.map((edge, i) => {
            const from = NODES.find(n => n.id === edge.from)
            const to = NODES.find(n => n.id === edge.to)
            if (!from || !to) return null
            const fc = getNodeCenter(from)
            const tc = getNodeCenter(to)

            // Determine connection points
            let x1 = fc.x, y1 = fc.y, x2 = tc.x, y2 = tc.y
            // Connect from bottom of source to top of target
            y1 = from.y + from.h / 100 * 85
            y2 = to.y + to.h / 100 * 15

            const isHighlighted = hoveredNode === edge.from || hoveredNode === edge.to
            const midY = (y1 + y2) / 2

            return (
              <g key={i}>
                <path
                  d={`M${x1},${y1} C${x1},${midY} ${x2},${midY} ${x2},${y2}`}
                  fill="none"
                  stroke={isHighlighted ? '#10b981' : '#334155'}
                  strokeWidth={isHighlighted ? 0.4 : 0.2}
                  markerEnd={isHighlighted ? 'url(#arrow-glow)' : 'url(#arrow)'}
                  opacity={isHighlighted ? 1 : 0.6}
                  className={isHighlighted ? 'arch-edge-glow' : ''}
                />
              </g>
            )
          })}
        </svg>

        {NODES.map(node => {
          const colors = GROUP_COLORS[node.group]
          const isHovered = hoveredNode === node.id
          const isSelected = selectedNode === node.id
          return (
            <div
              key={node.id}
              className={`arch-node ${isHovered ? 'hovered' : ''} ${isSelected ? 'selected' : ''}`}
              style={{
                left: `${node.x}%`,
                top: `${node.y}%`,
                width: `${node.w}px`,
                background: colors.bg,
                borderColor: isHovered || isSelected ? colors.border : 'rgba(255,255,255,0.1)',
                boxShadow: isHovered || isSelected ? `0 0 20px ${colors.glow}` : 'none',
              }}
              onMouseEnter={() => setHoveredNode(node.id)}
              onMouseLeave={() => setHoveredNode(null)}
              onClick={() => setSelectedNode(selectedNode === node.id ? null : node.id)}
            >
              <div className="arch-node-label">{node.label}</div>
              <div className="arch-node-desc">{node.desc}</div>
            </div>
          )
        })}
      </div>

      {/* K8s Architecture */}
      <div className="arch-k8s-section">
        <h3 className="arch-section-title">
          <span>☸</span> Kubernetes Deployment — AKS Edge Essentials
        </h3>
        <div className="arch-k8s-grid">
          {K8S_COMPONENTS.map((comp, i) => (
            <div key={i} className="arch-k8s-card">
              <div className="arch-k8s-icon">{comp.icon}</div>
              <div className="arch-k8s-info">
                <div className="arch-k8s-name">{comp.name}</div>
                <div className="arch-k8s-kind">{comp.kind}</div>
                <div className="arch-k8s-desc">{comp.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Tech Stack */}
      <div className="arch-stack-section">
        <h3 className="arch-section-title">
          <span>🛠️</span> Technology Stack
        </h3>
        <div className="arch-stack-grid">
          {TECH_STACK.map((cat, i) => (
            <div key={i} className="arch-stack-card">
              <div className="arch-stack-category">{cat.category}</div>
              <div className="arch-stack-items">
                {cat.items.map((item, j) => (
                  <span key={j} className="arch-stack-tag">{item}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Data Flow */}
      <div className="arch-flow-section">
        <h3 className="arch-section-title">
          <span>🔄</span> Data Flow
        </h3>
        <div className="arch-flow-steps">
          {[
            { step: '1', icon: '📤', title: 'Upload', desc: 'User uploads golf swing video via drag-and-drop' },
            { step: '2', icon: '🎬', title: 'Decode', desc: 'ffmpeg extracts frames, two-pass swing region detection' },
            { step: '3', icon: '🦴', title: 'Pose', desc: 'MediaPipe detects 33 body landmarks per frame' },
            { step: '4', icon: '📐', title: 'Segment', desc: 'Anchor-based algorithm identifies 8 swing stages' },
            { step: '5', icon: '🎯', title: 'Score', desc: 'Gaussian scoring against ideal body metrics' },
            { step: '6', icon: '🏆', title: 'Match', desc: 'CLIP embeddings find best pro golfer reference frame' },
            { step: '7', icon: '🖊️', title: 'Annotate', desc: 'Skeleton overlay, arrows, and callouts on both frames' },
            { step: '8', icon: '🏌️', title: 'Coach', desc: 'Actionable coaching tips delivered to user' },
          ].map((s, i) => (
            <div key={i} className="arch-flow-step">
              <div className="arch-flow-num">{s.step}</div>
              <div className="arch-flow-icon">{s.icon}</div>
              <div className="arch-flow-title">{s.title}</div>
              <div className="arch-flow-desc">{s.desc}</div>
              {i < 7 && <div className="arch-flow-arrow">→</div>}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ArchitecturePanel
