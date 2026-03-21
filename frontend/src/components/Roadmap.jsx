import { useState, useEffect, useRef } from 'react'
import { getRoadmap, askQuestion, getQAHistory } from '../api'
import './Roadmap.css'

function getStatus(lvl) {
  if (lvl.completed)       return 'completed'
  if (lvl.needs_revision)  return 'revision'
  if (lvl.current)         return 'current'
  if (lvl.available)       return 'available'
  return 'locked'
}

const STATUS_ICON = {
  completed: '✓',
  revision:  '↻',
  current:   '▶',
  available: '○',
  locked:    '🔒',
}

export default function Roadmap({ userId, isAdmin, onContinue, onLevelSelect, onLogout, onAdmin, onNews, onSimulator }) {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(true)
  const [tab, setTab]           = useState('path')   // 'path' | 'qa'

  // Q&A state
  const [qaInput, setQaInput]   = useState('')
  const [qaLoading, setQaLoading] = useState(false)
  const [qaAnswer, setQaAnswer] = useState(null)    // { answer, sources }
  const [qaHistory, setQaHistory] = useState([])
  const qaBottomRef = useRef(null)

  useEffect(() => {
    getRoadmap(userId).then(d => {
      setData(d)
      setLoading(false)
    })
    getQAHistory(userId).then(d => setQaHistory(d.history || []))
  }, [userId])

  useEffect(() => {
    qaBottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [qaAnswer, qaLoading])

  async function handleAsk(question) {
    const q = (question || qaInput).trim()
    if (!q || qaLoading) return
    setQaInput('')
    setQaAnswer(null)
    setQaLoading(true)
    try {
      const res = await askQuestion(userId, q)
      setQaAnswer({ question: q, answer: res.answer, sources: res.sources })
      setQaHistory(res.history || [])
    } catch {
      setQaAnswer({ question: q, answer: 'Sorry, something went wrong. Please try again.', sources: [] })
    } finally {
      setQaLoading(false)
    }
  }

  if (loading) return (
    <div className="rm-loading">
      <div className="rm-spinner" />
      <span>Loading your journey...</span>
    </div>
  )

  const currentLevel   = data?.current_level || 1
  const totalCompleted = data?.levels_completed?.length || 0
  const examDone       = data?.initial_exam_completed
  const xp             = totalCompleted * 350
  const maxXp          = 15 * 350
  const xpPct          = Math.round((xp / maxXp) * 100)
  const inProgress     = data?.levels?.filter(l => l.needs_revision) || []

  return (
    <div className="rm-page">
      {/* ── Top nav ── */}
      <nav className="rm-nav">
        <div className="rm-nav-logo">
          <span className="rm-nav-icon">🏛️</span>
          <span className="rm-nav-brand">Civic Lens</span>
        </div>
        <div className="rm-nav-links">
          <span className="rm-nav-link active">Dashboard</span>
          <span className="rm-nav-link" onClick={onContinue}>Learn</span>
          <span className="rm-nav-link" onClick={onNews}>News</span>
          {totalCompleted >= 5 && (
            <span className="rm-nav-link" onClick={onSimulator}>Simulator 🏛️</span>
          )}
          {isAdmin && (
            <span className="rm-nav-link" onClick={onAdmin}>Admin</span>
          )}
          <span className="rm-nav-link" onClick={onLogout}>Switch User</span>
        </div>
        <div className="rm-nav-right">
          <div className="rm-avatar">{userId[0]?.toUpperCase()}</div>
        </div>
      </nav>

      {/* ── Main body ── */}
      <div className="rm-body">

        {/* Left panel */}
        <aside className="rm-left">
          <div className="rm-profile-card">
            <div className="rm-profile-avatar">{userId[0]?.toUpperCase()}</div>
            <div className="rm-profile-name">{userId}</div>
            <div className="rm-profile-title">
              {examDone ? `Level ${currentLevel} Explorer` : 'New Learner'}
            </div>

            <div className="rm-xp-row">
              <span>{xp.toLocaleString()} / {maxXp.toLocaleString()} XP</span>
              <span>{xpPct}%</span>
            </div>
            <div className="rm-xp-bar">
              <div className="rm-xp-fill" style={{ width: `${xpPct}%` }} />
            </div>

            <div className="rm-streak">
              🔥 {totalCompleted} Level{totalCompleted !== 1 ? 's' : ''} Completed
            </div>
          </div>

          {/* In Progress */}
          <div className="rm-section-card">
            <div className="rm-section-title">In Progress</div>
            {inProgress.length === 0 && !examDone && (
              <div className="rm-section-empty">Take the placement quiz to get started!</div>
            )}
            {inProgress.length === 0 && examDone && (
              <div className="rm-section-empty">No levels need revision. Keep going!</div>
            )}
            {inProgress.map(lvl => (
              <div key={lvl.level} className="rm-progress-item">
                <div className="rm-progress-item-info">
                  <span className="rm-progress-item-icon">📌</span>
                  <span className="rm-progress-item-title">{lvl.title}</span>
                </div>
                <div className="rm-progress-bar-wrap">
                  <div className="rm-progress-bar-fill" style={{ width: '45%' }} />
                </div>
              </div>
            ))}
            {examDone && inProgress.length === 0 && data?.levels
              ?.filter(l => l.completed)
              .slice(-3)
              .reverse()
              .map(lvl => (
                <div key={lvl.level} className="rm-progress-item">
                  <div className="rm-progress-item-info">
                    <span className="rm-progress-item-icon">✅</span>
                    <span className="rm-progress-item-title">{lvl.title}</span>
                  </div>
                  <div className="rm-progress-bar-wrap">
                    <div className="rm-progress-bar-fill" style={{ width: '100%' }} />
                  </div>
                </div>
              ))}
          </div>
        </aside>

        {/* Center: tabs + content */}
        <section className="rm-center">
          {/* Tab bar */}
          <div className="rm-tabs">
            <button
              className={`rm-tab ${tab === 'path' ? 'active' : ''}`}
              onClick={() => setTab('path')}
            >
              🗺️ Learning Path
            </button>
            <button
              className={`rm-tab ${tab === 'qa' ? 'active' : ''}`}
              onClick={() => setTab('qa')}
            >
              💬 Ask Q&A
            </button>
          </div>

          {/* Q&A Panel */}
          {tab === 'qa' && (
            <div className="rm-qa-panel">
              {/* Suggestions */}
              {qaHistory.length > 0 && !qaAnswer && !qaLoading && (
                <div className="rm-qa-suggestions">
                  <div className="rm-qa-suggest-label">Your previous questions</div>
                  <div className="rm-qa-suggest-chips">
                    {qaHistory.slice(0, 8).map((q, i) => (
                      <button
                        key={i}
                        className="rm-qa-chip"
                        onClick={() => handleAsk(q)}
                      >
                        {q}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Answer card */}
              {qaAnswer && (
                <div className="rm-qa-answer-wrap">
                  <div className="rm-qa-question-echo">
                    <span className="rm-qa-q-icon">❓</span>
                    {qaAnswer.question}
                  </div>
                  <div className="rm-qa-answer-card">
                    <div className="rm-qa-answer-text">{qaAnswer.answer}</div>
                    {qaAnswer.sources?.length > 0 && (
                      <details className="rm-qa-sources">
                        <summary>Sources ({qaAnswer.sources.length})</summary>
                        {qaAnswer.sources.map((s, i) => (
                          <div key={i} className="rm-qa-source-item">
                            {s.label && <div className="rm-qa-source-label">{s.label}</div>}
                            <div className="rm-qa-source-text">{s.text}</div>
                          </div>
                        ))}
                      </details>
                    )}
                  </div>
                  <button
                    className="rm-qa-ask-another"
                    onClick={() => { setQaAnswer(null); setQaInput('') }}
                  >
                    Ask another question
                  </button>
                </div>
              )}

              {/* Loading */}
              {qaLoading && (
                <div className="rm-qa-loading">
                  <div className="rm-qa-dots">
                    <span /><span /><span />
                  </div>
                  <span>Searching the knowledge base...</span>
                </div>
              )}

              <div ref={qaBottomRef} />

              {/* Input */}
              <div className="rm-qa-input-wrap">
                {!qaAnswer && !qaLoading && qaHistory.length === 0 && (
                  <div className="rm-qa-empty">
                    <div className="rm-qa-empty-icon">🏛️</div>
                    <div className="rm-qa-empty-text">Ask anything about Indian civics, government, or democracy</div>
                  </div>
                )}
                <form
                  className="rm-qa-form"
                  onSubmit={e => { e.preventDefault(); handleAsk() }}
                >
                  <input
                    className="rm-qa-input"
                    type="text"
                    placeholder="e.g. What is the role of the Rajya Sabha?"
                    value={qaInput}
                    onChange={e => setQaInput(e.target.value)}
                    disabled={qaLoading}
                    autoComplete="off"
                  />
                  <button
                    type="submit"
                    className="rm-qa-submit"
                    disabled={!qaInput.trim() || qaLoading}
                  >
                    Ask →
                  </button>
                </form>
              </div>
            </div>
          )}

          {/* Learning path grid */}
          {tab === 'path' && (
            <>
          <div className="rm-path-title">Learning Path</div>
          <div className="rm-grid">
            {data?.levels?.map(lvl => {
              const status   = getStatus(lvl)
              const locked   = status === 'locked'
              const icon     = STATUS_ICON[status]

              return (
                <div
                  key={lvl.level}
                  className={`rm-card rm-card-${status}`}
                >
                  <div className="rm-card-header">
                    <span className="rm-card-level">Level {lvl.level}</span>
                    <span className="rm-card-icon">{icon}</span>
                  </div>
                  <div className="rm-card-title">{lvl.title}</div>
                  {!locked && (
                    <div className="rm-card-actions">
                      <button
                        className="rm-card-btn rm-card-btn-lesson"
                        onClick={() => onLevelSelect(lvl.level, 'lesson')}
                      >
                        Lesson
                      </button>
                      <button
                        className="rm-card-btn rm-card-btn-quiz"
                        onClick={() => onLevelSelect(lvl.level, 'quiz')}
                      >
                        Quiz
                      </button>
                    </div>
                  )}
                  {locked && (
                    <div className="rm-card-locked-msg">Complete previous levels</div>
                  )}
                </div>
              )
            })}
          </div>
            </>
          )}
        </section>

        {/* Right panel */}
        <aside className="rm-right">
          <div className="rm-stats-card">
            <div className="rm-rec-label">Your Progress</div>
            <div className="rm-ai-stat">
              <span className="rm-ai-pct">+{xpPct}%</span>
              <span className="rm-ai-label">Overall completion</span>
            </div>
            <div className="rm-ai-text">
              {totalCompleted === 0
                ? 'Complete the placement quiz to begin your personalised learning path.'
                : totalCompleted < 5
                ? `Great start! You've completed ${totalCompleted} level${totalCompleted > 1 ? 's' : ''}. Keep the momentum going!`
                : `Excellent progress! ${15 - totalCompleted} levels remaining to master civic knowledge.`}
            </div>
            <button className="rm-btn-outline" onClick={onContinue}>
              {examDone ? `Continue Level ${currentLevel}` : 'Start Assessment'} →
            </button>
          </div>

          {/* Simulator Feature Card */}
          {totalCompleted >= 5 && (
            <div className="rm-stats-card" style={{marginTop: '1.5rem', background: 'var(--surface-light)', borderColor: 'var(--primary)', borderWidth: '2px'}}>
              <div className="rm-rec-label" style={{color: 'var(--primary)'}}>🏛️ New Feature Unlocked!</div>
              <div className="rm-ai-text">
                You've reached Level 5! You can now access the <b>Parliamentary Simulator</b>. Try drafting your own bill and debating the AI Opposition!
              </div>
              <button 
                className="rm-btn-outline" 
                style={{background: 'var(--primary)', color: 'white', borderColor: 'var(--primary)'}}
                onClick={onSimulator}
              >
                Enter Simulator
              </button>
            </div>
          )}

          {/* Legend */}
          <div className="rm-section-card">
            <div className="rm-section-title">Legend</div>
            <div className="rm-legend">
              <div className="rm-legend-item"><span className="rm-legend-dot dot-completed" />Completed</div>
              <div className="rm-legend-item"><span className="rm-legend-dot dot-current" />Current</div>
              <div className="rm-legend-item"><span className="rm-legend-dot dot-available" />Available</div>
              <div className="rm-legend-item"><span className="rm-legend-dot dot-revision" />Needs Revision</div>
              <div className="rm-legend-item"><span className="rm-legend-dot dot-locked" />Locked</div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  )
}
