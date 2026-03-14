import { useState, useEffect, useRef, useCallback } from 'react'
import { startSession, respond, getStatus } from '../api'
import MessageBubble from './MessageBubble'
import OptionBar from './OptionBar'
import QuizReview from './QuizReview'
import './Chat.css'

// States where the agent is waiting for user to advance (not a text input state)
const OPTION_STATES = new Set([
  'placement_quiz_intro',
  'placement_quiz_result',
  'placement_quiz_review',
  'level_quiz_intro',
  'level_quiz_result',
  'complete',
])

// States where the agent presents a quiz question
const QUIZ_STATES = new Set([
  'placement_quiz_question',
  'level_quiz_question',
])

// States where the user can also type a free question (lesson)
const LESSON_STATE = 'lesson_snippet'

export default function Chat({ userId, target, onExit }) {
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [options, setOptions] = useState([])
  const [question, setQuestion] = useState(null)
  const [state, setState] = useState('start')
  const [metadata, setMetadata] = useState({})
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [textInput, setTextInput] = useState('')
  const [reviewData, setReviewData] = useState(null)
  const bottomRef = useRef(null)
  const initialized = useRef(false)

  const addAgent = (text) => setMessages(m => [...m, { role: 'agent', text }])
  const addUser  = (text) => setMessages(m => [...m, { role: 'user', text }])

  const applyResponse = useCallback((data) => {
    setState(data.state)
    setOptions(data.options || [])
    setQuestion(data.question || null)
    setDone(data.done || false)
    setMetadata(data.metadata || {})

    // If the response has embedded review data, surface it
    if (data.metadata?.review && data.metadata?.type === 'quiz_review') {
      setReviewData(data.metadata.review)
    } else if (data.state === 'placement_quiz_review' || data.state === 'level_quiz_result') {
      // keep existing review if there is one
    } else {
      setReviewData(null)
    }

    if (data.message) addAgent(data.message)
  }, [])

  const refreshStatus = useCallback(async () => {
    const s = await getStatus(userId)
    if (s) setStatus(s)
  }, [userId])

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true
    ;(async () => {
      setLoading(true)
      try {
        const data = target
          ? await startSession(userId, false, target.level, target.mode)
          : await startSession(userId, true)
        setSessionId(data.session_id)
        applyResponse(data)
        await refreshStatus()
      } catch {
        addAgent('Failed to connect. Please make sure the backend is running.')
      } finally {
        setLoading(false)
      }
    })()
  }, [userId, applyResponse, refreshStatus])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, reviewData])

  async function handleRespond(input) {
    if (!sessionId || loading || !input.trim()) return
    addUser(input)
    setTextInput('')
    setReviewData(null)
    setLoading(true)
    setOptions([])
    try {
      const data = await respond(sessionId, input)
      applyResponse(data)
      await refreshStatus()
    } catch {
      addAgent('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function handleTextSubmit(e) {
    e.preventDefault()
    handleRespond(textInput)
  }

  // In lesson state: show text input + option buttons
  // In quiz states: show only option buttons (A/B/C/D)
  // In option states: show only chips
  const isLesson = state === LESSON_STATE
  const isQuiz   = QUIZ_STATES.has(state)
  const showOptions = options.length > 0 && !done && !loading
  const showTextInput = !done && !loading && (isLesson || (!isQuiz && !OPTION_STATES.has(state)))

  // Determine what "continue" does after viewing review
  function handleReviewDone() {
    setReviewData(null)
    // Send the first non-review option as the natural continuation
    const continueOpt = options.find(o =>
      !['review answers', 'review'].includes(o.toLowerCase())
    ) || options[0]
    if (continueOpt) handleRespond(continueOpt)
  }

  return (
    <div className="chat-layout">
      {/* Header */}
      <header className="chat-header">
        <div className="chat-header-left">
          <span className="chat-logo">🏛️</span>
          <div>
            <div className="chat-title">Civic Lens</div>
            {status && (
              <div className="chat-subtitle">
                {(status.initial_exam_completed || target)
                  ? `Level ${metadata.level || target?.level || status.current_level} of 15`
                  : 'Placement Assessment'}
              </div>
            )}
          </div>
        </div>
        <div className="chat-header-right">
          {(status?.initial_exam_completed || target) && (
            <div className="level-badge">Level {metadata.level || target?.level || status.current_level}</div>
          )}
          {metadata.total_snippets > 0 && (
            <div className="snippet-badge">
              Part {metadata.snippet_index + 1}/{metadata.total_snippets}
            </div>
          )}
          <button className="btn-exit" onClick={onExit} title="Back to roadmap">←</button>
        </div>
      </header>

      {/* Progress bar */}
      {(status?.initial_exam_completed || target) && (
        <div className="progress-bar-wrap">
          <div className="progress-bar-fill"
            style={{ width: `${(((status?.current_level ?? target?.level ?? 1) - 1) / 15) * 100}%` }} />
        </div>
      )}

      {/* Messages */}
      <div className="chat-messages">
        {messages.map((m, i) => (
          <MessageBubble key={i} role={m.role} text={m.text}
            isLesson={m.role === 'agent' && state === LESSON_STATE && i === messages.length - 1} />
        ))}

        {loading && (
          <div className="chat-typing">
            <span /><span /><span />
          </div>
        )}

        {/* Quiz review panel (inline, below the last message) */}
        {reviewData && !loading && (
          <div className="review-panel">
            <QuizReview
              review={reviewData}
              onDone={handleReviewDone}
              doneLabel={
                options.find(o => !['review answers','review'].includes(o.toLowerCase()))
                || 'Continue'
              }
            />
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="chat-input-area">
        {done ? (
          <div className="chat-done">
            <span>All levels complete!</span>
            <button className="btn-primary" onClick={onExit}>View Roadmap</button>
          </div>
        ) : (
          <>
            {showOptions && !reviewData && !isLesson && (
              <OptionBar
                options={options}
                question={question}
                onSelect={handleRespond}
                disabled={loading}
              />
            )}
            {showTextInput && (
              <form onSubmit={handleTextSubmit} className="text-input-row">
                <input
                  type="text"
                  placeholder={isLesson ? 'Ask a question about this section...' : 'Type a message...'}
                  value={textInput}
                  onChange={e => setTextInput(e.target.value)}
                  autoFocus
                  disabled={loading}
                />
                <button type="submit" className="btn-send"
                  disabled={!textInput.trim() || loading}>
                  {isLesson ? 'Ask' : 'Send'}
                </button>
              </form>
            )}
            {isLesson && (
              <div className="lesson-nav">
                <button
                  className="lesson-nav-btn"
                  onClick={() => handleRespond('previous')}
                  disabled={loading || !options.includes('previous')}
                >
                  ← Previous
                </button>
                <button
                  className="lesson-nav-btn"
                  onClick={() => handleRespond('next')}
                  disabled={loading || !options.includes('next')}
                >
                  Next →
                </button>
                <button
                  className="lesson-nav-btn lesson-nav-quiz"
                  onClick={() => handleRespond('ready for quiz')}
                  disabled={loading}
                >
                  Ready for Quiz ✓
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
