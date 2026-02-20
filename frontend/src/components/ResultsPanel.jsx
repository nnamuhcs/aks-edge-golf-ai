import { useState } from 'react'

function ResultsPanel({ result, onReset }) {
  const [selectedStage, setSelectedStage] = useState(0)
  const [lightboxSrc, setLightboxSrc] = useState(null)

  if (!result || !result.stages) return null

  const stage = result.stages[selectedStage]
  const scoreClass = result.overall_score >= 85 ? 'score-excellent'
    : result.overall_score >= 70 ? 'score-good'
    : result.overall_score >= 55 ? 'score-fair'
    : 'score-poor'

  return (
    <div className="results">
      {/* Overall Score */}
      <div className="overall-score">
        <div className={`score-circle ${scoreClass}`}>
          {Math.round(result.overall_score)}
        </div>
        <h2 style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: 8 }}>
          Overall Swing Score
        </h2>
        <p className="overall-comment">{result.overall_comment}</p>
        <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={onReset}>
          ↩ Analyze Another Swing
        </button>
      </div>

      {/* Stage Timeline */}
      <div className="stage-timeline">
        {result.stages.map((s, idx) => (
          <button
            key={s.stage}
            className={`stage-tab ${idx === selectedStage ? 'active' : ''}`}
            onClick={() => setSelectedStage(idx)}
          >
            {s.display_name}
            <span className="stage-score">{Math.round(s.score)}</span>
          </button>
        ))}
      </div>

      {/* Comparison Panel */}
      <div className="comparison-panel">
        <div className="comparison-card user">
          <h3>📹 Your Swing</h3>
          <img
            src={stage.user_image}
            alt={`Your ${stage.display_name}`}
            onClick={() => setLightboxSrc(stage.user_image)}
          />
        </div>
        <div className="comparison-card reference">
          <h3>✨ Good Practice</h3>
          <img
            src={stage.reference_image}
            alt={`Reference ${stage.display_name}`}
            onClick={() => setLightboxSrc(stage.reference_image)}
          />
        </div>
      </div>

      {/* Feedback Panel */}
      <div className="feedback-panel">
        <h3>
          {stage.display_name}
          <span style={{
            marginLeft: 'auto',
            fontSize: '1.2rem',
            fontWeight: 700,
            color: stage.score >= 70 ? 'var(--color-success)' : 'var(--color-warning)'
          }}>
            {Math.round(stage.score)}/100
          </span>
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div className="feedback-section good">
            <h4>✅ What&apos;s Good</h4>
            <ul>
              {stage.good_points.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </div>

          <div className="feedback-section issues">
            <h4>⚠️ Areas to Improve</h4>
            <ul>
              {stage.issues.map((p, i) => <li key={i}>{p}</li>)}
            </ul>
          </div>
        </div>

        <div className="why-box" style={{ marginTop: 12 }}>
          <strong>Why it matters:</strong> {stage.why_it_matters}
        </div>

        <div className="feedback-section tips" style={{ marginTop: 16 }}>
          <h4>💡 How to Improve</h4>
          <ul>
            {stage.improvement_tips.map((t, i) => <li key={i}>{t}</li>)}
          </ul>
        </div>
      </div>

      {/* Lightbox */}
      {lightboxSrc && (
        <div className="lightbox-overlay" onClick={() => setLightboxSrc(null)}>
          <img src={lightboxSrc} alt="Enlarged view" />
        </div>
      )}
    </div>
  )
}

export default ResultsPanel
