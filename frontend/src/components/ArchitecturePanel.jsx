import { useState, useRef, useCallback, useEffect } from 'react'

/* ── Layout: all positions in a virtual 1000×600 canvas ── */
const NODES = [
  { id: 'user',      label: '📹 Video Upload',       desc: 'Drag & drop golf swing video',       group: 'frontend', cx: 500, cy: 45,  w: 190, h: 52 },
  { id: 'api',       label: '⚡ FastAPI Gateway',     desc: 'POST /upload • GET /status • GET /result', group: 'backend',  cx: 500, cy: 140, w: 210, h: 52 },
  { id: 'decoder',   label: '🎬 Video Decoder',       desc: 'ffmpeg • Two-pass swing detection',   group: 'pipeline', cx: 170, cy: 250, w: 200, h: 52 },
  { id: 'pose',      label: '🦴 Pose Estimation',     desc: 'MediaPipe Heavy • 33 landmarks',     group: 'ml',       cx: 500, cy: 250, w: 200, h: 52 },
  { id: 'segment',   label: '📐 Stage Segmentation',  desc: 'Anchor-based • 8 swing stages',      group: 'pipeline', cx: 830, cy: 250, w: 210, h: 52 },
  { id: 'scoring',   label: '🎯 Scoring Engine',      desc: 'Gaussian curves • Body metrics → 0-100', group: 'pipeline', cx: 170, cy: 370, w: 200, h: 52 },
  { id: 'reference', label: '🏆 Reference Matcher',   desc: 'CLIP ViT-B/32 • Pro golfer similarity', group: 'ml',       cx: 500, cy: 370, w: 210, h: 52 },
  { id: 'annotator', label: '🖊️ Frame Annotator',     desc: 'Skeleton • Arrows • Side-by-side',    group: 'pipeline', cx: 830, cy: 370, w: 200, h: 52 },
  { id: 'results',   label: '📊 Results & Coaching',  desc: 'Scores • Actionable tips • Comparisons', group: 'frontend', cx: 500, cy: 490, w: 210, h: 52 },
]

const EDGES = [
  { from: 'user',    to: 'api',       label: 'Upload' },
  { from: 'api',     to: 'decoder',   label: 'Video file' },
  { from: 'api',     to: 'pose',      label: 'Frames' },
  { from: 'decoder', to: 'pose',      label: 'Frames' },
  { from: 'pose',    to: 'segment',   label: 'Landmarks' },
  { from: 'segment', to: 'scoring',   label: 'Stage idx' },
  { from: 'pose',    to: 'reference', label: 'Features' },
  { from: 'reference','to': 'annotator', label: 'Match' },
  { from: 'scoring', to: 'annotator', label: 'Metrics' },
  { from: 'annotator',to: 'results',  label: 'Annotated' },
  { from: 'scoring', to: 'results',   label: 'Scores' },
]

const K8S_COMPONENTS = [
  { icon: '☸', name: 'AKS Edge',           kind: 'Cluster',             desc: 'Lightweight K8s on edge devices' },
  { icon: '📦', name: 'golf-ai-backend',    kind: 'Deployment',          desc: 'FastAPI + ML pipeline container' },
  { icon: '🔗', name: 'golf-ai-api',        kind: 'Service',             desc: 'ClusterIP → port 8000' },
  { icon: '🌐', name: 'golf-ai-ingress',    kind: 'Ingress',             desc: 'External access routing' },
  { icon: '💾', name: 'model-cache-pvc',     kind: 'PersistentVolumeClaim', desc: 'MediaPipe + CLIP model weights' },
  { icon: '⚙️', name: 'golf-ai-config',      kind: 'ConfigMap',           desc: 'Runtime settings & thresholds' },
  { icon: '📁', name: 'results-pvc',         kind: 'PersistentVolumeClaim', desc: 'Generated analysis assets' },
]

const TECH_STACK = [
  { category: 'Frontend', items: ['React 18', 'Vite', 'CSS3 Custom Properties'] },
  { category: 'Backend', items: ['Python 3.11', 'FastAPI', 'uvicorn', 'OpenCV', 'ffmpeg'] },
  { category: 'ML Models', items: ['MediaPipe Pose (Heavy)', 'CLIP ViT-B/32 (HuggingFace)'] },
  { category: 'Infrastructure', items: ['Docker multi-stage', 'Kubernetes', 'AKS Edge'] },
]

const GROUP_COLORS = {
  frontend: { bg: '#1e3a5f', border: '#3b82f6', glow: 'rgba(59,130,246,0.35)' },
  backend:  { bg: '#2d1b4e', border: '#8b5cf6', glow: 'rgba(139,92,246,0.35)' },
  pipeline: { bg: '#1a3c34', border: '#10b981', glow: 'rgba(16,185,129,0.35)' },
  ml:       { bg: '#3b2313', border: '#f59e0b', glow: 'rgba(245,158,11,0.35)' },
}

const GROUP_LABELS = {
  frontend: '🖥️ Frontend',
  backend:  '🔌 REST API',
  pipeline: '⚙️ Processing Pipeline',
  ml:       '🧠 ML Models',
}

const FLOW_STEPS = [
  { step: '1', icon: '📤', title: 'Upload',   desc: 'User uploads golf swing video via drag-and-drop' },
  { step: '2', icon: '🎬', title: 'Decode',   desc: 'ffmpeg extracts frames, two-pass swing region detection' },
  { step: '3', icon: '🦴', title: 'Pose',     desc: 'MediaPipe detects 33 body landmarks per frame' },
  { step: '4', icon: '📐', title: 'Segment',  desc: 'Anchor-based algorithm identifies 8 swing stages' },
  { step: '5', icon: '🎯', title: 'Score',    desc: 'Gaussian scoring against ideal body metrics' },
  { step: '6', icon: '🏆', title: 'Match',    desc: 'CLIP embeddings find best pro golfer reference frame' },
  { step: '7', icon: '🖊️', title: 'Annotate', desc: 'Skeleton overlay, arrows, and callouts on both frames' },
  { step: '8', icon: '🏌️', title: 'Coach',    desc: 'Actionable coaching tips delivered to user' },
]

/* ── Edge path builder: bottom of source → top of target with bezier ── */
function edgePath(fromNode, toNode) {
  const x1 = fromNode.cx
  const y1 = fromNode.cy + fromNode.h / 2
  const x2 = toNode.cx
  const y2 = toNode.cy - toNode.h / 2
  const dy = Math.abs(y2 - y1)
  const cp = Math.max(dy * 0.45, 30)
  return `M${x1},${y1} C${x1},${y1 + cp} ${x2},${y2 - cp} ${x2},${y2}`
}

/* ── Edge label midpoint ── */
function edgeMid(fromNode, toNode) {
  return {
    x: (fromNode.cx + toNode.cx) / 2,
    y: (fromNode.cy + fromNode.h / 2 + toNode.cy - toNode.h / 2) / 2,
  }
}

function ArchitecturePanel({ onBack }) {
  const [hovered, setHovered] = useState(null)

  // Zoom / Pan state
  const svgRef = useRef(null)
  const [viewBox, setViewBox] = useState({ x: -20, y: -10, w: 1040, h: 560 })
  const [isPanning, setIsPanning] = useState(false)
  const panStart = useRef({ mx: 0, my: 0, vx: 0, vy: 0 })

  const handleWheel = useCallback((e) => {
    e.preventDefault()
    const factor = e.deltaY > 0 ? 1.1 : 0.9
    setViewBox(vb => {
      const svg = svgRef.current
      if (!svg) return vb
      const rect = svg.getBoundingClientRect()
      const mx = ((e.clientX - rect.left) / rect.width) * vb.w + vb.x
      const my = ((e.clientY - rect.top) / rect.height) * vb.h + vb.y
      const nw = vb.w * factor
      const nh = vb.h * factor
      // Clamp zoom
      if (nw < 300 || nw > 3000) return vb
      return {
        x: mx - (mx - vb.x) * factor,
        y: my - (my - vb.y) * factor,
        w: nw,
        h: nh,
      }
    })
  }, [])

  const handlePointerDown = useCallback((e) => {
    if (e.button !== 0) return
    // Only pan if clicking on the canvas background (SVG itself)
    if (e.target.closest('.arch-svg-node')) return
    setIsPanning(true)
    panStart.current = { mx: e.clientX, my: e.clientY, vx: viewBox.x, vy: viewBox.y }
    e.currentTarget.setPointerCapture(e.pointerId)
  }, [viewBox])

  const handlePointerMove = useCallback((e) => {
    if (!isPanning) return
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const dx = ((e.clientX - panStart.current.mx) / rect.width) * viewBox.w
    const dy = ((e.clientY - panStart.current.my) / rect.height) * viewBox.h
    setViewBox(vb => ({ ...vb, x: panStart.current.vx - dx, y: panStart.current.vy - dy }))
  }, [isPanning, viewBox.w, viewBox.h])

  const handlePointerUp = useCallback(() => setIsPanning(false), [])

  const resetZoom = () => setViewBox({ x: -20, y: -10, w: 1040, h: 560 })

  // Attach wheel listener with passive:false
  useEffect(() => {
    const el = svgRef.current
    if (!el) return
    el.addEventListener('wheel', handleWheel, { passive: false })
    return () => el.removeEventListener('wheel', handleWheel)
  }, [handleWheel])

  const connectedEdges = (nodeId) =>
    EDGES.filter(e => e.from === nodeId || e.to === nodeId)

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
        <div className="arch-legend-item" style={{ marginLeft: 'auto', opacity: 0.6 }}>
          Scroll to zoom • Drag to pan
        </div>
        <button className="arch-zoom-reset" onClick={resetZoom} title="Reset zoom">⟲ Reset</button>
      </div>

      {/* Flowchart — pure SVG with zoom/pan */}
      <div className="arch-canvas-wrap">
        <svg
          ref={svgRef}
          className="arch-svg"
          viewBox={`${viewBox.x} ${viewBox.y} ${viewBox.w} ${viewBox.h}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
          style={{ cursor: isPanning ? 'grabbing' : 'grab' }}
        >
          <defs>
            <marker id="ah" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <path d="M0,0 L10,3.5 L0,7" fill="#475569" />
            </marker>
            <marker id="ah-glow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
              <path d="M0,0 L10,3.5 L0,7" fill="#34d399" />
            </marker>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="g" />
              <feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          {/* Background dot grid */}
          <pattern id="dots" width="25" height="25" patternUnits="userSpaceOnUse">
            <circle cx="12.5" cy="12.5" r="0.8" fill="#1e293b" />
          </pattern>
          <rect x="-200" y="-200" width="1400" height="1000" fill="#0f172a" />
          <rect x="-200" y="-200" width="1400" height="1000" fill="url(#dots)" />

          {/* Edges */}
          {EDGES.map((edge, i) => {
            const fn = NODES.find(n => n.id === edge.from)
            const tn = NODES.find(n => n.id === edge.to)
            if (!fn || !tn) return null
            const isHi = hovered && (edge.from === hovered || edge.to === hovered)
            const mid = edgeMid(fn, tn)
            return (
              <g key={i}>
                <path
                  d={edgePath(fn, tn)}
                  fill="none"
                  stroke={isHi ? '#34d399' : '#334155'}
                  strokeWidth={isHi ? 2.5 : 1.5}
                  markerEnd={isHi ? 'url(#ah-glow)' : 'url(#ah)'}
                  opacity={hovered ? (isHi ? 1 : 0.2) : 0.7}
                  filter={isHi ? 'url(#glow)' : undefined}
                />
                {isHi && (
                  <text x={mid.x} y={mid.y - 6} textAnchor="middle"
                    fill="#94a3b8" fontSize="10" fontFamily="Inter, sans-serif">
                    {edge.label}
                  </text>
                )}
              </g>
            )
          })}

          {/* Nodes */}
          {NODES.map(node => {
            const c = GROUP_COLORS[node.group]
            const isHi = hovered === node.id
            const x = node.cx - node.w / 2
            const y = node.cy - node.h / 2
            return (
              <g key={node.id} className="arch-svg-node"
                onMouseEnter={() => setHovered(node.id)}
                onMouseLeave={() => setHovered(null)}
                style={{ cursor: 'pointer' }}
              >
                {/* Glow rect behind */}
                {isHi && (
                  <rect x={x - 4} y={y - 4} width={node.w + 8} height={node.h + 8}
                    rx="12" fill="none" stroke={c.border} strokeWidth="2"
                    opacity="0.5" filter="url(#glow)" />
                )}
                <rect x={x} y={y} width={node.w} height={node.h}
                  rx="10" fill={c.bg}
                  stroke={isHi ? c.border : 'rgba(255,255,255,0.12)'}
                  strokeWidth={isHi ? 2 : 1} />
                <text x={node.cx} y={node.cy - 5} textAnchor="middle"
                  fill="#f1f5f9" fontSize="13" fontWeight="700"
                  fontFamily="Inter, sans-serif">
                  {node.label}
                </text>
                <text x={node.cx} y={node.cy + 13} textAnchor="middle"
                  fill="#94a3b8" fontSize="9.5"
                  fontFamily="Inter, sans-serif">
                  {node.desc}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      {/* K8s Architecture */}
      <div className="arch-k8s-section">
        <h3 className="arch-section-title">
          <span>☸</span> Kubernetes Deployment — AKS Edge
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
          {FLOW_STEPS.map((s, i) => (
            <div key={i} className="arch-flow-step">
              <div className="arch-flow-num">{s.step}</div>
              <div className="arch-flow-icon">{s.icon}</div>
              <div className="arch-flow-title">{s.title}</div>
              <div className="arch-flow-desc">{s.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default ArchitecturePanel
