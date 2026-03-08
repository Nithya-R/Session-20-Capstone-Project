import { useState } from 'react'
import UserGuide from './UserGuide'
import './Login.css'

export default function Login({ onStart, savedUser }) {
  const [value, setValue]     = useState(savedUser || '')
  const [error, setError]     = useState('')
  const [showGuide, setShowGuide] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    const id = value.trim().toLowerCase().replace(/\s+/g, '_')
    if (!id) { setError('Please enter a name to continue.'); return }
    onStart(id)
  }

  return (
    <div className="login">
      <div className="login-card">
        <div className="login-icon">🏛️</div>
        <h1>Civic Lens</h1>
        <p className="login-sub">Your personal civics learning guide</p>

        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="uid">What should I call you?</label>
          <input
            id="uid"
            type="text"
            placeholder="Enter your name..."
            value={value}
            onChange={e => { setValue(e.target.value); setError('') }}
            autoFocus
            autoComplete="off"
          />
          {error && <span className="login-error">{error}</span>}
          <button type="submit" className="btn-primary">
            Start Learning
          </button>
        </form>

        <button className="login-guide-btn" onClick={() => setShowGuide(true)}>
          How does it work?
        </button>

        <p className="login-note">
          Your progress is saved automatically and resumes where you left off.
        </p>
      </div>

      {showGuide && <UserGuide onClose={() => setShowGuide(false)} />}
    </div>
  )
}
