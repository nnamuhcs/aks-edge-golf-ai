import { useState, useEffect } from 'react'

function ResultsPanel({ result, onReset }) {
  const [selectedStage, setSelectedStage] = useState(0)
  const [lightboxSrc, setLightboxSrc] = useState(null)
  const [showHint, setShowHint] = useState(true)

  // Fade out the pulse hint after 4 seconds
  useEffect(() => {
    if (!result) return
    setShowHint(true)
    const timer = setTimeout(() => setShowHint(false), 4000)
    return () => clearTimeout(timer)
  }, [result])

  if (!result || !result.stages) return null

  const stage = result.stages[selectedStage]
  const scoreClass = result.overall_score >= 85 ? 'score-excellent'
    : result.overall_score >= 70 ? 'score-good'
    : result.overall_score >= 55 ? 'score-fair'
    : 'score-poor'

  return (
    <div className="results">
      {/* Overall Score — compact inline */}
      <div className="overall-score">
        <div className={`score-circle ${scoreClass}`}>
          {Math.round(result.overall_score)}
        </div>
        <div className="overall-info">
          <h2>Overall Swing Score</h2>
          <p className="overall-comment">{result.overall_comment}</p>
        </div>
        <button className="btn btn-secondary" onClick={onReset}>
          ↩ Analyze Another
        </button>
      </div>

      {/* Stage Timeline */}
      <div className="stage-timeline">
        {result.stages.map((s, idx) => (
          <button
            key={s.stage}
            className={`stage-tab ${idx === selectedStage ? 'active' : ''} ${showHint && idx !== selectedStage ? 'hint-pulse' : ''}`}
            onClick={() => setSelectedStage(idx)}
          >
            <span className="stage-num">{idx + 1}</span>
            <span className="stage-name">{s.display_name}</span>
            <span className="stage-score">{Math.round(s.score)}</span>
            {idx === selectedStage && <span className="stage-indicator" />}
          </button>
        ))}
      </div>

      {/* Comparison: side by side */}
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

      {/* Coaching feedback below */}
      <div className="feedback-panel">
        <div className="feedback-header">
          <span className="feedback-stage">
            Stage: {stage.display_name}
            <span className={`feedback-stage-score ${stage.score >= 70 ? 'good' : 'warn'}`}>
              {Math.round(stage.score)}/100
            </span>
          </span>
          <span className="feedback-title">🤖 AI Coaching Insights</span>
        </div>

        <div className="feedback-grid">
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

        <div className="why-box">
          <strong>Why it matters:</strong> {stage.why_it_matters}
        </div>

        <div className="feedback-section tips">
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
