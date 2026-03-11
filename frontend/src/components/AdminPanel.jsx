import { useState, useEffect, useRef } from 'react'
import {
  adminListFiles, adminUploadFile, adminDeleteFile,
  adminFileContentUrl, adminGetTextContent,
  adminListLessons, adminGetLesson, adminGetQuiz,
  adminUpdateLesson, adminGenerateLesson, adminRegenerateQuiz,
} from '../api'
import './AdminPanel.css'

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ── Shared Status Banner ───────────────────────────────────────────────────
function StatusBanner({ status, onClose }) {
  if (!status) return null
  return (
    <div className={`ap-status ap-status-${status.type}`}>
      {status.type === 'success' && '✓ '}
      {status.type === 'error'   && '✗ '}
      {status.type === 'info'    && '⏳ '}
      {status.msg}
      <button className="ap-status-close" onClick={onClose}>×</button>
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// KNOWLEDGE BASE TAB
// ══════════════════════════════════════════════════════════════════════════
function KnowledgeBaseTab() {
  const [files, setFiles]           = useState([])
  const [loading, setLoading]       = useState(true)
  const [status, setStatus]         = useState(null)
  const [uploading, setUploading]   = useState(false)
  const [deletingFile, setDeletingFile] = useState(null)
  const [viewFile, setViewFile]     = useState(null)
  const fileInputRef = useRef(null)

  async function loadFiles() {
    try {
      const data = await adminListFiles()
      setFiles(data.files || [])
    } catch (e) {
      setStatus({ type: 'error', msg: `Failed to load files: ${e.message}` })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadFiles() }, [])

  async function handleUpload(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setStatus({ type: 'info', msg: `Uploading ${file.name}…` })
    try {
      const res = await adminUploadFile(file)
      setStatus({ type: 'success', msg: res.message })
      await loadFiles()
    } catch (err) {
      setStatus({ type: 'error', msg: err.message })
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  async function handleDelete(filename) {
    if (!window.confirm(`Delete "${filename}"? This removes it from the knowledge base.`)) return
    setDeletingFile(filename)
    setStatus({ type: 'info', msg: `Deleting ${filename}…` })
    try {
      const res = await adminDeleteFile(filename)
      setStatus({ type: 'success', msg: res.message || `"${filename}" deleted.` })
      await loadFiles()
    } catch (err) {
      setStatus({ type: 'error', msg: err.message })
    } finally {
      setDeletingFile(null)
    }
  }

  async function handleView(file) {
    const url = adminFileContentUrl(file.filename)
    if (file.extension === '.pdf') {
      setViewFile({ filename: file.filename, isPdf: true, url, content: null })
    } else {
      setStatus({ type: 'info', msg: `Loading ${file.filename}…` })
      try {
        const content = await adminGetTextContent(file.filename)
        setViewFile({ filename: file.filename, isPdf: false, url, content })
        setStatus(null)
      } catch (err) {
        setStatus({ type: 'error', msg: err.message })
      }
    }
  }

  const canView = (f) => ['.pdf', '.txt', '.md'].includes(f.extension)

  return (
    <div className="ap-tab-content">
      {/* Header */}
      <div className="ap-section-header">
        <div>
          <h2 className="ap-section-title">Knowledge Base</h2>
          <p className="ap-section-sub">Source documents and embeddings</p>
        </div>
        <div className="ap-upload-area">
          <input ref={fileInputRef} type="file" accept=".pdf,.txt,.md"
            style={{ display: 'none' }} onChange={handleUpload} disabled={uploading} />
          <button className="ap-btn ap-btn-primary"
            onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? 'Uploading…' : '+ Upload File'}
          </button>
          <span className="ap-hint">PDF, TXT or MD — embeddings run automatically</span>
        </div>
      </div>

      <StatusBanner status={status} onClose={() => setStatus(null)} />

      {loading ? (
        <div className="ap-loading"><div className="rm-spinner" /><span>Loading files…</span></div>
      ) : files.length === 0 ? (
        <div className="ap-empty">
          <div className="ap-empty-icon">📂</div>
          <div>No files yet.</div>
          <div className="ap-hint">Upload a PDF or TXT file to get started.</div>
        </div>
      ) : (
        <div className="ap-table-wrap">
          <table className="ap-table">
            <thead>
              <tr>
                <th>Filename</th><th>Type</th><th>Size</th>
                <th>Level</th><th>Indexed</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {files.map(f => (
                <tr key={f.filename}>
                  <td className="ap-filename">{f.filename}</td>
                  <td>
                    <span className={`ap-badge ap-badge-${f.extension?.replace('.','') || 'file'}`}>
                      {f.extension?.toUpperCase().replace('.','') || 'FILE'}
                    </span>
                  </td>
                  <td className="ap-size">{formatBytes(f.size_bytes)}</td>
                  <td>{f.level != null
                    ? <span className="ap-level-badge">Level {f.level}</span>
                    : <span className="ap-na">—</span>}
                  </td>
                  <td>
                    <span className={`ap-indexed ${f.indexed ? 'ap-indexed-yes' : 'ap-indexed-no'}`}>
                      {f.indexed ? '✓ Indexed' : '○ Pending'}
                    </span>
                  </td>
                  <td className="ap-actions">
                    {canView(f) && (
                      <button className="ap-btn ap-btn-sm ap-btn-view" onClick={() => handleView(f)}>View</button>
                    )}
                    <a className="ap-btn ap-btn-sm ap-btn-download"
                      href={adminFileContentUrl(f.filename)} download={f.filename}>Download</a>
                    <button className="ap-btn ap-btn-sm ap-btn-delete"
                      onClick={() => handleDelete(f.filename)} disabled={deletingFile === f.filename}>
                      {deletingFile === f.filename ? '…' : 'Delete'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* File viewer modal */}
      {viewFile && (
        <div className="ap-modal-overlay" onClick={() => setViewFile(null)}>
          <div className={`ap-modal${viewFile.isPdf ? ' ap-modal-pdf' : ''}`} onClick={e => e.stopPropagation()}>
            <div className="ap-modal-header">
              <span className="ap-modal-title">{viewFile.filename}</span>
              <div className="ap-modal-header-actions">
                <a className="ap-btn ap-btn-sm ap-btn-download"
                  href={viewFile.url} download={viewFile.filename}>Download</a>
                <button className="ap-modal-close" onClick={() => setViewFile(null)}>×</button>
              </div>
            </div>
            {viewFile.isPdf
              ? <iframe src={viewFile.url} className="ap-modal-iframe" title={viewFile.filename} />
              : <pre className="ap-modal-content">{viewFile.content}</pre>
            }
          </div>
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// CURRICULUM TAB — level row (expanded inline)
// ══════════════════════════════════════════════════════════════════════════
function LevelRow({ meta }) {
  const [open, setOpen]             = useState(false)
  const [innerTab, setInnerTab]     = useState('lesson')  // 'lesson' | 'quiz'
  const [lessonContent, setLessonContent] = useState(null)
  const [quizData, setQuizData]     = useState(null)
  const [loadingInner, setLoadingInner] = useState(false)

  // Edit state
  const [editMode, setEditMode]     = useState('manual')  // 'manual' | 'llm'
  const [editText, setEditText]     = useState('')        // manual textarea
  const [llmPrompt, setLlmPrompt]   = useState('')        // llm prompt
  const [saving, setSaving]         = useState(false)
  const [regenerating, setRegenerating] = useState(false)
  const [rowStatus, setRowStatus]   = useState(null)

  async function loadLesson() {
    setLoadingInner(true)
    try {
      const data = await adminGetLesson(meta.level)
      setLessonContent(data.content)
      setEditText(data.content)
    } catch {
      setLessonContent(null)
    } finally {
      setLoadingInner(false)
    }
  }

  async function loadQuiz() {
    setLoadingInner(true)
    try {
      const data = await adminGetQuiz(meta.level)
      setQuizData(data.questions)
    } catch {
      setQuizData(null)
    } finally {
      setLoadingInner(false)
    }
  }

  function handleToggle() {
    if (!open) {
      setOpen(true)
      loadLesson()
    } else {
      setOpen(false)
    }
  }

  function handleInnerTab(t) {
    setInnerTab(t)
    if (t === 'quiz' && quizData === null) loadQuiz()
    if (t === 'lesson' && lessonContent === null) loadLesson()
  }

  async function handleSaveManual() {
    setSaving(true)
    setRowStatus({ type: 'info', msg: 'Saving lesson…' })
    try {
      await adminUpdateLesson(meta.level, editText, false)
      setLessonContent(editText)
      setRowStatus({ type: 'success', msg: 'Lesson saved.' })
    } catch (err) {
      setRowStatus({ type: 'error', msg: err.message })
    } finally {
      setSaving(false)
    }
  }

  async function handleGenerateLLM() {
    if (!llmPrompt.trim()) return
    setSaving(true)
    setRowStatus({ type: 'info', msg: 'Generating lesson via LLM… this may take a moment.' })
    try {
      const res = await adminGenerateLesson(meta.level, llmPrompt, false)
      setLessonContent(res.lesson_markdown)
      setEditText(res.lesson_markdown)
      setInnerTab('lesson')
      setRowStatus({ type: 'success', msg: 'Lesson generated and saved.' })
    } catch (err) {
      setRowStatus({ type: 'error', msg: err.message })
    } finally {
      setSaving(false)
    }
  }

  async function handleRegenerateQuiz() {
    const content = lessonContent || editText
    if (!content) return
    setRegenerating(true)
    setRowStatus({ type: 'info', msg: 'Regenerating quiz questions via LLM…' })
    try {
      await adminRegenerateQuiz(meta.level, content)
      setQuizData(null)   // will reload on tab switch
      setInnerTab('quiz')
      await loadQuiz()
      setRowStatus({ type: 'success', msg: `Quiz regenerated with new questions.` })
    } catch (err) {
      setRowStatus({ type: 'error', msg: err.message })
    } finally {
      setRegenerating(false)
    }
  }

  const statusColor = meta.lesson_exists
    ? (meta.quiz_question_count > 0 ? 'cur-dot-full' : 'cur-dot-partial')
    : 'cur-dot-empty'

  return (
    <div className={`cur-row${open ? ' cur-row-open' : ''}`}>
      {/* Level summary bar */}
      <div className="cur-row-bar" onClick={handleToggle}>
        <span className={`cur-dot ${statusColor}`} />
        <span className="cur-row-label">Level {String(meta.level).padStart(2, '0')}</span>
        <div className="cur-row-meta">
          {meta.lesson_exists
            ? <span className="cur-chip cur-chip-green">Lesson ✓</span>
            : <span className="cur-chip cur-chip-gray">No Lesson</span>}
          {meta.quiz_question_count > 0
            ? <span className="cur-chip cur-chip-blue">{meta.quiz_question_count} Questions</span>
            : <span className="cur-chip cur-chip-gray">No Quiz</span>}
        </div>
        <span className="cur-chevron">{open ? '▲' : '▼'}</span>
      </div>

      {/* Expanded panel */}
      {open && (
        <div className="cur-panel">
          {/* Inner tabs */}
          <div className="cur-tabs">
            <button className={`cur-tab${innerTab === 'lesson' ? ' active' : ''}`}
              onClick={() => handleInnerTab('lesson')}>Lesson</button>
            <button className={`cur-tab${innerTab === 'quiz' ? ' active' : ''}`}
              onClick={() => handleInnerTab('quiz')}>Quiz Questions</button>
          </div>

          {loadingInner ? (
            <div className="ap-loading" style={{ padding: '32px' }}>
              <div className="rm-spinner" /><span>Loading…</span>
            </div>
          ) : (
            <>
              {/* ── Lesson view ── */}
              {innerTab === 'lesson' && (
                <div className="cur-lesson-view">
                  {lessonContent
                    ? <pre className="cur-lesson-content">{lessonContent}</pre>
                    : <div className="ap-empty" style={{ padding: '24px' }}>No lesson generated yet.</div>
                  }
                </div>
              )}

              {/* ── Quiz view ── */}
              {innerTab === 'quiz' && (
                <div className="cur-quiz-view">
                  {quizData && quizData.length > 0 ? (
                    quizData.map((q, i) => (
                      <div key={q.id || i} className="cur-q-card">
                        <div className="cur-q-num">Q{i + 1}</div>
                        <div className="cur-q-body">
                          <div className="cur-q-text">{q.question || q.question_text}</div>
                          <div className="cur-q-options">
                            {(q.options || []).map((opt, oi) => (
                              <div key={oi}
                                className={`cur-q-opt${oi === q.correct_index ? ' correct' : ''}`}>
                                {opt}
                              </div>
                            ))}
                          </div>
                          {q.explanation && (
                            <div className="cur-q-explanation">💡 {q.explanation}</div>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="ap-empty" style={{ padding: '24px' }}>No quiz questions yet.</div>
                  )}
                </div>
              )}

              {/* ── Edit section ── */}
              <div className="cur-edit-section">
                <div className="cur-edit-header">
                  <span className="cur-edit-label">Edit Lesson</span>
                  <div className="cur-edit-mode-btns">
                    <button className={`cur-mode-btn${editMode === 'manual' ? ' active' : ''}`}
                      onClick={() => setEditMode('manual')}>Manual Edit</button>
                    <button className={`cur-mode-btn${editMode === 'llm' ? ' active' : ''}`}
                      onClick={() => setEditMode('llm')}>LLM Generate</button>
                  </div>
                </div>

                {rowStatus && (
                  <StatusBanner status={rowStatus} onClose={() => setRowStatus(null)} />
                )}

                {editMode === 'manual' ? (
                  <div className="cur-edit-manual">
                    <textarea
                      className="cur-textarea"
                      value={editText}
                      onChange={e => setEditText(e.target.value)}
                      placeholder="Enter lesson content in Markdown…"
                      rows={10}
                    />
                    <div className="cur-edit-actions">
                      <button className="ap-btn ap-btn-primary" onClick={handleSaveManual}
                        disabled={saving || !editText.trim()}>
                        {saving ? 'Saving…' : 'Save Lesson'}
                      </button>
                      <button className="ap-btn ap-btn-regen" onClick={handleRegenerateQuiz}
                        disabled={regenerating || !lessonContent}>
                        {regenerating ? 'Regenerating…' : '↻ Regenerate Quiz'}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="cur-edit-llm">
                    <textarea
                      className="cur-textarea"
                      value={llmPrompt}
                      onChange={e => setLlmPrompt(e.target.value)}
                      placeholder={`Describe what this lesson should cover for Level ${meta.level}…\n\nExample: "Cover the role of the Rajya Sabha, how bills are passed, and differences from Lok Sabha. Make it suitable for beginners."`}
                      rows={5}
                    />
                    <div className="cur-edit-actions">
                      <button className="ap-btn ap-btn-primary" onClick={handleGenerateLLM}
                        disabled={saving || !llmPrompt.trim()}>
                        {saving ? 'Generating…' : '✦ Generate Lesson'}
                      </button>
                      <button className="ap-btn ap-btn-regen" onClick={handleRegenerateQuiz}
                        disabled={regenerating || !lessonContent}>
                        {regenerating ? 'Regenerating…' : '↻ Regenerate Quiz'}
                      </button>
                      <span className="ap-hint">Lesson will be generated and saved automatically.</span>
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// CURRICULUM TAB
// ══════════════════════════════════════════════════════════════════════════
function CurriculumTab() {
  const [levels, setLevels]   = useState([])
  const [loading, setLoading] = useState(true)
  const [status, setStatus]   = useState(null)

  useEffect(() => {
    adminListLessons()
      .then(d => setLevels(d.levels || []))
      .catch(e => setStatus({ type: 'error', msg: e.message }))
      .finally(() => setLoading(false))
  }, [])

  const lessonCount = levels.filter(l => l.lesson_exists).length
  const quizCount   = levels.filter(l => l.quiz_question_count > 0).length

  return (
    <div className="ap-tab-content">
      <div className="ap-section-header">
        <div>
          <h2 className="ap-section-title">Curriculum</h2>
          <p className="ap-section-sub">
            {lessonCount}/15 lessons &nbsp;·&nbsp; {quizCount}/15 quizzes generated
          </p>
        </div>
      </div>

      <StatusBanner status={status} onClose={() => setStatus(null)} />

      {loading ? (
        <div className="ap-loading"><div className="rm-spinner" /><span>Loading curriculum…</span></div>
      ) : (
        <div className="cur-list">
          {levels.map(lvl => <LevelRow key={lvl.level} meta={lvl} />)}
        </div>
      )}
    </div>
  )
}

// ══════════════════════════════════════════════════════════════════════════
// MAIN ADMIN PANEL
// ══════════════════════════════════════════════════════════════════════════
export default function AdminPanel({ onBack }) {
  const [mainTab, setMainTab] = useState('kb')  // 'kb' | 'curriculum'

  return (
    <div className="ap-page">
      <nav className="rm-nav">
        <div className="rm-nav-logo">
          <span className="rm-nav-icon">🏛️</span>
          <span className="rm-nav-brand">Civic Lens</span>
        </div>
        <div className="rm-nav-links">
          <span className="rm-nav-link" onClick={onBack}>Dashboard</span>
          <span className="rm-nav-link active">Admin</span>
        </div>
        <div className="rm-nav-right">
          <div className="rm-avatar">A</div>
        </div>
      </nav>

      {/* Main tabs */}
      <div className="ap-main-tabs">
        <button className={`ap-main-tab${mainTab === 'kb' ? ' active' : ''}`}
          onClick={() => setMainTab('kb')}>
          📂 Knowledge Base
        </button>
        <button className={`ap-main-tab${mainTab === 'curriculum' ? ' active' : ''}`}
          onClick={() => setMainTab('curriculum')}>
          📚 Curriculum
        </button>
      </div>

      <div className="ap-body">
        {mainTab === 'kb'         && <KnowledgeBaseTab />}
        {mainTab === 'curriculum' && <CurriculumTab />}
      </div>
    </div>
  )
}
